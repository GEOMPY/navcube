# geompy-display

> A Pythonic wrapper around pythonocc-core's viewer — adds an always-on 3D orientation ViewCube (chamfered, labelled faces) with zoom-adaptive stroke rendering. Drop-in replacement for `init_display()`.

Part of the [geompy](https://github.com/geompy) organization.

---

## Install

```bash
pip install geompy-display
```

> **Note:** `pythonocc-core` must be installed separately via conda:
> ```bash
> conda install -c conda-forge pythonocc-core
> ```

---

## Quick start

```python
from occdisplay import OCCDisplay, ViewCubeConfig

display = OCCDisplay(title="My App")

@display.on_ready
def populate(d):
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCC.Core.AIS import AIS_Shape
    box = BRepPrimAPI_MakeBox(50, 30, 20).Shape()
    d.context.Display(AIS_Shape(box), True)

display.start()   # blocks until window is closed
```

---

## ViewCube config

All parameters are optional — defaults work out of the box.

```python
cfg = ViewCubeConfig(
    cube_size    = 100.0,            # mm — side length
    chamfer_r    =   8.0,            # mm — bevel on edges/corners
    silver       = (0.75, 0.75, 0.78),  # face colour RGB
    label_color  = (0.0,  0.0,  0.0),   # text colour RGB
    side_margin  =   0.15,           # empty fraction each side of face
    char_aspect  =   0.60,           # letter width ratio
)

display = OCCDisplay(viewcube=cfg)
display.start()
```

Update any param before `start()`:

```python
cfg.update(cube_size=60, chamfer_r=4)
```

---

## API

| | |
|---|---|
| `display.start()` | Open window, enter event loop (blocks) |
| `display.on_ready(fn)` | Callback fired once viewer is live |
| `display.context` | `AIS_InteractiveContext` |
| `display.display` | `Viewer3d` |
| `display.view` | `V3d_View` |
| `display.DisplayShape(shape)` | Display a TopoDS shape |
| `display.EraseAll()` | Erase user shapes, keep ViewCube |
| `display.FitAll()` | Fit view to content |

---

## Controls

| Action | Input |
|---|---|
| Rotate | Left mouse drag |
| Zoom | Scroll wheel |
| Pan | Middle mouse drag |

---

## Structure

```
occdisplay/
├── __init__.py          # public API
├── display.py           # OCCDisplay — main wrapper
├── viewcube.py          # geometry + renderer
├── viewcube_config.py   # parameters dataclass
└── glyphs.py            # stroke font data
example.py
setup.py
LICENSE
NOTICE.md
README.md
```

---

## License

MIT — see [LICENSE](./LICENSE)

Third-party dependency notices — see [NOTICE.md](./NOTICE.md)
