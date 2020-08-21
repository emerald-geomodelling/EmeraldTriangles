import numpy as np
import pandas as pd
import scipy.spatial
import triangle

from . import cleanup
from . import points_in_mesh
from . import boundary

def replace_triangles(points, vertices, triangles):
    vertices, triangles = cleanup.reindex(vertices, triangles)
    points_start = len(vertices)
    points_and_nodes = vertices.append(points).reset_index(drop=True)

    P = points[["X", "Y"]].values
    A = vertices.loc[triangles[0].values][["X", "Y"]].values
    B = vertices.loc[triangles[1].values][["X", "Y"]].values
    C = vertices.loc[triangles[2].values][["X", "Y"]].values
    
    points_and_triangles = points_in_mesh.points_in_triangles(points, vertices, triangles)

    mask = np.zeros(triangles.index.shape, dtype="bool")
    mask[:] = 1
    mask[np.unique(points_and_triangles["triangle"])] = 0
    
    leftover = None
    all_new_faces = triangles[mask].copy()
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
                                                np.array((triangles[0].loc[triangle],
                                                          triangles[1].loc[triangle],
                                                          triangles[2].loc[triangle])))
        
        new_faces = triangles.iloc[pd.Index([triangle]).repeat(len(triangulation.simplices))].copy()
        new_faces[0] = triangulation_point_indices[triangulation.simplices[:,0]]
        new_faces[1] = triangulation_point_indices[triangulation.simplices[:,1]]
        new_faces[2] = triangulation_point_indices[triangulation.simplices[:,2]]        
        all_new_faces = all_new_faces.append(new_faces)

    return points_and_nodes, all_new_faces, leftover

def supplant_triangles(vertices, triangles):
    border_sides = boundary.mesh_boundary(triangles)

    tri = {
        "vertices": vertices,
        "segments": border_sides[[0, 1]].append(pd.DataFrame(
            scipy.spatial.ConvexHull(vertices).simplices, columns=[0,1])),
        "holes": (vertices.loc[triangles[0]].values
                  + vertices.loc[triangles[1]].values
                  + vertices.loc[triangles[2]].values) / 3
    }
    res = triangle.triangulate(tri, 'p')

    res["triangles"] = triangles.iloc[0:0].append(pd.DataFrame(res["triangles"]))
    res["vertices"] = vertices
    return res
