<img src="example.png" align="right"></image>

# EmeraldTriangles

This library provides transformations for triangle meshes built on top
of
[scipy.spatial.Delaunay](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.Delaunay.html)
and [Triangle](https://rufat.be/triangle/):

  * Insert points (nodes) in an existing mesh, splitting any triangles
    that points fall into.
    * Meshes created this way might not be Delaunay, but any new
      connected set of triangles added will be Delaunay if viewed in
      isolation (without the pre-existing mesh).
  * Extend a mesh outwards to include new points.
    * The extension to the mesh will be a constrained delaunay.
  * Calculate the boundary polygon of a mesh.
  
This library uses a similar data structure to the Triangles library
above, but replaces numpy arrays with pandas dataframes, preserving
any extra columns across operations. It also contains a plotting
function similar to the one in the Triangle library, that supports
color attributes for vertices as well as triangle faces.

In addition, EmeraldTriangles provides import and export functionality
for

  * LandXML (import and export, no extra columns)
  * VTK (only export)

# Documentation

Documentation is provided in the form of a [jupyter notebook with
example
usages](https://github.com/EMeraldGeo/EmeraldTriangles/blob/master/Example%20usage.ipynb)
as well as in docstrings accesible with the python help() function.
