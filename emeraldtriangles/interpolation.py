import numpy as np
import skgstat

def interpolate(col, variograms, variogram_args={}, kriging_args={}, **tri):
    vertices = tri["vertices"]

    existing = ~np.isnan(vertices[col])

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
