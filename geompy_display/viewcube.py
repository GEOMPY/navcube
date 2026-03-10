"""
occdisplay.viewcube
===================
Builds and manages the orientation ViewCube inside an OCC viewer.

Internal use — consumed by OCCDisplay.
"""

import traceback

from OCC.Core.BRepPrimAPI    import BRepPrimAPI_MakeBox
from OCC.Core.BRepFilletAPI  import BRepFilletAPI_MakeChamfer
from OCC.Core.TopExp         import TopExp_Explorer
from OCC.Core.TopAbs         import TopAbs_EDGE
from OCC.Core.TopoDS         import topods, TopoDS_Compound
from OCC.Core.gp             import gp_Pnt, gp_Dir
from OCC.Core.BRepMesh       import BRepMesh_IncrementalMesh
from OCC.Core.Quantity        import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.AIS            import AIS_Shape
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCC.Core.BRep           import BRep_Builder

from .glyphs          import GLYPHS
from .viewcube_config import ViewCubeConfig

try:
    from OCC.Core.Aspect import Aspect_TOTP_RIGHT_LOWER
    from OCC.Core.V3d    import V3d_ZBUFFER
    from OCC.Core.Quantity import Quantity_NOC_RED
    _HAS_TRIEDRON = True
except ImportError:
    _HAS_TRIEDRON = False


# ── Stroke-font edge builder ───────────────────────────────────────────────────

def _build_text_edges(text, origin, u_dir, v_dir, char_height, char_aspect, char_gap):
    """Return a TopoDS_Compound of 3-D line edges for `text` lying on a face."""
    builder  = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)

    char_width = char_height * char_aspect
    total_w    = len(text) * char_width + max(0, len(text) - 1) * char_gap

    ox = origin.X() - (total_w / 2) * u_dir.X() - (char_height / 2) * v_dir.X()
    oy = origin.Y() - (total_w / 2) * u_dir.Y() - (char_height / 2) * v_dir.Y()
    oz = origin.Z() - (total_w / 2) * u_dir.Z() - (char_height / 2) * v_dir.Z()

    cursor = 0.0
    for ch in text.upper():
        for stroke in GLYPHS.get(ch, []):
            pts = []
            for lx, ly in stroke:
                px = ox + (cursor + lx*char_width)*u_dir.X() + ly*char_height*v_dir.X()
                py = oy + (cursor + lx*char_width)*u_dir.Y() + ly*char_height*v_dir.Y()
                pz = oz + (cursor + lx*char_width)*u_dir.Z() + ly*char_height*v_dir.Z()
                pts.append(gp_Pnt(px, py, pz))
            for i in range(len(pts) - 1):
                try:
                    builder.Add(compound, BRepBuilderAPI_MakeEdge(pts[i], pts[i+1]).Edge())
                except Exception:
                    pass
        cursor += char_width + char_gap

    return compound


# ── Face definitions ───────────────────────────────────────────────────────────

def _face_defs(size):
    h, e = size / 2.0, 0.02
    return [
        ("FRONT",  gp_Pnt(h,      -e,      h), gp_Dir(1, 0, 0), gp_Dir(0, 0, 1)),
        ("BACK",   gp_Pnt(h,  size+e,      h), gp_Dir(-1,0, 0), gp_Dir(0, 0, 1)),
        ("LEFT",   gp_Pnt(-e,      h,      h), gp_Dir(0,-1, 0), gp_Dir(0, 0, 1)),
        ("RIGHT",  gp_Pnt(size+e,  h,      h), gp_Dir(0, 1, 0), gp_Dir(0, 0, 1)),
        ("TOP",    gp_Pnt(h,       h,  size+e),gp_Dir(1, 0, 0), gp_Dir(0, 1, 0)),
        ("BOTTOM", gp_Pnt(h,       h,     -e), gp_Dir(1, 0, 0), gp_Dir(0,-1, 0)),
    ]


# ── ViewCube renderer ──────────────────────────────────────────────────────────

class ViewCube:
    """
    Manages a chamfered orientation cube rendered in an OCC AIS context.

    Parameters
    ----------
    cfg : ViewCubeConfig
        All visual parameters.
    """

    def __init__(self, cfg: ViewCubeConfig):
        self.cfg         = cfg
        self._ais_cube   = None
        self._label_ais  = []   # all label AIS_Shape objects (for line-width updates)
        self._last_width = None

    # ── Build geometry ─────────────────────────────────────────────────────────

    def _make_cube(self):
        s, r = self.cfg.cube_size, self.cfg.chamfer_r
        box  = BRepPrimAPI_MakeBox(s, s, s).Shape()
        cf   = BRepFilletAPI_MakeChamfer(box)
        exp  = TopExp_Explorer(box, TopAbs_EDGE)
        while exp.More():
            cf.Add(r, topods.Edge(exp.Current()))
            exp.Next()
        cf.Build()
        if not cf.IsDone():
            raise RuntimeError("ViewCube chamfer failed — reduce chamfer_r.")
        return cf.Shape()

    # ── Display ────────────────────────────────────────────────────────────────

    def show(self, ctx):
        """
        Add the ViewCube (body + labels) to an AIS_InteractiveContext.
        Call this once after the viewer is initialised.
        """
        cfg = self.cfg

        # Body
        silver          = Quantity_Color(*cfg.silver, Quantity_TOC_RGB)
        self._ais_cube  = AIS_Shape(self._make_cube())
        self._ais_cube.SetColor(silver)
        ctx.Display(self._ais_cube, True)

        # Labels — 3 offset passes per face for bold appearance
        lc    = Quantity_Color(*cfg.label_color, Quantity_TOC_RGB)
        self._label_ais = []

        for label, centre, u_dir, v_dir in _face_defs(cfg.cube_size):
            for du, dv in [(0,0), (0.3,0), (0,0.3)]:
                shifted = gp_Pnt(
                    centre.X() + du*u_dir.X() + dv*v_dir.X(),
                    centre.Y() + du*u_dir.Y() + dv*v_dir.Y(),
                    centre.Z() + du*u_dir.Z() + dv*v_dir.Z(),
                )
                compound = _build_text_edges(
                    label, shifted, u_dir, v_dir,
                    cfg.char_height, cfg.char_aspect, cfg.char_gap,
                )
                ais = AIS_Shape(compound)
                ais.SetColor(lc)
                ais.SetWidth(cfg.line_width)
                ctx.Display(ais, False)
                self._label_ais.append(ais)

        ctx.UpdateCurrentViewer()

    def hide(self, ctx):
        """Remove the ViewCube from the context."""
        if self._ais_cube:
            ctx.Erase(self._ais_cube, False)
        for ais in self._label_ais:
            ctx.Erase(ais, False)
        ctx.UpdateCurrentViewer()

    # ── Zoom-adaptive line width ───────────────────────────────────────────────

    def update_line_width(self, ctx, view_scale: float):
        """
        Adjust label stroke width based on the current view scale
        (pixels per world unit, from V3d_View.Scale()).

        Call this from a QTimer at ~150 ms intervals.
        """
        w = max(1, min(6, round(view_scale * self.cfg.cube_size * 0.012)))
        if w == self._last_width:
            return
        self._last_width = w
        for ais in self._label_ais:
            ais.SetWidth(w)
            ctx.Redisplay(ais, False)
        ctx.UpdateCurrentViewer()

    # ── Corner trihedron (XYZ axis indicator) ─────────────────────────────────

    @staticmethod
    def show_trihedron(view):
        """Display the rotating XYZ trihedron in the bottom-right corner."""
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
                print(f"[ViewCube] trihedron unavailable: {e}")
