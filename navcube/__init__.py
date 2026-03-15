"""
navcube
───────────────
A zero-dependency FreeCAD-style NaviCube widget for PySide6 applications.

    >>> from navcube import NavCubeOverlay
    >>> cube = NavCubeOverlay(parent=my_window)
    >>> cube.show()
    >>> cube.viewOrientationRequested.connect(my_camera_fn)
    >>> cube.push_camera(dx, dy, dz, ux, uy, uz)
"""

from navcube.widget import NavCubeOverlay, NavCubeStyle

__all__ = ["NavCubeOverlay", "NavCubeStyle"]

try:
    from importlib.metadata import version as _v
    __version__ = _v("navcube")
except Exception:
    __version__ = "unknown"
