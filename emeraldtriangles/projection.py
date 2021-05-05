import numpy as np
import pyproj

def standard_reproject(projection=None, replace=False, **tri):
    """Reproject the coordinates of a triangulation to web mercator
    and lat/lon and store the results in the columns x_web/y_web and
    lon/lat respectively.
    """
    tri = reproject(projection=projection, replace=replace, projection_out=3857, x_col_out="x_web", y_col_out="y_web", **tri)
    tri = reproject(projection=projection, replace=replace, projection_out=4326, x_col_out="lon", y_col_out="lat", **tri)
    return tri

def reproject(projection=None, projection_out=None, x_col="X", y_col="Y", x_col_out="X", y_col_out="Y", replace=False, **tri):
    """Reproject a triangulation or add additional columns with a
    secondary projection. Projections are specified as epsg codes.
    
    Parameters
    projection : int
      The current projection (crs) of x_col and y_col. Defaults to tri["meta"]["projection"]
    projection_out : int
      The projection (crs) to reproject the coordinates to.
    x_col : str
      The x coordinate column to reproject from. Defaults to "X".
    y_col : str
      The y coordinate column to reproject from. Defaults to "Y".
    x_col_out : str
      The x coordinate column to reproject to. Defaults to "X".
    y_col_out : str
      The x coordinate column to reproject to. Defaults to "Y".
    replace : bool
      Replace existing values in the output columns. If false,
      reprojection is only done on rows with NaN in the output
      columns.
    **tri
      Triangulation to reproject
    """
    if "meta" not in tri:
        tri["meta"] = {}
        
    if projection is None:
        projection = tri["meta"]["projection"]

    if x_col_out in ("X", "x"):
        tri["meta"]["projection"] = projection_out

    if x_col == x_col_out:
        replace = True
        
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
            pyproj.Transformer.from_crs(int(projection), int(projection_out), always_xy=True).transform(
                vertices.loc[filt, x_col].values, vertices.loc[filt, y_col].values))
    return tri
