import bokeh

def points(fig, cmap, **tri):
    vertices = tri["vertices"].copy()
    vertices["color"] = vertices["color"].fillna(-1)
    source = bokeh.models.ColumnDataSource(data=vertices[["X","Y","color"]])
    color = {"field": "color", "transform": cmap["transform"]}
    fig.circle(x="X", y="Y", color=color, source=source)

def triangles(fig, cmap, **tri):
    vertices = tri["vertices"].copy()
    vertices["color"] = vertices["color"].fillna(-1)

    xs = [[[vertices["X"].values[
             [row[1].values[0], row[1].values[1], row[1].values[2], row[1].values[0]]]]]
          for row in tri["triangles"].iterrows()]
    ys = [[[vertices["Y"].values[
             [row[1].values[0], row[1].values[1], row[1].values[2], row[1].values[0]]]]]
          for row in tri["triangles"].iterrows()]
    color = [(vertices["color"].values[row[1].values[0]]
              + vertices["color"].values[row[1].values[1]]
              + vertices["color"].values[row[1].values[2]]) / 3
              for row in tri["triangles"].iterrows()]

    source = bokeh.models.ColumnDataSource(data={"xs": xs, "ys": ys, "color": color})

    color = {"field": "color", "transform": cmap["transform"]}
    
    glyph = bokeh.models.MultiPolygons(xs="xs", ys="ys", fill_color=color, line_color="#8073ac", line_width=1)
    fig.add_glyph(source, glyph)

def plot(fig, cmap = None, **tri):
    if cmap is None:
        vertices = tri["vertices"].copy()
        vertices["color"] = vertices["color"].fillna(-1)
        cmap = bokeh.transform.linear_cmap(
            "color", bokeh.palettes.Inferno256,
            vertices["color"].min(), vertices["color"].max())

    if "points" in tri and len(tri["points"]):
        points(fig, cmap, **tri)
    if 'segments' in tri:
        pass
    if 'triangles' in tri and len(tri["triangles"]):
        triangles(fig, cmap, **tri)
    if 'holes' in tri:
        pass
    if 'edges' in tri:
        pass
    if 'regions' in tri:
        pass
    if 'triangle_attributes' in tri:
        pass



