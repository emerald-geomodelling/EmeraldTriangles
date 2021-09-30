import numpy as np
import pandas as pd

def clean_triangles(points, faces, decimals = 10, offset=False):
    points = points.copy()
    faces = faces.copy()
    if decimals is None:
        points["Xp"] = points["X"]
        points["Yp"] = points["Y"]
    else:
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

    points = points.drop(columns=["Xp", "Yp"])
    
    # Remove z-size triangles
    faces = faces[(faces[0] != faces[1]) & (faces[0] != faces[2]) & (faces[1] != faces[2])]
    
    return points, faces

def reindex(points, faces):
    "Reindex points and faces so that they both have a natural/default index"
    
    faces = faces.reset_index(drop=True)
    points = points.rename_axis(index="index").reset_index()
    replacements = points.rename(columns={"index": "old"}).reset_index().rename(columns={"index": "new"}).set_index("old")["new"]
    faces[0] = replacements.loc[faces[0]].values
    faces[1] = replacements.loc[faces[1]].values
    faces[2] = replacements.loc[faces[2]].values
    
    points = points.drop(columns=["index"])
    return points, faces

def append_nodes(points, vertices, triangles):
    vertices, triangles = reindex(vertices, triangles)
    points_start = len(vertices)
    points_and_nodes = vertices.append(points).reset_index(drop=True)
    return points_and_nodes, triangles, points_start

def merge_tins(a, b):
    points_and_nodes, triangles, points_start = append_nodes(
        b["vertices"], a["vertices"], a["triangles"])
    res = dict(a)
    res["vertices"] = points_and_nodes
    b_triangles = b["triangles"].copy()
    b_triangles[0] += points_start
    b_triangles[1] += points_start
    b_triangles[2] += points_start
    res["triangles"] = triangles.append(b_triangles).reset_index()
    return res

def remove_overlapping_points_vertices(points, vertices, keep='points'):
    p_xy = points.loc[:, ['X', 'Y']]
    v_xy = vertices.loc[:, ['X', 'Y']]

    merged_points = pd.merge(p_xy, v_xy, on=['X', 'Y'], how='left', indicator='indicator')
    merged_points['duplicated_flag'] = np.where(merged_points.loc[:, 'indicator'] == 'both', True, False)

    if keep in ('points','p'):
        merged_vertices = pd.merge(v_xy, points, on=['X', 'Y'], how='left', indicator='indicator')
        merged_vertices['duplicated_flag'] = np.where(merged_vertices.loc[:, 'indicator'] == 'both', True, False)

    elif keep in ('vertices','v'):

        points = points.loc[~ merged_points['duplicated_flag'].values]
    else:
        ValueError('value of "keep" parameter set to %s, but must be one of ("vertices","points","v","p")'%(str(keep)))

    return points, vertices
