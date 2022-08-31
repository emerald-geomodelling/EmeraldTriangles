import numpy as np
import pandas as pd

from scipy.sparse import coo_array

def point_in_triangle(P, A,B,C):   
    v0 = C - A
    v1 = B - A
    v2 = P - A
    dot00 = np.einsum('ij,ij->i', v0, v0)
    dot01 = np.einsum('ij,ij->i', v0, v1)
    dot02 = np.einsum('ij,ij->i', v0, v2)
    dot11 = np.einsum('ij,ij->i', v1, v1)
    dot12 = np.einsum('ij,ij->i', v1, v2)
    invDenom = 1 / (dot00 * dot11 - dot01 * dot01)
    u = (dot11 * dot02 - dot01 * dot12) * invDenom
    v = (dot00 * dot12 - dot01 * dot02) * invDenom
    return (u >= 0) & (v >= 0) & (u + v < 1)

def points_in_triangle(PS, A,B,C, batch_size = 1000):
    if len(A)==0:
        return np.array([])

    mi = np.minimum(np.minimum(A, B), C)
    ma = np.maximum(np.maximum(A, B), C)

    batch_breaks = np.arange(0,PS.shape[0],batch_size)
    if batch_breaks[-1] !=PS.shape[0]: batch_breaks = np.concatenate((batch_breaks, [PS.shape[0]]))

    results = []
    for idx in range(len(batch_breaks)-1):
        idx_start = batch_breaks[idx]
        idx_end   = batch_breaks[idx+1]

        n_rows = idx_end  - idx_start

        PS_broadcast = np.swapaxes(np.tile(np.atleast_3d(PS[idx_start:idx_end,:]), (1, 1,  A.shape[0])),1,2)
        mi_broadcast = np.moveaxis(np.tile(np.atleast_3d(mi), (1, 1, n_rows)), 2, 0)
        ma_broadcast = np.moveaxis(np.tile(np.atleast_3d(ma), (1, 1, n_rows)), 2, 0)

        filtered_by_bbox = np.all(PS_broadcast >= mi_broadcast, axis=2) & np.all(PS_broadcast <= ma_broadcast, axis=2)
        point_tri_pairs_in_bbox = np.argwhere(filtered_by_bbox)
        point_tri_pairs_in_bbox[:,0] += idx_start

        P_sub = PS[point_tri_pairs_in_bbox[:, 0],:]
        A_sub =  A[point_tri_pairs_in_bbox[:, 1], :]
        B_sub =  B[point_tri_pairs_in_bbox[:, 1], :]
        C_sub =  C[point_tri_pairs_in_bbox[:, 1], :]
        test_result = point_in_triangle(P_sub, A_sub, B_sub, C_sub)

        test_result_df  = pd.DataFrame(np.column_stack((point_tri_pairs_in_bbox,test_result)), columns=['point','triangle','test_result'])
        test_result_df = test_result_df[test_result_df.test_result > 0].drop(columns='test_result')

        results.append(test_result_df)

    results_concat = pd.concat(results, axis=0)

    return results_concat.groupby('point').agg(np.min)
    # filtered_by_bbox_sparse = coo_array(filtered_by_bbox)
    # for P in PS:
    #     bboxfilter = np.where(np.all(P >= mi, axis=1) & np.all(P <= ma, axis=1))[0]
    #     a, b, c = A[bboxfilter], B[bboxfilter], C[bboxfilter]
    #     matches = point_in_triangle(P, a,b,c)
    #     yield bboxfilter[matches]
        

def points_in_triangles(points, vertices, triangles, **kw):
    """
    points: DataFrame with columns X and Y
    vertices: DataFrame with columns X and Y
    triangles: DataFrame with columns 0, 1, 2 with indices into vertices
    Returns:
    DataFrame with columns point and triangle with indices into points and triangles respectively.
    """
    P = points[["X", "Y"]].values
    A = vertices.loc[triangles[0].values][["X", "Y"]].values
    B = vertices.loc[triangles[1].values][["X", "Y"]].values
    C = vertices.loc[triangles[2].values][["X", "Y"]].values

    formatted_result = pd.concat((points, points_in_triangle(P, A, B, C)), axis=1)['triangle']
    formatted_result = formatted_result.fillna(-1).astype(np.int64).reset_index().rename(columns={'index':'point'})

    return formatted_result
