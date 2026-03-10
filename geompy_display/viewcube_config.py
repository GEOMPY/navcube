"""
occdisplay.viewcube_config
==========================
All parameters that control the ViewCube appearance.
Instantiate ViewCubeConfig and pass it to OCCDisplay before calling .start().

Example
-------
    from occdisplay import OCCDisplay, ViewCubeConfig

    cfg = ViewCubeConfig(cube_size=80, chamfer_r=6, silver=(0.6, 0.6, 0.65))
    display = OCCDisplay(viewcube=cfg)
    display.start()
"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class ViewCubeConfig:
    # ── Geometry ──────────────────────────────────────────────────────────────
    cube_size:   float = 100.0   # mm — side length of the orientation cube
    chamfer_r:   float =   8.0   # mm — chamfer on every edge/corner (<cube_size/4)

    # ── Colours  (R, G, B) each in [0..1] ────────────────────────────────────
    silver:      Tuple[float,float,float] = (0.75, 0.75, 0.78)  # face colour
    label_color: Tuple[float,float,float] = (0.0,  0.0,  0.0)   # text colour

    # ── Text ─────────────────────────────────────────────────────────────────
    side_margin: float = 0.15   # fraction of flat-face kept empty each side
    char_aspect: float = 0.60   # char width = char_height * char_aspect

    # ── Rendering ─────────────────────────────────────────────────────────────
    # line_width is zoom-adaptive at runtime; this is only the initial value.
    line_width:  int   = 1      # px — initial stroke thickness

    # ── Position in viewport ──────────────────────────────────────────────────
    # Fraction of the main viewport width/height the cube occupies (approx).
    viewport_fraction: float = 0.18   # 0.1 = small corner, 0.3 = large

    # ── Derived (computed in __post_init__) ───────────────────────────────────
    char_height: float = field(init=False)
    char_gap:    float = field(init=False)

    _GAP_RATIO:  float = field(default=0.25, init=False, repr=False)
    _LONGEST:    str   = field(default="BOTTOM", init=False, repr=False)

    def __post_init__(self):
        self._recalc()

    def _recalc(self):
        """Recompute char_height and char_gap from current parameters."""
        n        = len(self._LONGEST)
        flat     = self.cube_size - 2.0 * self.chamfer_r
        usable   = flat * (1.0 - 2.0 * self.side_margin)
        self.char_height = usable / (n * self.char_aspect + (n - 1) * self._GAP_RATIO)
        self.char_gap    = self._GAP_RATIO * self.char_height

    def update(self, **kwargs):
        """Update any parameter and recompute derived values.

        Example::
            cfg.update(cube_size=60, chamfer_r=5)
        """
        for k, v in kwargs.items():
            if not hasattr(self, k):
                raise AttributeError(f"ViewCubeConfig has no parameter '{k}'")
            object.__setattr__(self, k, v)
        self._recalc()
        return self
