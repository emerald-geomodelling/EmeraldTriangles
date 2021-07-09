from . import points_in_mesh

def sample_points(**tri):
    # Find which triangle the point belongs to
    points_and_triangles = points_in_mesh.points_in_triangles(**tri)
    points_and_triangles = points_and_triangles.loc[points_and_triangles["triangle"] != -1]
    points = tri['points'].loc[points_and_triangles.point]
    
    # Get X and Y coordinates for vertices for relevant triangles
    tri_vert_np = tri['triangles'].loc[points_and_triangles.triangle.values, [0, 1, 2]].values
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
    for col in set(tri["vertices"].columns) - set(("X", "Y", "x", "y")):
        Z_tri = tri['vertices'][col].values[tri_vert_np]
        Pz = wv1 * Z_tri[:, 1] + wv2 * Z_tri[:, 2] + wv3 * Z_tri[:, 0]
        tri["points"].loc[points_and_triangles.point, col] = Pz

    return tri["points"]

