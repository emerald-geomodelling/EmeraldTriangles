import numpy as np
import rasterio
import pyproj

def interpolate_from_raster(raster, col="topo", projection=None, **tri):
    """Sample vertice data from a raster image. Coordinate reprojection is
    done using the crs of the raster and the supplied projection or
    tri["meta"]["projection"].

    Parameters
    -----------
    raster : rasterio.io.DatasetReader
      Raster to sample from.
    col : str
      Name of column to store sampled values in.
    projection : int
      CRS for the X and Y columns of the triangulation, optional.
    """

    if projection is None:
        projection = tri["meta"]["projection"]
    #UTM convention is coordinate order Northing-Easting. CCh, 2020-06-18
    xy = np.column_stack(
        pyproj.Transformer.from_crs(int(projection), raster.crs.to_epsg(), always_xy=True
        ).transform(tri["vertices"]["X"], tri["vertices"]["Y"]))
    
    filt = (  (xy[:,0] >= raster.bounds.left) & (xy[:,0] <= raster.bounds.right)
            & (xy[:,1] >= raster.bounds.bottom) & (xy[:,1] <= raster.bounds.top))
    filt = tri["vertices"].index[filt].values

    sampled = np.array(list(raster.sample(xy[filt,:])))[:,0]
    datafilt = ~np.isin(sampled, raster.get_nodatavals())

    filt = filt[datafilt]
    sampled = sampled[datafilt]

    tri["vertices"].loc[filt, col] = sampled
    return tri
