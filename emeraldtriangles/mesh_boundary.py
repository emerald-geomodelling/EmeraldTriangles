import numpy as np
import pandas as pd

def mesh_boundary(faces):
    sides = faces[[0, 1]].assign(face=faces.index).append(
        faces[[1, 2]].assign(face=faces.index).rename(columns={1:0, 2:1})).append(
        faces[[0, 2]].assign(face=faces.index).rename(columns={2:1})).reset_index(drop=True)


    sides.loc[sides[0] > sides[1], [1, 0]] = sides.loc[sides[0] > sides[1], [0, 1]].rename(columns={0:1, 1:0})

    sides = sides.sort_values([0, 1])

    border_sides = sides.drop_duplicates([0, 1], keep=False, ignore_index=True)
    
    return border_sides

def _mesh_boundary_mark_rings(border_sides):
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

def mesh_boundary_to_pointlists(border_sides):
    border_sides = _mesh_boundary_mark_rings(border_sides)
    
    res = {}
    for ring in border_sides["ring"].unique():
        ringborders = border_sides[border_sides["ring"] == ring]
    
    res[int(ring)] = ringborders[[0, "pos"]].rename(columns={0:"point"}).append(
        ringborders[[1, "pos"]].rename(columns={1:"point"})
    ).sort_values("pos").drop_duplicates("pos")["point"].values
    
    return res
