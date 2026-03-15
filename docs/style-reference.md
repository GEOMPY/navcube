---
layout: default
title: Style Reference
---

# Style Reference

Complete documentation of every field in the `NaviCubeStyle` dataclass. This is the single point of control for all visual and behavioral aspects of the NaviCube widget.

---

## Overview

`NaviCubeStyle` is a Python `dataclass` that holds every configurable parameter of the NaviCube. Pass it at construction time or swap it at runtime:

```python
from navicube import NaviCubeOverlay, NaviCubeStyle

# At construction
style = NaviCubeStyle(size=150, theme="dark")
cube = NaviCubeOverlay(parent=win, style=style)

# At runtime
new_style = NaviCubeStyle(size=100, theme="light", hover_color=(255, 80, 0, 235))
cube.set_style(new_style)
```

Calling `set_style()` triggers a full rebuild of the internal geometry, clears the font cache, and forces a repaint. It is safe to call at any time.

### Color type

Throughout this reference, the `Color` type is defined as:

```python
Color = Union[Tuple[int, int, int], Tuple[int, int, int, int]]
```

RGB values are in the range 0--255. The optional fourth element is the alpha channel (0 = fully transparent, 255 = fully opaque). If alpha is omitted, the color is fully opaque.

---

## Geometry

These fields control the physical dimensions of the widget and the 3D projection.

### `size`

| | |
|:--|:--|
| **Type** | `int` |
| **Default** | `120` |
| **Description** | Base cube drawing area in pixels before DPI scaling. The actual widget size is `size + 2 * padding` on each side. At 96 DPI this is used as-is; at higher DPI the widget scales proportionally. |

```python
# Large cube for a 4K monitor
style = NaviCubeStyle(size=180)

# Compact cube for a sidebar
style = NaviCubeStyle(size=80)
```

### `padding`

| | |
|:--|:--|
| **Type** | `int` |
| **Default** | `10` |
| **Description** | Transparent padding on each side of the cube drawing area, in pixels (before DPI scaling). This creates space around the cube for the orbit buttons and shadow to render without clipping. The total widget side length is `size + 2 * padding`. |

```python
# More room for controls and shadow
style = NaviCubeStyle(padding=20)

# Tight fit (controls may clip)
style = NaviCubeStyle(padding=4)
```

### `scale`

| | |
|:--|:--|
| **Type** | `float` |
| **Default** | `27.0` |
| **Description** | 3D-to-screen projection scale factor. Controls how large the cube appears within the drawing area. Higher values make the cube fill more of the widget; lower values leave more margin. The effective scale is adjusted proportionally when DPI scaling changes `size`. |

```python
# Bigger cube within the same widget size
style = NaviCubeStyle(scale=32.0)

# Smaller cube with more margin
style = NaviCubeStyle(scale=20.0)
```

### `chamfer`

| | |
|:--|:--|
| **Type** | `float` |
| **Default** | `0.12` |
| **Description** | FreeCAD-style chamfer ratio for edge and corner bevels. This determines how much of each edge is "cut off" to create the beveled edge and corner faces. A value of `0.0` would give sharp edges (no edge/corner faces visible); values approaching `0.25` produce very large bevels. The default `0.12` matches FreeCAD's NaviCube appearance. |

```python
# Sharp, minimal bevels
style = NaviCubeStyle(chamfer=0.05)

# Rounded, heavily beveled look
style = NaviCubeStyle(chamfer=0.20)
```

---

## Animation and Timing

These fields control the speed and timing of face-click animations and the internal timer.

### `animation_ms`

| | |
|:--|:--|
| **Type** | `int` |
| **Default** | `240` |
| **Description** | Duration of the face-click animation in milliseconds. When a user clicks a face, edge, or corner, the camera smoothly rotates to the target orientation over this duration using quaternion SLERP with a quintic ease-in-out curve. |

```python
# Snappy, quick transitions
style = NaviCubeStyle(animation_ms=120)

# Slow, cinematic transitions
style = NaviCubeStyle(animation_ms=600)

# Instant (no animation)
style = NaviCubeStyle(animation_ms=1)
```

### `tick_ms`

| | |
|:--|:--|
| **Type** | `int` |
| **Default** | `16` |
| **Description** | Internal QTimer tick interval in milliseconds. This controls how often the animation loop updates. The default of 16 ms corresponds to approximately 60 FPS. Lower values give smoother animations but use more CPU. This timer only does work during active animations; idle ticks return immediately. |

```python
# Higher frame rate for smoother animation
style = NaviCubeStyle(tick_ms=8)

# Lower frame rate to save CPU
style = NaviCubeStyle(tick_ms=33)
```

---

## Thresholds

These fields control visibility, interaction sensitivity, and rendering behavior.

### `visibility_threshold`

| | |
|:--|:--|
| **Type** | `float` |
| **Default** | `0.10` |
| **Description** | Dot-product threshold for back-face culling. A face is visible when `dot(face_normal, camera_direction) < visibility_threshold`. Lower values hide faces earlier (only nearly front-facing faces are drawn); higher values show more faces (including nearly edge-on faces). |

```python
# Show fewer faces (only clearly visible ones)
style = NaviCubeStyle(visibility_threshold=0.0)

# Show more faces (including grazing angles)
style = NaviCubeStyle(visibility_threshold=0.25)
```

### `orbit_step_deg`

| | |
|:--|:--|
| **Type** | `float` |
| **Default** | `15.0` |
| **Description** | Rotation step size in degrees for the orbit buttons (North/South/East/West arrows). Each click rotates the camera by this amount around the corresponding axis. |

```python
# Fine-grained orbit control
style = NaviCubeStyle(orbit_step_deg=5.0)

# Coarse orbit steps
style = NaviCubeStyle(orbit_step_deg=45.0)
```

### `sync_epsilon`

| | |
|:--|:--|
| **Type** | `float` |
| **Default** | `1e-3` |
| **Description** | Minimum camera direction/up vector change (Euclidean norm) required to trigger a redraw. Prevents unnecessary repaints when `push_camera()` is called with effectively identical values. |

```python
# More sensitive (redraw on tiny changes)
style = NaviCubeStyle(sync_epsilon=1e-5)

# Less sensitive (ignore small jitter)
style = NaviCubeStyle(sync_epsilon=1e-2)
```

### `inactive_opacity`

| | |
|:--|:--|
| **Type** | `float` |
| **Default** | `0.72` |
| **Description** | Widget opacity when the mouse is not hovering over it. The value ranges from `0.0` (fully transparent) to `1.0` (fully opaque). When the mouse enters the widget, opacity immediately jumps to `1.0`. During face-click animations the widget also renders at full opacity. |

```python
# Nearly invisible when not hovered
style = NaviCubeStyle(inactive_opacity=0.3)

# Always fully visible
style = NaviCubeStyle(inactive_opacity=1.0)

# Semi-transparent
style = NaviCubeStyle(inactive_opacity=0.5)
```

---

## Lighting

### `light_direction`

| | |
|:--|:--|
| **Type** | `Tuple[float, float, float]` |
| **Default** | `(-0.8, -1.0, -1.8)` |
| **Description** | Direction vector for the Lambertian lighting model applied to face colors. This is automatically normalized internally. The light direction determines the shading gradient across the cube faces -- faces whose normals point opposite to this direction appear brighter. |

```python
# Light from top-right
style = NaviCubeStyle(light_direction=(1.0, -1.0, -2.0))

# Flat lighting (no shading)
style = NaviCubeStyle(light_direction=(0.0, 0.0, -1.0))

# Dramatic side lighting
style = NaviCubeStyle(light_direction=(-2.0, 0.0, 0.0))
```

The shading formula is: `shade = 0.85 + 0.15 * max(0, dot(face_normal, -light_direction))`. This means the darkest a face can get is 85% of its base color, and the brightest is 100%.

---

## Theme

### `theme`

| | |
|:--|:--|
| **Type** | `str` |
| **Default** | `"auto"` |
| **Description** | Theme selection mode. Controls which color palette is used for rendering. |

Valid values:

| Value | Behavior |
|:------|:---------|
| `"auto"` | Detects theme from `QApplication.palette()`. If `Window` color lightness > 128, uses light theme; otherwise dark theme. |
| `"light"` | Forces light theme colors regardless of system palette. |
| `"dark"` | Forces dark theme colors regardless of system palette. |

```python
# Auto-detect from system
style = NaviCubeStyle(theme="auto")

# Force dark
style = NaviCubeStyle(theme="dark")

# Force light
style = NaviCubeStyle(theme="light")
```

---

## Light Theme Colors

These colors are used when the resolved theme is "light". Each is an RGB or RGBA tuple.

### `face_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(248, 248, 252)` |
| **Description** | Base fill color for the six main faces (TOP, FRONT, LEFT, BACK, RIGHT, BOTTOM). Subject to Lambertian shading. |

### `edge_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(210, 210, 215)` |
| **Description** | Base fill color for the 12 edge faces (FRONT_TOP, FRONT_BOTTOM, etc.). Typically darker than `face_color` to create visual depth. |

### `corner_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(185, 185, 190)` |
| **Description** | Base fill color for the 8 corner faces (FTR, FTL, FBR, etc.). Typically the darkest of the three face types. |

### `text_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(18, 18, 18)` |
| **Description** | Color for face labels (TOP, FRONT, etc.) when the face is not hovered. |

### `border_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(28, 28, 32)` |
| **Description** | Border/outline color for the six main faces. |

### `border_secondary_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(50, 50, 55)` |
| **Description** | Border/outline color for edge and corner faces. Typically lighter than `border_color` to de-emphasize these smaller faces. |

### `control_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(186, 186, 192, 120)` |
| **Description** | Fill color for control buttons (orbit arrows, roll arrows, home, backside dot) when not hovered. The default includes transparency (alpha=120) so controls blend with the background. |

### `control_rim_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(105, 105, 110, 170)` |
| **Description** | Border color for control buttons when not hovered. |

### `hover_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(0, 148, 255, 235)` |
| **Description** | Fill color for any element (face, edge, corner, or control button) when the mouse is hovering over it. The default is a bright blue with slight transparency. |

### `hover_text_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(255, 255, 255)` |
| **Description** | Text color for face labels when the face is hovered. Typically white to contrast with the `hover_color`. |

### `dot_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(195, 195, 198, 225)` |
| **Description** | Color of the small dot at the center of the XYZ gizmo (when `show_gizmo=True`). |

### `shadow_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(0, 0, 0, 42)` |
| **Description** | Color of the drop shadow rendered behind each cube face. The default is a very subtle black shadow. Set alpha to 0 to disable shadows. |

---

## Dark Theme Colors

Mirror of the light theme colors, used when the resolved theme is "dark". Same types and semantics; different defaults optimized for dark backgrounds.

### `face_color_dark`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(155, 160, 178)` |
| **Description** | Base fill color for main faces in dark theme. A medium blue-gray that reads well against dark backgrounds. |

### `edge_color_dark`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(118, 122, 138)` |
| **Description** | Base fill color for edge faces in dark theme. |

### `corner_color_dark`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(96, 99, 113)` |
| **Description** | Base fill color for corner faces in dark theme. |

### `text_color_dark`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(238, 238, 238)` |
| **Description** | Face label text color in dark theme. Near-white for readability. |

### `border_color_dark`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(10, 10, 12)` |
| **Description** | Border color for main faces in dark theme. Nearly black. |

### `border_secondary_color_dark`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(20, 20, 22)` |
| **Description** | Border color for edge/corner faces in dark theme. |

### `control_color_dark`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(78, 78, 82, 125)` |
| **Description** | Control button fill color in dark theme. |

### `control_rim_color_dark`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(42, 42, 46, 175)` |
| **Description** | Control button border color in dark theme. |

### `hover_color_dark`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(0, 148, 255, 235)` |
| **Description** | Hover highlight color in dark theme. Same blue as light theme by default. |

### `hover_text_color_dark`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(255, 255, 255)` |
| **Description** | Hover text color in dark theme. |

### `dot_color_dark`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(145, 145, 148, 225)` |
| **Description** | Gizmo center dot color in dark theme. |

### `shadow_color_dark`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(0, 0, 0, 78)` |
| **Description** | Shadow color in dark theme. Stronger than the light theme default since dark backgrounds need more pronounced shadows. |

---

## Font

These fields control how face labels are rendered.

### `font_family`

| | |
|:--|:--|
| **Type** | `str` |
| **Default** | `"Arial"` |
| **Description** | Primary font family name for face labels. If this font is not available on the system, Qt falls back to the style hint specified by `font_fallback`. |

```python
style = NaviCubeStyle(font_family="Helvetica Neue")
style = NaviCubeStyle(font_family="Segoe UI")
style = NaviCubeStyle(font_family="Noto Sans CJK JP")  # For Japanese labels
```

### `font_fallback`

| | |
|:--|:--|
| **Type** | `str` |
| **Default** | `"SansSerif"` |
| **Description** | Qt font style hint used as a fallback when `font_family` is not available. This is passed to `QFont.setStyleHint()`. |

Valid values: `"SansSerif"`, `"Serif"`, `"Monospace"`, `"TypeWriter"`, `"Cursive"`, `"Fantasy"`, `"System"`.

```python
style = NaviCubeStyle(font_fallback="Monospace")
```

### `font_weight`

| | |
|:--|:--|
| **Type** | `str` |
| **Default** | `"bold"` |
| **Description** | Font weight for face labels. Maps to Qt font weight constants. |

Valid values: `"thin"`, `"extralight"`, `"light"`, `"normal"`, `"medium"`, `"demibold"`, `"bold"`, `"extrabold"`, `"black"`.

```python
# Lighter labels
style = NaviCubeStyle(font_weight="normal")

# Maximum weight
style = NaviCubeStyle(font_weight="black")
```

### `label_max_width_ratio`

| | |
|:--|:--|
| **Type** | `float` |
| **Default** | `0.70` |
| **Description** | Maximum fraction of the 200-unit virtual label canvas that text may occupy horizontally. The font size is automatically scaled down to fit within this width. Lower values force smaller text; higher values allow text to fill more of the face. |

```python
# Allow text to fill almost the entire face
style = NaviCubeStyle(label_max_width_ratio=0.90)

# Compact text with lots of margin
style = NaviCubeStyle(label_max_width_ratio=0.50)
```

### `label_max_height_ratio`

| | |
|:--|:--|
| **Type** | `float` |
| **Default** | `0.45` |
| **Description** | Maximum fraction of the 200-unit virtual label canvas that text may occupy vertically. Works in conjunction with `label_max_width_ratio` -- the font size is the minimum that satisfies both constraints. |

```python
# Taller text allowed
style = NaviCubeStyle(label_max_height_ratio=0.60)
```

### `min_font_size`

| | |
|:--|:--|
| **Type** | `float` |
| **Default** | `40.0` |
| **Description** | Minimum computed font point size in the 200-unit virtual label space. Prevents text from becoming unreadably small on faces with long labels. If the auto-computed size falls below this, the text may overflow the face slightly rather than becoming invisible. |

```python
# Allow very small text for long labels
style = NaviCubeStyle(min_font_size=20.0)

# Force large text
style = NaviCubeStyle(min_font_size=60.0)
```

---

## Labels

### `labels`

| | |
|:--|:--|
| **Type** | `Dict[str, str]` |
| **Default** | `{"TOP": "TOP", "FRONT": "FRONT", "LEFT": "LEFT", "BACK": "BACK", "RIGHT": "RIGHT", "BOTTOM": "BOTTOM"}` |
| **Description** | Mapping from internal face name to display text. Customize this for localization or alternative naming conventions. Only the six main faces have labels; edge and corner faces have no text. |

The keys must be exactly: `TOP`, `FRONT`, `LEFT`, `BACK`, `RIGHT`, `BOTTOM`.

```python
# German labels
style = NaviCubeStyle(labels={
    "TOP": "OBEN", "FRONT": "VORNE", "LEFT": "LINKS",
    "BACK": "HINTEN", "RIGHT": "RECHTS", "BOTTOM": "UNTEN",
})

# Japanese labels
style = NaviCubeStyle(
    font_family="Noto Sans CJK JP",
    labels={
        "TOP": "\u4e0a", "FRONT": "\u524d", "LEFT": "\u5de6",
        "BACK": "\u5f8c", "RIGHT": "\u53f3", "BOTTOM": "\u4e0b",
    },
)

# Short labels
style = NaviCubeStyle(labels={
    "TOP": "T", "FRONT": "F", "LEFT": "L",
    "BACK": "Bk", "RIGHT": "R", "BOTTOM": "Bo",
})
```

---

## Controls

### `show_controls`

| | |
|:--|:--|
| **Type** | `bool` |
| **Default** | `True` |
| **Description** | Whether to show the orbit buttons, roll arrows, home button, and backside dot around the cube. Setting this to `False` hides all control elements, leaving only the cube faces. |

```python
# Cube only, no surrounding buttons
style = NaviCubeStyle(show_controls=False)
```

The control elements include:
- **ArrowNorth / ArrowSouth / ArrowEast / ArrowWest** -- orbit buttons that rotate the camera by `orbit_step_deg`
- **ArrowLeft / ArrowRight** -- roll arrows that rotate the camera around the view axis
- **ViewMenu** -- home button (small cube icon) that returns to the home orientation
- **DotBackside** -- small dot that flips the camera 180 degrees to view the opposite side

### `show_gizmo`

| | |
|:--|:--|
| **Type** | `bool` |
| **Default** | `False` |
| **Description** | Whether to show an XYZ axis gizmo in the lower-left corner of the widget. The gizmo shows three colored lines representing the world X (red), Y (green), and Z (blue) axes, oriented to match the current camera view. |

```python
# Show the XYZ gizmo
style = NaviCubeStyle(show_gizmo=True)
```

### `gizmo_x_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(215, 52, 52)` |
| **Description** | Color of the X-axis line in the gizmo. Default is red. |

### `gizmo_y_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(52, 195, 52)` |
| **Description** | Color of the Y-axis line in the gizmo. Default is green. |

### `gizmo_z_color`

| | |
|:--|:--|
| **Type** | `Color` |
| **Default** | `(55, 115, 255)` |
| **Description** | Color of the Z-axis line in the gizmo. Default is blue. |

### `gizmo_font_size`

| | |
|:--|:--|
| **Type** | `int` |
| **Default** | `9` |
| **Description** | Font size in points for the X/Y/Z axis labels on the gizmo. |

---

## Border Widths

### `border_width_main`

| | |
|:--|:--|
| **Type** | `float` |
| **Default** | `2.0` |
| **Description** | Pen width in pixels for the border/outline of the six main faces. |

```python
# Thick borders
style = NaviCubeStyle(border_width_main=3.5)

# No visible borders
style = NaviCubeStyle(border_width_main=0.0)
```

### `border_width_secondary`

| | |
|:--|:--|
| **Type** | `float` |
| **Default** | `1.2` |
| **Description** | Pen width in pixels for the border/outline of edge and corner faces. Typically thinner than `border_width_main` to create visual hierarchy. |

### `control_border_width`

| | |
|:--|:--|
| **Type** | `float` |
| **Default** | `1.2` |
| **Description** | Pen width in pixels for the border of control buttons (orbit arrows, roll arrows, home, backside dot). |

---

## Shadow

### `shadow_offset_x`

| | |
|:--|:--|
| **Type** | `float` |
| **Default** | `1.8` |
| **Description** | Horizontal offset of the drop shadow behind each cube face, in pixels. Positive values shift the shadow to the right. |

### `shadow_offset_y`

| | |
|:--|:--|
| **Type** | `float` |
| **Default** | `2.3` |
| **Description** | Vertical offset of the drop shadow behind each cube face, in pixels. Positive values shift the shadow downward. |

```python
# No shadow
style = NaviCubeStyle(shadow_color=(0, 0, 0, 0))

# Dramatic shadow
style = NaviCubeStyle(
    shadow_offset_x=4.0,
    shadow_offset_y=5.0,
    shadow_color=(0, 0, 0, 100),
)
```

---

## Complete field reference table

| Field | Type | Default | Section |
|:------|:-----|:--------|:--------|
| `size` | `int` | `120` | Geometry |
| `padding` | `int` | `10` | Geometry |
| `scale` | `float` | `27.0` | Geometry |
| `chamfer` | `float` | `0.12` | Geometry |
| `animation_ms` | `int` | `240` | Animation |
| `tick_ms` | `int` | `16` | Animation |
| `visibility_threshold` | `float` | `0.10` | Thresholds |
| `orbit_step_deg` | `float` | `15.0` | Thresholds |
| `sync_epsilon` | `float` | `1e-3` | Thresholds |
| `inactive_opacity` | `float` | `0.72` | Thresholds |
| `light_direction` | `Tuple[float,float,float]` | `(-0.8, -1.0, -1.8)` | Lighting |
| `theme` | `str` | `"auto"` | Theme |
| `face_color` | `Color` | `(248, 248, 252)` | Light Colors |
| `edge_color` | `Color` | `(210, 210, 215)` | Light Colors |
| `corner_color` | `Color` | `(185, 185, 190)` | Light Colors |
| `text_color` | `Color` | `(18, 18, 18)` | Light Colors |
| `border_color` | `Color` | `(28, 28, 32)` | Light Colors |
| `border_secondary_color` | `Color` | `(50, 50, 55)` | Light Colors |
| `control_color` | `Color` | `(186, 186, 192, 120)` | Light Colors |
| `control_rim_color` | `Color` | `(105, 105, 110, 170)` | Light Colors |
| `hover_color` | `Color` | `(0, 148, 255, 235)` | Light Colors |
| `hover_text_color` | `Color` | `(255, 255, 255)` | Light Colors |
| `dot_color` | `Color` | `(195, 195, 198, 225)` | Light Colors |
| `shadow_color` | `Color` | `(0, 0, 0, 42)` | Light Colors |
| `face_color_dark` | `Color` | `(155, 160, 178)` | Dark Colors |
| `edge_color_dark` | `Color` | `(118, 122, 138)` | Dark Colors |
| `corner_color_dark` | `Color` | `(96, 99, 113)` | Dark Colors |
| `text_color_dark` | `Color` | `(238, 238, 238)` | Dark Colors |
| `border_color_dark` | `Color` | `(10, 10, 12)` | Dark Colors |
| `border_secondary_color_dark` | `Color` | `(20, 20, 22)` | Dark Colors |
| `control_color_dark` | `Color` | `(78, 78, 82, 125)` | Dark Colors |
| `control_rim_color_dark` | `Color` | `(42, 42, 46, 175)` | Dark Colors |
| `hover_color_dark` | `Color` | `(0, 148, 255, 235)` | Dark Colors |
| `hover_text_color_dark` | `Color` | `(255, 255, 255)` | Dark Colors |
| `dot_color_dark` | `Color` | `(145, 145, 148, 225)` | Dark Colors |
| `shadow_color_dark` | `Color` | `(0, 0, 0, 78)` | Dark Colors |
| `font_family` | `str` | `"Arial"` | Font |
| `font_fallback` | `str` | `"SansSerif"` | Font |
| `font_weight` | `str` | `"bold"` | Font |
| `label_max_width_ratio` | `float` | `0.70` | Font |
| `label_max_height_ratio` | `float` | `0.45` | Font |
| `min_font_size` | `float` | `40.0` | Font |
| `labels` | `Dict[str, str]` | `{"TOP":"TOP", ...}` | Labels |
| `show_controls` | `bool` | `True` | Controls |
| `show_gizmo` | `bool` | `False` | Controls |
| `gizmo_x_color` | `Color` | `(215, 52, 52)` | Controls |
| `gizmo_y_color` | `Color` | `(52, 195, 52)` | Controls |
| `gizmo_z_color` | `Color` | `(55, 115, 255)` | Controls |
| `gizmo_font_size` | `int` | `9` | Controls |
| `border_width_main` | `float` | `2.0` | Border Widths |
| `border_width_secondary` | `float` | `1.2` | Border Widths |
| `control_border_width` | `float` | `1.2` | Border Widths |
| `shadow_offset_x` | `float` | `1.8` | Shadow |
| `shadow_offset_y` | `float` | `2.3` | Shadow |

---

## Example: dark blue theme

```python
style = NaviCubeStyle(
    theme="dark",
    face_color_dark=(40, 60, 120),
    edge_color_dark=(30, 45, 90),
    corner_color_dark=(20, 30, 60),
    text_color_dark=(200, 220, 255),
    border_color_dark=(10, 15, 40),
    border_secondary_color_dark=(15, 20, 50),
    hover_color_dark=(80, 160, 255, 235),
    hover_text_color_dark=(255, 255, 255),
    control_color_dark=(30, 50, 100, 120),
    control_rim_color_dark=(20, 35, 70, 170),
    shadow_color_dark=(0, 0, 20, 90),
)
```

## Example: minimal wireframe theme

```python
style = NaviCubeStyle(
    theme="light",
    face_color=(255, 255, 255),
    edge_color=(255, 255, 255),
    corner_color=(255, 255, 255),
    text_color=(0, 0, 0),
    border_color=(0, 0, 0),
    border_secondary_color=(0, 0, 0),
    border_width_main=1.5,
    border_width_secondary=0.8,
    shadow_color=(0, 0, 0, 0),  # No shadow
    hover_color=(230, 230, 230, 255),
    hover_text_color=(0, 0, 0),
    show_controls=False,
    inactive_opacity=1.0,
)
```

## Runtime style changes with `set_style()`

```python
from navicube import NaviCubeOverlay, NaviCubeStyle

cube = NaviCubeOverlay(parent=win)

# Later, switch to a custom style
dark_style = NaviCubeStyle(theme="dark", size=150)
cube.set_style(dark_style)

# Switch back to defaults
cube.set_style(NaviCubeStyle())
```

`set_style()` performs the following steps internally:
1. Stores the new style
2. Recomputes all derived values (scale, light direction, thresholds, etc.)
3. Clears the font size cache
4. Rebuilds all face geometry (in case `chamfer` changed)
5. Recalculates DPI scaling and widget size
6. Updates the timer interval
7. Triggers a full repaint
