# geompy-display

geompy-display is a Python wrapper around pythonocc-core's viewer with an always-on 3D orientation ViewCube.

It is designed as a practical, drop-in display layer for OCC-based applications, with a clean API and configurable ViewCube rendering.

## Highlights

- Always-visible orientation ViewCube with labeled faces.
- Zoom-adaptive line rendering for readable labels.
- Simple event setup with an `on_ready` callback.
- Direct access to OCC viewer handles when advanced control is needed.

## Installation

Install the package:

```bash
pip install geompy-display
```

Install pythonocc-core separately (conda-forge):

```bash
conda install -c conda-forge pythonocc-core
```

## Quick Start

```python
from geompy_display import OCCDisplay, ViewCubeConfig

cfg = ViewCubeConfig(
	cube_size=30.0,
	chamfer_r=5,
	position="top-right",
	padding=4.0,
)

display = OCCDisplay(
	title="geompy-display example",
	width=1100,
	height=800,
	viewcube=cfg,
)


@display.on_ready
def populate(d):
	# Add OCC geometry here.
	# from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
	# from OCC.Core.AIS import AIS_Shape
	# d.context.Display(AIS_Shape(BRepPrimAPI_MakeBox(50, 30, 20).Shape()), True)
	pass


display.start()
```

## Core API

- `OCCDisplay`: Main viewer wrapper.
- `ViewCubeConfig`: ViewCube appearance and placement options.
- `ViewCube`: Low-level ViewCube implementation.

See full generated API docs in [API Reference](api.md).

## Typical Workflow

1. Create `OCCDisplay` with optional `ViewCubeConfig`.
2. Register an `on_ready` callback to add shapes.
3. Call `start()` to run the Qt event loop.

## Project Links

- Source example: [example.py](https://github.com/GEOMPY/geompy-display/blob/main/example.py)
- API docs: [API Reference](api.md)
