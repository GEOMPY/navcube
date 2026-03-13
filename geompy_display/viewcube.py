"""ViewCube builder and manager for OCC viewer orientation cube.

Manages the construction, positioning, and rendering of a 3D orientation cube
with labeled faces (FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM). Provides automatic
zoom-adaptive line width rendering and screen-corner positioning.

Core Functions:
    _translate: Translate a shape in 3D space.
    _build_text_edges: Build text geometry from stroke glyphs.
    _face_defs: Define label positions and orientations.
    _position_offset: Compute corner offset from position string.
    _corner_offset: Compute world-space cube position and size.

Main Class:
    ViewCube: Builds and manages the cube visualization.
"""

from __future__ import annotations

from typing import Tuple, TYPE_CHECKING

from .viewcube_config import ViewCubeConfig
from .glyphs import GLYPHS
from OCC.Core.BRep import BRep_Builder

if TYPE_CHECKING:
    from OCC.Core.AIS import AIS_InteractiveContext
    from OCC.Core.V3d import V3d_View
    from OCC.Display.qtDisplay import qtViewer3d
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_Transform
from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Trsf, gp_Vec
from OCC.Core.TopoDS import topods, TopoDS_Compound, TopoDS_Shape
from OCC.Core.TopAbs import TopAbs_EDGE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.BRepFilletAPI import BRepFilletAPI_MakeChamfer
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
import logging
import traceback

log = logging.getLogger(__name__)


try:
    from OCC.Core.Aspect import Aspect_TOTP_RIGHT_LOWER
    from OCC.Core.V3d import V3d_ZBUFFER
    from OCC.Core.Quantity import Quantity_NOC_RED
    _HAS_TRIEDRON = True
except ImportError:
    _HAS_TRIEDRON = False


# ── Helpers ────────────────────────────────────────────────────────────────────

def _translate(shape: TopoDS_Shape, dx: float, dy: float, dz: float) -> TopoDS_Shape:
    """Translate a shape by the given offset.

    Creates a new translated copy of the shape without modifying the original.

    Args:
        shape: OCC TopoDS shape to translate.
        dx: Translation distance along X axis.
        dy: Translation distance along Y axis.
        dz: Translation distance along Z axis.

    Returns:
        Translated OCC shape.
    """
    t = gp_Trsf()
    t.SetTranslation(gp_Vec(dx, dy, dz))
    return BRepBuilderAPI_Transform(shape, t, True).Shape()


def _build_text_edges(
    text: str,
    origin: gp_Pnt,
    u_dir: gp_Dir,
    v_dir: gp_Dir,
    char_height: float,
    char_aspect: float,
    char_gap: float,
) -> TopoDS_Compound:
    """Build 3D text geometry from 2D stroke glyphs.

    Converts character glyphs into 3D polyline edges positioned at the given
    origin and oriented along u_dir (horizontal) and v_dir (vertical) axes.
    Text is centered at the origin.

    Args:
        text: Text string to render (converted to uppercase).
        origin: gp_Pnt specifying text center position.
        u_dir: gp_Dir for horizontal (left-right) direction.
        v_dir: gp_Dir for vertical (up-down) direction.
        char_height: Height of characters in world units.
        char_aspect: Width-to-height aspect ratio of characters.
        char_gap: Horizontal gap between characters in world units.

    Returns:
        OCC TopoDS_Compound containing all text edges.
    """
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)

    char_width = char_height * char_aspect
    total_w = len(text) * char_width + max(0, len(text) - 1) * char_gap

    ox = origin.X() - (total_w / 2) * u_dir.X() - (char_height / 2) * v_dir.X()
    oy = origin.Y() - (total_w / 2) * u_dir.Y() - (char_height / 2) * v_dir.Y()
    oz = origin.Z() - (total_w / 2) * u_dir.Z() - (char_height / 2) * v_dir.Z()

    cursor = 0.0
    for ch in text.upper():
        for stroke in GLYPHS.get(ch, []):
            pts = []
            for lx, ly in stroke:
                px = ox + (cursor + lx*char_width) * \
                    u_dir.X() + ly*char_height*v_dir.X()
                py = oy + (cursor + lx*char_width) * \
                    u_dir.Y() + ly*char_height*v_dir.Y()
                pz = oz + (cursor + lx*char_width) * \
                    u_dir.Z() + ly*char_height*v_dir.Z()
                pts.append(gp_Pnt(px, py, pz))
            for i in range(len(pts) - 1):
                try:
                    builder.Add(compound, BRepBuilderAPI_MakeEdge(
                        pts[i], pts[i+1]).Edge())
                except Exception:
                    log.warning("Skipping degenerate edge in glyph '%s'", ch)
        cursor += char_width + char_gap
    return compound


def _face_defs(size: float) -> list[Tuple[str, gp_Pnt, gp_Dir, gp_Dir]]:
    """Define face label positions and orientations for a cube.

    Returns label definitions for all six cube faces at the given cube size,
    positioned at the center of each face with appropriate direction vectors
    for text orientation.

    Args:
        size: Edge length of the cube.

    Returns:
        List of tuples (label, center_point, u_dir, v_dir) for each face:
            - label: Face name (FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM).
            - center_point: gp_Pnt at face center for text origin.
            - u_dir: gp_Dir for text horizontal direction.
            - v_dir: gp_Dir for text vertical direction.
    """
    h, e = size / 2.0, 0.02
    return [
        ("FRONT",  gp_Pnt(h,      -e,      h), gp_Dir(1, 0, 0), gp_Dir(0, 0, 1)),
        ("BACK",   gp_Pnt(h,  size+e,      h), gp_Dir(-1, 0, 0), gp_Dir(0, 0, 1)),
        ("LEFT",   gp_Pnt(-e,      h,      h), gp_Dir(0, -1, 0), gp_Dir(0, 0, 1)),
        ("RIGHT",  gp_Pnt(size+e,  h,      h), gp_Dir(0, 1, 0), gp_Dir(0, 0, 1)),
        ("TOP",    gp_Pnt(h,       h,  size+e), gp_Dir(1, 0, 0), gp_Dir(0, 1, 0)),
        ("BOTTOM", gp_Pnt(h,       h,     -e), gp_Dir(1, 0, 0), gp_Dir(0, -1, 0)),
    ]


def _position_offset(
    pos: str,
    cx: float,
    cz: float,
    half_w: float,
    half_h: float,
    s: float,
    p: float,
) -> Tuple[float, float]:
    """Compute (dx, dz) offset for cube placement at a screen corner.

    Calculates the world-space offset from the view center to position
    a cube of size s with padding p at the specified corner.

    Args:
        pos: Position string ("top-right", "top-left", "bottom-right", "bottom-left").
        cx: View center X coordinate in world space.
        cz: View center Z coordinate in world space.
        half_w: Half-width of visible viewport in world units.
        half_h: Half-height of visible viewport in world units.
        s: Cube size in world units.
        p: Padding (gap from edge) in world units.

    Returns:
        Tuple (dx, dz) for cube placement offset.
    """
    if pos == "top-right":
        return cx + half_w - s - p, cz + half_h - s - p
    elif pos == "top-left":
        return cx - half_w + p, cz + half_h - s - p
    elif pos == "bottom-right":
        return cx + half_w - s - p, cz - half_h + p
    else:  # bottom-left
        return cx - half_w + p, cz - half_h + p


def _corner_offset(
    position: str,
    cube_size: float,
    padding: float,
    viewer_widget: qtViewer3d,
) -> Tuple[float, float, float, float]:
    """Compute world-space cube position and size.

    Calculates the (dx, dy, dz, world_size) for the ViewCube based on the
    actual viewport dimensions and camera view. The cube is sized to 10% of
    the smaller viewport dimension for balance between visibility and
    non-intrusiveness.

    Args:
        position: Corner position string ("top-right", "top-left", etc.).
        cube_size: Reference cube size configured (may be scaled by viewport).
        padding: Padding between cube and viewport edge.
        viewer_widget: qtViewer3d widget to read viewport and view data from.

    Returns:
        Tuple (dx, dy, dz, world_size):
            - dx, dy, dz: World-space position for cube placement.
            - world_size: Computed cube size in world units.
    """
    pos = position.lower()
    try:
        view = viewer_widget._display.View
        scale = view.Scale()            # pixels per world unit
        if not scale or scale <= 0:
            raise ValueError("view scale not ready")
        width = viewer_widget.width()
        height = viewer_widget.height()

        # cube size = 10% of smaller viewport side in world units
        target_px = min(width, height) * 0.10
        world_size = target_px / scale
        pad_world = world_size * 0.08   # 8% of cube as padding

        # half extents of the visible viewport in world units
        half_w = (width / 2.0) / scale
        half_h = (height / 2.0) / scale

        # view centre in world space (where the camera is looking)
        try:
            cx, cy, cz = view.ViewAxisIntersectWithZPlane(0)
        except Exception:
            cx, cz = 0.0, 0.0

        dx, dz = _position_offset(
            pos, cx, cz, half_w, half_h, world_size, pad_world)
        return dx, 0, dz, world_size

    except Exception:
        o = cube_size * 3
        dx, dz = _position_offset(
            pos, 0, 0, o + cube_size, o + cube_size, cube_size, 0)
        return dx, 0, dz, cube_size


# ── ViewCube ───────────────────────────────────────────────────────────────────

class ViewCube:
    """Builder and manager for 3D orientation cube with labeled faces.

    Constructs a chamfered cube with labeled faces (FRONT, BACK, LEFT, RIGHT,
    TOP, BOTTOM) positioned in a screen corner. Handles scaling to world-space,
    text rendering on each face, and zoom-adaptive line width for visibility
    at any zoom level.

    Attributes:
        cfg: ViewCubeConfig controlling appearance and position.
        _ais_cube: AIS_Shape for the cube body (set by show()).
        _label_ais: List of AIS_Shape objects for face labels (set by show()).
        _last_width: Cache of last applied line width for optimization.
    """

    def __init__(self, cfg: ViewCubeConfig) -> None:
        """Initialize ViewCube with configuration.

        Args:
            cfg: ViewCubeConfig instance controlling visualization parameters.
        """
        self.cfg: ViewCubeConfig = cfg
        self._ais_cube: AIS_Shape | None = None
        self._label_ais: list[AIS_Shape] = []
        self._last_width: int | None = None

    def _make_cube_shape(self) -> TopoDS_Shape:
        """Build a chamfered cube shape.

        Creates a box with chamfered (beveled) edges according to the
        configuration. Used internally to build the cube geometry.

        Returns:
            OCC TopoDS shape representing the chamfered cube.

        Raises:
            RuntimeError: If OCCT chamfer operation fails.
        """
        s, r = self.cfg.cube_size, self.cfg.chamfer_r
        box = BRepPrimAPI_MakeBox(s, s, s).Shape()
        cf = BRepFilletAPI_MakeChamfer(box)
        exp = TopExp_Explorer(box, TopAbs_EDGE)
        while exp.More():
            cf.Add(r, topods.Edge(exp.Current()))
            exp.Next()
        cf.Build()
        if not cf.IsDone():
            raise RuntimeError("ViewCube chamfer failed.")
        return cf.Shape()

    def show(self, ctx: AIS_InteractiveContext, viewer_widget: qtViewer3d) -> None:
        """Display ViewCube in the viewer at the configured corner position.

        Builds the cube geometry, positions it in world space, creates and
        positions face labels, and displays both in the OCC context. The cube
        is sized proportional to the viewport dimensions for responsive layout.

        Args:
            ctx: OCC AIS_InteractiveContext where the cube is displayed.
            viewer_widget: qtViewer3d widget for reading viewport dimensions
                and view information.

        Side Effects:
            Updates self._ais_cube and self._label_ais with display objects.
            Increases context display count.
        """
        cfg = self.cfg
        dx, dy, dz, world_size = _corner_offset(
            cfg.position, cfg.cube_size, cfg.padding, viewer_widget
        )

        # Recompute font metrics for the actual world_size used
        from .viewcube_config import ViewCubeConfig as _VCC, POSITIONS
        _n = len("BOTTOM")
        _flat = world_size - 2.0 * (cfg.chamfer_r / cfg.cube_size * world_size)
        _usable = _flat * (1.0 - 2.0 * cfg.side_margin)
        _ch = _usable / (_n * cfg.char_aspect + (_n - 1) *
                         0.25 * cfg.char_aspect / cfg.char_aspect)
        _cg = 0.25 * _ch
        # simpler: just scale char_height proportionally
        scale_f = world_size / cfg.cube_size
        char_h = cfg.char_height * scale_f
        char_g = cfg.char_gap * scale_f
        chamfer = cfg.chamfer_r * scale_f

        # ── Body ──────────────────────────────────────────────────────────────
        # Build cube at world_size, not cfg.cube_size
        s, r = world_size, chamfer
        box = BRepPrimAPI_MakeBox(s, s, s).Shape()
        cf = BRepFilletAPI_MakeChamfer(box)
        exp = TopExp_Explorer(box, TopAbs_EDGE)
        while exp.More():
            cf.Add(r, topods.Edge(exp.Current()))
            exp.Next()
        cf.Build()
        body = _translate(cf.Shape() if cf.IsDone() else box, dx, dy, dz)
        silver = Quantity_Color(*cfg.silver, Quantity_TOC_RGB)
        self._ais_cube = AIS_Shape(body)
        self._ais_cube.SetColor(silver)
        ctx.Display(self._ais_cube, True)

        # ── Labels — build all faces into a single compound ─────────────────
        lc = Quantity_Color(*cfg.label_color, Quantity_TOC_RGB)
        all_labels_builder = BRep_Builder()
        all_labels_compound = TopoDS_Compound()
        all_labels_builder.MakeCompound(all_labels_compound)

        for label, centre, u_dir, v_dir in _face_defs(world_size):
            sc = gp_Pnt(centre.X() + dx, centre.Y() + dy, centre.Z() + dz)
            compound = _build_text_edges(
                label, sc, u_dir, v_dir,
                char_h, cfg.char_aspect, char_g,
            )
            all_labels_builder.Add(all_labels_compound, compound)

        ais_labels = AIS_Shape(all_labels_compound)
        ais_labels.SetColor(lc)
        ais_labels.SetWidth(cfg.line_width)
        ctx.Display(ais_labels, False)
        self._label_ais = [ais_labels]

        ctx.UpdateCurrentViewer()

    def hide(self, ctx: AIS_InteractiveContext) -> None:
        """Remove ViewCube from the viewer.

        Erases both the cube body and face labels from the OCC context
        without destroying the geometry objects.

        Args:
            ctx: OCC AIS_InteractiveContext.
        """
        if self._ais_cube:
            ctx.Erase(self._ais_cube, False)
        for ais in self._label_ais:
            ctx.Erase(ais, False)
        ctx.UpdateCurrentViewer()

    def redisplay(self, ctx: AIS_InteractiveContext) -> None:
        """Re-display previously built ViewCube without rebuilding geometry.

        Shows the cube and labels that were previously built by show().
        This is more efficient than show() when the geometry hasn't changed.

        Args:
            ctx: OCC AIS_InteractiveContext.
        """
        if self._ais_cube is not None:
            ctx.Display(self._ais_cube, False)
            for ais in self._label_ais:
                ctx.Display(ais, False)
            ctx.UpdateCurrentViewer()

    def update_line_width(self, ctx: AIS_InteractiveContext, view_scale: float) -> None:
        """Update face label stroke width based on zoom level.

        Implements zoom-adaptive rendering: as the user zooms in/out,
        recalculates the stroke width to maintain visual thickness.
        Caches the last width to avoid redundant updates.

        Args:
            ctx: OCC AIS_InteractiveContext.
            view_scale: Current view scale (pixels per world unit).
        """
        w = max(1, min(3, round(view_scale * self.cfg.cube_size * 0.015)))
        if w == self._last_width:
            return
        self._last_width = w
        for ais in self._label_ais:
            ais.SetWidth(w)
            ctx.Redisplay(ais, False)
        ctx.UpdateCurrentViewer()

    @staticmethod
    def show_trihedron(view: V3d_View) -> None:
        """Display an optional trihedron reference axes in the view.

        Shows a red/green/blue axis indicator to help orient the viewer.
        This is a static helper method that gracefully degrades if the
        required OCC module is not available.

        Args:
            view: OCC V3d_View object.
        """
        if not _HAS_TRIEDRON:
            return
        try:
            view.TriedronDisplay(
                Aspect_TOTP_RIGHT_LOWER,
                Quantity_Color(Quantity_NOC_RED),
                0.08,
                V3d_ZBUFFER,
            )
            view.Redraw()
        except Exception:
            try:
                view.TriedronDisplay()
            except Exception as e:
                print(f"[ViewCube] trihedron: {e}")
