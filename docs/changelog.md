---
layout: default
title: Changelog
---

# Changelog

All notable changes to pyside-navicube are documented here. This project follows [Semantic Versioning](https://semver.org/).

---

## v1.0.0

**Initial release.**

### Features

- **NaviCubeOverlay** -- Pure PySide6 widget rendering a FreeCAD-style NaviCube with QPainter
  - 6 main faces, 12 edge faces, 8 corner faces with FreeCAD-style chamfered geometry
  - Orbit buttons (North/South/East/West), roll arrows (Left/Right), home button, backside dot
  - Smooth quaternion SLERP animations with antipodal handling (no NaN crashes on 180-degree flips)
  - Quintic ease-in-out animation curve for natural motion
  - Per-face Lambertian shading with configurable light direction
  - Full back-face culling with configurable visibility threshold
  - DPI-aware rendering with automatic scaling on screen changes
  - Overlay mode (transparent floating window) and inline mode (standard QWidget)
  - Light and dark theme support with automatic detection from QPalette

- **NaviCubeStyle** -- Complete style customization via a Python dataclass
  - 60+ configurable fields covering geometry, animation, colors, fonts, labels, borders, and shadows
  - Runtime style changes via `set_style()` with full rebuild and repaint
  - Separate light-theme and dark-theme color palettes
  - Customizable face labels for localization (any language, any script)
  - Configurable font family, weight, and size constraints
  - Optional XYZ axis gizmo with configurable colors

- **Coordinate system support**
  - Z-up by default (OCC, FreeCAD, Blender)
  - Y-up via `_WORLD_ROT` class attribute override (Three.js, Unity, Unreal)
  - Clean sign convention: `push_camera()` takes inward direction, `viewOrientationRequested` emits outward direction

- **OCCNaviCubeSync** -- OCC V3d_View connector
  - Adaptive poll rate: every tick during interaction, every 4 ticks when idle
  - Atomic camera updates via Camera.SetEye() + Camera.SetUp() to avoid flicker
  - Fallback to SetProj/SetUp for older pythonocc builds
  - Clean teardown with no dangling references

- **VTKNaviCubeSync** -- VTK renderer connector
  - Same architecture and API as the OCC connector

- **SLERP smoothing** during live camera interaction
  - Quaternion-based smoothing (alpha 0.65) absorbs momentary renderer instabilities
  - Approximately 8 ms effective visual lag -- imperceptible to users
  - Automatically disabled when interaction ends

### Dependencies

- Python 3.10+
- PySide6
- NumPy
- Optional: pythonocc-core (for OCC connector)
- Optional: vtk (for VTK connector)

### License

LGPL-2.1
