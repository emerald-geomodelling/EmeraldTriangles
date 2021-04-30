import scipy.spatial.distance
import numpy as np

def distance_to_data(col, x_col="X", y_col="Y", **tri):
    XA = tri["vertices"][[x_col,y_col]].values
    filt = ~tri["vertices"][col].isna()
    XB = tri["vertices"].loc[filt][[x_col,y_col]].values
    if len(XB):
        tri["vertices"]['%s_dist' % col] = np.min(scipy.spatial.distance.cdist(XA, XB),axis=1)
    return tri
