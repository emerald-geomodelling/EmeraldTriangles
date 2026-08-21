"""Tests for the geometric triangle filter (issue #33) and the remove_unused_vertices dtype fix (#26)."""
import warnings

import numpy as np
import pandas as pd
import pytest

import emeraldtriangles as et
from emeraldtriangles import cleanup, refine_mesh


def _right_triangle_tin():
    # 3-4-5 right triangle: area 6, perimeter 12, angles 36.87 / 53.13 / 90 degrees
    vertices = pd.DataFrame({"X": [0.0, 4.0, 0.0], "Y": [0.0, 0.0, 3.0]})
    triangles = pd.DataFrame({0: [0], 1: [1], 2: [2]})
    return {"vertices": vertices, "triangles": triangles}


def _lattice_points(nx=6, ny=5, dx=10.0, dy=10.0, hole=((2, 4), (2, 4))):
    ix, iy = np.meshgrid(np.arange(nx), np.arange(ny), indexing="ij")
    pts = pd.DataFrame({"X": ix.ravel() * dx, "Y": iy.ravel() * dy, "value": (ix * 10 + iy).ravel().astype(float)})
    if hole is not None:
        (x0, x1), (y0, y1) = hole
        keep = ~((ix.ravel() >= x0) & (ix.ravel() < x1) & (iy.ravel() >= y0) & (iy.ravel() < y1))
        pts = pts.loc[keep].reset_index(drop=True)
    return pts


def test_triangle_metrics_hand_computed():
    tin = _right_triangle_tin()
    m = cleanup.triangle_metrics(tin["vertices"], tin["triangles"])
    assert m.index.equals(tin["triangles"].index)
    assert np.isclose(m.loc[0, "area"], 6.0)
    assert np.isclose(m.loc[0, "perimeter"], 12.0)
    assert np.isclose(m.loc[0, "max_side_length"], 5.0)
    assert np.isclose(m.loc[0, "min_side_length"], 3.0)
    assert np.isclose(m.loc[0, "min_angle_deg"], np.degrees(np.arctan(3 / 4)))
    # inradius of a 3-4-5 triangle is 1 -> aspect = 5 / 2
    assert np.isclose(m.loc[0, "aspect"], 2.5)


def test_triangle_metrics_degenerate_and_bad_index():
    vertices = pd.DataFrame({"X": [0.0, 1.0, 2.0], "Y": [0.0, 0.0, 0.0]})
    m = cleanup.triangle_metrics(vertices, pd.DataFrame({0: [0], 1: [1], 2: [2]}))
    assert m.loc[0, "area"] == 0 and np.isinf(m.loc[0, "aspect"])
    with pytest.raises(ValueError, match="reindex"):
        cleanup.triangle_metrics(vertices, pd.DataFrame({0: [0], 1: [1], 2: [7]}))


def test_remove_triangles_by_shape_removes_hull_slivers():
    pts = _lattice_points()
    tin = refine_mesh.points_to_tin(pts)
    m0 = cleanup.triangle_metrics(tin["vertices"], tin["triangles"])
    assert m0["max_side_length"].max() > np.hypot(10, 10) + 1e-6     # the hole is spanned
    out = cleanup.remove_triangles_by_shape(max_side_length=1.05 * np.hypot(10, 10), **tin)
    m1 = cleanup.triangle_metrics(out["vertices"], out["triangles"])
    assert m1["max_side_length"].max() <= 1.05 * np.hypot(10, 10)
    assert out["n_triangles_removed"] >= 1
    assert len(out["triangles"]) + out["n_triangles_removed"] == len(tin["triangles"])
    assert out["triangles"].index.equals(pd.RangeIndex(len(out["triangles"])))
    # vertices untouched; other keys passed through
    assert out["vertices"] is tin["vertices"]
    assert set(tin) <= set(out)
    # no triangle centroid inside the hole any more
    idx = out["triangles"][[0, 1, 2]].to_numpy()
    cx = out["vertices"]["X"].to_numpy()[idx].mean(axis=1)
    cy = out["vertices"]["Y"].to_numpy()[idx].mean(axis=1)
    assert not ((cx > 20) & (cx < 30) & (cy > 20) & (cy < 30)).any()


def test_remove_triangles_by_shape_criteria_and_metrics():
    pts = _lattice_points(hole=None)
    tin = refine_mesh.points_to_tin(pts)
    full = cleanup.remove_triangles_by_shape(**tin)
    assert full["n_triangles_removed"] == 0 and len(full["triangles"]) == len(tin["triangles"])
    by_area = cleanup.remove_triangles_by_shape(max_area=49.0, **tin)          # regular triangles have area 50
    assert len(by_area["triangles"]) == 0
    by_angle = cleanup.remove_triangles_by_shape(min_angle_deg=44.0, **tin)    # right isosceles: 45 degrees
    assert len(by_angle["triangles"]) == len(tin["triangles"])
    by_aspect = cleanup.remove_triangles_by_shape(max_aspect=2.0, **tin)       # right isosceles aspect ~ 2.41
    assert len(by_aspect["triangles"]) == 0
    with_metrics = cleanup.remove_triangles_by_shape(keep_metrics=True, **tin)
    assert {"area", "perimeter", "max_side_length", "min_angle_deg", "aspect"} <= set(with_metrics["triangles"].columns)
    assert et.remove_triangles_by_shape is cleanup.remove_triangles_by_shape      # star-exported


def test_points_to_tin_with_boundary_and_attributes():
    shapely = pytest.importorskip("shapely")
    pts = _lattice_points(hole=None).rename(columns={"X": "x", "Y": "y"})
    tin = refine_mesh.points_to_tin(pts, x_col="x", y_col="y")
    assert {"X", "Y", "value"} <= set(tin["vertices"].columns)
    assert len(tin["vertices"]) == len(pts) and "points" not in tin
    np.testing.assert_allclose(np.sort(tin["vertices"]["value"]), np.sort(pts["value"]))
    poly = shapely.geometry.box(0, 0, 25, 40)
    clipped = refine_mesh.points_to_tin(pts, boundary=poly, x_col="x", y_col="y")
    idx = clipped["triangles"][[0, 1, 2]].to_numpy()
    cx = clipped["vertices"]["X"].to_numpy()[idx].mean(axis=1)
    assert (cx < 25).all() and len(clipped["triangles"]) < len(tin["triangles"])
    assert et.points_to_tin is refine_mesh.points_to_tin


def test_remove_unused_vertices_int32_no_dtype_warning():
    pts = _lattice_points()
    tin = refine_mesh.points_to_tin(pts)
    out = cleanup.remove_triangles_by_shape(max_side_length=1.05 * np.hypot(10, 10), **tin)
    # emulate the `triangle` library's int32 ids and drop a corner vertex so something is unused
    tri = {"vertices": out["vertices"], "triangles": out["triangles"][[0, 1, 2]].astype("int32")}
    tri["triangles"] = tri["triangles"].iloc[:-3].reset_index(drop=True)
    used_before = set(tri["triangles"].to_numpy().ravel())
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        res = cleanup.remove_unused_vertices(**tri)
    assert len(res["vertices"]) == len(used_before)
    assert res["triangles"][[0, 1, 2]].dtypes.unique().tolist() == [np.dtype("int64")]
    assert res["triangles"][[0, 1, 2]].to_numpy().max() < len(res["vertices"])
    # the input triangles frame is not mutated any more
    assert tri["triangles"].dtypes.unique().tolist() == [np.dtype("int32")]
