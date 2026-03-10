"""
geompy-display
==============
A Pythonic wrapper around pythonocc-core's viewer — always-on orientation
ViewCube with zoom-adaptive stroke rendering.

    from geompy_display import OCCDisplay, ViewCubeConfig

    display = OCCDisplay(title="My App")

    @display.on_ready
    def populate(d):
        from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCC.Core.AIS import AIS_Shape
        d.context.Display(AIS_Shape(BRepPrimAPI_MakeBox(50,30,20).Shape()), True)

    display.start()
"""

from .viewcube_config import ViewCubeConfig
from .viewcube        import ViewCube
from .display         import OCCDisplay

__all__    = ["OCCDisplay", "ViewCubeConfig", "ViewCube"]
__version__ = "0.1.0"
