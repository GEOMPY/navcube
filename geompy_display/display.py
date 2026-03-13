"""OCCDisplay: Drop-in viewer wrapper with automatic orientation ViewCube.

This module provides `OCCDisplay`, a high-level wrapper around pythonocc-core's
Viewer3d that automatically embeds an orientation ViewCube in a configurable
corner with zoom-adaptive stroke rendering.

Typical Usage:
    >>> from geompy_display import OCCDisplay, ViewCubeConfig
    >>> cfg = ViewCubeConfig(cube_size=25, position="top-right")
    >>> display = OCCDisplay(title="My App", viewcube=cfg)
    >>> @display.on_ready
    ... def populate(d):
    ...     from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
    ...     from OCC.Core.AIS import AIS_Shape
    ...     d.context.Display(AIS_Shape(BRepPrimAPI_MakeBox(50,30,20).Shape()), True)
    >>> display.start()
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable, TYPE_CHECKING

from .viewcube_config import ViewCubeConfig
from .viewcube import ViewCube

if TYPE_CHECKING:
    from OCC.Core.AIS import AIS_InteractiveContext
    from OCC.Core.V3d import V3d_View
    from OCC.Display.qtDisplay import qtViewer3d
    from OCC.Display.SimpleGui import Viewer3d
    from PySide6.QtWidgets import QMainWindow
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication


log = logging.getLogger(__name__)


class OCCDisplay:
    """Wrapper around qtViewer3d with automatic orientation ViewCube integration.

    Embeds a chamfered cube with FRONT/BACK/LEFT/RIGHT/TOP/BOTTOM labels
    in a configurable screen corner. Provides both direct OCC handles and
    high-level convenience methods.

    Attributes:
        title (str): Window title.
        width (int): Initial window width in pixels.
        height (int): Initial window height in pixels.
        bg_color (tuple): Background RGB color, each channel in [0..1].
        display: OCC Viewer3d object (set after initialization).
        context: OCC AIS_InteractiveContext (set after initialization).
        view: OCC V3d_View (set after initialization).

    Args:
        title: Window title. Defaults to "OCC Viewer".
        width: Initial window width in pixels. Defaults to 1100.
        height: Initial window height in pixels. Defaults to 800.
        viewcube: ViewCubeConfig instance or None for defaults.
        bg_color: Background RGB tuple [0..1] per channel. Defaults to (0.32, 0.32, 0.32).

    Examples:
        Basic setup with default configuration:

            >>> display = OCCDisplay(title="My Viewer")
            >>> @display.on_ready
            ... def setup(d):
            ...     # Access d.context, d.display, d.view
            ...     pass
            >>> display.start()

        Custom ViewCube configuration:

            >>> cfg = ViewCubeConfig(cube_size=30, position="bottom-left", padding=10)
            >>> display = OCCDisplay(title="Custom", viewcube=cfg, width=1200, height=900)
    """

    _app: QApplication | None = (
        None  # QApplication singleton (PySide6.QtWidgets.QApplication)
    )
    _backend_loaded: bool = False

    @classmethod
    def _ensure_app(cls) -> None:
        """Ensure QApplication instance exists.

        Creates a new QApplication or reuses existing instance.
        This must be called before creating vieweres.
        """
        from PySide6.QtWidgets import QApplication

        if cls._app is None:
            cls._app = QApplication.instance() or QApplication(sys.argv)

    @classmethod
    def _ensure_backend(cls) -> None:
        """Load pythonocc-core pyside6 backend.

        Must be called before creating viewers. Sets the rendering backend
        to use PySide6 for all subsequent viewer instances.
        """
        if not cls._backend_loaded:
            from OCC.Display.backend import load_backend

            load_backend("pyside6")
            cls._backend_loaded = True

    def __init__(
        self,
        title: str = "OCC Viewer",
        width: int = 1100,
        height: int = 800,
        viewcube: ViewCubeConfig | None = None,
        bg_color: tuple[float, float, float] = (0.32, 0.32, 0.32),
    ) -> None:
        """Initialize OCCDisplay instance.

        Args:
            title: Window title.
            width: Initial window width in pixels.
            height: Initial window height in pixels.
            viewcube: ViewCubeConfig instance, or None to use defaults.
            bg_color: Background RGB tuple with values in [0..1].

        Raises:
            ValueError: If bg_color is not a valid RGB tuple.
        """
        self.title: str = title
        self.width: int = width
        self.height: int = height
        self.bg_color: tuple[float, float, float] = bg_color
        self._cfg: ViewCubeConfig = (
            viewcube if viewcube is not None else ViewCubeConfig()
        )
        self._cube: ViewCube = ViewCube(self._cfg)

        # Public OCC handles — set after _init_scene
        self.display: Viewer3d | None = None  # Viewer3d
        self.context: AIS_InteractiveContext | None = None
        self.view: V3d_View | None = None

        self._win: QMainWindow | None = None
        self._viewer: qtViewer3d | None = None
        self._zoom_timer: QTimer | None = None
        self._last_scale: float | None = None
        self._on_ready_cb: list[Callable[["OCCDisplay"], None]] = []

    def on_ready(
        self, fn: Callable[["OCCDisplay"], None]
    ) -> Callable[["OCCDisplay"], None]:
        """Register callback to run after viewer initialization.

        The callback receives the initialized OCCDisplay instance as its sole argument,
        allowing access to `display`, `context`, and `view` OCC handles.

        Args:
            fn: Callback function accepting this OCCDisplay instance.

        Returns:
            The callback function (allows use as decorator).

        Examples:
            >>> display = OCCDisplay()
            >>> @display.on_ready
            ... def setup(d):
            ...     from OCC.Core.AIS import AIS_Shape
            ...     d.context.Display(AIS_Shape(some_shape), True)
        """
        self._on_ready_cb.append(fn)
        return fn

    def start(self) -> int:
        """Open the window and enter the Qt event loop.

        Blocks execution until the window is closed by the user.
        Initializes scene and runs all registered on_ready callbacks
        before starting the Qt event loop.

        Returns:
            The Qt application exit code. Return this to parent process if desired.

        Examples:
            >>> display = OCCDisplay(title="My App")
            >>> exit_code = display.start()
            >>> sys.exit(exit_code)
        """
        self._ensure_app()
        self._ensure_backend()
        self._build_window()

        from PySide6.QtCore import QTimer

        QTimer.singleShot(200, self._init_scene)
        if self._app is not None:
            return self._app.exec()
        else:
            log.warning("QApplication instance not found when starting event loop")
            return 1

    # ── Delegates ──────────────────────────────────────────────────────────────

    def DisplayShape(self, shape: Any, update: bool = True) -> Any:
        """Display a TopoDS shape in the viewer.

        Wraps the shape in an AIS_Shape and displays it in the context.

        Args:
            shape: OCC TopoDS shape to display.
            update: If True, update the viewer immediately.

        Returns:
            The AIS_Shape display object for further manipulation.

        Examples:
            >>> from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
            >>> from OCC.Core.AIS import AIS_Shape
            >>> @display.on_ready
            ... def show(d):
            ...     shape = BRepPrimAPI_MakeBox(10, 20, 30).Shape()
            ...     ais = d.DisplayShape(shape)
        """
        from OCC.Core.AIS import AIS_Shape

        ais = AIS_Shape(shape)
        if self.context is not None:
            self.context.Display(ais, update)
        else:
            log.warning("DisplayShape called before context is initialized")
        return ais

    def FitAll(self) -> None:
        """Fit all geometry in the view.

        Adjusts the camera and zoom level to show all displayed shapes.
        """
        if self.display is not None:
            self.display.FitAll()
        else:
            log.warning("FitAll called before display is initialized")

    def View_Iso(self) -> None:
        """Set isometric view orientation.

        Sets the view to a standard isometric angle (±45°, ±30° elevation).
        """
        if self.display is not None:
            self.display.View_Iso()
        else:
            log.warning("View_Iso called before display is initialized")

    def View_Front(self) -> None:
        """Set front view orientation.

        Sets the view to look directly at the front side of the model.
        """
        if self.display is not None:
            self.display.View_Front()
        else:
            log.warning("View_Front called before display is initialized")

    def View_Top(self) -> None:
        """Set top view orientation.

        Sets the view to look down from above the model.
        """
        if self.display is not None:
            self.display.View_Top()
        else:
            log.warning("View_Top called before display is initialized")

    def EraseAll(self) -> None:
        """Erase all user-displayed shapes except the ViewCube.

        Clears the scene while preserving the orientation cube for navigation.
        """
        if self.context is not None:
            self.context.EraseAll(False)
        else:
            log.warning("EraseAll called before context is initialized")
        if self._cube is not None:
            self._cube.redisplay(self.context)
        else:
            log.warning("EraseAll called before ViewCube is initialized")

    # ── Window ─────────────────────────────────────────────────────────────────

    def _build_window(self) -> None:
        """Create and configure the main QMainWindow and qtViewer3d.

        Sets up the window with the configured title, width, and height.
        Called internally by start() before entering the event loop.
        """
        from PySide6.QtWidgets import QMainWindow
        from OCC.Display.qtDisplay import qtViewer3d

        self._win = QMainWindow()
        self._win.setWindowTitle(self.title)
        self._win.resize(self.width, self.height)

        self._viewer = qtViewer3d(self._win)
        self._win.setCentralWidget(self._viewer)
        self._win.show()

    # ── Scene init (deferred) ──────────────────────────────────────────────────

    def _init_scene(self) -> None:
        """Initialize the OCC viewer and display the ViewCube.

        Called deferred by start() via QTimer to ensure Qt event loop is active.
        Sets up OCC context handles, fits the view, displays the ViewCube,
        and runs all registered on_ready callbacks.

        Handles exceptions gracefully by logging them without crashing.
        """
        try:
            from PySide6.QtCore import QTimer

            if self.display is not None:
                if self._viewer is not None:
                    self.display = self._viewer._display
                else:
                    log.warning(
                        "qtViewer3d instance not found during scene initialization"
                    )
            else:
                log.warning("Viewer3d instance not found during scene initialization")
            self.context = self.display.Context
            self.view = self.display.View

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
                    log.exception("on_ready callback %s failed", fn.__name__)

            log.info("ready — ViewCube active.")

        except Exception:
            log.exception("scene init failed")

    # ── Zoom tick ──────────────────────────────────────────────────────────────

    def _on_zoom_tick(self) -> None:
        """Callback triggered on zoom changes to update ViewCube line width.

        Called ~6.7 times per second (150ms interval) to check if the view
        scale has changed. If so, recalculates the ViewCube stroke width
        to maintain visual thickness as the user zooms.

        This ensures the ViewCube remains clearly visible at any zoom level.
        """
        if self.context is None:
            return None
        try:
            if self.view is None:
                log.warning("View not initialized during zoom tick")
                return None
            scale = self.view.Scale()
            if scale == self._last_scale:
                return
            self._last_scale = scale
            self._cube.update_line_width(self.context, scale)
        except Exception:
            log.debug("zoom tick failed", exc_info=True)
