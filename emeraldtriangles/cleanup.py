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

    index_name = 'index'
    if points.index.name is not None:
        index_name = points.index.name

    replacements = points.join(points.reset_index().groupby(["Xp", "Yp"])[index_name].min().rename("new"), on=("Xp", "Yp"))["new"]

    # Merge points that are close to each other
    faces[0] = replacements.loc[faces[0]].values
    faces[1] = replacements.loc[faces[1]].values
    faces[2] = replacements.loc[faces[2]].values

    replacements = replacements.reset_index()
    keep = replacements[replacements[index_name] == replacements["new"]]
    
    points = points.loc[keep["new"]]
    
    # Rename so that points has a natural index (no gaps)
    points, faces = reindex(points, faces)

    points = points.drop(columns=["Xp", "Yp"])
    
    # Remove z-size triangles
    faces = faces[(faces[0] != faces[1]) & (faces[0] != faces[2]) & (faces[1] != faces[2])]
    
    return points, faces

def reindex(points, faces):
    "Reindex points and faces so that they both have a natural/default index"
    index_name = points.index.name
    faces = faces.reset_index(drop=True)
    points = points.rename_axis(index="index").reset_index()
    replacements = points.rename(columns={"index": "old"}).reset_index().rename(columns={"index": "new"}).set_index("old")["new"]
    faces[0] = replacements.loc[faces[0]].values
    faces[1] = replacements.loc[faces[1]].values
    faces[2] = replacements.loc[faces[2]].values
    
    points = points.drop(columns=["index"])
    points = points.rename_axis(index=index_name)
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

def remove_unused_vertices(**tri):
    """
    After triangulation, if there are vertices that are unsused in the triangulation, this function will remove them and
    recompute the appropriate index pointers linking 'triangles' and 'vertices'.
    """

    index_name = 'index'
    if tri['vertices'].index.name is not None:
        index_name = tri['vertices'].index.name
    index_orig_name = f'{index_name}_orig'

    v_indices_orig = tri['vertices'].index.values
    t_vertices_orig = tri['triangles'].loc[:,[0,1,2]].values
    if 'segments' in tri.keys():
        segments_set = set(tri['segments'].loc[:,[0,1,]].values.flatten())
    else:
        segments_set = set()

    used_indices = set(v_indices_orig) &  (set(t_vertices_orig.flatten()) | segments_set)

    v_subset = tri['vertices'].loc[list(used_indices)]
    v_subset = v_subset.reset_index().rename(columns={index_name: index_orig_name})

    new_index_mapping =dict(zip(v_subset.loc[:,index_orig_name].values,v_subset.index.values))

    triangles_copy = tri['triangles'].loc[:,[0,1,2]].copy()
    for col in triangles_copy.columns:
        triangles_copy[col] = triangles_copy[col].map(new_index_mapping)
        
    if 'segments' in tri.keys():
        segments_copy = tri['segments'].loc[:, [0, 1]].copy()
        for col in segments_copy.columns:
            segments_copy[col] = segments_copy[col].map(new_index_mapping)
        tri['segments'].loc[:, [0, 1]] = segments_copy

    tri['vertices'] = v_subset
    tri['triangles'].loc[:, [0, 1, 2]] = triangles_copy

    return tri

def remove_invalid_triangles(points, faces):
    """
    removes traingles whose vertices are missing, and reindexes the vertices and triangles back to natural indexes
    (that is, indices starting at 0 and increasing by 1 with each row)
    """

    valid_tri_mask = np.all(faces.loc[:,[0,1,2]].isin(points.index), axis=1)
    faces = faces[valid_tri_mask]
    return reindex(points, faces)