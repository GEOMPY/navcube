"""
geompy_display.viewcube_config
===============================
All parameters that control the ViewCube appearance and position.

Example
-------
    from geompy_display import OCCDisplay, ViewCubeConfig

    cfg = ViewCubeConfig(
        cube_size = 30,
        position  = "top-right",   # or "top-left", "bottom-right", "bottom-left"
        silver    = (0.7, 0.7, 0.75),
    )
    display = OCCDisplay(viewcube=cfg)
    display.start()
"""

from dataclasses import dataclass, field
from typing import Tuple

# Valid corner positions
POSITIONS = ("top-right", "top-left", "bottom-right", "bottom-left")


@dataclass
class ViewCubeConfig:

    # ── Geometry ──────────────────────────────────────────────────────────────
    cube_size:   float = 25.0    # mm — keep small, it's just a nav aid
    chamfer_r:   float =  2.0   # mm — bevel (<cube_size/4)

    # ── Position ──────────────────────────────────────────────────────────────
    position:    str   = "top-right"   # "top-right" | "top-left" |
                                        # "bottom-right" | "bottom-left"
    padding:     float = 5.0           # mm — gap between cube and viewport edge

    # ── Colours (R, G, B) each in [0..1] ─────────────────────────────────────
    silver:      Tuple[float,float,float] = (0.75, 0.75, 0.78)
    label_color: Tuple[float,float,float] = (0.0,  0.0,  0.0)

    # ── Text ──────────────────────────────────────────────────────────────────
    side_margin: float = 0.15   # fraction of flat-face kept empty each side
    char_aspect: float = 0.60   # char width = char_height * char_aspect

    # ── Rendering ─────────────────────────────────────────────────────────────
    line_width:  int   = 1      # px — keep at 1, zoom-adaptive will handle thickness

    # ── Derived ───────────────────────────────────────────────────────────────
    char_height: float = field(init=False)
    char_gap:    float = field(init=False)
    _GAP_RATIO:  float = field(default=0.25,     init=False, repr=False)
    _LONGEST:    str   = field(default="BOTTOM", init=False, repr=False)

    def __post_init__(self):
        if self.position not in POSITIONS:
            raise ValueError(f"position must be one of {POSITIONS}")
        if self.chamfer_r >= self.cube_size / 4:
            raise ValueError("chamfer_r must be < cube_size / 4")
        self._recalc()

    def _recalc(self):
        n              = len(self._LONGEST)
        flat           = self.cube_size - 2.0 * self.chamfer_r
        usable         = flat * (1.0 - 2.0 * self.side_margin)
        self.char_height = usable / (n * self.char_aspect + (n - 1) * self._GAP_RATIO)
        self.char_gap    = self._GAP_RATIO * self.char_height

    def update(self, **kwargs):
        """Update any parameter and recompute derived values.

        Example::
            cfg.update(cube_size=25, position="bottom-left")
        """
        for k, v in kwargs.items():
            if not hasattr(self, k):
                raise AttributeError(f"ViewCubeConfig has no parameter '{k}'")
            object.__setattr__(self, k, v)
        self.__post_init__()
        return self