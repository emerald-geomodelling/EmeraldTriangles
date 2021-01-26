import pandas as pd
import numpy as np

def dump(tri, filename):
    vertices = tri['vertices']
    if "Z" not in vertices.columns:
        vertices = vertices.assign(Z=0)
    point_coordinates = vertices.loc[:,['X','Y','Z']].to_numpy()
    cell_indices_np = tri['triangles'][[0,1,2]].to_numpy()
    
    num_nodes = np.ones((cell_indices_np.shape[0],1), dtype=np.int)*3

    cells_out_vtk = np.concatenate((num_nodes,cell_indices_np),axis=1)
    cell_types_out_vtk = np.ones((cell_indices_np.shape[0],1), dtype=np.int)*5

    with open(filename, 'w') as fid:
        print('# vtk DataFile Version 2.0', file=fid)
        print(tri.get("meta", {}).get("title", "Unnamed grid"), file=fid)
        print('ASCII', file=fid)

        fid.write('DATASET UNSTRUCTURED_GRID\n')

        print('POINTS', point_coordinates.shape[0], 'float', file=fid)
        np.savetxt(fid, point_coordinates, fmt='%.2f', delimiter=' ', newline='\n', )

        print('CELLS', cell_indices_np.shape[0], cells_out_vtk.size, file=fid)
        np.savetxt(fid, cells_out_vtk, fmt='%d', delimiter=' ', newline='\n')

        print('CELL_TYPES', cell_indices_np.shape[0], file=fid)
        np.savetxt(fid, cell_types_out_vtk, fmt='%d', delimiter=' ', newline='\n')

        print('POINT_DATA', tri['vertices'].shape[0], file=fid)
        for attr in tri['vertices'].columns:
            if attr in ("X", "Y", "Z"): continue
            print('SCALARS', attr, 'float 1', file=fid)
            print('LOOKUP_TABLE default', file=fid)
            np.savetxt(fid, tri['vertices'].loc[:, attr].to_numpy(), fmt='%f', delimiter=' ', newline='\n')
