import numpy as np
import pandas as pd

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

def points_in_triangle(PS, A,B,C):
    mi = np.minimum(np.minimum(A, B), C)
    ma = np.maximum(np.maximum(A, B), C)

    for P in PS:
        bboxfilter = np.where(np.all(P >= mi, axis=1) & np.all(P <= ma, axis=1))[0]
        a, b, c = A[bboxfilter], B[bboxfilter], C[bboxfilter]        
        matches = point_in_triangle(P, a,b,c)
        yield bboxfilter[matches]
        

def points_in_triangles(points, triangle_nodes, triangle_faces):
    """
    points: DataFrame with columns X and Y
    triangle_nodes: DataFrame with columns X and Y
    triangle_faces: DataFrame with columns 0, 1, 2 with indices into triangle_nodes
    Returns:
    DataFrame with columns point and triangle with indices into points and triangle_faces respectively.
    """
    P = points[["X", "Y"]].values
    A = triangle_nodes.loc[triangle_faces[0].values][["X", "Y"]].values
    B = triangle_nodes.loc[triangle_faces[1].values][["X", "Y"]].values
    C = triangle_nodes.loc[triangle_faces[2].values][["X", "Y"]].values

    points_and_triangles = pd.DataFrame([
        (idx, matches[0] if len(matches) > 0 else -1)
        for idx, matches in enumerate(points_in_triangle(P, A, B, C))])
    points_and_triangles.columns = ["point", "triangle"]
    return points_and_triangles
