---
layout: default
title: API Reference
---

# API Reference

Complete reference for all public classes, methods, and signals in pyside-navicube.

---

## `NaviCubeOverlay`

```python
from navicube import NaviCubeOverlay
```

A PySide6 `QWidget` subclass that renders a FreeCAD-style NaviCube as a 2D overlay. It communicates with your 3D renderer exclusively through `push_camera()` (input) and `viewOrientationRequested` (output).

### Constructor

```python
NaviCubeOverlay(
    parent: QWidget | None = None,
    *,
    overlay: bool = True,
    style: NaviCubeStyle | None = None,
)
```

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `parent` | `QWidget \| None` | `None` | Qt parent widget. For overlay mode, this should be the 3D viewport widget. |
| `overlay` | `bool` | `True` | If `True`, creates a transparent floating tool window with `Qt.Tool \| Qt.FramelessWindowHint \| Qt.NoDropShadowWindowHint \| Qt.WindowDoesNotAcceptFocus` flags. If `False`, creates a plain opaque QWidget suitable for embedding in layouts or docks. |
| `style` | `NaviCubeStyle \| None` | `None` | Visual and behavioral configuration. If `None`, uses `NaviCubeStyle()` with all defaults. |

### Signals

#### `viewOrientationRequested`

```python
viewOrientationRequested = Signal(float, float, float, float, float, float)
```

Emitted when the user clicks a cube face, edge, corner, or control button, and on every animation tick during the resulting transition.

| Parameter | Description |
|:----------|:------------|
| `dx` | Outward camera direction X (scene center toward eye) |
| `dy` | Outward camera direction Y |
| `dz` | Outward camera direction Z |
| `ux` | Camera up vector X |
| `uy` | Camera up vector Y |
| `uz` | Camera up vector Z |

The direction vector is in your application's world space (after `_WORLD_ROT` transformation). It is ready for use with OCC `SetProj()` or equivalent -- no sign flip needed.

### Methods

#### `push_camera`

```python
@Slot(float, float, float, float, float, float)
def push_camera(
    self,
    dx: float, dy: float, dz: float,
    ux: float, uy: float, uz: float,
) -> None
```

Update the navicube to match the current camera state. Call this whenever your camera changes.

| Parameter | Description |
|:----------|:------------|
| `dx` | Inward camera direction X (eye toward scene) |
| `dy` | Inward camera direction Y |
| `dz` | Inward camera direction Z |
| `ux` | Camera up vector X |
| `uy` | Camera up vector Y |
| `uz` | Camera up vector Z |

**Behavior:**
- During a face-click animation, the push is silently ignored (unless interaction is active, in which case the animation is cancelled).
- During active interaction (`set_interaction_active(True)`), the push is smoothed via quaternion SLERP (alpha 0.65).
- Otherwise, the camera state is applied directly.
- Must be called from the Qt main thread.

**Thread safety:** If your render loop runs on a worker thread, post back via:

```python
QMetaObject.invokeMethod(
    cube, "push_camera", Qt.QueuedConnection,
    Q_ARG(float, dx), Q_ARG(float, dy), Q_ARG(float, dz),
    Q_ARG(float, ux), Q_ARG(float, uy), Q_ARG(float, uz),
)
```

#### `set_home`

```python
def set_home(
    self,
    dx: float, dy: float, dz: float,
    ux: float, uy: float, uz: float,
) -> None
```

Set the camera orientation that the Home button returns to.

| Parameter | Description |
|:----------|:------------|
| `dx` | Inward camera direction X (same convention as `push_camera`) |
| `dy` | Inward camera direction Y |
| `dz` | Inward camera direction Z |
| `ux` | Up vector X |
| `uy` | Up vector Y |
| `uz` | Up vector Z |

Default is the navicube's internal ISO view expressed in the current `_WORLD_ROT` coordinate system. Call this once after construction or after loading user preferences.

#### `set_interaction_active`

```python
def set_interaction_active(self, active: bool) -> None
```

Notify the navicube that the user is actively dragging the camera.

| Parameter | Description |
|:----------|:------------|
| `active` | `True` on mouse press, `False` on mouse release |

While active, `push_camera()` applies SLERP smoothing (alpha 0.65, approximately 8 ms effective visual lag) to absorb momentary renderer instabilities such as OCC up-vector flicker near poles.

#### `set_style`

```python
def set_style(self, style: NaviCubeStyle) -> None
```

Apply a new style at runtime. Forces a full rebuild and repaint.

| Parameter | Description |
|:----------|:------------|
| `style` | A `NaviCubeStyle` instance with the desired configuration |

This method:
1. Stores the new style
2. Recomputes all derived values
3. Clears the font size cache
4. Rebuilds face geometry
5. Recalculates DPI scaling and widget size
6. Updates the timer interval
7. Triggers a repaint

### Class attributes

#### `_WORLD_ROT`

```python
_WORLD_ROT: np.ndarray = np.eye(3)
```

3x3 rotation matrix mapping from navicube's internal Z-up space to your application's world space. Override as a class attribute in a subclass for Y-up or other coordinate systems. See [Coordinate Systems](coordinate-systems) for details.

### Properties

#### `hovered_id`

```python
hovered_id: str | None
```

The ID string of the currently hovered element, or `None` if nothing is hovered. Face IDs include: `TOP`, `FRONT`, `LEFT`, `BACK`, `RIGHT`, `BOTTOM`, `FRONT_TOP`, `FTR`, etc. Control IDs include: `ArrowNorth`, `ArrowSouth`, `ArrowEast`, `ArrowWest`, `ArrowLeft`, `ArrowRight`, `ViewMenu`, `DotBackside`.

---

## `NaviCubeStyle`

```python
from navicube import NaviCubeStyle
```

A Python `dataclass` containing every visual and behavioral configuration parameter for the NaviCube widget. See the [Style Reference](style-reference) page for exhaustive documentation of every field.

### Constructor

```python
NaviCubeStyle(**kwargs)
```

All fields have defaults. Pass only the fields you want to customize:

```python
# All defaults
style = NaviCubeStyle()

# Customize specific fields
style = NaviCubeStyle(size=150, theme="dark", animation_ms=300)
```

### Fields summary

| Category | Fields |
|:---------|:-------|
| Geometry | `size`, `padding`, `scale`, `chamfer` |
| Animation | `animation_ms`, `tick_ms` |
| Thresholds | `visibility_threshold`, `orbit_step_deg`, `sync_epsilon`, `inactive_opacity` |
| Lighting | `light_direction` |
| Theme | `theme` |
| Light colors | `face_color`, `edge_color`, `corner_color`, `text_color`, `border_color`, `border_secondary_color`, `control_color`, `control_rim_color`, `hover_color`, `hover_text_color`, `dot_color`, `shadow_color` |
| Dark colors | `face_color_dark`, `edge_color_dark`, `corner_color_dark`, `text_color_dark`, `border_color_dark`, `border_secondary_color_dark`, `control_color_dark`, `control_rim_color_dark`, `hover_color_dark`, `hover_text_color_dark`, `dot_color_dark`, `shadow_color_dark` |
| Font | `font_family`, `font_fallback`, `font_weight`, `label_max_width_ratio`, `label_max_height_ratio`, `min_font_size` |
| Labels | `labels` |
| Controls | `show_controls`, `show_gizmo`, `gizmo_x_color`, `gizmo_y_color`, `gizmo_z_color`, `gizmo_font_size` |
| Borders | `border_width_main`, `border_width_secondary`, `control_border_width` |
| Shadow | `shadow_offset_x`, `shadow_offset_y` |

---

## `OCCNaviCubeSync`

```python
from navicube.connectors.occ import OCCNaviCubeSync
```

Bridges an OCC `V3d_View` with a `NaviCubeOverlay` widget. Handles camera polling, signal connection, and teardown.

### Constructor

```python
OCCNaviCubeSync(view, navicube)
```

| Parameter | Type | Description |
|:----------|:-----|:------------|
| `view` | `V3d_View` | An initialized OCC V3d_View instance |
| `navicube` | `NaviCubeOverlay` | The navicube widget to synchronize |

Starts polling immediately upon construction.

### Methods

#### `set_interaction_active`

```python
def set_interaction_active(self, active: bool) -> None
```

Call with `True` when the user starts dragging the camera, `False` when they release. Forwarded to the navicube for SLERP smoothing. Also resets the tick counter for an immediate camera read on state change.

#### `teardown`

```python
def teardown(self) -> None
```

Stop polling and disconnect all signals. Call this when the OCC view is being destroyed. After calling teardown, the sync object holds no references to the view or navicube.

### Class constants

| Constant | Value | Description |
|:---------|:------|:------------|
| `_TICK_MS` | `16` | Base timer interval (ms) |
| `_INTERACTION_TICKS` | `1` | Poll every tick during interaction |
| `_IDLE_TICKS` | `4` | Poll every 4 ticks when idle |

---

## `VTKNaviCubeSync`

```python
from navicube.connectors.vtk import VTKNaviCubeSync
```

Bridges a VTK renderer with a `NaviCubeOverlay` widget. Same API surface as `OCCNaviCubeSync`.

### Constructor

```python
VTKNaviCubeSync(renderer, navicube)
```

| Parameter | Type | Description |
|:----------|:-----|:------------|
| `renderer` | VTK renderer | A VTK renderer instance |
| `navicube` | `NaviCubeOverlay` | The navicube widget to synchronize |

### Methods

#### `set_interaction_active`

```python
def set_interaction_active(self, active: bool) -> None
```

Same behavior as `OCCNaviCubeSync.set_interaction_active()`.

#### `teardown`

```python
def teardown(self) -> None
```

Same behavior as `OCCNaviCubeSync.teardown()`.

---

## Face and control IDs

These string IDs are used in `hovered_id`, hit testing, and internal face/control lookup.

### Main faces (6)

`TOP`, `FRONT`, `LEFT`, `BACK`, `RIGHT`, `BOTTOM`

### Edge faces (12)

`FRONT_TOP`, `FRONT_BOTTOM`, `REAR_BOTTOM`, `REAR_TOP`, `REAR_RIGHT`, `FRONT_RIGHT`, `FRONT_LEFT`, `REAR_LEFT`, `TOP_LEFT`, `TOP_RIGHT`, `BOTTOM_RIGHT`, `BOTTOM_LEFT`

### Corner faces (8)

`FTR` (Front-Top-Right), `FTL` (Front-Top-Left), `FBR` (Front-Bottom-Right), `FBL` (Front-Bottom-Left), `RTR` (Rear-Top-Right), `RTL` (Rear-Top-Left), `RBR` (Rear-Bottom-Right), `RBL` (Rear-Bottom-Left)

### Control buttons (8)

| ID | Action | Description |
|:---|:-------|:------------|
| `ArrowNorth` | `orbit_u` | Orbit camera upward |
| `ArrowSouth` | `orbit_d` | Orbit camera downward |
| `ArrowEast` | `orbit_r` | Orbit camera rightward |
| `ArrowWest` | `orbit_l` | Orbit camera leftward |
| `ArrowLeft` | `roll_ccw` | Roll camera counter-clockwise |
| `ArrowRight` | `roll_cw` | Roll camera clockwise |
| `ViewMenu` | `home` | Return to home orientation |
| `DotBackside` | `backside` | Flip 180 degrees to opposite view |
