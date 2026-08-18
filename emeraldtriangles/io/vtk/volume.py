import warnings

import pandas as pd
import numpy as np
import itertools
import logging
import pyvista
import vtk
import re

logger = logging.getLogger(__name__)

def split_layer_columns(df):
    # Only string column labels can be per-layer ("name_0", "name_1", ...). Guard against
    # non-string labels (e.g. a stray float/NaN column), which re.match cannot accept; these
    # fall through to per_position_cols.
    per_layer_cols = [col for col in df.columns
                      if isinstance(col, str) and re.match(r"^.*?[(\[]?[0-9]+[)\]]?$", col)]
    per_position_cols = [col for col in df.columns if not col in per_layer_cols]

    colgroups = {}
    for col in per_layer_cols:
        group = re.match(r"^(.*?)[(\[]?[0-9]+[)\]]?$", col).groups()[0]
        if group not in colgroups: colgroups[group] = []
        colgroups[group].append(col)

    def move_single_member_groups(colgroups,per_position_cols):
        """
        Catches cases where there may be a lone group with a numerical suffix that gets mistaken as a sequence of layers
        representing values varying in depth.
        :param colgroups:
        :param per_position_cols:
        :return:
        """
        groups_to_move = []
        for group_name, group_list in colgroups.items():
            if len(group_list)<2:
                groups_to_move.append(group_name)
        for group_name in groups_to_move:
            per_position_cols += colgroups[group_name]
            del colgroups[group_name]

    move_single_member_groups( colgroups,per_position_cols)

    def sort_by_dict_values_length(my_dict):
        # Sorting the keys by the length of their corresponding lists in descending order
        sorted_keys = sorted(my_dict.keys(), key=lambda k: len(my_dict[k]), reverse=True)

        # Creating a new dictionary with sorted keys
        sorted_dict = {k: my_dict[k] for k in sorted_keys}
        return sorted_dict

    colgroups = sort_by_dict_values_length(colgroups)


    def columns_to_layers(columns):
        layers = np.array([int(re.match(r"^.*?[(\[]?([0-9]+)[)\]]?$", col).groups()[0]) for col in columns])
        layers -= np.min(layers)
        return dict(zip(columns, layers))
        
    colgroups = {key.strip("_"):
                 df[columns].rename(
                     columns = columns_to_layers(columns))
                 for key, columns in colgroups.items()}

    return df[per_position_cols], colgroups
    

def _validate_cell_indices(cell_indices, corner_cols, point_arrays):
    """Check that every cell found all six of its corner points, and return integer indices.

    The corner indices are produced by left-merging each cell corner against the melted
    per-layer point table, so a corner whose (vertex_id, layer_id) pair is missing from that
    table comes back as NaN -- which also promotes the whole array to float. VTK requires
    integer indices, so an unchecked array surfaces much later as an opaque
    ``TypeError: Indices must be either a mask or an integer array-like`` from pyvista, which
    says nothing about the missing points. Fail here instead, naming the likely cause.

    The usual cause is that the per-layer columns did not group: ``split_layer_columns``
    matches a *trailing integer*, so columns named e.g. ``res_0.0`` (a float layer index
    upstream) or ``label_nan`` are each treated as a single-member group and discarded,
    leaving the melted table nearly empty.
    """
    if np.issubdtype(cell_indices.dtype, np.integer):
        return cell_indices

    missing = pd.isna(cell_indices)
    if not missing.any():
        # Float dtype but every corner resolved -- safe to restore the integer indices VTK
        # needs, but the float dtype itself means something upstream promoted integer IDs,
        # so leave a breadcrumb rather than repairing it silently.
        warnings.warn(
            'Cell corner indices arrived as floats but are complete; cast back to integer. '
            'The output mesh is unaffected, but this suggests vertex or layer IDs were '
            'float-promoted somewhere upstream -- worth investigating if unexpected.')
        return cell_indices.astype(np.int64)

    incomplete = missing.any(axis=1)
    per_corner = ', '.join(f'{name}={int(n)}'
                           for name, n in zip(corner_cols, missing.sum(axis=0)))
    n_layer_cols = sum(1 for col in point_arrays.columns if str(col).endswith('_layer'))
    raise ValueError(
        f'{int(incomplete.sum())} of {len(cell_indices)} cells '
        f'({incomplete.mean():.1%}) reference points that are missing from the melted '
        f'per-layer table, so their corner indices are NaN (missing per corner: {per_corner}). '
        f'The melted table has {n_layer_cols} per-layer column(s) and {len(point_arrays)} rows. '
        'This usually means the per-layer columns of tin["vertices"] did not group: '
        'split_layer_columns groups on a trailing integer, so names like "res_0.0" or '
        '"res_nan" are discarded as single-member groups. Check that the layer index used to '
        'build those column names is an integer.')


def to_meshdata(tin, layer_depths, x_col="X", y_col="Y", z_col="Z"):
    """Layer depths is a list of offsets from z_col. Values are
    subtracted from z_col, so positive numbers mean downwards."""

    layer_depths = np.array(layer_depths)
    
    layer_thicknesses = np.concatenate(([0], layer_depths[:-1])) - layer_depths

    n_layers = len(layer_depths)    
    lyr_ids = np.arange(n_layers)

    vertices = tin['vertices'].copy()
    triangles = tin['triangles'].copy()

    # Remove vertices with no z coord (and triangles using them)
    v_index_name = vertices.index.name
    if v_index_name is None: v_index_name='index'
    vertices = vertices.loc[~vertices[z_col].isna()].reset_index()
    index_mapping = vertices[[v_index_name]].rename(columns={v_index_name : "old_index"}).reset_index().set_index("old_index")["index"]
    triangles = triangles.loc[triangles[0].isin(index_mapping.index)
                              & triangles[1].isin(index_mapping.index)
                              & triangles[2].isin(index_mapping.index)]
    for col in (0, 1, 2):
        triangles[col] = index_mapping.loc[triangles[col]].values

    vertices['vertex_id'] = vertices.index
    vertices, per_layer_dfs =  split_layer_columns(vertices)
    if not per_layer_dfs:
        raise ValueError(
            'No per-layer columns were found on tin["vertices"], so there is no depth data to '
            'build a volume from. split_layer_columns groups columns on a *trailing integer*, so '
            'names like "res_0.0" (a float layer index upstream) or "res_nan" are each treated as '
            'a single-member group and discarded. Check that the layer index used to build these '
            'column names is an integer.')
    dfs = []
    for idx, (name, per_layer_df) in enumerate(per_layer_dfs.items()):
        dfs.append(per_layer_df.assign(
            vertex_id=vertices.vertex_id
        ).melt(
            id_vars=['vertex_id'],
            value_name="%s_layer" % name,
            var_name="layer_id"
        ).drop(columns=[] if idx == 0 else ["vertex_id", "layer_id"]))

    df = pd.concat(dfs, axis=1)
    df = df.dropna(subset=["vertex_id", "layer_id"]).astype({"layer_id": int})
    
    df['layer_thickness'] = layer_thicknesses[df.layer_id.values]
    df['layer_bottom_depth'] = np.abs(layer_depths[df.layer_id.values])
    df = df.merge(vertices.drop(columns=['vertex_id']), left_on='vertex_id', right_index=True)
    df['point_z'] = df[z_col] - df.layer_bottom_depth
    df['point_depth'] = df[z_col] - df['point_z']

    # Add dummy copy of points for top face of volumetric cells (triangular prisms)

    df_dummy = df.loc[df.layer_id == 0].copy()
    df_dummy['layer_id'] = -1
    df_dummy['layer_bottom_depth'] = 0
    df_dummy['point_z'] = df_dummy[z_col]
    df = pd.concat([df, df_dummy], ignore_index=True)

    df = df.reset_index()
    df['vertex_id_3d'] = df.index

    # -----------------------------------------------------------------------
    # Generate cell geometry

    # generate table of cells with n_layers * triangles rows
    series = [tin['triangles'].index, lyr_ids]
    df_cell = pd.DataFrame(list(itertools.product(*series)), columns=['triangle_id', 'layer_id'])
    df_cell['layer_id_top'] = df_cell.layer_id - 1

    # generate array of point IDS for the six vertices of each cell
    df_cell = df_cell.merge(triangles, left_on='triangle_id', right_index=True)

    lookup_dict = {
        '0_3d': {'vertex_id_col': 0, 'layer_id_col': 'layer_id', },
        '1_3d': {'vertex_id_col': 1, 'layer_id_col': 'layer_id', },
        '2_3d': {'vertex_id_col': 2, 'layer_id_col': 'layer_id', },
        '3_3d': {'vertex_id_col': 0, 'layer_id_col': 'layer_id_top', },
        '4_3d': {'vertex_id_col': 1, 'layer_id_col': 'layer_id_top', },
        '5_3d': {'vertex_id_col': 2, 'layer_id_col': 'layer_id_top', }
    }

    for k in lookup_dict.keys():
        vertex_id_col = lookup_dict[k]['vertex_id_col']
        layer_id_col = lookup_dict[k]['layer_id_col']
        df_cell = df_cell.merge(df.loc[:, ['layer_id', 'vertex_id', 'vertex_id_3d']],
                                left_on=[vertex_id_col, layer_id_col],
                                right_on=['vertex_id', 'layer_id'],
                                how='left',
                                suffixes=['', '_copy'])
        df_cell = df_cell.drop(columns=['vertex_id', 'layer_id_copy'], errors='ignore')
        df_cell = df_cell.rename(columns={'vertex_id_3d': k})

    # -----------------------------------------------------------------------
    # Reformat geometry for vtk output
    
    point_coordinates = df[[x_col, y_col, 'point_z']].to_numpy()
    corner_cols = ['0_3d', '1_3d', '2_3d', '3_3d', '4_3d', '5_3d']
    cell_indices_np = _validate_cell_indices(df_cell[corner_cols].to_numpy(), corner_cols, df)
    num_nodes = np.full((cell_indices_np.shape[0], 1), 6, dtype=np.int64)

    cells_out_vtk = np.concatenate( (num_nodes,cell_indices_np), axis=1)
    cell_types_out_vtk = np.full((cell_indices_np.shape[0], 1), vtk.VTK_WEDGE, dtype=np.int64)

    return {
        "cells": cells_out_vtk,
        "celltypes": cell_types_out_vtk,
        "points": point_coordinates,
        "point_arrays": df,
        "cell_arrays":df_cell
    }


def to_pyvista(tin, *arg, **kw):
    meshdata = to_meshdata(tin, *arg, **kw)
    m = pyvista.UnstructuredGrid(meshdata["cells"], meshdata["celltypes"], meshdata["points"])
    for col in meshdata["point_arrays"].columns:
        #if col == "label_layer":
         #   print('Appending point arrays label layer')
          #  m.point_arrays[col] = meshdata["point_arrays"][col]
        # if meshdata["point_arrays"][col].dtype == object:
        #     continue
        try:
            m.point_data[str(col)] = meshdata["point_arrays"][col]
        except UnicodeEncodeError:
            warnings.warn(f'Encountered UnicodeEncodeError with {col}.Skipping...')
    for col in meshdata["cell_arrays"].columns:
        #if col == "label_layer":
         #   print('Appending cell arrays label layer')
          #  m.cell_arrays[col] = meshdata["cell_arrays"][col]
        # if meshdata["cell_arrays"][col].dtype != float:
        #     #print('cell array dtype not float', col)
        #     continue
        try:
            m.cell_data[str(col)] = meshdata["cell_arrays"][col]
        except UnicodeEncodeError:
            warnings.warn(f'Encountered UnicodeEncodeError with {col}.Skipping...')
    return m
