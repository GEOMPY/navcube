from geompy_display import OCCDisplay, ViewCubeConfig

cfg = ViewCubeConfig(
    cube_size   = 30.0,
    chamfer_r   =  5,
    position    = "top-right",   # "top-right"|"top-left"|"bottom-right"|"bottom-left"
    padding     =  4.0,
    silver      = (0.75, 0.75, 0.78),
    label_color = (0.0,  0.0,  0.0),
    side_margin =  0.15,
)

display = OCCDisplay(
    title    = "geompy-display — example",
    width    = 1100,
    height   = 800,
    viewcube = cfg,
)

@display.on_ready
def populate(d):
    # Add your OCC geometry here:
    # from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
    # from OCC.Core.AIS import AIS_Shape
    # d.context.Display(AIS_Shape(BRepPrimAPI_MakeBox(50,30,20).Shape()), True)
    # d.display.FitAll()
    pass

display.start()