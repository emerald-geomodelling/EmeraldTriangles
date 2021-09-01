import numpy as np
import skgstat
import logging

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

    if np.isnan(values).min():
        return np.full(len(new_positions), np.nan), np.full(len(new_positions), np.nan)
    elif np.nanmin(values) == np.nanmax(values):
        return np.full(len(new_positions), np.nanmax(values)), np.full(len(new_positions), 0)
        
    if param_name not in variograms.index:
        logger.debug("...Generating variogram for %s..." % param_name)
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
