"""
navicube.connectors.vtk  —  VTK / PyVista ↔ NavCubeOverlay connector
======================================================================
Bridges a vtkRenderer (or PyVista Plotter) with a NavCubeOverlay widget.
This is the only file in the library that imports VTK.

Usage — plain VTK
─────────────────
    from navicube import NavCubeOverlay
    from navcube.connectors.vtk import VTKNavCubeSync

    cube = NavCubeOverlay(parent=vtk_widget)
    cube.show()

    sync = VTKNavCubeSync(renderer, cube, render_window=vtk_widget.GetRenderWindow())

    # In your interactor style's OnLeftButtonDown / OnLeftButtonUp:
    sync.set_interaction_active(True)   # drag start
    sync.set_interaction_active(False)  # drag end

    # When the viewer is torn down:
    sync.teardown()

Usage — PyVista
───────────────
    import pyvista as pv
    from navicube import NavCubeOverlay
    from navcube.connectors.vtk import VTKNavCubeSync

    pl = pv.Plotter()
    cube = NavCubeOverlay(parent=None)  # or parent to plotter widget
    cube.show()

    sync = VTKNavCubeSync(
        pl.renderer,
        cube,
        render_window=pl.render_window,
    )

Camera direction convention
───────────────────────────
  VTK camera: position - focal_point = outward direction (eye → scene centre is inward).
  push_camera expects the INWARD direction, so we negate (position - focal_point).

  viewOrientationRequested emits the OUTWARD direction, so we set:
      camera.SetPosition(focal_point + outward * distance)
      camera.SetViewUp(ux, uy, uz)
"""

import math
from PySide6.QtCore import QTimer


class VTKNavCubeSync:
    """
    Connects a vtkRenderer's camera to a NavCubeOverlay.

    Parameters
    ──────────
    renderer       vtkRenderer instance (must already have a camera)
    navicube       NavCubeOverlay instance
    render_window  vtkRenderWindow to call Render() on after orientation
                   changes.  If None, renderer.GetRenderWindow() is used.
    """

    _TICK_MS           = 16   # poll interval ms
    _INTERACTION_TICKS = 1    # every tick during drag  (~16 ms)
    _IDLE_TICKS        = 4    # every 4 ticks when idle (~64 ms)

    def __init__(self, renderer, navicube, render_window=None):
        self._renderer     = renderer
        self._navicube     = navicube
        self._render_window = render_window
        self._interaction_active = False
        self._tick_count   = 0

        navicube.viewOrientationRequested.connect(self._on_orientation_requested)

        self._tmr = QTimer()
        self._tmr.timeout.connect(self._tick)
        self._tmr.start(self._TICK_MS)

    # ── public ──────────────────────────────────────────────────────

    def set_interaction_active(self, active: bool) -> None:
        """Call True on drag start, False on drag end."""
        self._interaction_active = bool(active)
        self._tick_count = 0
        if self._navicube is not None:
            self._navicube.set_interaction_active(active)

    def teardown(self) -> None:
        """Stop polling and disconnect. Call when the VTK view is destroyed."""
        self._tmr.stop()
        try:
            if self._navicube is not None:
                self._navicube.viewOrientationRequested.disconnect(
                    self._on_orientation_requested
                )
        except Exception:
            pass
        self._renderer    = None
        self._navicube    = None
        self._render_window = None

    # ── internals ───────────────────────────────────────────────────

    def _tick(self) -> None:
        if self._renderer is None or self._navicube is None:
            return

        poll_every = (
            self._INTERACTION_TICKS if self._interaction_active else self._IDLE_TICKS
        )
        self._tick_count += 1
        if self._tick_count < poll_every:
            return
        self._tick_count = 0

        try:
            cam = self._renderer.GetActiveCamera()
            pos = cam.GetPosition()
            fp  = cam.GetFocalPoint()
            up  = cam.GetViewUp()

            # Inward direction = focal_point - position, normalised
            dx = fp[0] - pos[0]
            dy = fp[1] - pos[1]
            dz = fp[2] - pos[2]
            length = math.sqrt(dx*dx + dy*dy + dz*dz)
            if length < 1e-10:
                return

            self._navicube.push_camera(
                dx / length, dy / length, dz / length,
                up[0], up[1], up[2],
            )
        except Exception:
            pass

    def _on_orientation_requested(
        self,
        px: float, py: float, pz: float,
        ux: float, uy: float, uz: float,
    ) -> None:
        """Navicube clicked: move VTK camera to the requested orientation."""
        if self._renderer is None:
            return

        mag = math.sqrt(px*px + py*py + pz*pz)
        if mag < 1e-6:
            return

        try:
            cam = self._renderer.GetActiveCamera()
            fp  = cam.GetFocalPoint()
            pos = cam.GetPosition()

            dist = math.sqrt(
                (pos[0]-fp[0])**2 + (pos[1]-fp[1])**2 + (pos[2]-fp[2])**2
            )
            if dist < 1e-6:
                dist = 1.0

            scale = dist / mag
            cam.SetPosition(
                fp[0] + px * scale,
                fp[1] + py * scale,
                fp[2] + pz * scale,
            )
            cam.SetViewUp(ux, uy, uz)
            self._renderer.ResetCameraClippingRange()

            rw = self._render_window or self._renderer.GetRenderWindow()
            if rw is not None:
                rw.Render()
        except Exception:
            pass
