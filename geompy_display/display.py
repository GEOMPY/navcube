"""
occdisplay.display
==================
OCCDisplay — a drop-in replacement for the standard pythonocc-core display
that always renders an orientation ViewCube in the top-right corner.

Usage
-----
    from occdisplay import OCCDisplay, ViewCubeConfig

    # Optional: customise before creation
    cfg = ViewCubeConfig(cube_size=80, chamfer_r=6)

    display = OCCDisplay(title="My App", viewcube=cfg)
    display.start()                        # blocks — opens the window

    # Inside callbacks / after start you can access the raw OCC objects:
    display.display   →  OCC Viewer3d  (same as what init_display() returns)
    display.context   →  AIS_InteractiveContext
    display.view      →  V3d_View
"""

import sys
import traceback

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore    import QTimer

# OCC backend must be loaded before qtViewer3d
from OCC.Display.backend  import load_backend
load_backend("pyside6")
from OCC.Display.qtDisplay import qtViewer3d

from .viewcube_config import ViewCubeConfig
from .viewcube        import ViewCube


class OCCDisplay:
    """
    Wrapper around qtViewer3d that automatically embeds an orientation
    ViewCube (chamfered cube with FRONT/BACK/LEFT/RIGHT/TOP/BOTTOM labels).

    Parameters
    ----------
    title : str
        Window title.
    width, height : int
        Initial window size in pixels.
    viewcube : ViewCubeConfig | None
        Visual config for the cube.  Pass ``None`` to disable the cube.
    bg_color : tuple(float,float,float)
        Background colour RGB [0..1].  Default is dark grey.
    """

    # ── QApplication singleton ─────────────────────────────────────────────────
    # One QApplication per process — shared if already created.
    _app = None

    @classmethod
    def _ensure_app(cls):
        if cls._app is None:
            cls._app = QApplication.instance() or QApplication(sys.argv)

    # ── Init ───────────────────────────────────────────────────────────────────

    def __init__(
        self,
        title:     str            = "OCC Viewer",
        width:     int            = 1100,
        height:    int            = 800,
        viewcube:  ViewCubeConfig = None,
        bg_color:  tuple          = (0.32, 0.32, 0.32),
    ):
        self._ensure_app()

        self.title     = title
        self.width     = width
        self.height    = height
        self.bg_color  = bg_color
        self._cfg      = viewcube if viewcube is not None else ViewCubeConfig()
        self._cube     = ViewCube(self._cfg)

        # Public OCC handles (set after _init_scene)
        self.display   = None   # Viewer3d
        self.context   = None   # AIS_InteractiveContext
        self.view      = None   # V3d_View

        self._win      = None
        self._viewer   = None
        self._label_ais = []
        self._zoom_timer = QTimer()
        self._zoom_timer.timeout.connect(self._on_zoom_tick)

        self._on_ready_cb  = []   # user callbacks fired after scene init

    # ── Public API ─────────────────────────────────────────────────────────────

    def on_ready(self, fn):
        """Register a callback fired once the viewer is initialised.

        The callback receives this OCCDisplay instance::

            @display.on_ready
            def populate(d):
                ais = AIS_Shape(my_shape)
                d.context.Display(ais, True)
        """
        self._on_ready_cb.append(fn)
        return fn

    def start(self):
        """Open the window and enter the Qt event loop.  Blocks until closed."""
        self._build_window()
        QTimer.singleShot(200, self._init_scene)
        sys.exit(self._app.exec())

    # ── Delegates that mirror the standard pythonocc display API ───────────────

    def DisplayShape(self, shape, update=True):
        """Display a TopoDS shape."""
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
        # Re-display the cube so it survives EraseAll
        self._cube.show(self.context)
        self.context.UpdateCurrentViewer()

    # ── Window construction ────────────────────────────────────────────────────

    def _build_window(self):
        self._win = QMainWindow()
        self._win.setWindowTitle(self.title)
        self._win.resize(self.width, self.height)

        self._viewer = qtViewer3d(self._win)
        self._win.setCentralWidget(self._viewer)
        self._win.show()

    # ── Scene initialisation (deferred via QTimer) ─────────────────────────────

    def _init_scene(self):
        try:
            self.display = self._viewer._display
            self.context = self.display.Context
            self.view    = self.display.View

            # ViewCube
            self._cube.show(self.context)
            ViewCube.show_trihedron(self.view)

            # Camera
            self.display.View_Iso()
            self.display.FitAll()

            # Zoom-adaptive line width
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
