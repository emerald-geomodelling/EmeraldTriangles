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
    vertice_cols.to_sql(name="%s_vertices_columns" % name, con=con, if_exists="append", method='multi', index=False)    
    triangles_pure.to_sql(name="%s_triangles" % name, con=con, if_exists="append", method='multi', index=False)
    triangle_cols.to_sql(name="%s_triangles_columns" % name, con=con, if_exists="append", method='multi', index=False)

def read_sql(con, name, tri_id):
    info = pd.read_sql_query("select * from %s where tri_id = %%s" % name, params=(tri_id,), con=con)
    vertices = pd.read_sql_query("select * from %s_vertices where tri_id = %%s" % name, params=(tri_id,), con=con)
    vertices_columns = pd.read_sql_query("select * from %s_vertices_columns where tri_id = %%s" % name, params=(tri_id,), con=con)
    triangles = pd.read_sql_query("select * from %s_triangles where tri_id = %%s" % name, params=(tri_id,), con=con)
    triangles_columns = pd.read_sql_query("select * from %s_triangles_columns where tri_id = %%s" % name, params=(tri_id,), con=con)

    vertices_columns = vertices_columns.pivot("vertex_id", "column", "value")
    triangles_columns = triangles_columns.pivot("triangle_id", "column", "value")

    vertices = vertices.set_index("vertex_id").sort_index().join(vertices_columns)
    triangles = triangles.set_index("triangle_id").sort_index().join(triangles_columns)

    triangles.columns = [int(col) if col in ("0", "1", "2") else col for col in triangles.columns]

    info = dict(info.iloc[0])
    for key, value in info.items():
        try:
            info[key] = json.loads(value)
        except:
            pass

    return {"vertices": vertices, "triangles": triangles, "meta": info}

