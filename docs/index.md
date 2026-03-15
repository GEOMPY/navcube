---
layout: default
title: Home
---

# pyside-navicube

A FreeCAD-style 3D orientation cube for **any PySide6 application**.
Zero renderer dependency. Full style control. Drop-in ready.

[Get Started]({{ '/getting-started' | relative_url }}){: .btn }
[View on GitHub](https://github.com/nishikantmandal007/pyside-navicube){: .btn }
[PyPI](https://pypi.org/project/pyside-navicube/){: .btn }

---

## Interactive Demo

Drag to orbit. Click a NaviCube face (top-right corner) to snap to that view. Scroll to zoom.

<div id="demo-canvas" style="width:100%; height:400px; border:1px solid #ccc; border-radius:8px; overflow:hidden; background:#1a1d23; margin:1rem 0;"></div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="{{ '/assets/js/demo.js' | relative_url }}"></script>

<small><em>This browser demo uses Three.js. The actual widget uses QPainter and runs natively in any PySide6 app.</em></small>

---

## What is this?

**pyside-navicube** is a pure-Python PySide6 widget that renders an interactive 3D orientation cube as a 2D overlay. It talks to your 3D engine through two simple hooks:

- **You push** camera state in: `cube.push_camera(dx, dy, dz, ux, uy, uz)`
- **It emits** orientation requests: `cube.viewOrientationRequested.connect(your_fn)`

That's the entire integration surface. Works with **OCC, VTK, OpenGL, Three.js** — anything with a camera.

---

## Key Features

| Feature | Description |
|:--------|:------------|
| **Zero Dependencies** | Core widget needs only PySide6 + NumPy. No OpenGL context sharing, no C++ bindings. |
| **Full Style Control** | 60+ configurable fields via `NaviCubeStyle` — every color, size, font, label. Change at runtime. |
| **Smooth Animations** | Quaternion SLERP with antipodal handling. No gimbal lock, no NaN crashes. |
| **Z-up & Y-up** | Default Z-up (OCC/FreeCAD/Blender). One-line subclass for Y-up (Unity, Unreal, Three.js). |
| **Ready Connectors** | Built-in sync for OCC and VTK. Write your own in ~50 lines. |
| **DPI Aware** | Auto-scales from 96 DPI to 4K Retina. Recomputes when moved between monitors. |

---

## Install

```bash
pip install pyside-navicube            # core (PySide6 + NumPy)
pip install pyside-navicube[occ]       # + OCC connector
pip install pyside-navicube[vtk]       # + VTK connector
```

---

## Quick Start

```python
from navicube import NaviCubeOverlay, NaviCubeStyle

# Basic — default style
cube = NaviCubeOverlay(parent=your_3d_widget)
cube.show()

# Connect: navicube face click → your renderer
cube.viewOrientationRequested.connect(your_camera_update)

# Connect: your renderer camera change → navicube
cube.push_camera(dx, dy, dz, ux, uy, uz)  # inward dir + up vector
```

## Fully Customized

```python
style = NaviCubeStyle(
    size=160,
    face_color=(30, 40, 60),
    text_color=(200, 220, 255),
    hover_color=(0, 180, 255, 240),
    font_family="Segoe UI",
    labels={"TOP": "UP", "BOTTOM": "DN", "FRONT": "F",
            "BACK": "B", "LEFT": "L", "RIGHT": "R"},
    theme="dark",
    show_gizmo=True,
)

cube = NaviCubeOverlay(parent=widget, style=style)
```

---

## Documentation

| Page | What's inside |
|:-----|:-------------|
| [Getting Started]({{ '/getting-started' | relative_url }}) | Install, basic usage, signal flow, first integration |
| [Style Reference]({{ '/style-reference' | relative_url }}) | Every `NaviCubeStyle` field — type, default, example |
| [Coordinate Systems]({{ '/coordinate-systems' | relative_url }}) | Z-up vs Y-up, `_WORLD_ROT`, sign conventions |
| [Connectors]({{ '/connectors' | relative_url }}) | OCC & VTK integration, writing custom connectors |
| [API Reference]({{ '/api-reference' | relative_url }}) | Full class, method, and signal reference |
| [Examples]({{ '/examples' | relative_url }}) | Copy-paste code for every common scenario |
| [Changelog]({{ '/changelog' | relative_url }}) | Version history |

---

## Sign Convention Cheat Sheet

| Direction | Value | Notes |
|:----------|:------|:------|
| `push_camera` d | **Inward** (eye → scene) | Same as OCC `cam.Direction()` |
| `viewOrientationRequested` p | **Outward** (scene → eye) | Ready for OCC `SetProj()` |

> **Mnemonic**: Read inward, write outward.
