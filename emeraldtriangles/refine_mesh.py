import numpy as np
import pandas as pd
import scipy.spatial
import triangle

from . import cleanup
from . import points_in_mesh
from . import boundary

def replace_triangle_faces(points, triangle_nodes, triangle_faces):
    triangle_nodes, triangle_faces = cleanup.reindex(triangle_nodes, triangle_faces)
    points_start = len(triangle_nodes)
    points_and_nodes = triangle_nodes.append(points).reset_index(drop=True)

    P = points[["X", "Y"]].values
    A = triangle_nodes.loc[triangle_faces[0].values][["X", "Y"]].values
    B = triangle_nodes.loc[triangle_faces[1].values][["X", "Y"]].values
    C = triangle_nodes.loc[triangle_faces[2].values][["X", "Y"]].values
    
    points_and_triangles = points_in_mesh.points_in_triangles(points, triangle_nodes, triangle_faces)

    mask = np.zeros(triangle_faces.index.shape, dtype="bool")
    mask[:] = 1
    mask[np.unique(points_and_triangles["triangle"])] = 0
    
    leftover = None
    all_new_faces = triangle_faces[mask].copy()
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
                                                np.array((triangle_faces[0].loc[triangle],
                                                          triangle_faces[1].loc[triangle],
                                                          triangle_faces[2].loc[triangle])))
        
        new_faces = triangle_faces.iloc[pd.Index([triangle]).repeat(len(triangulation.simplices))].copy()
        new_faces[0] = triangulation_point_indices[triangulation.simplices[:,0]]
        new_faces[1] = triangulation_point_indices[triangulation.simplices[:,1]]
        new_faces[2] = triangulation_point_indices[triangulation.simplices[:,2]]        
        all_new_faces = all_new_faces.append(new_faces)

    return points_and_nodes, all_new_faces, leftover

def supplant_triangle_faces(triangle_nodes, triangle_faces):
    border_sides = boundary.mesh_boundary(triangle_faces)

    tri = {
        "vertices": triangle_nodes,
        "segments": border_sides[[0, 1]].append(pd.DataFrame(
            scipy.spatial.ConvexHull(triangle_nodes).simplices, columns=[0,1])),
        "holes": (triangle_nodes.loc[triangle_faces[0]].values
                  + triangle_nodes.loc[triangle_faces[1]].values
                  + triangle_nodes.loc[triangle_faces[2]].values) / 3
    }
    res = triangle.triangulate(tri, 'p')

    res["triangles"] = triangle_faces.iloc[0:0].append(pd.DataFrame(res["triangles"]))
    res["vertices"] = triangle_nodes
    return res
