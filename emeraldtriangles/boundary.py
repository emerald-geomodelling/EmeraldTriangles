import numpy as np
import pandas as pd

def mesh_boundary(**tri):
    triangles = tri["triangles"]
    
    sides = triangles[[0, 1]].assign(triangle=triangles.index).append(
        triangles[[1, 2]].assign(triangle=triangles.index).rename(columns={1:0, 2:1})).append(
        triangles[[0, 2]].assign(triangle=triangles.index).rename(columns={2:1})).reset_index(drop=True)

    sides.loc[sides[0] > sides[1], [1, 0]] = sides.loc[sides[0] > sides[1], [0, 1]].rename(columns={0:1, 1:0})

    sides = sides.sort_values([0, 1])

    segments = sides.drop_duplicates([0, 1], keep=False, ignore_index=True)

    res = dict(tri)
    res["segments"] = segments
    
    return res

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

def mesh_boundary_to_pointlists(segments, **tri):
    segments = _mesh_boundary_mark_rings(segments)
    
    res = {}
    for ring in segments["ring"].unique():
        ringborders = segments[segments["ring"] == ring]
    
    res[int(ring)] = ringborders[[0, "pos"]].rename(columns={0:"point"}).append(
        ringborders[[1, "pos"]].rename(columns={1:"point"})
    ).sort_values("pos").drop_duplicates("pos")["point"].values
    
    return res
