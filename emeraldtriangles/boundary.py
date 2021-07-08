import numpy as np
import pandas as pd
import scipy.spatial
import shapely.geometry
import warnings
    
from . import cleanup

def mesh_boundary(**tri):
    triangles = tri["triangles"]

    if not len(triangles):
        return tri
    
    sides = triangles[[0, 1]].assign(triangle=triangles.index).append(
        triangles[[1, 2]].assign(triangle=triangles.index).rename(columns={1:0, 2:1})).append(
        triangles[[0, 2]].assign(triangle=triangles.index).rename(columns={2:1})).reset_index(drop=True)

    sides.loc[sides[0] > sides[1], [1, 0]] = sides.loc[sides[0] > sides[1], [0, 1]].rename(columns={0:1, 1:0})

    sides = sides.sort_values([0, 1])

    segments = sides.drop_duplicates([0, 1], keep=False, ignore_index=True)

    if "segments" in tri:
        segments = tri["segments"].append(segments).reset_index().drop(columns=['index'])
        segments.loc[:, 'vertex_set'] = segments.apply(lambda x: set([x.loc[0], x.loc[1]]), axis=1)
        segments_unique = segments.vertex_set.astype('str').drop_duplicates(keep='last')
        segments = segments.loc[segments_unique.index,[0,1,'triangle']]
        segments = segments.drop_duplicates([0, 1], keep='last', ignore_index=True).reset_index().drop(columns=['index'])
        
    tri["segments"] = segments
    
    return tri

def _mesh_boundary_mark_rings(segments):
    segments = segments.copy()
    
    segments["ring"] = np.NaN
    segments["pos"] = np.NaN
    ring = 0

    while True:
        remaining = segments[np.isnan(segments["ring"])]
        if not len(remaining): break

        current = remaining.index[0]

        ring += 1
        pos = 0
        segments.loc[current, "ring"] = ring
        segments.loc[current, "pos"] = pos

        right = segments.loc[current, 1]


        while True:
            nxt = segments[(segments[0] == right) & (segments.index != current)]
            prv = segments[(segments[1] == right) & (segments.index != current)]
            if len(nxt):
                current = nxt.index[0]
                right = segments.loc[current, 1]
            elif len(prv):
                current = prv.index[0]
                right = segments.loc[current, 0]
            else:
                break


            if not np.isnan(segments.loc[current, "ring"]):
                # Merge an existing ring
                existing = segments.loc[current, "ring"]

                segments.loc[segments["ring"] == existing, "pos"] += pos
                segments.loc[segments["ring"] == existing, "ring"] = ring
                break

            pos += 1
            segments.loc[current, "ring"] = ring
            segments.loc[current, "pos"] = pos
            
    return segments

def _mesh_boundary_to_pointlists(segments, **tri):
    segments = _mesh_boundary_mark_rings(segments)
    
    res = {}
    for ring in segments["ring"].unique():
        ringborders = segments[segments["ring"] == ring]
    
        res[int(ring)] = ringborders[[0, "pos"]].rename(columns={0:"point"}).append(
            ringborders[[1, "pos"]].rename(columns={1:"point"})
        ).sort_values("pos").drop_duplicates("pos")["point"].values

    return res

def mesh_boundary_to_pointlists(segments, **tri):
    warnings.warn("Use mesh_boundary_rings() instead", DeprecationWarning)
    return _mesh_boundary_to_pointlists(segments, **tri)
    
def mesh_boundary_rings(**tri):
    tri["rings"] = mesh_boundary_to_pointlists(**tri)
    return tri
    
def rings_multipolygon(coord_columns=["X", "Y"], **tri):
    if "rings" not in tri:
        tri = mesh_boundary(**tri)
        tri = mesh_boundary_rings(**tri)
    return shapely.geometry.MultiPolygon([
        shapely.geometry.Polygon(
            shapely.geometry.LineString(
                tri["vertices"].loc[p][coord_columns].values))
        for p in tri["rings"].values()])

    
def vertices_boundary(**tri):
    segments = pd.DataFrame(
        scipy.spatial.ConvexHull(tri["vertices"][["X", "Y"]]).simplices,
        columns=[0,1])
    if "segments" in tri:
        segments = tri["segments"].append(segments)
    tri["segments"] = segments
    return tri

def polygon_to_boundary(poly, **tri):
    if hasattr(poly.boundary, 'geoms'):
        boundary_geoms = poly.boundary.geoms
    else:
        boundary_geoms = [poly.boundary]

    for boundary in boundary_geoms:
        tri["vertices"], tri["triangles"], start = cleanup.append_nodes(
            pd.DataFrame(np.array(boundary.coords[:-1]), columns=["X", "Y"]),
            tri["vertices"], tri["triangles"])

        segments = start + np.append(np.arange(len(boundary.coords) - 1), [0])
        segments = pd.DataFrame(np.column_stack((segments[:-1], segments[1:])))

        if "segments" in tri:
            tri["segments"] = tri["segments"].append(segments)
        else:
            tri["segments"] = segments
    return tri
