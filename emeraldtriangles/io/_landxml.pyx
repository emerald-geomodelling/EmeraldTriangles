import pandas as pd
import numpy as np

cimport numpy as np
cimport cpython.bytes
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
    cdef int vertices_start

    cdef object triangles
    cdef np.ndarray triangles_0
    cdef np.ndarray triangles_1
    cdef np.ndarray triangles_2
    cdef int triangles_start
    
    cdef char content[CONTENT_BUFFER_SIZE]
    cdef size_t content_pos
    cdef int vertice_idx
    cdef int triangle_idx
    
    def __init__(self, chunk_size = 10240):
        self.chunk_size = chunk_size
        self.path = []
        self.meta = {}
        self.surfaces = {}
        self.content[0] = 0
        self.content_pos = 0
        
    def add_meta(self, path, meta, attributes):
        if len(path) == 0:
            meta.update(attributes)
        else:
            if path[0] not in meta:
                meta[path[0]] = {}
            self.add_meta(path[1:], meta[path[0]], attributes)
        
    cdef append_point(State self, double point[4]):
        end = self.vertices.index.max() if self.vertices is not None else -1
        if self.vertice_idx > end:
            self.vertices = pd.DataFrame(index=pd.RangeIndex(end + 1, end + 1 + self.chunk_size), columns=("Y", "X", "Z", "M"), dtype=float)
            self.vertices_x = self.vertices["X"].values
            self.vertices_y = self.vertices["Y"].values
            self.vertices_z = self.vertices["Z"].values
            self.vertices_m = self.vertices["M"].values
            self.vertices_start = end + 1
            self.surface["vertices"].append(self.vertices)
        self.vertices_y[self.vertice_idx - self.vertices_start] = point[0]
        self.vertices_x[self.vertice_idx - self.vertices_start] = point[1]
        self.vertices_z[self.vertice_idx - self.vertices_start] = point[2]
        self.vertices_m[self.vertice_idx - self.vertices_start] = point[3]
        self.vertice_idx += 1

    cdef append_triangle(State self, long long triangle[3]):
        end = self.triangles.index.max() if self.triangles is not None else -1
        if self.triangle_idx > end:
            self.triangles = pd.DataFrame(index=pd.RangeIndex(end + 1, end + 1 + self.chunk_size), columns=(0, 1, 2), dtype=int, data=-1)
            self.triangles_0 = self.triangles[0].values
            self.triangles_1 = self.triangles[1].values
            self.triangles_2 = self.triangles[2].values
            self.triangles_start = end + 1
            self.surface["triangles"].append(self.triangles)
        self.triangles_0[self.triangle_idx - self.triangles_start] = triangle[0]-1 # LandXML points are numbered from 1, not 0
        self.triangles_1[self.triangle_idx - self.triangles_start] = triangle[1]-1
        self.triangles_2[self.triangle_idx - self.triangles_start] = triangle[2]-1
        self.triangle_idx += 1

cdef str getAttrValue(libxml.const_xmlChar **atts, libxml.const_xmlChar *name):
    while atts[0]:
        if strcmp(<char *>atts[0], <char *>name) == 0:
            return (<bytes>atts[1]).decode("utf-8")
        atts += 2
    return None

cdef dict getAttrValues(libxml.const_xmlChar **atts):
    cdef dict res = {} 
    while atts and atts[0] and atts[1]:
         res[(<bytes>atts[0]).decode("utf-8")] = (<bytes>atts[1]).decode("utf-8")
         atts += 2
    return res

cdef void land_xml_startElementSAX(void* ctx, libxml.const_xmlChar* name, libxml.const_xmlChar** atts):
    cdef State state = <State>ctx
    
    state.path.append((<bytes>name).decode("utf-8"))
    if state.path[:2] == ["LandXML", "Surfaces"]:
        if state.path == ["LandXML", "Surfaces", "Surface"]:
            state.surfaces[getAttrValue(atts, b"name")] = state.surface = {
                "vertices": [],
                "triangles": []
            }
            state.vertices = None
            state.triangles = None
            state.vertice_idx = 0
            state.triangle_idx = 0
        if (strcmp(<char *>name, b"P") == 0) or (strcmp(<char *>name, b"F") == 0):
            state.content[0] = 0
            state.content_pos = 0
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
        state.surface["vertices"] = pd.concat(state.surface["vertices"]).loc[:state.vertice_idx - 1]
        state.surface["triangles"] = pd.concat(state.surface["triangles"]).loc[:state.triangle_idx - 1]
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

def parse(filename):
    cdef State state = State()

    # Levanger_terrain_tri_high_res_2020juni_rev02_Surface.xml
    filename = filename.encode("utf-8")
    if libxml.xmlSAXUserParseFile(&land_xml_handler, <void *>state, filename) < 0:
        raise Exception("Parser failure")
    else:
        return {"meta": state.meta,
                "surfaces":  state.surfaces}
