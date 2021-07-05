import uuid
import json
import pandas as pd
import pandasio
import shapely.wkb
import emeraldtriangles.boundary
import geoalchemy2
import pyproj

def split_extra_columns(df, index_columns, base_columns):
    missing = set(index_columns + base_columns) - set(df.columns)
    if missing:
        df = df.assign(**{name:None for name in missing})
    base = df[index_columns + base_columns]
    extra = df[[name for name in df.columns
                if name not in base_columns]
              ].melt(index_columns, var_name="column")
    return base, extra

def to_sql(con, name, tri_id=None, vertice_base_columns=["X", "Y"], triangle_base_columns=[0, 1, 2], info_base_columns=None, store_shape=True, **tri):
    if tri_id is None:
        tri_id = str(uuid.uuid4())

    info_dtype = {}
    info = dict(tri.get("meta", {}))
    if info_base_columns is not None:
        extra = {}
        for col in set(info.keys()) - set(info_base_columns):
            extra[col] = info.pop(col)
        info["extra"] = extra
    for key, value in info.items():
        if isinstance(value, dict):
            info[key] = json.dumps(value)
    info["tri_id"] = tri_id

    projection = info.get("projection", None)
    if store_shape and projection is not None:
        coord_columns=["X", "Y"] if "X" in tri["vertices"].columns else ["x", "y"]
        coord_x, coord_y = coord_columns
        if "rings" not in tri:
            tri = emeraldtriangles.boundary.mesh_boundary(**tri)
            tri = emeraldtriangles.boundary.mesh_boundary_rings(**tri)
        polygon = emeraldtriangles.boundary.rings_multipolygon(coord_columns=coord_columns, **tri)
        info["the_geom_orig"] = shapely.wkb.dumps(polygon, srid=projection).hex()
        info_dtype.update({"the_geom_orig": geoalchemy2.Geometry('GEOMETRY')})

        vertices = tri["vertices"]
        if "lon" not in vertices.columns:
            vertices["lon"], vertices["lat"] = pyproj.Transformer.from_crs(projection, 4326, always_xy=True
            ).transform(vertices[coord_x], vertices[coord_y])
        if "x_web" not in vertices.columns:
            vertices["x_web"], vertices["y_web"] = pyproj.Transformer.from_crs(projection, 3857, always_xy=True
            ).transform(vertices[coord_x], vertices[coord_y])
            
        polygon = emeraldtriangles.boundary.rings_multipolygon(coord_columns=["lon", "lat"], **tri)
        info["the_geom"] = shapely.wkb.dumps(polygon, srid=4326).hex()
        info_dtype.update({"the_geom": geoalchemy2.Geometry('GEOMETRY', srid=4326)})

        polygon = emeraldtriangles.boundary.rings_multipolygon(coord_columns=["x_web", "y_web"], **tri)
        info["the_geom_webmercator"] = shapely.wkb.dumps(polygon, srid=3857).hex()
        info_dtype.update({"the_geom_webmercator": geoalchemy2.Geometry('GEOMETRY', srid=3857)})
        
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

    pandasio.to_sql(info, name="%s" % name, con=con, index=False, dtype=info_dtype)
    pandasio.to_sql(vertices_pure, name="%s_vertices" % name, con=con, index=False)
    pandasio.to_sql(vertice_cols, name="%s_vertices_columns" % name, con=con, index=False)    
    pandasio.to_sql(triangles_pure, name="%s_triangles" % name, con=con, index=False)
    pandasio.to_sql(triangle_cols, name="%s_triangles_columns" % name, con=con, index=False)

def read_sql(con, name, tri_id):
    info = pandasio.read_sql_query("select * from %s where tri_id = %%s" % name, params=(tri_id,), con=con)
    vertices = pandasio.read_sql_query("select * from %s_vertices where tri_id = %%s" % name, params=(tri_id,), con=con)
    vertices_columns = pandasio.read_sql_query("select * from %s_vertices_columns where tri_id = %%s" % name, params=(tri_id,), con=con)
    triangles = pandasio.read_sql_query("select * from %s_triangles where tri_id = %%s" % name, params=(tri_id,), con=con)
    triangles_columns = pandasio.read_sql_query("select * from %s_triangles_columns where tri_id = %%s" % name, params=(tri_id,), con=con)

    vertices_columns = vertices_columns.pivot("vertex_id", "column", "value")
    triangles_columns = triangles_columns.pivot("triangle_id", "column", "value")

    vertices = vertices.set_index("vertex_id").sort_index().join(vertices_columns, rsuffix='_duplicate')
    triangles = triangles.set_index("triangle_id").sort_index().join(triangles_columns, rsuffix='_duplicate')

    triangles.columns = [int(col) if col in ("0", "1", "2") else col for col in triangles.columns]

    info = dict(info.iloc[0])
    for key, value in info.items():
        try:
            info[key] = json.loads(value)
        except:
            pass
    if "extra" in info:
        info.update(info.pop("extra"))
        
    return {"vertices": vertices, "triangles": triangles, "meta": info}

