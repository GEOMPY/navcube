"""
navicube_overlay.py  —  FreeCAD-style NaviCube  ·  Standalone PySide6 library
═══════════════════════════════════════════════════════════════════════════════
Zero renderer dependency · drop-in for any PySide6 application

Quick-start
───────────
  navicube = NavCubeOverlay(parent=some_widget)
  navicube.viewOrientationRequested.connect(your_camera_update)
  navicube.show()

  # Push your camera state in whenever it changes:
  navicube.push_camera(dx, dy, dz, ux, uy, uz)   # inward dir + up

  # Signal interaction start / end so smoothing kicks in:
  navicube.set_interaction_active(True)    # mouse press
  navicube.set_interaction_active(False)   # mouse release

OCC users
─────────
  Use OCCNavCubeSync (occ_navicube_sync.py) — it owns the polling
  timer, wires the signal, and calls push_camera() for you.

Sign-convention contract (critical — do not change)
────────────────────────────────────────────────────
  _dir  = inward camera direction = OCC cam.Direction() = eye → scene.

  This matches what the projection math and face-visibility check both
  require.  When we emit via viewOrientationRequested we negate
  (_dir → outward) because OCC SetProj(Vx,Vy,Vz) places the eye in
  the +V direction.

  Mnemonic:  read inward,  write outward.

Antipodal SLERP
───────────────
  dot(v0,v1) ≈ -1 → sin(ω) → 0 → division by zero → NaN.
  Fixed by routing through a stable perpendicular midpoint.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Tuple, Union

import numpy as np
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QEvent, QPointF, Signal, QRectF, QTimer, QElapsedTimer, Slot
from PySide6.QtGui import (
    QPainter, QColor, QPolygonF, QFont, QFontMetricsF, QPen, QBrush,
    QTransform, QCursor, QPalette,
)

# ═══════════════════════════════════════════════════════════════════════
#  Math helpers
# ═══════════════════════════════════════════════════════════════════════

def _norm(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 1e-10 else v

def _rod(v: np.ndarray, axis: np.ndarray, ang: float) -> np.ndarray:
    """Rodrigues rotation of v around unit-axis by ang radians."""
    a = _norm(np.asarray(axis, dtype=float))
    c, s = math.cos(ang), math.sin(ang)
    return v * c + np.cross(a, v) * s + a * float(np.dot(a, v)) * (1.0 - c)

def _vslerp(v0: np.ndarray, v1: np.ndarray, t: float) -> np.ndarray:
    """
    Spherical-linear interpolation.  Handles antipodal case (dot ≈ -1)
    that causes sin(ω)→0 → NaN → OCC V3d_BadValue crash.
    """
    v0 = _norm(np.asarray(v0, dtype=float))
    v1 = _norm(np.asarray(v1, dtype=float))
    d  = float(np.clip(np.dot(v0, v1), -1.0, 1.0))

    if d > 0.9999:
        return _norm(v0 + t * (v1 - v0))

    if d < -0.9999:                   # antipodal — route through perpendicular
        cand = np.array([1.,0.,0.]) if abs(v0[0]) < 0.9 else np.array([0.,1.,0.])
        mid  = _norm(np.cross(v0, cand))
        return _vslerp(v0, mid, t*2.) if t < 0.5 else _vslerp(mid, v1, (t-.5)*2.)

    omega = math.acos(d)
    s_o   = math.sin(omega)
    return (math.sin((1.-t)*omega)/s_o)*v0 + (math.sin(t*omega)/s_o)*v1

def _smooth(t: float) -> float:
    t = max(0., min(1., t))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)

def _project_to_plane(v: np.ndarray, normal: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    n = _norm(np.asarray(normal, dtype=float))
    return v - np.dot(v, n) * n

def _camera_basis(d: np.ndarray, u: np.ndarray) -> np.ndarray:
    d = _norm(np.asarray(d, dtype=float))
    u = _norm(np.asarray(u, dtype=float))
    r = np.cross(d, u)
    if np.linalg.norm(r) < 1e-6:
        fallback = np.array([1.0, 0.0, 0.0]) if abs(d[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        r = np.cross(d, fallback)
    r = _norm(r)
    u = _norm(np.cross(r, d))
    return np.column_stack((r, u, -d))

def _qnorm(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=float)
    n = np.linalg.norm(q)
    return q / n if n > 1e-10 else np.array([1.0, 0.0, 0.0, 0.0], dtype=float)

def _quat_from_matrix(m: np.ndarray) -> np.ndarray:
    m = np.asarray(m, dtype=float)
    tr = float(m[0, 0] + m[1, 1] + m[2, 2])
    if tr > 0.0:
        s = math.sqrt(tr + 1.0) * 2.0
        q = np.array([
            0.25 * s,
            (m[2, 1] - m[1, 2]) / s,
            (m[0, 2] - m[2, 0]) / s,
            (m[1, 0] - m[0, 1]) / s,
        ])
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2.0
        q = np.array([
            (m[2, 1] - m[1, 2]) / s,
            0.25 * s,
            (m[0, 1] + m[1, 0]) / s,
            (m[0, 2] + m[2, 0]) / s,
        ])
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2.0
        q = np.array([
            (m[0, 2] - m[2, 0]) / s,
            (m[0, 1] + m[1, 0]) / s,
            0.25 * s,
            (m[1, 2] + m[2, 1]) / s,
        ])
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2.0
        q = np.array([
            (m[1, 0] - m[0, 1]) / s,
            (m[0, 2] + m[2, 0]) / s,
            (m[1, 2] + m[2, 1]) / s,
            0.25 * s,
        ])
    return _qnorm(q)

def _matrix_from_quat(q: np.ndarray) -> np.ndarray:
    w, x, y, z = _qnorm(q)
    return np.array([
        [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
        [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
        [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
    ])

def _qslerp(q0: np.ndarray, q1: np.ndarray, t: float) -> np.ndarray:
    q0 = _qnorm(q0)
    q1 = _qnorm(q1)
    d = float(np.dot(q0, q1))
    if d < 0.0:
        q1 = -q1
        d = -d
    if d > 0.9995:
        return _qnorm(q0 + t * (q1 - q0))
    theta_0 = math.acos(max(-1.0, min(1.0, d)))
    sin_theta_0 = math.sin(theta_0)
    theta = theta_0 * t
    sin_theta = math.sin(theta)
    s0 = math.cos(theta) - d * sin_theta / sin_theta_0
    s1 = sin_theta / sin_theta_0
    return _qnorm((s0 * q0) + (s1 * q1))


# ═══════════════════════════════════════════════════════════════════════
#  Style dataclass
# ═══════════════════════════════════════════════════════════════════════

Color = Union[Tuple[int, int, int], Tuple[int, int, int, int]]

def _default_labels() -> Dict[str, str]:
    return {
        "TOP": "TOP", "FRONT": "FRONT", "LEFT": "LEFT",
        "BACK": "BACK", "RIGHT": "RIGHT", "BOTTOM": "BOTTOM",
    }

@dataclass
class NavCubeStyle:
    """Complete visual and behavioral configuration for NavCubeOverlay.

    Pass an instance to ``NavCubeOverlay(style=...)`` or call
    ``set_style()`` at runtime.  Every field has a sensible default that
    matches the original hard-coded behavior.
    """

    # Geometry
    size: int = 120
    """Base cube drawing area in pixels (before DPI scaling)."""
    padding: int = 10
    """Transparent padding on each side in pixels."""
    scale: float = 27.0
    """3-D units to screen pixels projection scale."""
    chamfer: float = 0.12
    """FreeCAD-style chamfer ratio for edge/corner bevels."""

    # Animation / timing
    animation_ms: int = 240
    """Duration of face-click animation in milliseconds."""
    tick_ms: int = 16
    """Timer tick interval in milliseconds."""

    # Thresholds
    visibility_threshold: float = 0.10
    """Face dot-product threshold for back-face culling."""
    orbit_step_deg: float = 15.0
    """Orbit button rotation step in degrees."""
    sync_epsilon: float = 1e-3
    """Minimum camera change to trigger a redraw."""
    inactive_opacity: float = 0.72
    """Widget opacity when the mouse is not hovering."""

    # Lighting
    light_direction: Tuple[float, float, float] = (-0.8, -1.0, -1.8)
    """Lambertian light direction (auto-normalized)."""

    # Theme selection
    theme: str = "auto"
    """'auto' (detect from QPalette), 'light', or 'dark'."""

    # Light-theme colors
    face_color: Color = (248, 248, 252)
    edge_color: Color = (210, 210, 215)
    corner_color: Color = (185, 185, 190)
    text_color: Color = (18, 18, 18)
    border_color: Color = (28, 28, 32)
    border_secondary_color: Color = (50, 50, 55)
    control_color: Color = (186, 186, 192, 120)
    control_rim_color: Color = (105, 105, 110, 170)
    hover_color: Color = (0, 148, 255, 235)
    hover_text_color: Color = (255, 255, 255)
    dot_color: Color = (195, 195, 198, 225)
    shadow_color: Color = (0, 0, 0, 42)

    # Dark-theme colors
    face_color_dark: Color = (155, 160, 178)
    edge_color_dark: Color = (118, 122, 138)
    corner_color_dark: Color = (96, 99, 113)
    text_color_dark: Color = (238, 238, 238)
    border_color_dark: Color = (10, 10, 12)
    border_secondary_color_dark: Color = (20, 20, 22)
    control_color_dark: Color = (78, 78, 82, 125)
    control_rim_color_dark: Color = (42, 42, 46, 175)
    hover_color_dark: Color = (0, 148, 255, 235)
    hover_text_color_dark: Color = (255, 255, 255)
    dot_color_dark: Color = (145, 145, 148, 225)
    shadow_color_dark: Color = (0, 0, 0, 78)

    # Font
    font_family: str = "Arial"
    font_fallback: str = "SansSerif"
    """Qt style hint name (SansSerif, Serif, Monospace, etc.)."""
    font_weight: str = "bold"
    """'normal', 'bold', 'demibold', etc."""
    label_max_width_ratio: float = 0.70
    """Fraction of 200-unit virtual canvas used for text width."""
    label_max_height_ratio: float = 0.45
    """Fraction of 200-unit virtual canvas used for text height."""
    min_font_size: float = 40.0
    """Minimum computed font point size."""

    # Face labels
    labels: Dict[str, str] = field(default_factory=_default_labels)
    """Mapping of face name to display text.  Customize for localization."""

    # Controls
    show_controls: bool = True
    """Show orbit/roll/backside/home buttons around the cube."""
    show_gizmo: bool = False
    """Show XYZ axis gizmo in the corner."""
    gizmo_x_color: Color = (215, 52, 52)
    gizmo_y_color: Color = (52, 195, 52)
    gizmo_z_color: Color = (55, 115, 255)
    gizmo_font_size: int = 9

    # Border widths
    border_width_main: float = 2.0
    """Border width for main faces."""
    border_width_secondary: float = 1.2
    """Border width for edge/corner faces."""
    control_border_width: float = 1.2
    """Border width for control buttons."""

    # Shadow offsets
    shadow_offset_x: float = 1.8
    shadow_offset_y: float = 2.3


# ═══════════════════════════════════════════════════════════════════════
#  Palette
# ═══════════════════════════════════════════════════════════════════════

_FONT_WEIGHT_MAP = {
    "thin": QFont.Thin,
    "extralight": QFont.ExtraLight,
    "light": QFont.Light,
    "normal": QFont.Normal,
    "medium": QFont.Medium,
    "demibold": QFont.DemiBold,
    "bold": QFont.Bold,
    "extrabold": QFont.ExtraBold,
    "black": QFont.Black,
}

_FONT_HINT_MAP = {
    "sansserif": QFont.SansSerif,
    "serif": QFont.Serif,
    "monospace": QFont.Monospace,
    "typwriter": QFont.TypeWriter,
    "typewriter": QFont.TypeWriter,
    "cursive": QFont.Cursive,
    "fantasy": QFont.Fantasy,
    "system": QFont.System,
}


def _qcolor(c: Color) -> QColor:
    if len(c) == 4:
        return QColor(c[0], c[1], c[2], c[3])
    return QColor(c[0], c[1], c[2])


class _Pal:
    def __init__(self, style: NavCubeStyle, light: bool):
        if light:
            self.f_main = _qcolor(style.face_color)
            self.f_edge = _qcolor(style.edge_color)
            self.f_corn = _qcolor(style.corner_color)
            self.text   = _qcolor(style.text_color)
            self.bord   = _qcolor(style.border_color)
            self.bord_s = _qcolor(style.border_secondary_color)
            self.ctrl   = _qcolor(style.control_color)
            self.ctrl_r = _qcolor(style.control_rim_color)
            self.hover  = _qcolor(style.hover_color)
            self.hov_tx = _qcolor(style.hover_text_color)
            self.dot    = _qcolor(style.dot_color)
            self.shadow = _qcolor(style.shadow_color)
        else:
            self.f_main = _qcolor(style.face_color_dark)
            self.f_edge = _qcolor(style.edge_color_dark)
            self.f_corn = _qcolor(style.corner_color_dark)
            self.text   = _qcolor(style.text_color_dark)
            self.bord   = _qcolor(style.border_color_dark)
            self.bord_s = _qcolor(style.border_secondary_color_dark)
            self.ctrl   = _qcolor(style.control_color_dark)
            self.ctrl_r = _qcolor(style.control_rim_color_dark)
            self.hover  = _qcolor(style.hover_color_dark)
            self.hov_tx = _qcolor(style.hover_text_color_dark)
            self.dot    = _qcolor(style.dot_color_dark)
            self.shadow = _qcolor(style.shadow_color_dark)


# ═══════════════════════════════════════════════════════════════════════
#  Widget
# ═══════════════════════════════════════════════════════════════════════

class NavCubeOverlay(QWidget):
    """
    FreeCAD-style NaviCube overlay.

    Signal: viewOrientationRequested(dx, dy, dz, ux, uy, uz)
        dx/dy/dz = outward direction  (ready for OCC SetProj)
        ux/uy/uz = camera up vector   (ready for OCC SetUp)
    """

    viewOrientationRequested = Signal(float, float, float, float, float, float)

    # ISO inward direction in navicube-internal Z-up space
    _DDEF  = _norm(np.array([-1., 1., -1.]))
    _UDEF  = np.array([0., 0.,  1.])

    # ── Coordinate-system bridge ──────────────────────────────────────
    # _WORLD_ROT maps FROM navicube's internal Z-up space TO your app's
    # world space.  Override as a class attribute for Y-up engines.
    #
    #   Z-up  (OCC, FreeCAD, Blender world):   _WORLD_ROT = np.eye(3)  ← default
    #   Y-up  (Three.js, GLTF, Unity, Unreal): _WORLD_ROT = np.array([
    #                                               [1, 0,  0],
    #                                               [0, 0, -1],
    #                                               [0, 1,  0]])
    #
    # push_camera() and viewOrientationRequested both use YOUR world space.
    # The navicube internally renders in Z-up; _WORLD_ROT bridges the two.
    _WORLD_ROT: np.ndarray = np.eye(3)

    def __init_subclass__(cls, **kwargs):
        """Ensure each subclass gets its own copy of _WORLD_ROT so that
        mutating one subclass's matrix never affects another."""
        super().__init_subclass__(**kwargs)
        if "_WORLD_ROT" in cls.__dict__:
            cls._WORLD_ROT = np.array(cls._WORLD_ROT, dtype=float)

    def __init__(self, parent=None, *, overlay: bool = True,
                 style: NavCubeStyle | None = None):
        """
        Parameters
        ──────────
        parent   Qt parent widget.
        overlay  True (default): floating transparent overlay — use when
                 positioning the cube over a 3-D viewport.
                 False: plain opaque QWidget that can live in any layout
                 or dock without Tool-window side-effects.
        style    Optional NavCubeStyle for full visual/behavioral control.
                 Defaults match original hard-coded behavior exactly.
        """
        super().__init__(parent)
        self._style = style if style is not None else NavCubeStyle()
        self._apply_style_internals()

        self._overlay = overlay
        self.setMouseTracking(True)
        if overlay:
            self.setWindowFlags(
                Qt.Tool
                | Qt.FramelessWindowHint
                | Qt.NoDropShadowWindowHint
                | Qt.WindowDoesNotAcceptFocus
            )
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setAttribute(Qt.WA_ShowWithoutActivating, True)
            self.setAutoFillBackground(False)

        self.hovered_id: str | None = None
        self._hovering = False
        self._label_font_sizes: dict[str, float] = {}

        ROT = self.__class__._WORLD_ROT
        self._dir = _norm(ROT @ self._DDEF)
        self._up  = _norm(ROT @ self._UDEF)

        self._home_dir = self._dir.copy()
        self._home_up  = self._up.copy()

        # animation
        self._at    = 1.0
        self._adt   = 16.0 / self._style.animation_ms
        self._d0    = self._dir.copy()
        self._u0    = self._up.copy()
        self._d1: np.ndarray | None = None
        self._u1: np.ndarray | None = None
        self._q0 = _quat_from_matrix(_camera_basis(self._dir, self._up))
        self._q1 = self._q0.copy()
        self._interaction_active = False

        self._build_geo()
        self._update_dpi()

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._tick)
        self._tmr.start(self._style.tick_ms)

        self._anim_clock = QElapsedTimer()
        self._anim_clock.start()
        self._anim_last_ms = 0

    def _apply_style_internals(self):
        """Pre-compute derived values from the current style."""
        s = self._style
        self._SIZE  = s.size
        self._PAD   = s.padding
        self._SCALE = s.scale
        self._C     = s.chamfer
        self._AMS   = s.animation_ms
        self._VIS   = s.visibility_threshold
        self._STEP  = math.radians(s.orbit_step_deg)
        self._TICK_MS = s.tick_ms
        self._SYNC_EPS = s.sync_epsilon
        self._INACTIVE_OPACITY = s.inactive_opacity
        self._LIGHT = _norm(np.array(s.light_direction, dtype=float))

    def set_style(self, style: NavCubeStyle) -> None:
        """Apply a new style at runtime. Forces a full rebuild and repaint."""
        self._style = style
        self._apply_style_internals()
        self._label_font_sizes.clear()
        self._build_geo()
        self._update_dpi()
        if hasattr(self, '_tmr'):
            self._tmr.setInterval(self._style.tick_ms)
        self.update()

    # ──────────────────────────── geometry ──────────────────────────

    def _build_geo(self):
        self._faces = {}

        x = np.array([1.0, 0.0, 0.0])
        y = np.array([0.0, 1.0, 0.0])
        z = np.array([0.0, 0.0, 1.0])

        self._add_cube_face("TOP", x, z, "main", "TOP")
        self._add_cube_face("FRONT", x, -y, "main", "FRONT")
        self._add_cube_face("LEFT", -y, -x, "main", "LEFT")
        self._add_cube_face("BACK", -x, y, "main", "BACK")
        self._add_cube_face("RIGHT", y, x, "main", "RIGHT")
        self._add_cube_face("BOTTOM", x, -z, "main", "BOTTOM")

        self._add_cube_face("FTR", -x - y, x - y + z, "corner")
        self._add_cube_face("FTL", -x + y, -x - y + z, "corner")
        self._add_cube_face("FBR", x + y, x - y - z, "corner")
        self._add_cube_face("FBL", x - y, -x - y - z, "corner")
        self._add_cube_face("RTR", x - y, x + y + z, "corner")
        self._add_cube_face("RTL", x + y, -x + y + z, "corner")
        self._add_cube_face("RBR", -x + y, x + y - z, "corner")
        self._add_cube_face("RBL", -x - y, -x + y - z, "corner")

        self._add_cube_face("FRONT_TOP", x, z - y, "edge")
        self._add_cube_face("FRONT_BOTTOM", x, -z - y, "edge")
        self._add_cube_face("REAR_BOTTOM", x, y - z, "edge")
        self._add_cube_face("REAR_TOP", x, y + z, "edge")
        self._add_cube_face("REAR_RIGHT", z, x + y, "edge")
        self._add_cube_face("FRONT_RIGHT", z, x - y, "edge")
        self._add_cube_face("FRONT_LEFT", z, -x - y, "edge")
        self._add_cube_face("REAR_LEFT", z, y - x, "edge")
        self._add_cube_face("TOP_LEFT", y, z - x, "edge")
        self._add_cube_face("TOP_RIGHT", y, x + z, "edge")
        self._add_cube_face("BOTTOM_RIGHT", y, x - z, "edge")
        self._add_cube_face("BOTTOM_LEFT", y, -z - x, "edge")

    def _add_cube_face(self, name, x_vec, z_vec, face_type, label=None):
        x_vec = np.asarray(x_vec, dtype=float)
        z_vec = np.asarray(z_vec, dtype=float)
        y_vec = np.cross(x_vec, -z_vec)
        chamfer = self._C

        if face_type == "corner":
            x_c = x_vec * chamfer
            y_c = y_vec * chamfer
            z_c = (1.0 - 2.0 * chamfer) * z_vec
            pts = [
                z_c - 2.0 * x_c,
                z_c - x_c - y_c,
                z_c + x_c - y_c,
                z_c + 2.0 * x_c,
                z_c + x_c + y_c,
                z_c - x_c + y_c,
            ]
            label_pts = None
        elif face_type == "edge":
            x_4 = x_vec * (1.0 - chamfer * 4.0)
            y_e = y_vec * chamfer
            z_e = z_vec * (1.0 - chamfer)
            pts = [
                z_e - x_4 - y_e,
                z_e + x_4 - y_e,
                z_e + x_4 + y_e,
                z_e - x_4 + y_e,
            ]
            label_pts = None
        else:
            x_2 = x_vec * (1.0 - chamfer * 2.0)
            y_2 = y_vec * (1.0 - chamfer * 2.0)
            x_4 = x_vec * (1.0 - chamfer * 4.0)
            y_4 = y_vec * (1.0 - chamfer * 4.0)
            pts = [
                z_vec - x_2 - y_4,
                z_vec - x_4 - y_2,
                z_vec + x_4 - y_2,
                z_vec + x_2 - y_4,
                z_vec + x_2 + y_4,
                z_vec + x_4 + y_2,
                z_vec - x_4 + y_2,
                z_vec - x_2 + y_4,
            ]
            label_pts = [
                z_vec - x_2 - y_2,
                z_vec + x_2 - y_2,
                z_vec + x_2 + y_2,
                z_vec - x_2 + y_2,
            ]

        pts = [np.asarray(pt, dtype=float) for pt in pts]
        ctr = np.mean(pts, axis=0)
        normal = _norm(ctr)
        self._faces[name] = {
            "pts": pts,
            "n": normal,
            "ctr": ctr,
            "lbl": label,
            "ft": face_type,
            "label_pts": label_pts,
        }

    def _build_ctrl(self):
        self._ctrl = {}
        if not self._style.show_controls:
            return
        self._add_button_shape("ArrowLeft", "roll_ccw")
        self._add_button_shape("ArrowRight", "roll_cw")
        self._add_button_shape("ArrowNorth", "orbit_u")
        self._add_button_shape("ArrowSouth", "orbit_d")
        self._add_button_shape("ArrowEast", "orbit_r")
        self._add_button_shape("ArrowWest", "orbit_l")
        self._add_button_shape("DotBackside", "backside")
        self._add_button_shape("ViewMenu", "home")

    def _add_button_shape(self, name, act):
        scale = 0.005
        off_x = 0.5
        off_y = 0.5

        if name in ("ArrowLeft", "ArrowRight"):
            point_data = [
                66.6, -66.6, 58.3, -74.0, 49.2, -80.3, 39.4, -85.5,
                29.0, -89.5, 25.3, -78.1, 34.3, -74.3, 42.8, -69.9,
                50.8, -64.4, 58.1, -58.1, 53.8, -53.8, 74.7, -46.8,
                70.7, -70.4,
            ]
        elif name in ("ArrowNorth", "ArrowSouth", "ArrowEast", "ArrowWest"):
            point_data = [100.0, 0.0, 80.0, -18.0, 80.0, 18.0]
        elif name == "ViewMenu":
            off_x = 0.84
            off_y = 0.84
            point_data = [
                0.0, 0.0,
                15.0, -6.0, 0.0, -12.0, -15.0, -6.0, 0.0, 0.0,
                -15.0, -6.0, -15.0, 12.0, 0.0, 18.0, 0.0, 0.0,
                0.0, 18.0, 15.0, 12.0, 15.0, -6.0,
            ]
        elif name == "DotBackside":
            point_data = []
            steps = 16
            for idx in range(steps):
                ang = 2.0 * math.pi * (idx + 0.5) / steps
                point_data.extend([10.0 * math.cos(ang) + 87.0, 10.0 * math.sin(ang) - 87.0])
        else:
            point_data = []

        pts = []
        count = len(point_data) // 2
        for idx in range(count):
            x_val = point_data[idx * 2] * scale + off_x
            y_val = point_data[idx * 2 + 1] * scale + off_y
            if name in ("ArrowNorth", "ArrowWest", "ArrowLeft"):
                x_val = 1.0 - x_val
            if name in ("ArrowSouth", "ArrowNorth"):
                pts.append(QPointF(y_val * self._SIZE, x_val * self._SIZE))
            else:
                pts.append(QPointF(x_val * self._SIZE, y_val * self._SIZE))

        self._ctrl[name] = {
            "poly": QPolygonF(pts),
            "act": act,
        }

    def _update_dpi(self) -> None:
        """
        Recompute _SIZE and _SCALE for the screen this widget is on, then
        apply setFixedSize and rebuild the pixel-space control polygons.

        Called once at construction and again whenever the widget moves to
        a screen with a different DPI (changeEvent ScreenChangeInternal).
        """
        try:
            app = QApplication.instance()
            if app is None:
                dpi_scale = 1.0
            else:
                screen = self.screen() if self.isVisible() else None
                if screen is None:
                    screen = app.primaryScreen()
                dpi_scale = (screen.logicalDotsPerInch() / 96.0) if screen else 1.0
                dpi_scale = max(0.75, min(dpi_scale, 4.0))
        except Exception:
            dpi_scale = 1.0

        base = self._style.size
        new_size = round(base * dpi_scale)
        if new_size == self._SIZE and hasattr(self, "_ctrl"):
            return

        self._SIZE  = new_size
        self._PAD   = round(self._style.padding * dpi_scale)
        self._SCALE = self._style.scale * (new_size / base)
        self._label_font_sizes.clear()
        widget_side = self._SIZE + 2 * self._PAD
        self.setFixedSize(widget_side, widget_side)
        self._build_ctrl()

    # ──────────────────────────── camera ────────────────────────────

    @Slot(float, float, float, float, float, float)
    def push_camera(self, dx: float, dy: float, dz: float,
                    ux: float, uy: float, uz: float) -> None:
        """
        Update the navicube to match the current camera state.

        Call this whenever your camera changes (mouse drag, programmatic
        update, etc.).  The navicube will NOT call back to your renderer
        in response — it only redraws its own 2-D widget.

        Convention
        ──────────
          dx/dy/dz  INWARD direction (eye → scene).
                    For OCC: cam.Direction() values directly — no negation.
          ux/uy/uz  Camera up vector.

        During an active face-click animation the push is silently ignored
        (the navicube is driving the camera, not the other way around).
        Exception: if set_interaction_active(True) was already called, the
        animation is cancelled and the navicube immediately follows live.

        During active interaction (set_interaction_active(True)) the push
        is smoothed via quaternion SLERP to filter transient instabilities
        such as OCC Up-vector flicker near poles.

        Thread safety
        ─────────────
        Must be called from the Qt main thread.  If your render loop runs
        on a worker thread, post back with:
            QMetaObject.invokeMethod(cube, "push_camera",
                Qt.QueuedConnection,
                Q_ARG(float, dx), Q_ARG(float, dy), Q_ARG(float, dz),
                Q_ARG(float, ux), Q_ARG(float, uy), Q_ARG(float, uz))
        or wrap in a QTimer.singleShot(0, lambda: cube.push_camera(...)).
        """
        if self._at < 1.0:
            if not self._interaction_active:
                return
            self._at = 1.0

        d = _norm(np.array([dx, dy, dz], dtype=float))
        u = _norm(np.array([ux, uy, uz], dtype=float))

        if self._interaction_active:
            if self._smooth_camera_state(d, u, 0.65):
                self.update()
        else:
            if self._set_camera_state(d, u):
                self.update()

    def set_home(self, dx: float, dy: float, dz: float,
                 ux: float, uy: float, uz: float) -> None:
        """
        Set the camera orientation that the Home button returns to.

        Provide YOUR world-space inward direction + up vector — same
        convention as push_camera().  Default is the navicube's internal
        ISO view expressed in the current _WORLD_ROT coordinate system.

        Call this once after construction (or after loading user prefs)
        to match the "home" position of your application.
        """
        self._home_dir = _norm(np.array([dx, dy, dz], dtype=float))
        self._home_up  = _norm(np.array([ux, uy, uz], dtype=float))

    def set_interaction_active(self, active: bool) -> None:
        """
        Notify the navicube that the user is actively dragging the camera
        (active=True on mouse-press, active=False on mouse-release).

        While active, push_camera() applies SLERP smoothing (alpha 0.65,
        ~8 ms effective lag) to absorb momentary renderer instabilities.
        """
        self._interaction_active = bool(active)

    def _axes(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Return (D_inward, U, R) all in navicube's internal Z-up space.

        self._dir / self._up are in the app's world space.  _WORLD_ROT maps
        navicube Z-up → world, so .T maps world → navicube Z-up.
        All face geometry is in navicube space, so projection is consistent.
        """
        ROT = self.__class__._WORLD_ROT
        D = _norm(ROT.T @ self._dir)
        U = _norm(ROT.T @ self._up)
        R = _norm(np.cross(D, U))
        U = _norm(np.cross(R, D))
        return D, U, R

    def _set_camera_state(self, d: np.ndarray, u: np.ndarray) -> bool:
        d = _norm(np.asarray(d, dtype=float))
        u = _norm(np.asarray(u, dtype=float))
        r = np.cross(d, u)
        u = _norm(np.cross(r, d))

        if (
            np.linalg.norm(d - self._dir) <= self._SYNC_EPS
            and np.linalg.norm(u - self._up) <= self._SYNC_EPS
        ):
            return False

        self._dir = d
        self._up = u
        return True

    def _smooth_camera_state(self, d_tgt: np.ndarray, u_tgt: np.ndarray, alpha: float) -> bool:
        """
        SLERP current camera state toward (d_tgt, u_tgt) by factor alpha.
        Used during live interaction to follow OCC camera smoothly, which
        eliminates jitter from momentary OCC camera instabilities (e.g. Up
        vector flicker near poles) while keeping lag to ~1 tick.
        """
        d_tgt = _norm(np.asarray(d_tgt, dtype=float))
        u_tgt = _norm(np.asarray(u_tgt, dtype=float))
        r = np.cross(d_tgt, u_tgt)
        if np.linalg.norm(r) < 1e-6:
            return False
        u_tgt = _norm(np.cross(r, d_tgt))

        if (np.linalg.norm(d_tgt - self._dir) <= self._SYNC_EPS and
                np.linalg.norm(u_tgt - self._up) <= self._SYNC_EPS):
            return False

        q_cur = _quat_from_matrix(_camera_basis(self._dir, self._up))
        q_tgt = _quat_from_matrix(_camera_basis(d_tgt, u_tgt))
        q_new = _qslerp(q_cur, q_tgt, alpha)
        basis = _matrix_from_quat(q_new)
        self._dir = _norm(-basis[:, 2])
        self._up  = _norm( basis[:, 1])
        return True

    def _with_opacity(self, color: QColor, opacity: float) -> QColor:
        col = QColor(color)
        col.setAlpha(max(0, min(255, int(round(col.alpha() * opacity)))))
        return col

    def _resolve_font_weight(self) -> int:
        return _FONT_WEIGHT_MAP.get(self._style.font_weight.lower(), QFont.Bold)

    def _resolve_font_hint(self) -> int:
        return _FONT_HINT_MAP.get(self._style.font_fallback.lower(), QFont.SansSerif)

    def _label_font(self, text: str) -> QFont:
        size = self._label_font_sizes.get(text)
        if size is None:
            test_font = QFont(self._style.font_family, 100, QFont.Normal)
            test_font.setStyleHint(self._resolve_font_hint())
            metrics = QFontMetricsF(test_font)
            bounds = metrics.boundingRect(text)
            target_w = self._style.label_max_width_ratio * 200.0
            target_h = self._style.label_max_height_ratio * 200.0
            if bounds.width() > 1e-6 and bounds.height() > 1e-6:
                size = 100.0 * min(target_w / bounds.width(), target_h / bounds.height())
            else:
                size = 50.0
            self._label_font_sizes[text] = max(self._style.min_font_size, size)
            size = self._label_font_sizes[text]

        font = QFont(self._style.font_family)
        font.setStyleHint(self._resolve_font_hint())
        font.setWeight(self._resolve_font_weight())
        font.setPointSizeF(size)
        return font

    # ──────────────────────────── animation ─────────────────────────

    def _start_anim(self, tgt_dir: np.ndarray, tgt_up: np.ndarray):
        self._d0 = self._dir.copy()
        self._u0 = self._up.copy()
        self._d1 = _norm(np.asarray(tgt_dir, dtype=float))
        self._u1 = _norm(np.asarray(tgt_up,  dtype=float))
        self._q0 = _quat_from_matrix(_camera_basis(self._d0, self._u0))
        self._q1 = _quat_from_matrix(_camera_basis(self._d1, self._u1))
        self._at = 0.0
        self._anim_last_ms = self._anim_clock.elapsed()
        self._pending_sync = False
        self._idle_frames = 0

    def _tick(self):
        """Animation-only tick. Camera sync is driven externally via push_camera()."""
        if self._at >= 1.0:
            return

        now_ms = self._anim_clock.elapsed()
        dt = float(now_ms - self._anim_last_ms)
        self._anim_last_ms = now_ms
        dt = max(1.0, min(dt, 100.0))

        self._at = min(1.0, self._at + dt / self._AMS)
        te = _smooth(self._at)
        q = _qslerp(self._q0, self._q1, te)
        basis = _matrix_from_quat(q)
        u = _norm(basis[:, 1])
        d = _norm(-basis[:, 2])
        self._dir, self._up = d, u

        if np.linalg.norm(d) > 1e-6 and np.linalg.norm(u) > 1e-6:
            self.viewOrientationRequested.emit(
                -float(d[0]), -float(d[1]), -float(d[2]),
                 float(u[0]),  float(u[1]),  float(u[2]))

        self.update()

    # ──────────────────────────── projection ────────────────────────

    def _proj(self, P, R, U, cx, cy) -> QPointF:
        S = self._SCALE
        return QPointF(cx + float(np.dot(P,R))*S,
                       cy - float(np.dot(P,U))*S)

    # ═══════════════════════════════════════════════════════════════
    #  Paint
    # ═══════════════════════════════════════════════════════════════

    def _resolve_is_light(self) -> bool:
        theme = self._style.theme.lower()
        if theme == "light":
            return True
        if theme == "dark":
            return False
        try:
            win_col = QApplication.palette().color(QPalette.Window)
            return win_col.lightness() > 128
        except Exception:
            return True

    def paintEvent(self, event):   # noqa: N802
        p = QPainter(self)
        if self._overlay:
            p.setCompositionMode(QPainter.CompositionMode_Source)
            p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.setRenderHints(QPainter.Antialiasing |
                         QPainter.TextAntialiasing |
                         QPainter.SmoothPixmapTransform)
        p.translate(self._PAD, self._PAD)

        light = self._resolve_is_light()
        pal = _Pal(self._style, light)
        opacity = 1.0 if self._hovering or self._at < 1.0 else self._INACTIVE_OPACITY

        cx = cy = self._SIZE / 2
        D, U, R = self._axes()

        self._draw_cube(p, pal, D, U, R, cx, cy, opacity)
        if self._style.show_controls:
            self._draw_ctrl(p, pal, opacity)
        if self._style.show_gizmo:
            self._draw_gizmo(p, pal, D, U, R, opacity)
        p.end()

    # ── cube ────────────────────────────────────────────────────────

    def _draw_cube(self, p, pal, D, U, R, cx, cy, opacity):
        vis = [(float(np.dot(f['ctr'], D)), nm, f)
               for nm, f in self._faces.items()
               if float(np.dot(f['n'], D)) < self._VIS]
        vis.sort(key=lambda x: x[0], reverse=True)

        sx = self._style.shadow_offset_x
        sy = self._style.shadow_offset_y
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self._with_opacity(pal.shadow, opacity)))
        for _, _, f in vis:
            shadow_poly = QPolygonF([
                QPointF(pt.x() + sx, pt.y() + sy)
                for pt in [self._proj(pt3, R, U, cx, cy) for pt3 in f['pts']]
            ])
            p.drawPolygon(shadow_poly)
        p.restore()

        bw_main = self._style.border_width_main
        bw_sec = self._style.border_width_secondary
        for _, nm, f in vis:
            pts2d = [self._proj(pt, R, U, cx, cy) for pt in f['pts']]
            poly  = QPolygonF(pts2d)
            hov   = (nm == self.hovered_id)
            fill  = pal.hover if hov else self._face_col(f, pal)
            p.setBrush(QBrush(self._with_opacity(fill, opacity)))
            bw = bw_main if f['ft'] == 'main' else bw_sec
            bc = pal.bord if f['ft'] == 'main' else pal.bord_s
            p.setPen(QPen(self._with_opacity(bc, opacity), bw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPolygon(poly)
            if f['lbl']:
                label_text = self._style.labels.get(f['lbl'], f['lbl'])
                self._draw_label(p, f, R, U, cx, cy,
                                 self._label_font(label_text), label_text,
                                 self._with_opacity(pal.hov_tx if hov else pal.text, opacity))

    def _face_col(self, f, pal) -> QColor:
        """FreeCAD-style: main=bright, edge=medium, corner=dark.  Pure gray."""
        ft = f['ft']
        base = pal.f_main if ft == 'main' else (pal.f_edge if ft == 'edge' else pal.f_corn)
        shade = 0.85 + 0.15 * max(0., float(np.dot(f['n'], -self._LIGHT)))
        return QColor(min(255, int(base.red() * shade)),
                      min(255, int(base.green() * shade)),
                      min(255, int(base.blue() * shade)))

    def _draw_label(self, p, f, R, U, cx, cy, font, text, col):
        """Draw a face label via direct quad mapping — no mirror detection needed.

        label_pts are [BL, BR, TR, TL] in the face's own coordinate system.
        Faces are only drawn when facing the camera (dot < _VIS), so the
        projected quad always preserves the face's natural reading direction.
        quadToQuad handles the perspective distortion; the 1-to-1 corner
        mapping guarantees the text reads left-to-right on every visible face.
        """
        pad = self._PAD
        # Project to device-space (including PAD offset for paintEvent translate).
        dst_pts = [QPointF(pt.x() + pad, pt.y() + pad)
                   for pt in (self._proj(lp, R, U, cx, cy) for lp in f['label_pts'])]

        # Text canvas: 200x200, TL=(0,0) TR=(200,0) BR=(200,200) BL=(0,200)
        # Face label_pts: [0]=BL [1]=BR [2]=TR [3]=TL
        # Map canvas corners 1-to-1 to projected face corners:
        #   src[i] → dst[i]  where ordering is [TL, TR, BR, BL]
        src = QPolygonF([QPointF(0, 0), QPointF(200, 0),
                         QPointF(200, 200), QPointF(0, 200)])
        dst = QPolygonF([dst_pts[3], dst_pts[2], dst_pts[1], dst_pts[0]])

        tf = QTransform()
        if QTransform.quadToQuad(src, dst, tf):
            p.save()
            p.setTransform(tf)
            p.setFont(font)
            p.setPen(QPen(col))
            p.drawText(QRectF(0, 0, 200, 200), Qt.AlignCenter, text)
            p.restore()

    # ── surrounding controls ─────────────────────────────────────────

    def _draw_ctrl(self, p, pal, opacity):
        cbw = self._style.control_border_width
        for cid, ctrl in self._ctrl.items():
            hov = (cid == self.hovered_id)
            fill = self._with_opacity(pal.hover if hov else pal.ctrl, opacity)
            rim = self._with_opacity(pal.ctrl_r if hov else pal.bord_s, opacity)
            p.setBrush(QBrush(fill))
            p.setPen(QPen(rim, cbw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPolygon(ctrl["poly"])

    # ── XYZ gizmo ────────────────────────────────────────────────────

    def _draw_gizmo(self, p, pal, D, U, R, opacity):
        ax = round(self._SIZE * 0.15)
        ay = round(self._SIZE * 0.80)
        L = max(20, round(self._SIZE * 0.16))
        ROT = self.__class__._WORLD_ROT
        axes = [
            (ROT.T @ np.array([1., 0., 0.]), _qcolor(self._style.gizmo_x_color), 'X'),
            (ROT.T @ np.array([0., 1., 0.]), _qcolor(self._style.gizmo_y_color), 'Y'),
            (ROT.T @ np.array([0., 0., 1.]), _qcolor(self._style.gizmo_z_color), 'Z'),
        ]
        axes.sort(key=lambda a: float(np.dot(a[0], D)))
        p.save()
        p.setFont(QFont("DejaVu Sans", self._style.gizmo_font_size, QFont.Bold))
        for wa, col, lbl in axes:
            sx = float(np.dot(wa, R)) * L
            sy = -float(np.dot(wa, U)) * L
            axis_col = self._with_opacity(col, opacity)
            p.setPen(QPen(axis_col, 2.8, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(ax, ay), QPointF(ax + sx, ay + sy))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self._with_opacity(pal.dot, opacity)))
        p.drawEllipse(QPointF(ax, ay), 3.2, 3.2)
        p.restore()

    # ═══════════════════════════════════════════════════════════════
    #  Hit testing
    # ═══════════════════════════════════════════════════════════════

    def _hit(self, pos: QPointF) -> str | None:
        pos = QPointF(pos.x() - self._PAD, pos.y() - self._PAD)
        D, U, R = self._axes()
        cx = cy = self._SIZE / 2
        for cid, ctrl in self._ctrl.items():
            if ctrl["poly"].containsPoint(pos, Qt.OddEvenFill):
                return cid
        fs = sorted([(float(np.dot(f['ctr'], D)), nm, f)
                     for nm, f in self._faces.items()
                     if float(np.dot(f['n'], D)) < self._VIS])
        for _, nm, f in fs:
            if QPolygonF([self._proj(pt, R, U, cx, cy) for pt in f['pts']]).containsPoint(
                    pos, Qt.OddEvenFill):
                return nm
        return None

    # ═══════════════════════════════════════════════════════════════
    #  Qt events
    # ═══════════════════════════════════════════════════════════════

    def resizeEvent(self, event):   # noqa: N802
        super().resizeEvent(event)
        self.clearMask()

    def changeEvent(self, event):   # noqa: N802
        """Re-scale when the widget moves to a screen with a different DPI."""
        if event.type() == QEvent.Type.ScreenChangeInternal:
            self._update_dpi()
        super().changeEvent(event)

    def mouseMoveEvent(self, event):   # noqa: N802
        was_hovering = self._hovering
        self._hovering = True
        hid = self._hit(event.position())
        if hid != self.hovered_id or not was_hovering:
            self.hovered_id = hid
            self.update()
        self.setCursor(QCursor(Qt.PointingHandCursor if hid else Qt.ArrowCursor))
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):   # noqa: N802
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        hid = self._hit(event.position())
        if not hid:
            return super().mousePressEvent(event)
        self.hovered_id = None
        event.accept()
        if hid in self._faces:
            self._act_face(hid)
        else:
            self._act_ctrl(self._ctrl[hid]['act'])
        self.update()

    def leaveEvent(self, event):   # noqa: N802
        self._hovering = False
        self.hovered_id = None
        self.update()
        super().leaveEvent(event)

    # ═══════════════════════════════════════════════════════════════
    #  Actions
    # ═══════════════════════════════════════════════════════════════

    def _nearest_face_up(self, tgt: np.ndarray, default_up: np.ndarray,
                         face_type: str, *, cur_dir=None, cur_up=None) -> np.ndarray:
        """
        All vectors must be in the same space (navicube Z-up space).
        Pass cur_dir / cur_up explicitly when calling from _act_face so that
        the current world-space camera state is pre-converted before this call.
        """
        cur_dir = self._dir if cur_dir is None else cur_dir
        cur_up  = self._up  if cur_up  is None else cur_up
        tgt = _norm(tgt)
        base_up = _project_to_plane(default_up, tgt)
        if np.linalg.norm(base_up) < 1e-6:
            fallback = np.array([0.0, 1.0, 0.0]) if abs(tgt[2]) > 0.9 else np.array([0.0, 0.0, 1.0])
            base_up = _project_to_plane(fallback, tgt)
        base_up = _norm(base_up)

        current_up = _project_to_plane(cur_up, tgt)
        if np.linalg.norm(current_up) < 1e-6:
            current_up = _project_to_plane(np.cross(tgt, cur_dir), tgt)
        if np.linalg.norm(current_up) < 1e-6:
            return base_up
        current_up = _norm(current_up)

        step = math.pi / 3.0 if face_type == "corner" else math.pi / 2.0
        sin_a = float(np.dot(np.cross(base_up, current_up), tgt))
        cos_a = float(np.clip(np.dot(base_up, current_up), -1.0, 1.0))
        ang = math.atan2(sin_a, cos_a)
        snap = round(ang / step) * step
        snapped_up = _rod(base_up, tgt, snap)
        return _norm(snapped_up)

    def _act_face(self, nm: str):
        ROT = self.__class__._WORLD_ROT
        face = self._faces[nm]
        n_nav = face['n']
        tgt_nav = -n_nav
        default_up = np.array([0., 1., 0.]) if abs(n_nav[2]) > 0.95 else np.array([0., 0., 1.])
        cur_dir_nav = _norm(ROT.T @ self._dir)
        cur_up_nav  = _norm(ROT.T @ self._up)
        up_nav = self._nearest_face_up(tgt_nav, default_up, face['ft'],
                                        cur_dir=cur_dir_nav, cur_up=cur_up_nav)
        self._start_anim(_norm(ROT @ tgt_nav), _norm(ROT @ up_nav))

    def _act_ctrl(self, act: str):
        ROT = self.__class__._WORLD_ROT
        if act == 'home':
            self._start_anim(self._home_dir.copy(), self._home_up.copy())
            return
        D, U, R = self._axes()
        step = self._STEP
        if   act == 'orbit_u': nd, nu = _rod(D, R, -step), _rod(U, R, -step)
        elif act == 'orbit_d': nd, nu = _rod(D, R,  step), _rod(U, R,  step)
        elif act == 'orbit_l': nd, nu = _rod(D, np.array([0., 0., 1.]),  step), U.copy()
        elif act == 'orbit_r': nd, nu = _rod(D, np.array([0., 0., 1.]), -step), U.copy()
        elif act == 'roll_ccw': nd, nu = D.copy(), _rod(U, D, -step)
        elif act == 'roll_cw':  nd, nu = D.copy(), _rod(U, D,  step)
        elif act == 'backside': nd, nu = -D.copy(), U.copy()
        else: return
        self._start_anim(_norm(ROT @ nd), _norm(ROT @ nu))
