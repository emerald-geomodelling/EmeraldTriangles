import pandas as pd
import numpy as np
from ..cleanup import reindex

cimport numpy as np
cimport cpython.bytes
from libc.math cimport isnan
from libc.stdlib cimport atoi
from . cimport libxml

cdef extern from "string.h":
    int strcmp(char* str1, char* str2)
    char *strncpy(char* dest, char* src, size_t n)

cdef extern from "stdlib.h":
    double atof(const char *nptr)
    long long atoll(const char *nptr)
    
DEF CONTENT_BUFFER_SIZE = 1024
cdef double NAN
NAN = float("NaN")

cdef class State(object):
    cdef int chunk_size
    cdef list path
    cdef dict meta
    cdef dict surfaces
    cdef dict surface
    
    cdef object vertices
    cdef np.ndarray vertices_x
    cdef np.ndarray vertices_y
    cdef np.ndarray vertices_z
    cdef np.ndarray vertices_m
    cdef np.ndarray vertices_id
    cdef int vertices_start

    cdef object triangles
    cdef np.ndarray triangles_0
    cdef np.ndarray triangles_1
    cdef np.ndarray triangles_2
    cdef int triangles_start
    
    cdef char content[CONTENT_BUFFER_SIZE]
    cdef size_t content_pos
    cdef int vertex_row_idx    
    cdef int triangle_row_idx
    cdef int vertex_id_no

    cdef char reindex_points
    
    def __init__(self, chunk_size = 10240, reindex_points=False):
        self.chunk_size = chunk_size
        self.path = []
        self.meta = {}
        self.surfaces = {}
        self.content[0] = 0
        self.content_pos = 0
        self.reindex_points = reindex_points
        
    def add_meta(self, path, meta, attributes):
        if len(path) == 0:
            meta.update(attributes)
        else:
            if path[0] not in meta:
                meta[path[0]] = {}
            self.add_meta(path[1:], meta[path[0]], attributes)
        
    cdef append_point(State self, double point[4]):
        end = self.vertices.index.max() if self.vertices is not None else -1
        if self.vertex_row_idx > end:
            self.vertices = pd.DataFrame(index=pd.RangeIndex(end + 1, end + 1 + self.chunk_size), columns=("Y", "X", "Z", "M", "id"), dtype=float)
            self.vertices.id = self.vertices.id.fillna(-1).astype(int)
            self.vertices_x = self.vertices["X"].values
            self.vertices_y = self.vertices["Y"].values
            self.vertices_z = self.vertices["Z"].values
            self.vertices_m = self.vertices["M"].values
            self.vertices_id= self.vertices["id"].values
            self.vertices_start = end + 1
            self.surface["vertices"].append(self.vertices)
        self.vertices_y[self.vertex_row_idx - self.vertices_start] = point[0]
        self.vertices_x[self.vertex_row_idx - self.vertices_start] = point[1]
        if not isnan(point[2]):
            self.vertices_z[self.vertex_row_idx - self.vertices_start] = point[2]
            if not isnan(point[3]):
                self.vertices_m[self.vertex_row_idx - self.vertices_start] = point[3]
        self.vertices_id[self.vertex_row_idx - self.vertices_start] = self.vertex_id_no
        self.vertex_row_idx += 1
        
    cdef append_triangle(State self, long long triangle[3]):
        end = self.triangles.index.max() if self.triangles is not None else -1
        if self.triangle_row_idx > end:
            self.triangles = pd.DataFrame(index=pd.RangeIndex(end + 1, end + 1 + self.chunk_size), columns=(0, 1, 2,), dtype=int, data=-1)
            self.triangles_0 = self.triangles[0].values
            self.triangles_1 = self.triangles[1].values
            self.triangles_2 = self.triangles[2].values
            self.triangles_start = end + 1
            self.surface["triangles"].append(self.triangles)
        self.triangles_0[self.triangle_row_idx - self.triangles_start] = triangle[0]
        self.triangles_1[self.triangle_row_idx - self.triangles_start] = triangle[1]
        self.triangles_2[self.triangle_row_idx - self.triangles_start] = triangle[2]
        self.triangle_row_idx += 1

cdef char *getAttrValueC(libxml.const_xmlChar **atts, libxml.const_xmlChar *name):
    while atts[0]:
        if strcmp(<char *>atts[0], <char *>name) == 0:
            return <char *>atts[1]
        atts += 2
    return NULL

cdef str getAttrValue(libxml.const_xmlChar **atts, libxml.const_xmlChar *name):
    cdef char *res = getAttrValueC(atts, name)
    if not res:
        return None
    return (<bytes>res).decode("utf-8")

cdef dict getAttrValues(libxml.const_xmlChar **atts):
    cdef dict res = {} 
    while atts and atts[0] and atts[1]:
         res[(<bytes>atts[0]).decode("utf-8")] = (<bytes>atts[1]).decode("utf-8")
         atts += 2
    return res

cdef void land_xml_startElementSAX(void* ctx, libxml.const_xmlChar* name, libxml.const_xmlChar** atts):
    cdef State state = <State>ctx
    cdef char is_p
    cdef char *idstr
    
    state.path.append((<bytes>name).decode("utf-8"))
    if state.path[:2] == ["LandXML", "Surfaces"]:
        if state.path == ["LandXML", "Surfaces", "Surface"]:
            state.surfaces[getAttrValue(atts, b"name")] = state.surface = {
                "vertices": [],
                "triangles": []
            }
            state.vertices = None
            state.triangles = None
            state.vertex_row_idx = 0
            state.triangle_row_idx = 0
        is_p = strcmp(<char *>name, b"P") == 0
        if is_p or (strcmp(<char *>name, b"F") == 0):
            state.content[0] = 0
            state.content_pos = 0
            if is_p:
                idstr = getAttrValueC(atts, b"id")
                if idstr:
                    state.vertex_id_no = atoi(idstr)
                else:
                    state.vertex_id_no = -1

        pass
    else:
        state.add_meta(state.path[1:], state.meta, getAttrValues(atts))

    #print((<bytes>name).decode("utf-8"))

cdef void land_xml_endElementSAX(void* ctx, libxml.const_xmlChar* name):
    cdef State state = <State>ctx
    cdef double[4] point = [NAN, NAN, NAN, NAN]
    cdef long long[3] triangle = [-47, -47, -47]
    cdef int i

    if strcmp(<char *>name, b"P") == 0:
        for i, val in enumerate((<bytes>state.content).strip().split(b" ")):
            point[i] = atof(val)
        state.append_point(point)
        state.content[0] = 0
        state.content_pos = 0
    elif strcmp(<char *>name, b"F") == 0:
        for i, val in enumerate((<bytes>state.content).strip().split(b" ")):
            triangle[i] = atoll(val)
        state.append_triangle(triangle)
        state.content[0] = 0
        state.content_pos = 0
    elif strcmp(<char *>name, b"Surface") == 0:
        state.surface["vertices"] = pd.concat(state.surface["vertices"]).loc[:state.vertex_row_idx - 1]
        state.surface["triangles"] = pd.concat(state.surface["triangles"]).loc[:state.triangle_row_idx - 1]

        state.surface['vertices'].set_index('id', drop=False,verify_integrity=True, inplace=True)
        state.surface['vertices'].index.rename(None, inplace=True)
        if state.reindex_points:
            state.surface['vertices'], state.surface['triangles'] = reindex(state.surface['vertices'],
                                                                            state.surface['triangles'])

    state.path.pop()

    #print("/" + (<bytes>name).decode("utf-8"))


cdef void land_xml_characters(void *ctx, libxml.const_xmlChar *ch, int len):
    cdef State state = <State>ctx

    if state.content_pos + len >= CONTENT_BUFFER_SIZE:
        return
    strncpy(state.content + state.content_pos, <char *>ch, len)
    state.content_pos += len
    state.content[state.content_pos] = 0
    
cdef libxml.xmlSAXHandler land_xml_handler

land_xml_handler.startElement = <libxml.startElementSAXFunc>land_xml_startElementSAX
land_xml_handler.endElement = <libxml.endElementSAXFunc>land_xml_endElementSAX
land_xml_handler.characters = <libxml.charactersSAXFunc>land_xml_characters

def parse(filename, chunk_size = 10240, reindex_points=True):
    cdef State state = State(chunk_size=chunk_size, reindex_points=reindex_points)

    # Levanger_terrain_tri_high_res_2020juni_rev02_Surface.xml
    filename = filename.encode("utf-8")
    if libxml.xmlSAXUserParseFile(&land_xml_handler, <void *>state, filename) < 0:
        raise Exception("Parser failure")
    else:
        return {"meta": state.meta,
                "surfaces":  state.surfaces}
