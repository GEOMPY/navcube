---
layout: default
title: Coordinate Systems
---

# Coordinate Systems

Understanding how pyside-navicube maps between its internal coordinate space and your application's world space.

---

## Z-up vs Y-up

3D applications disagree on which axis points "up":

| Convention | Used by | Up axis | Forward axis |
|:-----------|:--------|:--------|:-------------|
| **Z-up** | OCC, FreeCAD, Blender (world), AutoCAD, Civil engineering | +Z | -Y or +X |
| **Y-up** | Three.js, glTF, Unity, Unreal, most game engines | +Y | -Z or +X |

pyside-navicube renders internally in **Z-up** space. The face labeled "TOP" always corresponds to the +Z direction in the internal coordinate system. The `_WORLD_ROT` matrix bridges between internal Z-up space and your application's world space.

---

## How `_WORLD_ROT` works

`_WORLD_ROT` is a 3x3 rotation matrix that maps **FROM** navicube's internal Z-up space **TO** your application's world space:

```
world_vector = _WORLD_ROT @ navicube_vector
navicube_vector = _WORLD_ROT.T @ world_vector
```

### Default: Z-up (identity)

For Z-up applications (OCC, FreeCAD, Blender), no transformation is needed:

```python
_WORLD_ROT = np.eye(3)  # identity matrix -- this is the default
```

```
Internal Z-up          Your world (Z-up)
    +Z (TOP)    --->       +Z (TOP)
    +Y (BACK)   --->       +Y (BACK)
    +X (RIGHT)  --->       +X (RIGHT)
```

### Y-up transformation

For Y-up applications, the transformation swaps Y and Z (with a sign flip to maintain a right-handed system):

```python
_WORLD_ROT = np.array([
    [1,  0,  0],
    [0,  0, -1],
    [0,  1,  0],
])
```

```
Internal Z-up          Your world (Y-up)
    +Z (TOP)    --->       +Y (TOP)
    +Y (BACK)   --->       -Z (BACK)
    +X (RIGHT)  --->       +X (RIGHT)
```

This matrix rotates -90 degrees around the X axis, turning Z-up into Y-up.

---

## Subclassing for Y-up

The recommended way to use pyside-navicube with a Y-up engine is to subclass `NaviCubeOverlay` and set `_WORLD_ROT` as a class attribute:

```python
import numpy as np
from navicube import NaviCubeOverlay

class YUpNaviCube(NaviCubeOverlay):
    """NaviCube configured for Y-up coordinate systems (Three.js, Unity, etc.)."""
    _WORLD_ROT = np.array([
        [1,  0,  0],
        [0,  0, -1],
        [0,  1,  0],
    ], dtype=float)

# Usage
cube = YUpNaviCube(parent=viewport)
cube.viewOrientationRequested.connect(on_orient)

# push_camera receives Y-up vectors directly -- no manual conversion needed
cube.push_camera(dx, dy, dz, ux, uy, uz)
```

The `__init_subclass__` hook ensures each subclass gets its own copy of `_WORLD_ROT`, so mutating one subclass never affects another.

**Important:** Both `push_camera()` and `viewOrientationRequested` work in YOUR world space. The navicube converts to/from internal Z-up space internally. You never need to manually transform coordinates.

---

## Sign convention

This is the most critical contract in the library. Getting the sign wrong will cause the navicube to rotate backwards.

### `push_camera` -- INWARD direction

```
push_camera(dx, dy, dz, ux, uy, uz)
             ↑                ↑
        INWARD dir        Up vector
       (eye → scene)
```

The direction vector points FROM the camera eye TOWARD the scene center. This is the convention used by OCC's `Camera().Direction()`.

### `viewOrientationRequested` -- OUTWARD direction

```
viewOrientationRequested(dx, dy, dz, ux, uy, uz)
                          ↑                ↑
                     OUTWARD dir       Up vector
                    (scene → eye)
```

The direction vector points FROM the scene center TOWARD the camera eye. This is the convention used by OCC's `V3d_View.SetProj()`.

### Mnemonic

> **Read inward, write outward.**
>
> - You **read** your camera state and push it **inward** (eye toward scene).
> - The navicube **writes** orientation requests **outward** (scene toward eye).

The navicube handles the negation internally. You never need to flip signs yourself.

---

## Sign convention cheat sheet

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR RENDERER                        │
│                                                         │
│  Camera state:                                          │
│    direction = eye → scene   (INWARD)                   │
│    up        = camera up vector                         │
│                                                         │
│         │ push_camera(dir, up)                           │
│         ▼                                               │
│  ┌─────────────────────────────┐                        │
│  │     NaviCubeOverlay         │                        │
│  │                             │                        │
│  │  Internal: negates dir      │                        │
│  │  for emission               │                        │
│  └─────────────────────────────┘                        │
│         │ viewOrientationRequested(-dir, up)             │
│         ▼                                               │
│                                                         │
│  Update camera:                                         │
│    SetProj(dx, dy, dz)  ← OUTWARD (scene → eye)        │
│    SetUp(ux, uy, uz)                                    │
│    Redraw()                                             │
└─────────────────────────────────────────────────────────┘
```

---

## Axis diagrams

### Z-up coordinate system (default)

```
        +Z (TOP)
         │
         │
         │
         │
         ┼──────── +X (RIGHT)
        ╱
       ╱
      ╱
    +Y (BACK)


    Face mapping:
    ┌─────────────────────────┐
    │  +Z normal  →  TOP      │
    │  -Z normal  →  BOTTOM   │
    │  -Y normal  →  FRONT    │
    │  +Y normal  →  BACK     │
    │  +X normal  →  RIGHT    │
    │  -X normal  →  LEFT     │
    └─────────────────────────┘
```

### Y-up coordinate system (with `_WORLD_ROT`)

```
        +Y (TOP)
         │
         │
         │
         │
         ┼──────── +X (RIGHT)
        ╱
       ╱
      ╱
    +Z (FRONT)


    World-space face mapping after _WORLD_ROT:
    ┌─────────────────────────┐
    │  +Y normal  →  TOP      │
    │  -Y normal  →  BOTTOM   │
    │  +Z normal  →  FRONT    │
    │  -Z normal  →  BACK     │
    │  +X normal  →  RIGHT    │
    │  -X normal  →  LEFT     │
    └─────────────────────────┘
```

### Default ISO view

The default camera orientation is an isometric view looking at the FRONT-RIGHT-TOP corner:

```
        +Z
         │  ╲
         │    ╲  Camera looks from here
         │      ●  (iso view)
         │    ╱
         ┼──╱──── +X
        ╱
       ╱
    +Y

    Default inward direction: normalize(-1, +1, -1)
    Default up vector: (0, 0, +1)
```

The camera looks toward the origin from the direction `(-1, +1, -1)` (normalized), with Z as the up vector. This places the FRONT, RIGHT, and TOP faces all partially visible.

---

## Custom `_WORLD_ROT` examples

### Left-handed Y-up (rare)

```python
class LeftHandedYUpNaviCube(NaviCubeOverlay):
    _WORLD_ROT = np.array([
        [1,  0,  0],
        [0,  0,  1],
        [0, -1,  0],
    ], dtype=float)
```

### Swapped X and Y

```python
class SwappedXYNaviCube(NaviCubeOverlay):
    _WORLD_ROT = np.array([
        [0,  1,  0],
        [1,  0,  0],
        [0,  0,  1],
    ], dtype=float)
```

### Arbitrary rotation

You can use any valid 3x3 rotation matrix. The matrix must be orthonormal (columns are unit vectors, mutually perpendicular) for correct behavior.
