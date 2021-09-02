import numpy as np
import pandas as pd
import scipy.spatial
import triangle

from . import cleanup
from . import points_in_mesh
from . import boundary

def replace_triangles(points, vertices=None, triangles=None, **tri):
    if vertices is None:
        vertices = pd.DataFrame({"X": [], "Y": []})
    if triangles is None:
       triangles = pd.DataFrame({0: [], 1: [], 2:[]})
    vertices, triangles = cleanup.reindex(vertices, triangles)

    # remove duplicated coordinates to not create invalid geometries
    # check first within points, then check if points overlap with any vertex in vertices
    # TODO: Are there important data in the extra columns of `points` that we lose by dropping them?
    #       Maybe the most proper approach would be to replace lines of `vertices` with those of `points`...
    #       or at least users should have the choice of which one should be overwritten.
    #       2021-09-02, Duke-of-Lizard
    points = points.drop_duplicates(['X','Y'])

    p_xy = points.loc[:, ['X', 'Y']]
    v_xy = vertices.loc[:, ['X', 'Y']]
    merged_pv = pd.merge(p_xy, v_xy, on=['X', 'Y'], how='left', indicator='indicator')
    merged_pv['duplicated_flag'] = np.where(merged_pv.loc[:, 'indicator'] == 'both', True, False)
    points = points[~ merged_pv['duplicated_flag']]


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
    if "triangles" not in tri:
        tri["triangles"] = pd.DataFrame({0: [], 1: [], 2:[]})        

    # Remove any duplicate vertices, or triangle.triangulate() is
    # going to segfault!    
    tri["vertices"], tri["triangles"] = cleanup.clean_triangles(
        tri["vertices"], tri["triangles"], decimals = None)
        
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
            holes = np.append(process_tri["holes"], holes, axis=0)
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
            holes = np.append(process_tri["holes"], holes, axis=0)
        process_tri["holes"] = holes

    return process_tri
    res.update(triangle.triangulate(process_tri, 'p'))
    
    if "triangles" in tri:
        triangles = tri["triangles"]
        res["triangles"] = triangles.append(triangles.iloc[0:0].append(pd.DataFrame(res["triangles"])))

    res["vertices"] = tri["vertices"].append(
        pd.DataFrame(res["vertices"][len(tri["vertices"]):,:], columns=["X", "Y"]), ignore_index=True)

    new_points = res["vertices"].loc[len(tri["vertices"]):].index
    if len(new_points):
        res = interpolate_vertices(res, new_points)

    if 'segments' in tri:
        res['segments'] = pd.DataFrame(res['segments'])

    return res


def triangles_to_segments(triangles):
    return triangles[[0, 1]].append(
        triangles[[1, 2]].rename(columns={1:0, 2:1})).append(
        triangles[[2, 0]].rename(columns={2:0, 0:1})).append(
        triangles[[0, 1]].rename(columns={0:1, 1:0})).append(
        triangles[[1, 2]].rename(columns={2:0, 1:1})).append(
        triangles[[2, 0]].rename(columns={0:0, 2:1})).drop_duplicates().set_index(0).sort_index()

def interpolate_vertices(tri, to_interpolate_idxs):
    new_points = to_interpolate_idxs
    
    new_triangles = (
          tri["triangles"][0].isin(new_points)
        | tri["triangles"][1].isin(new_points)
        | tri["triangles"][2].isin(new_points))

    segments = triangles_to_segments(tri["triangles"].loc[new_triangles])

    segments2 = segments.join(
        tri["vertices"]
    ).reset_index().rename(columns={"index":0}).set_index(1).join(
        tri["vertices"][["X", "Y"]].rename(columns={"X":"X1", "Y":"Y1"}))

    segments2["segment_length"] = np.sqrt(  (segments2["X1"]-segments2["X"])**2
                                          + (segments2["Y1"]-segments2["Y"])**2)
    segments2["segment_weight"] = 1. / segments2["segment_length"]
    segments2 = segments2[~segments2[0].isin(new_points)]

    segments3 = segments2.mul(
        segments2["segment_weight"], axis=0
    ).assign(
        segment_weight=segments2["segment_weight"]
    ).groupby(level=0).sum()

    interpolated = segments3.div(segments3["segment_weight"], axis=0)

    res = dict(tri)
    res["vertices"] = res["vertices"].copy()
    cols = set(interpolated.columns).intersection(set(tri["vertices"].columns)) - set(("X", "Y"))
    res["vertices"].loc[interpolated.index, cols] = interpolated[cols]
    return res
