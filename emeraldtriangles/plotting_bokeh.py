try:
    import bokeh
except:
    pass
    
def colormap_default(color, column="color", fixed="red", palette="Inferno256", datasets=[]):
    datacolumn = False
    dataset = None
    for d in datasets:
        if column in d.columns:
            datacolumn = column
            dataset = d
            break
    for d in datasets:
        if color in d.columns:
            datacolumn = color
            dataset = d
            break
    if datacolumn:
        return bokeh.transform.linear_cmap(
            datacolumn, getattr(bokeh.palettes, palette),
            dataset[datacolumn].min(), dataset[datacolumn].max())
    return color or fixed
        
def points(fig, color=None, tags=[], **tri):
    color = colormap_default(color, fixed="green", palette="Greens256", datasets=[tri["vertices"]])
    source = bokeh.models.ColumnDataSource(data=tri["vertices"])
    fig.circle(x="X", y="Y", color=color, source=source, tags=tags + ["points"])

def triangles(fig, color, tags=[], line_color=None, **tri):
    color = colormap_default(color, column="color", fixed="red", palette="Inferno256", datasets=[tri["vertices"], tri["triangles"]])
    vertices = tri["vertices"]
    triangles = tri["triangles"]

    xs = [[[vertices["X"].values[
             [row[1][0], row[1][1], row[1][2], row[1][0]]]]]
          for row in triangles.iterrows()]
    ys = [[[vertices["Y"].values[
             [row[1][0], row[1][1], row[1][2], row[1][0]]]]]
          for row in triangles.iterrows()]
    data={"xs": xs, "ys": ys}
    for col in vertices.columns:
        if (    col not in ("X", "Y")
            and (   vertices[col].dtype.name.startswith("float")
                 or vertices[col].dtype.name.startswith("int"))):
            data[col] = (  vertices[col].values[triangles[0].values]
                         + vertices[col].values[triangles[1].values]
                         + vertices[col].values[triangles[2].values]) / 3
            
    for col in triangles.columns:
        if (    col not in (0, 1, 2)
            and (   triangles[col].dtype.name.startswith("float")
                 or triangles[col].dtype.name.startswith("int"))):
            data[col] = col
    
    colorcol = None
    if isinstance(color, str) and (color in vertices.columns or color in triangles.columns):
        colorcol = color
    elif isinstance(color, dict):
        colorcol = color["field"]

    if colorcol is not None:
        if colorcol in triangles.columns:
            data[colorcol] = triangles[colorcol].values
        else:
            data[colorcol] = (  vertices[colorcol].values[triangles[0].values]
                              + vertices[colorcol].values[triangles[1].values]
                              + vertices[colorcol].values[triangles[2].values]) / 3

    face_params = {"line_width": 0.1, "line_color": "#8073ac", "fill_color": color}
    if "face_params" in tri:
        face_params.update(tri["face_params"])
    source = bokeh.models.ColumnDataSource(data=data)
    glyph = bokeh.models.MultiPolygons(xs="xs", ys="ys", **face_params, tags=tags + ["triangles"])
    fig.add_glyph(source, glyph)

def plot(fig, color = None, tags=[], **tri):
    if "vertices" in tri:
        tri["vertices"] = tri["vertices"].copy().fillna(-1)
    
    if "points" in tri and len(tri["points"]):
        points(fig, color, tags, **tri)
    if 'segments' in tri:
        pass
    if 'triangles' in tri and len(tri["triangles"]):
        triangles(fig, color, tags, **tri)
    if 'holes' in tri:
        pass
    if 'edges' in tri:
        pass
    if 'regions' in tri:
        pass
    if 'triangle_attributes' in tri:
        pass



