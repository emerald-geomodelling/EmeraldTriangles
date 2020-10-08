import bokeh

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
        
def points(fig, color=None, **tri):
    color = colormap_default(color, fixed="green", palette="Greens256", datasets=[tri["vertices"]])
    source = bokeh.models.ColumnDataSource(data=tri["vertices"])
    fig.circle(x="X", y="Y", color=color, source=source)

def triangles(fig, color, line_color=None, **tri):
    color = colormap_default(color, column="color", fixed="red", palette="Inferno256", datasets=[tri["vertices"], tri["triangles"]])
    vertices = tri["vertices"]
    triangles = tri["triangles"]

    xs = [[[vertices["X"].values[
             [row[1].values[0], row[1].values[1], row[1].values[2], row[1].values[0]]]]]
          for row in triangles.iterrows()]
    ys = [[[vertices["Y"].values[
             [row[1].values[0], row[1].values[1], row[1].values[2], row[1].values[0]]]]]
          for row in triangles.iterrows()]
    data={"xs": xs, "ys": ys}
    
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

    source = bokeh.models.ColumnDataSource(data=data)
    glyph = bokeh.models.MultiPolygons(xs="xs", ys="ys", fill_color=color, line_color="#8073ac", line_width=1)
    fig.add_glyph(source, glyph)

def plot(fig, color = None, **tri):
    if "vertices" in tri:
        tri["vertices"] = tri["vertices"].copy().fillna(-1)
    
    if "points" in tri and len(tri["points"]):
        points(fig, color, **tri)
    if 'segments' in tri:
        pass
    if 'triangles' in tri and len(tri["triangles"]):
        triangles(fig, color, **tri)
    if 'holes' in tri:
        pass
    if 'edges' in tri:
        pass
    if 'regions' in tri:
        pass
    if 'triangle_attributes' in tri:
        pass



