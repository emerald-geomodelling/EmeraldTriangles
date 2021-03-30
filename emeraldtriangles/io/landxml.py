import lxml.etree as ET
import pandas as pd
import numpy as np
import xml.sax
try:
    from emeraldtriangles.io._landxml import parse
except:
    class LandXMLHandler(xml.sax.ContentHandler):
        chunk_size = 1024

        def __init__(self):
            self.path = []
            self.meta = {}
            self.surfaces = {}
            self.content = ""

        def add_meta(self, path, meta, attributes):
            if len(path) == 0:
                meta.update(attributes)
            else:
                if path[0] not in meta:
                    meta[path[0]] = {}
                self.add_meta(path[1:], meta[path[0]], attributes)

        def startElement(self, tag, attributes):
            self.path.append(tag)
            if self.path[:2] == ["LandXML", "Surfaces"]:
                if self.path == ["LandXML", "Surfaces", "Surface"]:
                    self.surfaces[attributes["name"]] = self.surface = {
                        "vertices": [],
                        "triangles": []
                    }
                    self.vertices = None
                    self.triangles = None
                    self.vertice_idx = 0
                    self.triangle_idx = 0
                if tag in ("P", "F"):
                    self.content = ""
            else:
                self.add_meta(self.path[1:], self.meta, attributes)

        def endElement(self, tag):
            if tag == "P":
                self.append_point([float(val) for val in self.content.strip().split(" ")])
                self.content = ""
            elif tag == "F":
                self.append_triangle([int(val) for val in self.content.strip().split(" ")])
                self.content = ""
            elif tag == "Surface":
                self.surface["vertices"] = pd.concat(self.surface["vertices"]).loc[:self.vertice_idx - 1]
                self.surface["triangles"] = pd.concat(self.surface["triangles"]).loc[:self.triangle_idx - 1]
            self.path.pop()

        def characters(self, content):
            self.content += content

        def append_point(self, point):
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
            if len(point) > 2:
                self.vertices_z[self.vertice_idx - self.vertices_start] = point[2]
                if len(point) > 3:
                    self.vertices_m[self.vertice_idx - self.vertices_start] = point[3]
            self.vertice_idx += 1

        def append_triangle(self, triangle):
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

    def parse(xmlfile):
        parser = xml.sax.make_parser()
        parser.setFeature(xml.sax.handler.feature_namespaces, 0)
        handler = LandXMLHandler()
        parser.setContentHandler(handler)
        parser.parse(xmlfile)
        return {"meta": handler.meta, "surfaces": handler.surfaces}

def dump(landxmldict, filename):
    # Adapted from http://www.knickknackcivil.com/tin2landxml.html

    # Initializing landxml surface items
    landxml = ET.Element('LandXML')
    units = ET.SubElement(landxml, 'Units')
    surfaces = ET.SubElement(landxml, 'Surfaces')

    default_units = {"Metric": {
        "areaUnit": 'squareMeter',
        "linearUnit": 'meter',
        "volumeUnit": 'cubicMeter',
        "temperatureUnit": 'celsius',
        "pressureUnit": 'mmHG'}}
    for key, values in landxmldict.get("meta", {}).get("Units", default_units).items():
        ET.SubElement(units, key, **values)

    if "CoordinateSystem" in landxmldict.get("meta", {}):
        ET.SubElement(landxml, 'CoordinateSystem', **landxmldict.get("meta", {})['CoordinateSystem'])
                     
    for surf_name, tin in landxmldict["surfaces"].items():
        surface = ET.SubElement(surfaces, 'Surface', name=surf_name)
        definition = ET.SubElement(surface, 'Definition', surfType="TIN")
        pnts = ET.SubElement(definition, 'Pnts')
        faces = ET.SubElement(definition, 'Faces')

        # Initializing output variables
        pnt_dict = {}
        face_list = []
        cnt = 0

        # Writing faces to landxml
        for cnt, vertice in tin["vertices"].iterrows():
            if "Z" in tin["vertices"].columns:
                coord = vertice[["Y", "X", "Z"]].values
            else:
                coord = vertice[["Y", "X"]].values
            # Individual point landxml features
            pnt_text = " ".join(coord.astype(str))
            pnt = ET.SubElement(pnts, 'P', id=str(cnt + 1)).text = pnt_text
        triangles = tin["triangles"].copy()
        triangles[[0, 1, 2]] += 1
        for idx, triangle in triangles.iterrows():
            ET.SubElement(faces, 'F').text = " ".join(triangle[[0, 1, 2]].astype(int).astype(str))
            
    tree = ET.ElementTree(landxml)
    tree.write(filename, pretty_print=True, xml_declaration=True, encoding="iso-8859-1")
    

if __name__ == "__main__":
    import yaml
    import sys
    
    data = parse(sys.argv[1])
    
    print(yaml.dump(data["meta"]))

    tins = data["surfaces"]

    print()
    for key in tins.keys():
        print("%s:" % (key,))
        print("Vertices:")
        print(tins[key]["vertices"].head())
        print("Triangles:")
        print(tins[key]["triangles"].head())
        print()
