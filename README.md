# NavCube

A 3D orientation cube widget for PySide6 — works with OpenCASCADE, VTK, raw OpenGL, or anything else with a camera. The core widget has zero renderer dependencies.

**[Full docs](https://nishikantmandal007.github.io/navcube/)** &nbsp;·&nbsp; **[PyPI](https://pypi.org/project/navcube/)** &nbsp;·&nbsp; **[GitHub](https://github.com/nishikantmandal007/navcube)**

---

## Why does this exist?

NavCube grew out of a real problem in [Osdag](https://osdag.fossee.in), an open-source structural steel design tool built on PythonOCC. Osdag lets users open multiple design tabs at once, and we wanted a NaviCube on each one.

OCC's built-in ViewCube lives inside the OpenGL context. That's fine for single-window apps, but once you start opening and closing tabs, you hit all kinds of lifecycle problems — OCC objects outliving their context, double-free crashes on tab close, the cube occasionally painting into the wrong viewport. The fundamental issue is that the cube and the renderer are too tightly coupled.

The fix was to pull the cube out of OCC entirely. NavCube is a plain PySide6 `QWidget` that draws itself with `QPainter`. No OpenGL, no OCC handles, no shared context. When a tab closes, the widget just disappears like any other Qt widget. The crashes went away.

The side effect: since the widget doesn't touch your renderer, it works equally well with VTK, custom OpenGL, or anything else. So we turned it into its own library.

---

## Install

```bash
pip install navcube            # core widget only
pip install navcube[occ]       # + OpenCASCADE connector
pip install navcube[vtk]       # + VTK/PyVista connector
```

---

## Quick start

```python
from navcube import NavCubeOverlay

cube = NavCubeOverlay(parent=your_window)
cube.show()

# Push your camera state in whenever it changes
cube.push_camera(dx, dy, dz, ux, uy, uz)

# React when someone clicks a NaviCube face
cube.viewOrientationRequested.connect(your_camera_update_fn)
```

That's it for the basics. The full integration guide, connector docs, and style reference are all over at **[nishikantmandal007.github.io/navcube](https://nishikantmandal007.github.io/navcube/)**.

---

## Try it now

Run this from a terminal or Jupyter cell to open a live window with a working NavCube:

```python
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from navcube import NavCubeOverlay

app = QApplication(sys.argv)
win = QWidget()
win.setWindowTitle("My First NavCube")
win.resize(800, 600)
win.setStyleSheet("background: #2b2d3a;")

label = QLabel("Click a NaviCube face to change the view")
label.setStyleSheet("color: #aab0c4; font-size: 14px;")
label.setAlignment(Qt.AlignCenter)
QVBoxLayout(win).addWidget(label)
win.show()

cube = NavCubeOverlay(parent=win)
cube.viewOrientationRequested.connect(
    lambda dx, dy, dz, ux, uy, uz:
        label.setText(f"Dir ({dx:+.2f}, {dy:+.2f}, {dz:+.2f})  Up ({ux:+.2f}, {uy:+.2f}, {uz:+.2f})")
)
cube.show()
cube.move(win.width() - cube.width() - 10, 10)

sys.exit(app.exec())
```

Click any face — the label updates with the orientation signal your real camera would receive.

---

## What's in the docs

| | |
|:--|:--|
| [Getting Started](https://nishikantmandal007.github.io/navcube/getting-started) | Install, architecture overview, first integration |
| [Connectors](https://nishikantmandal007.github.io/navcube/connectors) | OCC, VTK, and how to write your own |
| [Style Reference](https://nishikantmandal007.github.io/navcube/style-reference) | Every field in `NavCubeStyle`, with examples |
| [Coordinate Systems](https://nishikantmandal007.github.io/navcube/coordinate-systems) | Z-up vs Y-up, sign conventions |
| [API Reference](https://nishikantmandal007.github.io/navcube/api-reference) | Classes, methods, signals |
| [Changelog](https://nishikantmandal007.github.io/navcube/changelog) | What changed and when |

---

## Requirements

- Python 3.10+
- PySide6
- NumPy

Optional: `pythonocc-core` (OCC connector), `vtk` (VTK connector).

---

## License

LGPL-2.1
