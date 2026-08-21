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
    points_and_nodes = pd.concat([vertices, points], ignore_index=True)
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
    res["triangles"] = pd.concat([triangles,b_triangles], axis=0, ignore_index=True)
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
    t_vertices_orig = tri['triangles'].loc[:, [0, 1, 2]].values

    if 'segments' in tri.keys():
        segments_set = set(tri['segments'].loc[:, [0, 1, ]].values.flatten())
    else:
        segments_set = set()

    used_indices = set(v_indices_orig) & (set(t_vertices_orig.flatten()) | segments_set)
    v_subset = tri['vertices'].loc[list(used_indices)]

    if not len(v_subset.columns) == len(set(v_subset.columns)):
        v_subset = v_subset.T.drop_duplicates().T
    v_subset = v_subset.reset_index()
    if index_orig_name not in v_subset.columns:
        v_subset.rename(columns={index_name: index_orig_name}, inplace=True)
    else:
        del v_subset[index_name]

    new_index_mapping = dict(zip(v_subset.loc[:, index_orig_name].values, v_subset.index.values))

    # Whole-column assignment on copies: the old ``.loc[:, [0, 1, 2]] = ...`` wrote int64 (or float64 when a key
    # was missing) into int32 columns in place -- a FutureWarning on pandas 2 and an error on pandas 3 (#26).
    tri['triangles'] = _remap_index_columns(tri['triangles'], [0, 1, 2], new_index_mapping)
    if 'segments' in tri.keys():
        tri['segments'] = _remap_index_columns(tri['segments'], [0, 1], new_index_mapping)
    tri['vertices'] = v_subset

    return tri


def _remap_index_columns(df, columns, mapping):
    """Return a copy of ``df`` with the vertex-id ``columns`` remapped through ``mapping`` (dtype int64 when every
    id is known, float64 with NaN otherwise)."""
    out = df.copy()
    for col in columns:
        mapped = out[col].map(mapping)
        out[col] = mapped.astype("int64") if mapped.notna().all() else mapped.astype("float64")
    return out

def remove_invalid_triangles(points, faces):
    """
    removes traingles whose vertices are missing, and reindexes the vertices and triangles back to natural indexes
    (that is, indices starting at 0 and increasing by 1 with each row)
    """

    valid_tri_mask = np.all(faces.loc[:,[0,1,2]].isin(points.index), axis=1)
    faces = faces[valid_tri_mask]
    return reindex(points, faces)


def set_case_column_names(df, columns, uppercase=True, ):
    """
    Take a pandas.DataFrame, and convert the columns specified to either uppercase (default) or to lowercase. Can
    be used to convert coordinate column names to the uppercase "X", "Y" and optional "Z" to the uppercase forms
    that most code in EMeraldTriangles expects. The DataFrame is modified in place (columns are renamed)

    @param df: input pandas.DataFrame
    @param columns: list of column names to operate on
    @param uppercase: boolean that controls whether columns will be converted to upperase (default) or lowercase

    """
    upper = lambda s: s.upper()
    lower = lambda s: s.lower()

    if uppercase:
        function_target = upper
        function_source = lower
        case_target = 'upper'
        case_source = 'lower'
    else:
        function_target = lower
        function_source = upper
        case_target = 'lower'
        case_source = 'upper'

    for col in columns:
        if function_source(col) in df.columns and function_target(col) in df.columns:
            raise ValueError(f"both uppercase and lower versions of the column {col} found in this DataFrame!")
        if function_target(col) not in df.columns:
            df.rename(columns={function_source(col): function_target(col)}, inplace=True)


# ----------------------------------------------------------------------------------------------------------------
# geometric quality of triangles (issue #20, #33)
# ----------------------------------------------------------------------------------------------------------------

def triangle_metrics(vertices, triangles, x_col="X", y_col="Y"):
    """Per-triangle shape metrics as a DataFrame aligned with ``triangles``.

    Columns: ``area``, ``perimeter``, ``max_side_length``, ``min_side_length``, ``min_angle_deg`` and ``aspect``
    (longest side over the diameter of the inscribed circle; 1.73 for an equilateral triangle, large for slivers).
    ``triangles[[0, 1, 2]]`` are taken as *positions* into ``vertices`` (the natural 0..n-1 index that
    :func:`reindex` produces); call :func:`reindex` first if the vertex index has gaps.
    """
    idx = triangles.loc[:, [0, 1, 2]].to_numpy(dtype=np.int64)
    if idx.size and (idx.min() < 0 or idx.max() >= len(vertices)):
        raise ValueError("triangles reference vertex positions outside the vertex table; reindex() first")
    xt = vertices[x_col].to_numpy(dtype=float)[idx]
    yt = vertices[y_col].to_numpy(dtype=float)[idx]
    area = 0.5 * np.abs((xt[:, 2] - xt[:, 1]) * (yt[:, 0] - yt[:, 1]) - (xt[:, 0] - xt[:, 1]) * (yt[:, 2] - yt[:, 1]))
    # side i is opposite vertex i
    sides = np.empty_like(xt)
    sides[:, 0] = np.hypot(xt[:, 1] - xt[:, 2], yt[:, 1] - yt[:, 2])
    sides[:, 1] = np.hypot(xt[:, 0] - xt[:, 2], yt[:, 0] - yt[:, 2])
    sides[:, 2] = np.hypot(xt[:, 0] - xt[:, 1], yt[:, 0] - yt[:, 1])
    a, b, c = sides[:, 0], sides[:, 1], sides[:, 2]
    with np.errstate(invalid="ignore", divide="ignore"):
        cosines = np.stack([(b ** 2 + c ** 2 - a ** 2) / (2 * b * c),
                            (a ** 2 + c ** 2 - b ** 2) / (2 * a * c),
                            (a ** 2 + b ** 2 - c ** 2) / (2 * a * b)], axis=1)
        angles = np.degrees(np.arccos(np.clip(cosines, -1.0, 1.0)))
        perimeter = sides.sum(axis=1)
        inradius = np.where(perimeter > 0, 2.0 * area / perimeter, 0.0)      # r = area / semi-perimeter
        aspect = np.where(inradius > 0, sides.max(axis=1) / (2.0 * inradius), np.inf)
    return pd.DataFrame({"area": area, "perimeter": perimeter, "max_side_length": sides.max(axis=1),
                         "min_side_length": sides.min(axis=1), "min_angle_deg": np.nanmin(angles, axis=1),
                         "aspect": aspect}, index=triangles.index)


def remove_triangles_by_shape(*, max_side_length=None, max_area=None, max_perimeter=None, min_angle_deg=None,
                              max_aspect=None, keep_metrics=False, x_col="X", y_col="Y", **tri):
    """Drop triangles that fail any of the given shape criteria; return a new tri dict.

    Typical use: after ``supplant_triangles(existing_boundary=False)`` the mesh reaches out to the convex hull of the
    vertices, so concave footprints and interior gaps are spanned by long, thin triangles. For vertices on a regular
    lattice with spacing ``dx, dy`` the legitimate triangles have ``max_side_length <= hypot(dx, dy)`` and
    ``area <= dx*dy/2``; thresholds a few percent above those remove exactly the spanning triangles.

    Parameters
    ----------
    max_side_length, max_area, max_perimeter : float, optional -- upper bounds
    min_angle_deg : float, optional -- smallest internal angle allowed (slivers have tiny angles)
    max_aspect : float, optional -- upper bound on ``max_side_length / (2 * inradius)``
    keep_metrics : bool -- append the metric columns to the returned ``triangles``
    **tri : the tin dict (``vertices``, ``triangles``, and anything else, which is passed through)

    Triangles are re-indexed to 0..n-1; vertices are untouched (use :func:`remove_unused_vertices` afterwards to
    drop vertices that no triangle references).
    """
    vertices, triangles = tri["vertices"], tri["triangles"]
    m = triangle_metrics(vertices, triangles, x_col=x_col, y_col=y_col)
    keep = np.ones(len(triangles), dtype=bool)
    if max_side_length is not None:
        keep &= m["max_side_length"].to_numpy() <= max_side_length
    if max_area is not None:
        keep &= m["area"].to_numpy() <= max_area
    if max_perimeter is not None:
        keep &= m["perimeter"].to_numpy() <= max_perimeter
    if min_angle_deg is not None:
        keep &= m["min_angle_deg"].to_numpy() >= min_angle_deg
    if max_aspect is not None:
        keep &= m["aspect"].to_numpy() <= max_aspect
    out = dict(tri)
    kept = triangles.loc[keep]
    if keep_metrics:
        kept = pd.concat([kept, m.loc[keep]], axis=1)
    out["triangles"] = kept.reset_index(drop=True)
    out["n_triangles_removed"] = int((~keep).sum())
    return out
