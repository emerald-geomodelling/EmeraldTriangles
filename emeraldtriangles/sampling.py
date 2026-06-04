from . import points_in_mesh
import numpy as np

def sample_points(columns = None, **tri, ):
    if columns is None:
        columns = list(tri['vertices'].columns)
    else:
        missing_columns = []
        for column in columns:
            if column not in tri['vertices']:
                missing_columns.append(columns)
        if len(missing_columns)>0:
            raise KeyError(f'{len(missing_columns)} columns are missing from tri["vertices"]: {missing_columns}')

    # Find which triangle the point belongs to
    points_and_triangles = points_in_mesh.points_in_triangles(**tri)
    points_and_triangles = points_and_triangles.loc[points_and_triangles["triangle"] != -1]
    # `point` is a positional row number into tri['points'] (the enumerate index from
    # points_in_triangles), so select with .iloc and don't assume a natural 0..n index.
    points = tri['points'].iloc[points_and_triangles.point.values]
    
    # Get X and Y coordinates for vertices for relevant triangles.
    # `points_and_triangles.triangle` holds positional row numbers into `triangles`
    # (not index labels), so select rows with .iloc and make no assumption of a
    # natural 0..n index. Columns are selected by label [0, 1, 2] so the vertex-index
    # columns stay correct even when `triangles` carries extra columns (area, perimeter, ...).
    tri_vert_np = tri['triangles'].iloc[points_and_triangles.triangle.values][[0, 1, 2]].values
    X_tri = tri['vertices'].X.values[tri_vert_np]
    Y_tri = tri['vertices'].Y.values[tri_vert_np]
    Y1 = Y_tri[:, 1]
    Y2 = Y_tri[:, 2]
    Y3 = Y_tri[:, 0]
    X1 = X_tri[:, 1]
    X2 = X_tri[:, 2]
    X3 = X_tri[:, 0]

    # compute Barycentric weights of each vertex for every query point, then compute Z
    Px = points.X.values
    Py = points.Y.values
    wv1 = ((Y2 - Y3) * (Px - X3) + (X3 - X2) * (Py - Y3)) / ((Y2 - Y3) * (X1 - X3) + (X3 - X2) * (Y1 - Y3))
    wv2 = ((Y3 - Y1) * (Px - X3) + (X1 - X3) * (Py - Y3)) / ((Y2 - Y3) * (X1 - X3) + (X3 - X2) * (Y1 - Y3))
    wv3 = 1 - wv2 - wv1

    # Interpolate each column
    for col in set(columns) - set(("X", "Y", "x", "y")):
        Z_tri = tri['vertices'][col].values[tri_vert_np]
        Pz = wv1 * Z_tri[:, 1] + wv2 * Z_tri[:, 2] + wv3 * Z_tri[:, 0]
        if col not in tri["points"].columns:
            tri["points"] = tri["points"].assign(**{col:np.nan})
        # Single positional indexer (rows by position, col by position) avoids both the
        # natural-index assumption and the chained assignment (.loc[:,col].iloc[...] = )
        # that silently writes to a temporary under pandas copy-on-write.
        tri["points"].iloc[points_and_triangles.point.values,
                           tri["points"].columns.get_loc(col)] = Pz

    return tri["points"]

