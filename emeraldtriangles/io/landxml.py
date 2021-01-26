import xml.dom.minidom
import lxml.etree as ET
import pandas as pd
import numpy as np

def xml_to_dict(node, exclude = []):
    if node.nodeName in exclude: return {}
    res = dict(node.attributes.items())
    content = ''
    for child in node.childNodes:
        if child.nodeType == child.TEXT_NODE:
            content += '\n' + child.data
        else:
            res.update(xml_to_dict(child, exclude))
    content = content.strip()
    if content:
        if res:
            res["content"] = content
        else:
            res = content
    return {node.nodeName: res}
    
def parse(xmlfile):
    """Parses a LandXML file into a dictionary structure

        {
          "meta": { metadata from the landxml header },
          "surfaces": {name: TIN, ...}
        }

    where TIN is a TIN dictionary as used by the rest of this library.
    """
    

    doc = xml.dom.minidom.parse(xmlfile)

    surfaces = {}
    for surface_node in doc.getElementsByTagName('Surface'):
        surface = {}
        points = []
        for point_node in surface_node.getElementsByTagName('P'):
            coords = [float(val) for val in point_node.childNodes[0].data.split(" ")]
            # id = point_node.getAttributeNode("id").value
            points.append(coords)
        points = np.array(points)
        surface["vertices"] = pd.DataFrame(points, columns=("Y", "X", "Z", "M")[:points.shape[1]])

        triangles = []
        for triangle_node in surface_node.getElementsByTagName('F'):
            idxs = [int(val) for val in triangle_node.childNodes[0].data.split(" ")]
            triangles.append(idxs)
        surface["triangles"] = pd.DataFrame(triangles, columns=(0, 1, 2), dtype=int)
        surface["triangles"] = surface["triangles"] - 1 # LandXML points are numbered from 1, not 0

        surfaces[surface_node.getAttributeNode("name").value] = surface

    res = {"meta": xml_to_dict(doc.getElementsByTagName('LandXML')[0], ["Surfaces"])["LandXML"]}
    res["surfaces"] = surfaces
    
    return res

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
