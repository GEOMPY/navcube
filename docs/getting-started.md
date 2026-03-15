---
layout: default
title: Getting Started
---

# Getting Started

This guide walks you through installing pyside-navicube, understanding its architecture, and writing your first integration.

---

## Prerequisites

| Requirement | Version |
|:------------|:--------|
| Python | 3.10 or later |
| PySide6 | Any recent release (6.4+) |
| NumPy | Any recent release (1.23+) |

Optional, only if you use the built-in connectors:

| Package | For |
|:--------|:----|
| pythonocc-core | `OCCNaviCubeSync` connector |
| vtk | `VTKNaviCubeSync` connector |

---

## Installation

```bash
# Core only (no renderer dependencies)
pip install pyside-navicube

# With OCC support
pip install pyside-navicube[occ]

# With VTK support
pip install pyside-navicube[vtk]
```

To verify the installation:

```python
from navicube import NaviCubeOverlay, NaviCubeStyle
print("pyside-navicube installed successfully")
```

---

## Architecture overview

pyside-navicube follows a strict separation between the **widget** (pure Qt 2D rendering) and **your 3D renderer**:

```
┌─────────────────────┐          ┌──────────────────────┐
│   Your 3D Renderer  │          │   NaviCubeOverlay    │
│   (OCC / VTK / …)   │          │   (PySide6 QWidget)  │
│                      │          │                      │
│  Camera changes ─────┼── push_camera() ──►  Redraws   │
│                      │          │          cube        │
│  SetProj / SetUp ◄───┼── viewOrientationRequested ──  │
│                      │          │  (user clicked face) │
└─────────────────────┘          └──────────────────────┘
```

The widget never imports or links against any 3D library. All communication happens through:

1. **`push_camera(dx, dy, dz, ux, uy, uz)`** -- you call this to tell the navicube where your camera is pointing.
2. **`viewOrientationRequested` signal** -- the navicube emits this when the user clicks a face, edge, corner, or control button.

---

## Basic usage with any renderer

The generic integration pattern works with **any** 3D engine:

```python
from navicube import NaviCubeOverlay

# 1. Create the overlay, parented to your viewport widget
cube = NaviCubeOverlay(parent=your_3d_widget)
cube.show()

# 2. Connect the signal to update your renderer's camera
def on_orientation(dx, dy, dz, ux, uy, uz):
    """
    dx/dy/dz = OUTWARD camera direction (eye position relative to scene center).
    ux/uy/uz = Camera up vector.
    """
    your_renderer.set_camera_direction(dx, dy, dz)
    your_renderer.set_camera_up(ux, uy, uz)
    your_renderer.redraw()

cube.viewOrientationRequested.connect(on_orientation)

# 3. Push camera state whenever it changes (e.g. in your render loop or mouse handler)
def on_camera_changed():
    d = your_renderer.get_camera_direction()  # INWARD: eye -> scene
    u = your_renderer.get_camera_up()
    cube.push_camera(d.x, d.y, d.z, u.x, u.y, u.z)
```

---

## How signals work

### `viewOrientationRequested(dx, dy, dz, ux, uy, uz)`

Emitted when the user clicks on a cube face, edge, corner, orbit button, roll arrow, home button, or backside dot. The six float arguments represent:

- `dx, dy, dz` -- the **outward** camera direction (from scene center toward the eye). This is ready for use with OCC `SetProj()` or equivalent.
- `ux, uy, uz` -- the camera **up** vector.

During a face-click animation (default 240 ms), the signal is emitted on every animation tick so your renderer can follow the smooth transition.

### `push_camera(dx, dy, dz, ux, uy, uz)`

A slot you call to update the navicube with your renderer's current camera state:

- `dx, dy, dz` -- the **inward** camera direction (eye toward scene). For OCC, this is `cam.Direction()` directly.
- `ux, uy, uz` -- the camera **up** vector.

**Important sign convention:** `push_camera` takes the **inward** direction. `viewOrientationRequested` emits the **outward** direction. The navicube handles the negation internally.

---

## Interaction state and SLERP smoothing

Call `set_interaction_active()` to tell the navicube when the user is actively dragging the camera:

```python
# In your viewport's mouse handlers:
def mousePressEvent(self, event):
    cube.set_interaction_active(True)
    # ... your orbit logic ...

def mouseReleaseEvent(self, event):
    cube.set_interaction_active(False)
    # ... your orbit logic ...
```

When interaction is active, `push_camera()` applies **quaternion SLERP smoothing** (alpha = 0.65) to filter out momentary renderer instabilities such as OCC's up-vector flicker near gimbal-lock poles. This keeps the navicube visually stable during fast orbiting while adding only ~8 ms of effective visual lag.

When interaction is **not** active, `push_camera()` applies the camera state directly with no smoothing.

---

## Overlay vs inline mode

The `overlay` constructor parameter controls how the widget behaves:

```python
# Overlay mode (default): transparent floating window
cube = NaviCubeOverlay(parent=viewport, overlay=True)

# Inline mode: regular QWidget for layouts and docks
cube = NaviCubeOverlay(parent=None, overlay=False)
layout.addWidget(cube)
```

| Feature | Overlay (`True`) | Inline (`False`) |
|:--------|:-----------------|:-----------------|
| Window flags | `Tool + FramelessWindowHint + NoDropShadowWindowHint` | Standard QWidget |
| Background | Translucent | Opaque (respects parent palette) |
| Positioning | Manual (`move()` / `raise_()`) | Managed by layout |
| Use case | Floating over a 3D viewport | Sidebar / dock / toolbar |

---

## Complete working example

This example creates a standalone window with a navicube that prints orientation changes to the console:

```python
import sys
import math
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer
from navicube import NaviCubeOverlay, NaviCubeStyle

class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NaviCube Demo")
        self.resize(600, 500)

        layout = QVBoxLayout(self)
        self.label = QLabel("Click a cube face to change orientation")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        # Create navicube as an overlay
        self.cube = NaviCubeOverlay(parent=self)
        self.cube.viewOrientationRequested.connect(self.on_orient)
        self.cube.show()

        # Position it in the top-right corner
        self._reposition_cube()

    def on_orient(self, dx, dy, dz, ux, uy, uz):
        self.label.setText(
            f"Direction: ({dx:+.3f}, {dy:+.3f}, {dz:+.3f})\n"
            f"Up:        ({ux:+.3f}, {uy:+.3f}, {uz:+.3f})"
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_cube()

    def _reposition_cube(self):
        cw = self.cube.width()
        self.cube.move(self.width() - cw - 10, 10)
        self.cube.raise_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DemoWindow()
    win.show()
    sys.exit(app.exec())
```
