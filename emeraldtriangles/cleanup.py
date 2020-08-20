import numpy as np
import pandas as pd

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
