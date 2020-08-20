import numpy as np
import pandas as pd
import scipy.spatial

from . import cleanup
from . import points_in_mesh

def replace_triangle_faces(points, triangle_nodes, triangle_faces):
    triangle_nodes, triangle_faces = cleanup.reindex(triangle_nodes, triangle_faces)
    points_start = len(triangle_nodes)
    points_and_nodes = triangle_nodes.append(points).reset_index(drop=True)

    P = points[["X", "Y"]].values
    A = triangle_nodes.loc[triangle_faces[0].values][["X", "Y"]].values
    B = triangle_nodes.loc[triangle_faces[1].values][["X", "Y"]].values
    C = triangle_nodes.loc[triangle_faces[2].values][["X", "Y"]].values
    
    points_and_triangles = points_in_mesh.points_in_triangles(points, triangle_nodes, triangle_faces)
    
    leftover = None
    all_new_faces = []
    for triangle, group in points_and_triangles.groupby("triangle"):
        if triangle == -1:
            leftover = group["point"] + points_start
            continue
        triangulation_points = np.append(P[group["point"]],
                                         np.array((A[triangle],
                                                   B[triangle],
                                                   C[triangle])), axis=0)

        # Normalization to get around floating point precision problem in scipy.spatial.Delaunay
        triangulation_points[:,0] -= triangulation_points[:,0].mean()
        triangulation_points[:,1] -= triangulation_points[:,1].mean()

        triangulation = scipy.spatial.Delaunay(triangulation_points, qhull_options="QJ")

        triangulation_point_indices = np.append((group["point"] + points_start),
                                                np.array((triangle_faces.loc[triangle][0],
                                                          triangle_faces.loc[triangle][1],
                                                          triangle_faces.loc[triangle][2])))

        new_faces = pd.concat([triangle_faces.iloc[triangle:triangle+1]]*len(triangulation.simplices))
        new_faces[0] = triangulation_point_indices[triangulation.simplices[:,0]]
        new_faces[1] = triangulation_point_indices[triangulation.simplices[:,1]]
        new_faces[2] = triangulation_point_indices[triangulation.simplices[:,2]]

        all_new_faces.append(new_faces)

    mask = np.zeros(triangle_faces.index.shape, dtype="bool")
    mask[:] = 1
    mask[np.unique(points_and_triangles["triangle"])] = 0
    
    return points_and_nodes, triangle_faces[mask].append(pd.concat(all_new_faces)), leftover
