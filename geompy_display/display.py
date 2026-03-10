"""
geompy_display.display
=======================
OCCDisplay — a drop-in wrapper around pythonocc-core's viewer that
always shows an orientation ViewCube in a chosen corner.

Usage
-----
    from geompy_display import OCCDisplay, ViewCubeConfig

    cfg = ViewCubeConfig(cube_size=25, position="top-right")
    display = OCCDisplay(title="My App", viewcube=cfg)

    @display.on_ready
    def populate(d):
        from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCC.Core.AIS import AIS_Shape
        d.context.Display(AIS_Shape(BRepPrimAPI_MakeBox(50,30,20).Shape()), True)

    display.start()
"""

import sys
import traceback

from .viewcube_config import ViewCubeConfig
from .viewcube        import ViewCube


class OCCDisplay:
    """
    Wrapper around qtViewer3d that automatically embeds an orientation
    ViewCube (chamfered cube with FRONT/BACK/LEFT/RIGHT/TOP/BOTTOM labels).

    Parameters
    ----------
    title    : str             — window title
    width    : int             — initial window width in pixels
    height   : int             — initial window height in pixels
    viewcube : ViewCubeConfig  — cube appearance/position config (None = default)
    bg_color : tuple           — background RGB [0..1]
    """

    _app    = None   # QApplication singleton
    _backend_loaded = False

    @classmethod
    def _ensure_app(cls):
        from PySide6.QtWidgets import QApplication
        if cls._app is None:
            cls._app = QApplication.instance() or QApplication(sys.argv)

    @classmethod
    def _ensure_backend(cls):
        if not cls._backend_loaded:
            from OCC.Display.backend import load_backend
            load_backend("pyside6")
            cls._backend_loaded = True

    # ── Init ───────────────────────────────────────────────────────────────────

    def __init__(
        self,
        title    : str            = "OCC Viewer",
        width    : int            = 1100,
        height   : int            = 800,
        viewcube : ViewCubeConfig = None,
        bg_color : tuple          = (0.32, 0.32, 0.32),
    ):
        self.title    = title
        self.width    = width
        self.height   = height
        self.bg_color = bg_color
        self._cfg     = viewcube if viewcube is not None else ViewCubeConfig()
        self._cube    = ViewCube(self._cfg)

        # Public OCC handles — set after _init_scene
        self.display  = None   # Viewer3d
        self.context  = None   # AIS_InteractiveContext
        self.view     = None   # V3d_View

        self._win          = None
        self._viewer       = None
        self._zoom_timer   = None
        self._on_ready_cb  = []

    # ── Public API ─────────────────────────────────────────────────────────────

    def on_ready(self, fn):
        """Register a callback fired once the viewer is initialised.

        The callback receives this OCCDisplay instance::

            @display.on_ready
            def populate(d):
                d.context.Display(AIS_Shape(my_shape), True)
        """
        self._on_ready_cb.append(fn)
        return fn

    def start(self):
        """Open the window and enter the Qt event loop. Blocks until closed."""
        self._ensure_app()
        self._ensure_backend()
        self._build_window()

        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, self._init_scene)
        sys.exit(self._app.exec())

    # ── Delegates ──────────────────────────────────────────────────────────────

    def DisplayShape(self, shape, update=True):
        """Display a TopoDS shape, returns the AIS_Shape object."""
        from OCC.Core.AIS import AIS_Shape
        ais = AIS_Shape(shape)
        self.context.Display(ais, update)
        return ais

    def FitAll(self):
        self.display.FitAll()

    def View_Iso(self):
        self.display.View_Iso()

    def View_Front(self):
        self.display.View_Front()

    def View_Top(self):
        self.display.View_Top()

    def EraseAll(self):
        """Erase all user shapes but KEEP the ViewCube."""
        self.context.EraseAll(False)
        self._cube.show(self.context, self._viewer)
        self.context.UpdateCurrentViewer()

    # ── Window ─────────────────────────────────────────────────────────────────

    def _build_window(self):
        from PySide6.QtWidgets import QMainWindow
        from OCC.Display.qtDisplay import qtViewer3d

        self._win = QMainWindow()
        self._win.setWindowTitle(self.title)
        self._win.resize(self.width, self.height)

        self._viewer = qtViewer3d(self._win)
        self._win.setCentralWidget(self._viewer)
        self._win.show()

    # ── Scene init (deferred) ──────────────────────────────────────────────────

    def _init_scene(self):
        try:
            from PySide6.QtCore import QTimer

            self.display = self._viewer._display
            self.context = self.display.Context
            self.view    = self.display.View

            # FitAll FIRST — Scale()/Convert() must be valid before cube placement
            self.display.View_Iso()
            self.display.FitAll()

            # ViewCube — placed after FitAll so corner offset is correct
            self._cube.show(self.context, self._viewer)
            ViewCube.show_trihedron(self.view)

            # Zoom-adaptive line width timer
            self._zoom_timer = QTimer()
            self._zoom_timer.timeout.connect(self._on_zoom_tick)
            self._zoom_timer.start(150)

            # User callbacks
            for fn in self._on_ready_cb:
                try:
                    fn(self)
                except Exception:
                    traceback.print_exc()

            print("[OCCDisplay] ready — ViewCube active.")

        except Exception:
            print("[OCCDisplay] ERROR during scene init:")
            traceback.print_exc()

    # ── Zoom tick ──────────────────────────────────────────────────────────────

    def _on_zoom_tick(self):
        if self.context is None:
            return
        try:
            scale = self.view.Scale()
            self._cube.update_line_width(self.context, scale)
        except Exception:
            pass