# Changelog

All notable changes to EMeraldTriangles are recorded here. This project uses
loose [semantic versioning](https://semver.org/); the version string lives in
`pyproject.toml`.

## Unreleased

* New geometric triangle filter (issue #33, the geometric half of #20):
  `cleanup.triangle_metrics(vertices, triangles)` (area, perimeter, max/min side length, min angle, aspect) and
  `cleanup.remove_triangles_by_shape(max_side_length=, max_area=, max_perimeter=, min_angle_deg=, max_aspect=, **tri)`
  to drop the sliver triangles that `supplant_triangles` creates across concave footprints and gaps; the kept
  triangles are re-indexed, vertices untouched (`remove_unused_vertices` afterwards if wanted).
* `refine_mesh.points_to_tin(points, boundary=None, existing_boundary=False)` — the usual
  `replace_triangles` + `supplant_triangles` pair for a table of points, with an optional footprint polygon (only
  triangles whose centroid lies inside are kept).
* `cleanup.remove_unused_vertices` no longer writes the remapped vertex ids into the caller's `triangles` /
  `segments` frames with an in-place `.loc[:, [0, 1, 2]] = ...` (int64/float64 into int32 columns: a FutureWarning on
  pandas 2, an error on pandas 3, #26); it now returns new frames with an `int64` dtype (float64 with NaN only if an
  id could not be mapped). The returned dict is unchanged; callers that relied on the in-place mutation of the
  input frames must use the return value.
* `io.vtk.volume.to_meshdata` now validates cell-corner indices instead of returning a float
  index array that VTK later rejects with an opaque
  `TypeError: Indices must be either a mask or an integer array-like`. Two checks:
  * raise if `split_layer_columns` found no per-layer column groups at all;
  * raise if any cell has NaN corner indices, reporting how many cells and which corners are
    affected, and naming the usual cause (per-layer columns that fail to group because their
    trailing layer index is not an integer, e.g. `res_0.0`).
  A float-but-complete index array is cast back to int rather than rejected, with a warning:
  the output mesh is unaffected, but the float dtype means integer IDs were promoted somewhere
  upstream, so the repair leaves a breadcrumb instead of hiding it.

## 0.1.10 

I think I may have included an unconmmitted local change in setup.py in v.0.1.9. Specifically, include_dirs was
garbled when I added a few character by accident. I'm pushing a new version to be absolutely sure it's correct.

## 0.1.9

Packaging fix so the project can be published to PyPI again.

### Fixed

- **Depend on `triangle` from PyPI instead of a Git URL.** The dependency was
  `triangle @ git+https://github.com/drufat/triangle.git`; PyPI rejects any
  distribution whose metadata contains a direct (`git+`) URL reference, which
  blocked publishing. Upstream `triangle` now ships wheels for Python 3.9–3.13
  (including cp312 on macOS arm64 / manylinux / Windows), so the plain
  dependency resolves to the same code (currently `20250106`) without a Git
  checkout or a source build.
  ([#23](https://github.com/emerald-geomodelling/EmeraldTriangles/issues/23))

## 0.1.8 (tagged, never published — superseded by 0.1.9)

Python 3.12 / pandas 2.x / NumPy 2 compatibility fixes. This is the first
release to carry the sampling, interpolation, and `split_layer_columns` fixes
that landed on `master` after 0.1.7 was published to PyPI (2025-11-27). Tagged
`2026-07-23-v.0.1.8` but not uploaded to PyPI: its `pyproject.toml` still
carried the `triangle @ git+...` direct URL (see 0.1.9). All changes below ship
in 0.1.9.

### Fixed

- **`split_layer_columns` no longer raises on non-string column labels.**
  `re.match` was applied to every column label assuming a string, so a
  float/`NaN` label raised `TypeError: expected string or bytes-like object,
  got 'float'`. Labels are now guarded with `isinstance(col, str)` and
  non-string labels fall through to per-position columns. Non-regressive on
  integer-suffixed per-layer columns.
  ([#29](https://github.com/emerald-geomodelling/EmeraldTriangles/pull/29))
- **pandas 2.x: positional `DataFrame.pivot()` calls.** `pivot()` arguments are
  keyword-only from pandas 2.0; the positional calls now pass `index=`/
  `columns=`/`values=` explicitly.
  ([#29](https://github.com/emerald-geomodelling/EmeraldTriangles/pull/29))
- **pandas 2.x: `sample_points` row indexing.** Switched to positional
  (`.iloc`) row indexing and removed chained assignment, which under
  Copy-on-Write silently no-op'd the write.
  ([#24](https://github.com/emerald-geomodelling/EmeraldTriangles/pull/24))
- **`interpolate_vertices` column indexer.** Use a list rather than a set as the
  column indexer, so column selection order is deterministic.
  ([#24](https://github.com/emerald-geomodelling/EmeraldTriangles/pull/24))

### Changed

- **Python 3.12 cleanups.** Regex literals made raw strings (clears
  `invalid escape sequence` `SyntaxWarning`s) and `idx is 0` replaced with
  `idx == 0`.
  ([#29](https://github.com/emerald-geomodelling/EmeraldTriangles/pull/29))

### Added

- Tests covering the sampling and interpolation fixes.
  ([#24](https://github.com/emerald-geomodelling/EmeraldTriangles/pull/24))

[0.1.9]: https://github.com/emerald-geomodelling/EmeraldTriangles/compare/2025-03-07-v.0.1.6...master
