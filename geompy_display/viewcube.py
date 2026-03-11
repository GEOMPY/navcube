"""
geompy_display.viewcube
========================
Builds and manages the orientation ViewCube inside an OCC viewer.
The cube is translated to a screen-corner position using a fixed world-space
offset computed from the view bounds at init time.
"""

from .viewcube_config import ViewCubeConfig
from .glyphs import GLYPHS
from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_Transform
from OCC.Core.AIS import AIS_Shape
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Trsf, gp_Vec
from OCC.Core.TopoDS import topods, TopoDS_Compound
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

def _translate(shape, dx, dy, dz):
    """Return a translated copy of shape."""
    t = gp_Trsf()
    t.SetTranslation(gp_Vec(dx, dy, dz))
    return BRepBuilderAPI_Transform(shape, t, True).Shape()


def _build_text_edges(text, origin, u_dir, v_dir, char_height, char_aspect, char_gap):
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


def _face_defs(size):
    """Face label definitions relative to cube origin at (0,0,0)."""
    h, e = size / 2.0, 0.02
    return [
        ("FRONT",  gp_Pnt(h,      -e,      h), gp_Dir(1, 0, 0), gp_Dir(0, 0, 1)),
        ("BACK",   gp_Pnt(h,  size+e,      h), gp_Dir(-1, 0, 0), gp_Dir(0, 0, 1)),
        ("LEFT",   gp_Pnt(-e,      h,      h), gp_Dir(0, -1, 0), gp_Dir(0, 0, 1)),
        ("RIGHT",  gp_Pnt(size+e,  h,      h), gp_Dir(0, 1, 0), gp_Dir(0, 0, 1)),
        ("TOP",    gp_Pnt(h,       h,  size+e), gp_Dir(1, 0, 0), gp_Dir(0, 1, 0)),
        ("BOTTOM", gp_Pnt(h,       h,     -e), gp_Dir(1, 0, 0), gp_Dir(0, -1, 0)),
    ]


def _corner_offset(position, cube_size, padding, viewer_widget):
    """
    Compute (dx, dy, dz, world_size).

    The cube is sized to 10% of the smaller viewport dimension.
    Position is computed from the actual view projection — we read
    the view centre in world space and add the half-extents.
    """
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
        cx, cy, cz = view.ViewAxisIntersectWithZPlane(0)

        s, p = world_size, pad_world
        pos = position.lower()

        if pos == "top-right":
            return cx + half_w - s - p,  0,  cz + half_h - s - p,  s
        elif pos == "top-left":
            return cx - half_w + p,      0,  cz + half_h - s - p,  s
        elif pos == "bottom-right":
            return cx + half_w - s - p,  0,  cz - half_h + p,       s
        else:  # bottom-left
            return cx - half_w + p,      0,  cz - half_h + p,        s

    except Exception:
        try:
            # Fallback: no view centre, assume origin
            view = viewer_widget._display.View
            scale = view.Scale()
            if not scale or scale <= 0:
                raise ValueError("view scale not ready")
            width = viewer_widget.width()
            height = viewer_widget.height()
            target_px = min(width, height) * 0.10
            world_size = target_px / scale
            pad_world = world_size * 0.08
            half_w = (width / 2.0) / scale
            half_h = (height / 2.0) / scale
            s, p = world_size, pad_world
            pos = position.lower()
            if pos == "top-right":
                return half_w - s - p, 0,  half_h - s - p, s
            elif pos == "top-left":
                return -half_w + p,     0,  half_h - s - p, s
            elif pos == "bottom-right":
                return half_w - s - p, 0, -half_h + p,    s
            else:
                return -half_w + p,     0, -half_h + p,     s
        except Exception:
            o = cube_size * 3
            pos = position.lower()
            if pos == "top-right":
                return o, 0,  o, cube_size
            if pos == "top-left":
                return -o, 0,  o, cube_size
            if pos == "bottom-right":
                return o, 0, -o, cube_size
            return -o, 0, -o, cube_size


# ── ViewCube ───────────────────────────────────────────────────────────────────

class ViewCube:
    def __init__(self, cfg: ViewCubeConfig):
        self.cfg = cfg
        self._ais_cube = None
        self._label_ais = []
        self._last_width = None

    def _make_cube_shape(self):
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

    def show(self, ctx, viewer_widget):
        """
        Add ViewCube to ctx, positioned in the correct corner.

        Parameters
        ----------
        ctx           : AIS_InteractiveContext
        viewer_widget : qtViewer3d  — needed to read window size + scale
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

        # ── Labels — single pass, clean single lines ─────────────────────────
        lc = Quantity_Color(*cfg.label_color, Quantity_TOC_RGB)
        self._label_ais = []

        for label, centre, u_dir, v_dir in _face_defs(world_size):
            sc = gp_Pnt(centre.X() + dx, centre.Y() + dy, centre.Z() + dz)
            compound = _build_text_edges(
                label, sc, u_dir, v_dir,
                char_h, cfg.char_aspect, char_g,
            )
            ais = AIS_Shape(compound)
            ais.SetColor(lc)
            ais.SetWidth(cfg.line_width)
            ctx.Display(ais, False)
            self._label_ais.append(ais)

        ctx.UpdateCurrentViewer()

    def hide(self, ctx):
        if self._ais_cube:
            ctx.Erase(self._ais_cube, False)
        for ais in self._label_ais:
            ctx.Erase(ais, False)
        ctx.UpdateCurrentViewer()

    def update_line_width(self, ctx, view_scale: float):
        w = max(1, min(3, round(view_scale * self.cfg.cube_size * 0.015)))
        if w == self._last_width:
            return
        self._last_width = w
        for ais in self._label_ais:
            ais.SetWidth(w)
            ctx.Redisplay(ais, False)
        ctx.UpdateCurrentViewer()

    @staticmethod
    def show_trihedron(view):
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
