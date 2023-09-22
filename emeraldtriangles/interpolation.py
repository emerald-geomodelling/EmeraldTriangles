import numpy as np
import skgstat
import logging
from .points_in_mesh import points_in_triangles
import scipy.interpolate
from copy import deepcopy

logger = logging.getLogger(__name__)



def interpolate_arrays(param_name, variograms, positions, values, new_positions, variogram_args={}, kriging_args={}):
    """Helper function for interpolate() that generates, stores and
    uses variograms the same way, but uses data from explicitly
    supplied arrays for both generating the variogram and for kriging.

    Parameters
    -----------
    
    param_name : str
      Name of variogram to use
    variograms : str
      Dataframe with a column "variogram" (dtype object) containing
      variogram descriptions and an index containing variogram names.
      This dataframe can be empty (or not have a row for the requested
      name), and if so will be populated with a new variogram.
    positions : np.ndarray[N,2]
      Positions to generate variogram for.
    values : np.ndarray[N]
      Values to generate variogram for.
    new_positions : np.ndarray[N,2]
      Positions to interpolate (krige) values to.
    variogram_args : dict
      Extra arguments to skgstat.Variogram
    kriging_args : dict
      Extra arguments to skgstat.OrdinaryKriging
    """
    kriging_args_copy = deepcopy(kriging_args)
    method = kriging_args_copy.pop("method", "kriging")
    logger.debug("Interpolating %s using %s..." % (param_name, method))

    if np.isnan(values).min():
        return np.full(len(new_positions), np.nan), np.full(len(new_positions), np.nan)
    elif np.nanmin(values) == np.nanmax(values):
        return np.full(len(new_positions), np.nanmax(values)), np.full(len(new_positions), 0)

    if method == "kriging":
        return interpolate_arrays_kriging(param_name, variograms, positions, values, new_positions, variogram_args, kriging_args_copy)
    elif method == "linear":
        res = scipy.interpolate.griddata(positions, values, new_positions)
        # Placeholder variance of np.nan everywhere
        return res, res * np.nan
    elif method == "cubic":
        res = scipy.interpolate.griddata(positions, values, new_positions, method="cubic")
        # Placeholder variance of np.nan everywhere
        return res, res * np.nan
    elif method == "spline":
        res = scipy.interpolate.SmoothBivariateSpline(
            positions[:,0], positions[:,1], values, s=0
        )(
            new_positions[:,0], new_positions[:,1], grid=False)
        # Placeholder variance of np.nan everywhere
        return res, res * np.nan
    else:
        raise NotImplementedError("Unknown interpolation method %s..." % (method,))

 
def interpolate_arrays_kriging(param_name, variograms, positions, values, new_positions, variogram_args={}, kriging_args={}):
    if param_name not in variograms.index:
        logger.debug(f"...Generating variogram for  {param_name}...")
        variogram = skgstat.Variogram(positions, values, **variogram_args)
        desc = variogram.describe()
        desc["experimental"] = list(variogram.experimental)
        desc["bins"] = list(variogram.bins)        
        variograms.loc[param_name] = {"variogram": {"type": "skgstat.Variogram", "values": desc}}
    else:
        variogram = variograms.loc[param_name, "variogram"]["values"]
        
    kriging = skgstat.OrdinaryKriging(
        variogram,
        coordinates=positions,
        values=values,
        **kriging_args)

    values = kriging.transform(new_positions[:,0], new_positions[:,1])
    variance = kriging.sigma
    return values, variance

def interpolate(col, variograms, variogram_args={}, kriging_args={}, **tri):
    """Interpolate vertice column data using scikit-gstat. Data is
    interpolated from rows with non-NaN values to rows with NaN
    values.
    
    Parameters
    -----------

    col : str
      Name of column to interpolate
    variograms : str
      Dataframe with a column "variogram" (dtype object) containing
      variogram descriptions and an index containing column names.
      This dataframe can be empty (or not have a row for the requested
      column), and if so will be populated with a new variogram.
    variogram_args : dict
      Extra arguments to skgstat.Variogram
    kriging_args : dict
      Extra arguments to skgstat.OrdinaryKriging
    **tri
      Triangulation to interpolate data over
    """
    vertices = tri["vertices"]

    existing = ~np.isnan(vertices[col])

    if existing.sum() > 0 and (~existing).sum() > 0:
        if "variogram" not in variograms.columns:
            variograms["variogram"] = None

        values, variance = interpolate_arrays(
            col,
            variograms,
            vertices.loc[existing, ["X", "Y"]].values,
            vertices.loc[existing, col].values,
            vertices.loc[~existing, ["X", "Y"]].values,
            variogram_args,
            kriging_args)

        vertices.loc[~existing, col] = values
        vertices.loc[~existing, col + '_kriging_uncertainty'] = variance

        if "meta" not in tri: tri["meta"] = {}
        if "columns" not in tri["meta"]: tri["meta"]["columns"] = {}
        if col not in tri["meta"]["columns"]: tri["meta"]["columns"][col] = {}

        tri["meta"]["columns"][col].update({"variogram": variogram_args, "kriging": kriging_args})
    
    return tri


def barycentric_interpolation(xt,yt,zt, triangles, xp,yp):

    X_tri = xt[triangles]
    Y_tri = yt[triangles]
    Z_tri = zt[triangles]

    # compute Barycentric weights of each vertex for every query point, then compute Z
    Y1 = Y_tri[:, 1]
    Y2 = Y_tri[:, 2]
    Y3 = Y_tri[:, 0]

    X1 = X_tri[:, 1]
    X2 = X_tri[:, 2]
    X3 = X_tri[:, 0]

    Px = xp
    Py = yp

    wv1 = ((Y2 - Y3) * (Px - X3) + (X3 - X2) * (Py - Y3)) / ((Y2 - Y3) * (X1 - X3) + (X3 - X2) * (Y1 - Y3))
    wv2 = ((Y3 - Y1) * (Px - X3) + (X1 - X3) * (Py - Y3)) / ((Y2 - Y3) * (X1 - X3) + (X3 - X2) * (Y1 - Y3))
    wv3 = 1 - wv2 - wv1

    Pz = wv1 * Z_tri[:, 1] + wv2 * Z_tri[:, 2] + wv3 * Z_tri[:, 0]
    return Pz

def sample_from_triangulation(col, col_output = None, **tri):
    """Interpolate vertices column data using barycentric interpolation.
    In other words, sample values from the existing triangles at points locations.

    Point not overlapping with the triangles get set to 0

    Parameters
    -----------

    col : str
      Name of column on vertices to interpolate
    col_output : str
      Name of column on points where output will be stored. By default, set to same as col
    **tri
      Triangulation to interpolate data over
    """

    if col_output is None:
        col_output = col

    points_and_triangles = points_in_triangles(**tri)

    mask_points_overlap = points_and_triangles["triangle"] != -1

    points_masked = tri['points'].iloc[points_and_triangles.loc[mask_points_overlap, 'point']]
    points_and_triangles_masked = points_and_triangles[mask_points_overlap]


    tri_vert = tri['triangles'].iloc[points_and_triangles_masked.triangle.values, :]
    tri_vert_np = tri_vert.loc[:, [0, 1, 2]].values

    xt = tri['vertices'].X.values
    yt = tri['vertices'].Y.values
    zt = tri['vertices'].loc[:, col].values

    xp = points_masked.X.values
    yp = points_masked.Y.values

    zp = barycentric_interpolation(xt, yt, zt, tri_vert_np, xp, yp)

    tri['points'].loc[points_masked.index, col_output] = zp


    return tri
