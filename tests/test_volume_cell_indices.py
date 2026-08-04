"""Tests for cell-corner index validation in emeraldtriangles.io.vtk.volume.to_meshdata.

The corner indices come from left-merging each cell corner against the melted per-layer point
table. A corner whose (vertex_id, layer_id) pair is missing comes back NaN, which promotes the
index array to float. VTK needs integers, so without a check this surfaces much later as an
opaque pyvista ``TypeError: Indices must be either a mask or an integer array-like``.

The usual upstream cause is per-layer columns that fail to group -- ``split_layer_columns``
matches a trailing integer, so ``res_0.0`` (from a float layer index upstream) is treated as a
single-member group and discarded.
"""
import numpy as np
import pandas as pd
import pytest

from emeraldtriangles.io.vtk.volume import _validate_cell_indices, to_meshdata

LAYER_DEPTHS = [-5.0, -15.0, -25.0]
CORNER_COLS = ['0_3d', '1_3d', '2_3d', '3_3d', '4_3d', '5_3d']


def _tin(layer_suffixes=('0', '1', '2')):
    """Square of four vertices split into two triangles, with three per-layer `res` columns."""
    vertices = pd.DataFrame({
        'X': [0.0, 1.0, 1.0, 0.0],
        'Y': [0.0, 0.0, 1.0, 1.0],
        'Z': [100.0, 101.0, 102.0, 103.0],
    })
    for i, suffix in enumerate(layer_suffixes):
        vertices[f'res_{suffix}'] = np.arange(len(vertices), dtype=float) + i
    triangles = pd.DataFrame({0: [0, 0], 1: [1, 2], 2: [2, 3]})
    return {'vertices': vertices, 'triangles': triangles, 'meta': {'layer_depths': LAYER_DEPTHS}}


def test_integer_layer_suffixes_give_integer_cells():
    meshdata = to_meshdata(_tin(), LAYER_DEPTHS, x_col='X', y_col='Y', z_col='Z')
    cells = meshdata['cells']
    assert np.issubdtype(cells.dtype, np.integer)
    assert cells.shape == (len(_tin()['triangles']) * len(LAYER_DEPTHS), 7)
    assert (cells[:, 0] == 6).all()


def test_float_layer_suffixes_lose_every_group():
    """`res_0.0` style names are all discarded by split_layer_columns: nothing left to stack."""
    tin = _tin(layer_suffixes=('0.0', '1.0', '2.0'))
    with pytest.raises(ValueError) as excinfo:
        to_meshdata(tin, LAYER_DEPTHS, x_col='X', y_col='Y', z_col='Z')
    message = str(excinfo.value)
    assert 'No per-layer columns were found' in message
    assert 'trailing integer' in message


def test_short_surviving_group_reports_missing_corners():
    """The real-world shape: the genuine per-layer columns are lost to float suffixes, and a
    shorter non-layer group (`dist_corner_0`/`dist_corner_1`) survives and defines the melt.
    Cells then reference layers the melted table never had."""
    tin = _tin(layer_suffixes=('0.0', '1.0', '2.0'))
    tin['vertices']['dist_corner_0'] = 1.0
    tin['vertices']['dist_corner_1'] = 2.0
    with pytest.raises(ValueError) as excinfo:
        to_meshdata(tin, LAYER_DEPTHS, x_col='X', y_col='Y', z_col='Z')
    message = str(excinfo.value)
    assert 'corner indices are NaN' in message
    assert 'trailing integer' in message


def test_validate_cell_indices_passes_integers_through():
    cells = np.arange(12, dtype=np.int64).reshape(2, 6)
    out = _validate_cell_indices(cells, CORNER_COLS, pd.DataFrame({'res_layer': [0.0]}))
    assert out is cells


def test_validate_cell_indices_restores_complete_float_arrays():
    cells = np.arange(12, dtype=float).reshape(2, 6)
    out = _validate_cell_indices(cells, CORNER_COLS, pd.DataFrame({'res_layer': [0.0]}))
    assert np.issubdtype(out.dtype, np.integer)
    assert np.array_equal(out, cells.astype(np.int64))


def test_validate_cell_indices_reports_which_corners_are_missing():
    cells = np.arange(12, dtype=float).reshape(2, 6)
    cells[1, 3] = np.nan
    with pytest.raises(ValueError) as excinfo:
        _validate_cell_indices(cells, CORNER_COLS, pd.DataFrame({'res_layer': [0.0]}))
    message = str(excinfo.value)
    assert '1 of 2 cells' in message
    assert '3_3d=1' in message


if __name__ == '__main__':
    test_integer_layer_suffixes_give_integer_cells()
    test_validate_cell_indices_passes_integers_through()
    test_validate_cell_indices_restores_complete_float_arrays()
    print('all ok')
