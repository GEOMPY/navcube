"""
example.py — geompy-display demo
=================================
Run:
    python example.py
"""

from geompy_display import OCCDisplay, ViewCubeConfig

cfg = ViewCubeConfig(
    cube_size   = 100.0,
    chamfer_r   =   8.0,
    silver      = (0.75, 0.75, 0.78),
    label_color = (0.0,  0.0,  0.0),
    side_margin = 0.15,
)

display = OCCDisplay(
    title    = "geompy-display — example",
    width    = 1100,
    height   = 800,
    viewcube = cfg,
)

@display.on_ready
def populate(d):
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCC.Core.AIS         import AIS_Shape
    from OCC.Core.Quantity    import Quantity_Color, Quantity_TOC_RGB

    box = BRepPrimAPI_MakeBox(40, 25, 15).Shape()
    ais = AIS_Shape(box)
    ais.SetColor(Quantity_Color(0.2, 0.5, 0.9, Quantity_TOC_RGB))
    d.context.Display(ais, True)
    d.display.FitAll()

display.start()
