"""cleanup_tin (#36) and the lowercase x/y plotting fix (#36)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import emeraldtriangles.plotting as plotting
from emeraldtriangles.cleanup import INDEX_COLUMNS, cleanup_tin


def square_tin(uppercase=True):
    """Two triangles over four corners, plus one vertex no triangle references."""
    x, y = ("X", "Y") if uppercase else ("x", "y")
    v = pd.DataFrame({x: [0., 1., 0., 1., 5.], y: [0., 0., 1., 1., 5.]})
    t = pd.DataFrame({0: [0, 1], 1: [1, 3], 2: [2, 2]})
    return {"vertices": v, "triangles": t, "meta": {"projection": 25833}}


# --------------------------------------------------------------------------------------------
# cleanup_tin
# --------------------------------------------------------------------------------------------
def test_drops_the_unused_vertex_and_reindexes():
    tin = cleanup_tin(square_tin())
    assert len(tin["vertices"]) == 4                      # the stray vertex is gone
    assert list(tin["vertices"].index) == [0, 1, 2, 3]    # natural index
    assert tin["triangles"][[0, 1, 2]].to_numpy().max() < 4


def test_corner_columns_come_back_as_int64():
    tin = cleanup_tin(square_tin())
    for c in (0, 1, 2):
        assert tin["triangles"][c].dtype == np.int64


def test_bookkeeping_columns_are_removed():
    tin = square_tin()
    tin["vertices"]["index_orig"] = np.arange(len(tin["vertices"]))
    tin["vertices"]["vertex_id_orig"] = np.arange(len(tin["vertices"]))
    out = cleanup_tin(tin)
    assert not (set(INDEX_COLUMNS) & set(out["vertices"].columns))


def test_triangles_referencing_missing_vertices_are_dropped():
    tin = square_tin()
    tin["triangles"] = pd.concat(
        [tin["triangles"], pd.DataFrame({0: [0], 1: [1], 2: [99]})], ignore_index=True)
    out = cleanup_tin(tin)
    assert len(out["triangles"]) == 2                     # the dangling triangle is gone
    assert out["triangles"][[0, 1, 2]].to_numpy().max() < len(out["vertices"])


def test_other_keys_and_vertex_attributes_survive():
    tin = square_tin()
    tin["vertices"]["Z"] = np.arange(5.0)
    out = cleanup_tin(tin)
    assert out["meta"]["projection"] == 25833
    assert list(out["vertices"]["Z"]) == [0.0, 1.0, 2.0, 3.0]   # the stray vertex's Z=4 dropped


def test_already_clean_tin_is_unchanged():
    tin = square_tin()
    tin["vertices"] = tin["vertices"].iloc[:4].copy()
    before = tin["vertices"].copy()
    out = cleanup_tin(tin)
    pd.testing.assert_frame_equal(out["vertices"], before, check_dtype=False)
    assert len(out["triangles"]) == 2


# --------------------------------------------------------------------------------------------
# plotting accepts either coordinate convention
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("uppercase", [True, False])
def test_plot_accepts_both_coordinate_conventions(uppercase):
    tin = square_tin(uppercase=uppercase)
    fig, ax = plt.subplots()
    try:
        plotting.plot(ax, vertices=tin["vertices"], triangles=tin["triangles"])
    finally:
        plt.close(fig)


@pytest.mark.parametrize("uppercase", [True, False])
def test_vertices_and_points_accept_both(uppercase):
    tin = square_tin(uppercase=uppercase)
    fig, ax = plt.subplots()
    try:
        plotting.vertices(ax, vertices=tin["vertices"])
        plotting.points(ax, points=tin["vertices"])
    finally:
        plt.close(fig)


def test_missing_coordinates_raise_a_named_error():
    fig, ax = plt.subplots()
    try:
        with pytest.raises(KeyError, match="neither X/Y nor x/y"):
            plotting.vertices(ax, vertices=pd.DataFrame({"a": [1.0], "b": [2.0]}))
    finally:
        plt.close(fig)


def test_uppercase_wins_when_a_frame_carries_both():
    v = pd.DataFrame({"X": [0., 1.], "Y": [0., 1.], "x": [9., 9.], "y": [9., 9.]})
    assert plotting._xy_columns(v) == ("X", "Y")
