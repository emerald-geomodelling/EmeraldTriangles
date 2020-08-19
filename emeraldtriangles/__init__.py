import numpy as np
import pandas as pd
import scipy.spatial

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

def replace_triangle_faces(points, triangle_nodes, triangle_faces):
    points_start = len(triangle_nodes)
    points_and_nodes = triangle_nodes.append(points)

    P = points[["X", "Y"]].values
    A = triangle_nodes.loc[triangle_faces[0].values][["X", "Y"]].values
    B = triangle_nodes.loc[triangle_faces[1].values][["X", "Y"]].values
    C = triangle_nodes.loc[triangle_faces[2].values][["X", "Y"]].values
    
    points_and_triangles = points_in_triangles(points, triangle_nodes, triangle_faces)
    points_and_triangles = points_and_triangles[points_and_triangles["triangle"] != -1]
    
    leftover = None
    all_new_faces = []
    for triangle, group in points_and_triangles.groupby("triangle"):
        if triangle == -1:
            leftover = group
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

        new_faces = np.zeros(triangulation.simplices.shape)
        new_faces[:,0] = triangulation_point_indices[triangulation.simplices[:,0]]
        new_faces[:,1] = triangulation_point_indices[triangulation.simplices[:,1]]
        new_faces[:,2] = triangulation_point_indices[triangulation.simplices[:,2]]

        all_new_faces.append(new_faces)

    mask = np.zeros(triangle_faces.index.shape, dtype="bool")
    mask[:] = 1
    mask[np.unique(points_and_triangles["triangle"])] = 0
    
    return points_and_nodes, triangle_faces[mask].append(pd.DataFrame(np.concatenate(all_new_faces))), leftover

def clean_triangles(points, faces, decimals = 10, offset=False):
    points = points.copy()
    faces = faces.copy()
    points["Xp"] = np.floor(points["X"]* decimals + (0.5 if offset else 0))
    points["Yp"] = np.floor(points["Y"]* decimals + (0.5 if offset else 0))

    replacements = points.join(points.reset_index().groupby(["Xp", "Yp"])["index"].min().rename("new"), on=("Xp", "Yp"))["new"]

    # Merge points that are close to each other
    faces[0] = replacements.loc[faces[0]].values
    faces[1] = replacements.loc[faces[1]].values
    faces[2] = replacements.loc[faces[2]].values

    replacements = replacements.reset_index()
    keep = replacements[replacements["index"] == replacements["new"]]
    
    points = points.loc[keep["new"]]
    
    # Rename so that points has a natural index (no gaps)
    points, faces = reindex(points, faces)
    
    # Remove z-size triangles
    faces = faces[(faces[0] != faces[1]) & (faces[0] != faces[2]) & (faces[1] != faces[2])]
    
    return points, faces

def reindex(points, faces):
    "Reindex points and faces so that they both have a natural/default index"
    
    faces = faces.reset_index(drop=True)
    points = points.reset_index()
    replacements = points.rename(columns={"index": "old"}).reset_index().rename(columns={"index": "new"}).set_index("old")["new"]
    faces[0] = replacements.loc[faces[0]].values
    faces[1] = replacements.loc[faces[1]].values
    faces[2] = replacements.loc[faces[2]].values
    
    points = points.drop(columns=["index"])
    return points, faces

def mesh_boundary(faces):
    sides = faces[[0, 1]].assign(face=faces.index).append(
        faces[[1, 2]].assign(face=faces.index).rename(columns={1:0, 2:1})).append(
        faces[[0, 2]].assign(face=faces.index).rename(columns={2:1})).reset_index(drop=True)


    sides.loc[sides[0] > sides[1], [1, 0]] = sides.loc[sides[0] > sides[1], [0, 1]].rename(columns={0:1, 1:0})

    sides = sides.sort_values([0, 1])

    border_sides = sides.drop_duplicates([0, 1], keep=False, ignore_index=True)
    
    return border_sides

def mesh_boundary_mark_rings(border_sides):
    border_sides = border_sides.copy()
    
    border_sides["ring"] = np.NaN
    border_sides["pos"] = np.NaN
    ring = 0

    while True:
        remaining = border_sides[np.isnan(border_sides["ring"])]
        if not len(remaining): break

        current = remaining.index[0]

        ring += 1
        pos = 0
        border_sides.loc[current, "ring"] = ring
        border_sides.loc[current, "pos"] = pos

        right = border_sides.loc[current, 1]


        while True:
            nxt = border_sides[(border_sides[0] == right) & (border_sides.index != current)]
            prv = border_sides[(border_sides[1] == right) & (border_sides.index != current)]
            if len(nxt):
                current = nxt.index[0]
                right = border_sides.loc[current, 1]
            elif len(prv):
                current = prv.index[0]
                right = border_sides.loc[current, 0]
            else:
                break


            if not np.isnan(border_sides.loc[current, "ring"]):
                # Merge an existing ring
                existing = border_sides.loc[current, "ring"]

                border_sides.loc[border_sides["ring"] == existing, "pos"] += pos
                border_sides.loc[border_sides["ring"] == existing, "ring"] = ring
                break

            pos += 1
            border_sides.loc[current, "ring"] = ring
            border_sides.loc[current, "pos"] = pos
            
    return border_sides

def ring_marked_mesh_boundary_to_pointlists(border_sides):
    res = {}
    for ring in border_sides["ring"].unique():
        ringborders = border_sides[border_sides["ring"] == ring]
    
    res[int(ring)] = ringborders[[0, "pos"]].rename(columns={0:"point"}).append(
        ringborders[[1, "pos"]].rename(columns={1:"point"})
    ).sort_values("pos").drop_duplicates("pos")["point"].values
    
    return res
