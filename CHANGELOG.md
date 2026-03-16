# Changelog

All notable changes to NavCube are documented here.
This project follows [Semantic Versioning](https://semver.org/).

---

## v1.0.1 — 2026-03-16

### Fixed

- **NavCube size is now stable across all display scale factors.**
  The previous implementation used `logicalDotsPerInch() / 96` as a *multiplier*,
  causing Qt 6's automatic HiDPI handling to double-scale the widget — at 150 %
  Windows zoom the cube appeared ~2.25× larger than at 100 %.
  The new formula targets a fixed physical size (≈ 26.5 mm) using
  `physicalDotsPerInch()` and `devicePixelRatio()`, so the cube looks identical
  on every display at every OS scale factor: 100 %, 125 %, 150 %, 200 %, 4K,
  and Retina.

### Added

- `NavCubeStyle.size_fraction` — when > 0, sizes the cube as a percentage of
  the parent widget's shorter side. The cube auto-resizes whenever the parent
  viewport resizes (via an event filter installed on `showEvent`).
- `NavCubeStyle.size_min` / `size_max` — pixel bounds (96-dpi-equivalent) used
  to clamp the computed size when `size_fraction` is active.
- `NavCubeStyle.size` default reduced from 120 → 100 (96-dpi-equivalent px),
  giving a slightly smaller default cube that better fits typical viewports.

---

## v1.0.0 — 2026-03-15

**Initial public release** — extracted from Osdag and polished into a
standalone library.

### Included

- **NavCubeOverlay** — pure PySide6 / QPainter widget, zero renderer dependency.
  6 main faces, 12 edge faces, 8 corner faces with FreeCAD-style chamfered geometry.
  Orbit, roll, home, and backside controls. Quaternion SLERP animations with
  antipodal handling. Lambertian shading. Light and dark theme. DPI-aware.
- **NavCubeStyle** — 60+ field dataclass for full visual and behavioral control.
  Runtime style swapping via `set_style()`.
- **OCCNavCubeSync** — OCC `V3d_View` connector with adaptive poll rate and
  flicker-free atomic camera updates.
- **VTKNavCubeSync** — VTK renderer connector, same architecture as OCC.
- Z-up by default; Y-up via `_WORLD_ROT` subclass override.
- Sign convention: `push_camera()` takes inward direction,
  `viewOrientationRequested` emits outward direction.
