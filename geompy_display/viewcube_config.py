"""ViewCube configuration dataclass for appearance and positioning.

Provides `ViewCubeConfig`, a dataclass that controls all aspects of the
3D orientation cube rendering—size, position, colors, text layout, and
rendering parameters. Settings support dynamic updates via the `update()` method.

Attributes:
    POSITIONS (tuple[str, ...]): Valid corner position values.

Examples:
    Create a custom ViewCube configuration:

        >>> from geompy_display import OCCDisplay, ViewCubeConfig
        >>> cfg = ViewCubeConfig(
        ...     cube_size=30,
        ...     position="top-left",   # or "top-right", "bottom-left", "bottom-right"
        ...     silver=(0.7, 0.7, 0.75),
        ...     padding=10,
        ... )
        >>> display = OCCDisplay(viewcube=cfg)

    Update configuration after creation:

        >>> cfg.update(cube_size=40, position="bottom-right")
"""

from dataclasses import dataclass, field
from typing import Tuple

# Valid corner positions
POSITIONS: Tuple[str, ...] = ("top-right", "top-left", "bottom-right", "bottom-left")


@dataclass
class ViewCubeConfig:
    """Configuration for ViewCube appearance, position, and rendering.

    This dataclass controls all visual and layout parameters of the orientation
    ViewCube. Includes validation in __post_init__() and supports dynamic updates
    via update(). Derived fields (char_height, char_gap) are computed from base
    parameters and updated automatically on any change.

    Attributes:
        cube_size: Size of the cube in world units. Defaults to 25.0.
        chamfer_r: Radius of chamfered (beveled) corners in world units.
            Defaults to 2.0. Must be < cube_size / 4.
        position: Corner position. One of POSITIONS. Defaults to "top-right".
        padding: Gap between cube and viewport edge in world units. Defaults to 5.0.
        silver: RGB color of cube faces, each channel in [0..1].
            Defaults to (0.75, 0.75, 0.78).
        label_color: RGB color of text labels, each channel in [0..1].
            Defaults to (0.0, 0.0, 0.0) for black.
        side_margin: Fraction of flat face reserved as empty space on each side.
            Defaults to 0.15 (15% margin each side).
        char_aspect: Character width ratio relative to height. Defaults to 0.60.
        line_width: Glyph stroke width in pixels. Defaults to 1.
            Keep at 1; zoom-adaptive rendering handles thickness.
        char_height: Computed character height (derived field, read-only).
        char_gap: Computed gap between characters (derived field, read-only).

    Raises:
        ValueError: If parameters fail validation (e.g., invalid colors,
            cube_size <= 0, invalid position).
    """

    # ── Geometry ──────────────────────────────────────────────────────────────
    cube_size: float = 25.0  # mm — keep small, it's just a nav aid
    chamfer_r: float = 2.0  # mm — bevel (<cube_size/4)

    # ── Position ──────────────────────────────────────────────────────────────
    position: str = (
        "top-right"  # "top-right" | "top-left" |"bottom-right" | "bottom-left"
    )
    padding: float = 5.0  # mm — gap between cube and viewport edge

    # ── Colours (R, G, B) each in [0..1] ─────────────────────────────────────
    silver: Tuple[float, float, float] = (0.75, 0.75, 0.78)
    label_color: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    # ── Text ──────────────────────────────────────────────────────────────────
    side_margin: float = 0.15  # fraction of flat-face kept empty each side
    char_aspect: float = 0.60  # char width = char_height * char_aspect

    # ── Rendering ─────────────────────────────────────────────────────────────
    line_width: int = 1  # px — keep at 1, zoom-adaptive will handle thickness

    # ── Derived ───────────────────────────────────────────────────────────────
    char_height: float = field(init=False)
    char_gap: float = field(init=False)
    _GAP_RATIO: float = field(default=0.25, init=False, repr=False)
    _LONGEST: str = field(default="BOTTOM", init=False, repr=False)

    @staticmethod
    def _validate_color(name: str, value: tuple[float, ...] | list[float]) -> None:
        """Validate an RGB color tuple.

        Args:
            name: Parameter name for error messages.
            value: Tuple/list to validate as RGB color.

        Raises:
            ValueError: If value is not a 3-element tuple/list with
                floats in [0..1].
        """
        if (
            not isinstance(value, (tuple, list))
            or len(value) != 3
            or not all(isinstance(c, (int, float)) and 0.0 <= c <= 1.0 for c in value)
        ):
            raise ValueError(f"{name} must be an (R, G, B) tuple with values in [0..1]")

    def __post_init__(self) -> None:
        """Validate all parameters and compute derived fields.

        Called automatically after initialization. Performs comprehensive
        validation of all parameters, computes derived fields (char_height,
        char_gap), and raises ValueError if any constraint is violated.

        Raises:
            ValueError: If any parameter fails validation.
        """
        if self.cube_size <= 0:
            raise ValueError("cube_size must be positive")
        if self.chamfer_r < 0:
            raise ValueError("chamfer_r must be non-negative")
        if self.padding < 0:
            raise ValueError("padding must be non-negative")
        if self.position not in POSITIONS:
            raise ValueError(f"position must be one of {POSITIONS}")
        if self.chamfer_r >= self.cube_size / 4:
            raise ValueError("chamfer_r must be < cube_size / 4")
        self._validate_color("silver", self.silver)
        self._validate_color("label_color", self.label_color)
        self._recalc()

    def _recalc(self) -> None:
        """Recompute derived text layout fields.

        Called by __post_init__() and update() to recalculate char_height
        and char_gap based on current cube_size and text layout parameters.
        """
        n = len(self._LONGEST)
        flat = self.cube_size - 2.0 * self.chamfer_r
        usable = flat * (1.0 - 2.0 * self.side_margin)
        self.char_height = usable / (n * self.char_aspect + (n - 1) * self._GAP_RATIO)
        self.char_gap = self._GAP_RATIO * self.char_height

    # Fields that can be set via update()
    _UPDATABLE: frozenset[str] = frozenset(
        {
            "cube_size",
            "chamfer_r",
            "position",
            "padding",
            "silver",
            "label_color",
            "side_margin",
            "char_aspect",
            "line_width",
        }
    )

    def update(
        self, **kwargs: float | str | int | Tuple[float, float, float]
    ) -> "ViewCubeConfig":
        """Update configuration parameters and recompute derived values.

        Allows selective updates of updatable parameters without recreating
        the entire dataclass. All changes trigger revalidation and recalculation
        of derived fields. Returns self for method chaining.

        Args:
            **kwargs: Parameter names and values to update. Only parameters
                in _UPDATABLE are allowed.

        Returns:
            This ViewCubeConfig instance (enables chaining).

        Raises:
            AttributeError: If any kwarg key is not in _UPDATABLE.
            ValueError: If updated parameters fail validation.

        Examples:
            >>> cfg = ViewCubeConfig()
            >>> cfg.update(cube_size=30, position="bottom-left")
            >>> cfg.cube_size
            30.0
        """
        for k, v in kwargs.items():
            if k not in self._UPDATABLE:
                raise AttributeError(f"ViewCubeConfig has no updatable parameter '{k}'")
            object.__setattr__(self, k, v)
        self.__post_init__()
        return self
