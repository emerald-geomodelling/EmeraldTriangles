"""Regression tests for emeraldtriangles.sampling.sample_points.

These guard the indexing fixes made in sample_points:

* `points_and_triangles.point` / `.triangle` are *positional* row numbers, so rows
  are selected with ``.iloc`` and no natural ``0..n`` index is assumed.
* the triangle vertex-index columns are selected by *label* ``[0, 1, 2]``, so they
  stay correct even when ``triangles`` carries extra columns (e.g. ``area``).
* the interpolation write-back uses a single positional indexer, so the result
  actually persists (the old chained ``.loc[:, col].iloc[...] =`` form silently
  wrote to a temporary under pandas copy-on-write).

Each assertion below fails on the pre-fix code (KeyError on the non-natural index,
wrong columns from positional selection, or dropped write-back).
"""
import numpy as np
import pandas as pd

import emeraldtriangles.sampling as sampling


def _linear(x, y):
    # A plane; barycentric interpolation of a linear field is exact.
    return 2.0 * x + 3.0 * y + 1.0


def test_sample_points_non_natural_index_and_extra_columns():
    # Unit square split into two triangles, vertices carry a linear field 'Z'.
    vertices = pd.DataFrame({"X": [0.0, 1.0, 1.0, 0.0],
                             "Y": [0.0, 0.0, 1.0, 1.0]})
    vertices["Z"] = _linear(vertices["X"], vertices["Y"])

    # triangles: vertex-index columns 0, 1, 2 with an extra 'area' column placed
    # FIRST and a deliberately non-natural row index. Positional column selection
    # would grab 'area'; label-based [0, 1, 2] must still pick the vertex indices.
    triangles = pd.DataFrame(
        {"area": [0.5, 0.5], 0: [0, 0], 1: [1, 2], 2: [2, 3]},
        index=[100, 200])

    # Query points with a non-natural index; one strictly inside each triangle.
    points = pd.DataFrame({"X": [0.5, 0.25], "Y": [0.25, 0.5]}, index=[9, 99])

    out = sampling.sample_points(columns=["Z"], points=points.copy(),
                                 vertices=vertices, triangles=triangles)

    # Exact values prove the correct rows/columns were selected; notna proves the
    # write-back took effect.
    assert np.isclose(out["Z"].loc[9], _linear(0.5, 0.25))
    assert np.isclose(out["Z"].loc[99], _linear(0.25, 0.5))
    assert out["Z"].notna().all()
