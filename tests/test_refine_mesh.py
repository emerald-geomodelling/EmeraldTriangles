"""Regression tests for emeraldtriangles.refine_mesh.

Covers:

* ``interpolate_vertices`` — inverse-distance interpolation of vertex attributes onto
  new vertices, and specifically the set -> list column-indexer fix (pandas >= 2.0
  raises ``TypeError: Passing a set as an indexer is not supported``).
* ``replace_triangles`` + ``supplant_triangles`` — an end-to-end smoke test that
  exercises the ``DataFrame.append`` -> ``pd.concat`` forward-port across
  refine_mesh / boundary / cleanup (the old code raised ``AttributeError`` here).
"""
import numpy as np
import pandas as pd

import emeraldtriangles as et
import emeraldtriangles.refine_mesh as refine_mesh
import example_data


def test_interpolate_vertices_equidistant_mean():
    # Center vertex (index 0) interpolated from four equidistant neighbours whose
    # 'color' attribute is known; equal distances -> a plain mean of 10/20/30/40.
    vertices = pd.DataFrame(
        {"X": [0.0, 1.0, 0.0, -1.0, 0.0],
         "Y": [0.0, 0.0, 1.0, 0.0, -1.0],
         "color": [np.nan, 10.0, 20.0, 30.0, 40.0]})
    triangles = pd.DataFrame({0: [0, 0, 0, 0], 1: [1, 2, 3, 4], 2: [2, 3, 4, 1]})
    tri = {"triangles": triangles, "vertices": vertices}

    res = refine_mesh.interpolate_vertices(tri, pd.Index([0]))

    # Correct interpolated value; also proves the set->list indexer line executed.
    assert np.isclose(res["vertices"].loc[0, "color"], 25.0)
    assert res["vertices"]["color"].notna().all()
    # Existing coordinates are left untouched.
    assert (res["vertices"]["X"] == vertices["X"]).all()
    assert (res["vertices"]["Y"] == vertices["Y"]).all()


def test_replace_and_supplant_triangles_runs():
    tri = {k: v.copy() for k, v in example_data.tri.items()}

    res = et.replace_triangles(**tri)
    assert len(res["triangles"]) > 0
    assert {"X", "Y"}.issubset(res["vertices"].columns)

    res2 = et.supplant_triangles(existing_boundary=False, **res)

    # A non-empty, self-consistent mesh with finite vertex attributes.
    assert len(res2["triangles"]) > 0
    assert len(res2["vertices"]) > 0
    assert {"X", "Y", "color"}.issubset(res2["vertices"].columns)
    assert np.isfinite(res2["vertices"]["color"].to_numpy()).all()
    # Triangle vertex indices reference valid vertex rows.
    idx = res2["triangles"][[0, 1, 2]].to_numpy()
    assert idx.min() >= 0
    assert idx.max() < len(res2["vertices"])
