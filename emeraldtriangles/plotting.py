import triangle
import pandas as pd

def plot(ax, **tri):
    if isinstance(tri.get("triangles"), pd.core.frame.DataFrame):
        tri["triangles"] = tri["triangles"][[0, 1, 2]].values
    if isinstance(tri.get("vertices"), pd.core.frame.DataFrame):
        tri["vertices"] = tri["vertices"][["X", "Y"]].values
    triangle.plot(ax, **tri)
