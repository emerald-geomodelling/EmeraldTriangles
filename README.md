# EmeraldTriangles

This library provides transformations for triangle meshes build on top of scipy.spatial.Delaunay:

  * Insert points (nodes) in an existing mesh, splitting any triangles that points fall into.
  * Extend a mesh outwards to include new points.
  * Calculate the boundary polygon of a mesh.
  
Meshes created this way might not be Delaunay, but any new connected set of triangles added will be Delaunay if viewed in isolation (without the pre-existing mesh).
