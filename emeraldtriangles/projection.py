import numpy as np
import pyproj

def standard_reproject(projection=None, replace=False, **tri):
    tri = reproject(projection=projection, replace=replace, projection_out=3857, x_col_out="x_web", y_col_out="y_web", **tri)
    tri = reproject(projection=projection, replace=replace, projection_out=4326, x_col_out="lon", y_col_out="lat", **tri)
    return tri

def reproject(projection=None, projection_out=3857, x_col="X", y_col="Y", x_col_out="x_web", y_col_out="y_web", replace=False, **tri):
    if "meta" not in tri:
        tri["meta"] = {}
        
    if projection is None:
        projection = tri["meta"]["projection"]

    if x_col_out in ("X", "x"):
        tri["meta"]["projection"] = projection_out
        
    vertices = tri["vertices"]
    if x_col_out not in vertices.columns:
        vertices[x_col_out] = np.NaN

    if replace:
        filt = vertices.index
    else:
        filt = np.isnan(vertices[x_col_out])

    if replace or filt.max():
        projection = int(projection)
        projection_out = int(projection_out)
        #UTM convention is coordinate order Northing-Easting. CCh, 2020-06-18
        vertices.loc[filt, x_col_out], vertices.loc[filt, y_col_out]  = (
            pyproj.Transformer.from_crs(projection, projection_out, always_xy=True).transform(
                vertices.loc[filt, x_col].values, vertices.loc[filt, y_col].values))
    return tri
