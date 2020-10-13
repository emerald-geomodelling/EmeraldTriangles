import uuid
import json
import pandas as pd

def split_extra_columns(df, index_columns, base_columns):
    base = df[index_columns + base_columns]
    extra = df[[name for name in df.columns
                if name not in base_columns]
              ].melt(index_columns, var_name="column")
    return base, extra

def to_sql(con, name, tri_id=None, vertice_base_columns=["X", "Y"], triangle_base_columns=[0, 1, 2], **tri):
    if tri_id is None:
        tri_id = str(uuid.uuid4())

    info = dict(tri.get("meta", {}))
    for key, value in info.items():
        if isinstance(value, dict):
            info[key] = json.dumps(value)    
    info["tri_id"] = tri_id
    info = pd.DataFrame([info])

    vertices = tri["vertices"].reset_index().rename(columns={"index":"vertex_id"})
    vertices["tri_id"] = tri_id
    vertices_pure, vertice_cols = split_extra_columns(
        vertices,
        ["tri_id", "vertex_id"],
        vertice_base_columns)

    triangles = tri["triangles"].copy()
    triangles["tri_id"] = tri_id
    triangles = triangles.reset_index().rename(columns={"index":"triangle_id"})
    triangles_pure, triangle_cols = split_extra_columns(
        triangles,
        ["tri_id", "triangle_id"],
        triangle_base_columns)

    info.to_sql(name="%s" % name, con=con, if_exists="append", method='multi', index=False)
    vertices_pure.to_sql(name="%s_vertices" % name, con=con, if_exists="append", method='multi', index=False)
    vertice_cols.to_sql(name="%s_vertices_columns % name", con=con, if_exists="append", method='multi', index=False)    
    triangles_pure.to_sql(name="%s_triangles" % name, con=con, if_exists="append", method='multi', index=False)
    triangle_cols.to_sql(name="%s_triangles_columns" % name, con=con, if_exists="append", method='multi', index=False)
