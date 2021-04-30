import numpy as np
import skgstat

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
    
    if col not in variograms.index:
        variogram = skgstat.Variogram(
            vertices.loc[existing, ["X", "Y"]].values, vertices.loc[existing, col].values, **variogram_args
        ).describe()
        variograms.loc[col] = {"variogram": {"type": "skgstat.Variogram", "values": variogram}}
    else:
        variogram = variograms.loc[col, "variogram"]["values"]

    kriging = skgstat.OrdinaryKriging(
        variogram,
        coordinates=vertices.loc[existing, ["X", "Y"]].values,
        values=vertices.loc[existing, col].values,
        **kriging_args)

    vertices.loc[~existing, col] = kriging.transform(vertices.loc[~existing, "X"].values, vertices.loc[~existing, "Y"].values)
    vertices.loc[~existing, col + '_kriging_uncertainty'] = kriging.sigma

    if "meta" not in tri: tri["meta"] = {}
    if "columns" not in tri["meta"]: tri["meta"]["columns"] = {}
    if col not in tri["meta"]["columns"]: tri["meta"]["columns"][col] = {}

    tri["meta"]["columns"][col].update({"variogram": variogram_args, "kriging": kriging_args})
    
    return tri
