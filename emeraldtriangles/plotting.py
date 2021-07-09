import triangle
import pandas as pd
import numpy as np
import sys
import matplotlib.colors

# Yeah, module is shadowed by the function...
plotmod = sys.modules["triangle.plot"]

def triangles(ax, vertices, triangles, zorder=-1, edgecolors="red", facecolors="green", cmap="viridis", **kw):
    args = [vertices["X"], vertices["Y"], triangles[[0, 1, 2]]]
    kwargs = {"zorder": zorder, "edgecolors": edgecolors, "cmap": cmap}
    kwargs.update(kw.get("triangles_args", {}))
    if "facecolors" in triangles.columns:
        kwargs["facecolors"] = triangles["facecolors"].values
    elif "color" in vertices.columns:
        args.append(vertices["color"].values)
    else:
        kwargs["facecolors"] = np.zeros(len(triangles))
        kwargs["cmap"] = matplotlib.colors.ListedColormap(np.array([matplotlib.colors.to_rgba(facecolors)]))
        
    ax.tripcolor(*args, **kwargs)

def vertices(ax, **kw):
    verts = kw['vertices'][["X", "Y"]].values

    args = {}
    args.update(kw.get("vertices_args", {}))
    if "color" in kw['vertices'].columns:
        args["c"] = kw['vertices']["color"].values
    else:
        args["c"] = np.zeros(len(kw['vertices']))

    ax.scatter(kw['vertices']["X"], kw['vertices']["Y"], **args)
    if 'labels' in kw:
        for i in range(verts.shape[0]):
            ax.text(verts[i, 0], verts[i, 1], str(i))
    if 'markers' in kw:
        vm = kw['vertex_markers']
        for i in range(verts.shape[0]):
            ax.text(verts[i, 0], verts[i, 1], str(vm[i]))

def points(ax, **kw):
    verts = kw['points'][["X", "Y"]].values

    args = {}
    args.update(kw.get("points_args", {}))
    if "color" in kw['points'].columns:
        args["c"] = kw['points']["color"].values
    else:
        args["c"] = np.zeros(len(kw['points']))

    ax.scatter(kw['points']["X"], kw['points']["Y"], cmap="spring", **args)

            
def plot(ax, **kw):
    kworig = dict(kw)
    if isinstance(kw.get("triangles"), pd.core.frame.DataFrame):
        kw["triangles"] = kw["triangles"][[0, 1, 2]].values
    if isinstance(kw.get("vertices"), pd.core.frame.DataFrame):
        kw["vertices"] = kw["vertices"][["X", "Y"]].values
    if isinstance(kw.get("segments"), pd.core.frame.DataFrame):
        kw["segments"] = kw["segments"][[0, 1]].values
    
    ax.axes.set_aspect('equal')
    vertices(ax, **kworig)
    if "points" in kw and len(kw["points"]):
        points(ax, **kworig)
    if 'segments' in kw:
        plotmod.segments(ax, **kw)
    if 'triangles' in kw and len(kw["triangles"]):
        triangles(ax, **kworig)
    if 'holes' in kw:
        plotmod.holes(ax, **kw)
    if 'edges' in kw:
        plotmod.edges(ax, **kw)
    if 'regions' in kw:
        plotmod.regions(ax, **kw)
    if 'triangle_attributes' in kw:
        plotmod.triangle_attributes(ax, **kw)

    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
