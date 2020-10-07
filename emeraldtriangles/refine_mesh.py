import numpy as np
import pandas as pd
import scipy.spatial
import triangle

from . import cleanup
from . import points_in_mesh
from . import boundary

def replace_triangles(points, vertices, triangles, **tri):
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
    triangles_with_points = np.unique(points_and_triangles["triangle"])
    triangles_with_points = triangles_with_points[triangles_with_points != -1]
    mask[triangles_with_points] = 0
    
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

    res = dict(tri)
    res["vertices"] = points_and_nodes
    res["triangles"] = all_new_faces
    res["leftover"] = leftover
    return res

def supplant_triangles(existing_boundary=False, **tri):
    tri = boundary.mesh_boundary(**tri)
    if not existing_boundary:
        tri = boundary.vertices_boundary(**tri)

    trivertices = tri["vertices"][["X", "Y"]]

    res = dict(tri)
    process_tri = {"vertices": trivertices.values}
    if "segments" in tri:
        process_tri["segments"] = tri["segments"][[0, 1]].values
    if "holes" in tri:
        process_tri["holes"] = tri["holes"].values
    if "triangles" in tri and len(tri["triangles"]):
        triangles = tri["triangles"]
        holes = (trivertices.loc[triangles[0]].values
                 + trivertices.loc[triangles[1]].values
                 + trivertices.loc[triangles[2]].values) / 3
        if "holes" in process_tri:
            holes = np.append(process_tri["holes"], holes)
        process_tri["holes"] = holes

    if existing_boundary:
        xmin = tri["vertices"]["X"].min()
        ymin = tri["vertices"]["Y"].min()
        xmax = tri["vertices"]["X"].max()
        ymax = tri["vertices"]["Y"].max()

        process_tri["vertices"] = np.append(
            process_tri["vertices"],
            np.array([[xmin-20,ymin-20], [xmin-20, ymax+20], [xmax+20, ymax+20], [xmax+20, ymin-20]]),
            axis=0)
        
        holes = np.array([[xmin-10, ymin-10]])
        if "holes" in process_tri:
            holes = np.append(process_tri["holes"], holes)
        process_tri["holes"] = holes

    res.update(triangle.triangulate(process_tri, 'p'))
    if "triangles" in tri:
        triangles = tri["triangles"]
        res["triangles"] = triangles.append(triangles.iloc[0:0].append(pd.DataFrame(res["triangles"])))
    res["vertices"] = tri["vertices"]
    #res["vertices"] = pd.DataFrame(res["vertices"], columns=("X", "Y"))
    return res
