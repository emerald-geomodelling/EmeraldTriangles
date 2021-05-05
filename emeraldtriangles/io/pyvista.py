import pandas as pd
import numpy as np
import pyvista
import vtk

def to_meshdata(tri, x_col="X", y_col="Y", z_col="Z"):
    vertices = tri['vertices']
    triangles = tri['triangles']
    if z_col not in vertices.columns:
        vertices = vertices.assign(**{z_col: 0})
    point_coordinates = vertices.loc[:,[x_col,y_col,z_col]].to_numpy()
    cell_indices_np = triangles[[0,1,2]].to_numpy()
    
    num_nodes = np.ones((cell_indices_np.shape[0],1), dtype=np.int)*3

    cells_out_vtk = np.concatenate((num_nodes,cell_indices_np),axis=1)
    cell_types_out_vtk = np.full((cell_indices_np.shape[0],1), vtk.VTK_TRIANGLE, dtype=np.int)

    return {
        "cells": cells_out_vtk,
        "celltypes": cell_types_out_vtk,
        "points": point_coordinates,
        "point_arrays": vertices,
        "cell_arrays": triangles
    }

def to_pyvista(tri, **kw):
    meshdata = to_meshdata(tri, **kw)
    m = pyvista.UnstructuredGrid(meshdata["cells"], meshdata["celltypes"], meshdata["points"])
    for col, dtype in meshdata["point_arrays"].dtypes.items():
        if dtype != float: continue
        m.point_arrays[col] = meshdata["point_arrays"][col]
    for col, dtype in meshdata["cell_arrays"].dtypes.items():
        if dtype != float: continue
        m.cell_arrays[col] = meshdata["cell_arrays"][col]
    return m
