# pyside-navicube

A beautiful, FreeCAD-style NaviCube orientation widget for **any PySide6 application**.
Zero renderer dependency — works with OCC, VTK, custom OpenGL, or any 3D engine.

**[Documentation](https://nishikantmandal007.github.io/pyside-navicube/)** | **[PyPI](https://pypi.org/project/pyside-navicube/)** | **[GitHub](https://github.com/nishikantmandal007/pyside-navicube)**

---

## Install

```bash
pip install pyside-navicube          # core widget only (PySide6 + numpy)
pip install pyside-navicube[occ]     # + OCCNaviCubeSync helper for pythonocc
```

---

## Quick-start (any renderer)

```python
from navicube import NaviCubeOverlay

cube = NaviCubeOverlay(parent=your_window)
cube.show()

# 1. Navicube → your renderer
#    Emits outward direction (ready for OCC SetProj) + up vector
cube.viewOrientationRequested.connect(your_camera_update_fn)

# 2. Your renderer → navicube
#    Call this whenever the camera changes (mouse drag, programmatic update)
#    dx/dy/dz = INWARD direction (eye → scene)  — OCC cam.Direction() directly
cube.push_camera(dx, dy, dz, ux, uy, uz)

# 3. Interaction hints (enables SLERP smoothing to filter jitter)
cube.set_interaction_active(True)    # on mouse press
cube.set_interaction_active(False)   # on mouse release
```

---

## Full style customization

Every visual and behavioral aspect is configurable via `NaviCubeStyle`:

```python
from navicube import NaviCubeOverlay, NaviCubeStyle

style = NaviCubeStyle(
    size=160,                          # larger cube
    animation_ms=180,                  # snappier animations
    face_color=(30, 40, 60),           # dark blue faces
    edge_color=(20, 30, 50),
    corner_color=(15, 22, 38),
    text_color=(200, 220, 255),        # light blue text
    hover_color=(0, 180, 255, 240),
    font_family="Segoe UI",
    font_weight="bold",
    labels={"TOP": "UP", "BOTTOM": "DN", "FRONT": "F",
            "BACK": "B", "LEFT": "L", "RIGHT": "R"},
    show_gizmo=True,
    inactive_opacity=0.6,
    theme="dark",
)

cube = NaviCubeOverlay(parent=your_window, style=style)
```

Change styles at runtime:

```python
cube.set_style(NaviCubeStyle(size=200, theme="light"))
```

See the **[Style Reference](https://nishikantmandal007.github.io/pyside-navicube/style-reference)** for all 50+ configurable fields.

---

## OCC / pythonocc users

`OCCNaviCubeSync` handles polling, interaction detection, and the camera
update signal for you — the only file in the stack that imports OCC.

```python
from navicube import NaviCubeOverlay
from navicube.connectors.occ import OCCNaviCubeSync

cube = NaviCubeOverlay(parent=tab_widget)
cube.show()

# Call once your OCC view is initialised:
sync = OCCNaviCubeSync(occ_view, cube)

# In your viewer's mousePressEvent / mouseReleaseEvent:
sync.set_interaction_active(True)    # press
sync.set_interaction_active(False)   # release

# When the viewer is torn down:
sync.teardown()
```

---

## VTK / PyVista users

```python
from navicube import NaviCubeOverlay
from navicube.connectors.vtk import VTKNaviCubeSync

cube = NaviCubeOverlay(parent=vtk_widget)
cube.show()

sync = VTKNaviCubeSync(renderer, cube, render_window=vtk_widget.GetRenderWindow())
```

---

## Coordinate system (Z-up vs Y-up)

By default the navicube uses **Z-up** (OCC, FreeCAD, Blender world space).

For **Y-up** engines (Three.js, GLTF, Unity, Unreal):

```python
import numpy as np
from navicube import NaviCubeOverlay

class YUpNaviCube(NaviCubeOverlay):
    _WORLD_ROT = np.array([
        [1, 0,  0],
        [0, 0, -1],
        [0, 1,  0],
    ], dtype=float)

cube = YUpNaviCube(parent=my_window)
```

---

## Inline / dock mode

```python
cube = NaviCubeOverlay(parent=panel, overlay=False)
panel_layout.addWidget(cube)
```

## Custom home view

```python
cube.set_home(dx, dy, dz, ux, uy, uz)   # inward dir + up, world space
```

## Sign-convention cheat-sheet

| Direction | Value | Notes |
|---|---|---|
| `push_camera` dx/dy/dz | **Inward** (eye → scene) | Same as OCC `cam.Direction()` — no flip needed |
| `viewOrientationRequested` px/py/pz | **Outward** (scene → eye) | Ready for OCC `SetProj(px, py, pz)` directly |

---

## Writing a connector for another renderer

Implement a class that:
1. Polls or subscribes to camera changes and calls `cube.push_camera()`
2. Connects `cube.viewOrientationRequested` to update the renderer camera
3. Calls `cube.set_interaction_active(True/False)` on drag start/end

See `navicube/connectors/occ.py` for a complete reference implementation.

---

## License

LGPL-2.1
