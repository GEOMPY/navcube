"""geompy-display: Orientation ViewCube for pythonocc-core viewer.

A Pythonic wrapper around pythonocc-core's viewer with an always-on orientation
ViewCube featuring zoom-adaptive stroke rendering.

Attributes:
    __version__ (str): Package version.

Examples:
    Basic usage with default ViewCube configuration:

        >>> from geompy_display import OCCDisplay, ViewCubeConfig
        >>> display = OCCDisplay(title="My App")
        >>> @display.on_ready
        ... def populate(d):
        ...     from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
        ...     from OCC.Core.AIS import AIS_Shape
        ...     d.context.Display(AIS_Shape(BRepPrimAPI_MakeBox(50,30,20).Shape()), True)
        >>> display.start()

    Customizing ViewCube position and size:

        >>> cfg = ViewCubeConfig(cube_size=30, position="top-left")
        >>> display = OCCDisplay(title="My App", viewcube=cfg)
"""

from .viewcube_config import ViewCubeConfig
from .viewcube import ViewCube
from .display import OCCDisplay

__all__: list[str] = ["OCCDisplay", "ViewCubeConfig", "ViewCube"]
__version__: str = "0.1.0"
