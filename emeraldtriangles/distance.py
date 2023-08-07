#import scipy.spatial.distance
# from scipy.sparse import csr_array
from scipy.spatial import cKDTree
#import numpy as np

def distance_to_data(col, x_col="X", y_col="Y", **tri):
    """Calculate spatial distance (cartesian distance in the current
    projection) to vertices with non-NaN values in the column col and
    store the distance in the column col_dist.
    """
    filt = ~tri["vertices"][col].isna()
    XA = tri["vertices"].loc[~filt][[x_col,y_col]].values
    XB = tri["vertices"].loc[filt][[x_col,y_col]].values
    if len(XB):
        tri["vertices"].loc[filt,'%s_dist' % col] = 0.0
        d, i = cKDTree(XB).query(XA)
        tri["vertices"].loc[~filt,'%s_dist' % col] = d

    return tri
