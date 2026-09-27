"""The survey's typefaces, served from the survey's own host.

The families of the font presets — Source Serif 4, Inter and Nunito — ship
inside the package as woff2 files (``siamang/frontend/templates/react/fonts``:
the Google Fonts variable fonts in their ``latin``, ``latin-ext`` and
``cyrillic`` subsets, with their SIL Open Font License texts; the README there
says where they come from). A survey's stylesheet declares ``@font-face`` for
the bundled families its font stacks name, pointing at ``fonts/<file>`` next to
the stylesheet, and :class:`~siamang.frontend.builder.FrontendBuilder` puts the
files those rules reference, with each family's license, in the bundle.

Nothing is requested from Google Fonts or any other third party. A family
that is not bundled — a stack of ``"Roboto", sans-serif`` — is used where the
respondent's device has it installed, and the next family of the stack
otherwise; the runtime never fetched such a family, and it does not start to.
A survey that wants another web font declares its own ``@font-face`` in
``UIConfig.custom_css``, on a host of its choosing.

A host that serves the survey page some other way (Studio's preview inlines
the stylesheet) passes the URL it serves these files at as
``RuntimeRenderContext.font_base`` and serves them with :func:`font_file`.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources

__all__ = [
    "BUNDLED_FAMILIES",
    "FONT_BASE",
    "FONT_FILES",
    "BundledFamily",
    "bundled_families",
    "font_assets",
    "font_face_css",
    "font_file",
    "stack_families",
]

_PACKAGE = "siamang.frontend.templates.react"
_DIRECTORY = "fonts"

# Where a bundle keeps them, relative to its stylesheet (which is at the root).
FONT_BASE = "fonts/"

# The unicode ranges Google Fonts gives each subset (the same for the three
# families). Declared in Google's order, latin last: where two ranges overlap
# (U+0304, U+0308, U+0329) the face declared last is tried first.
_SUBSETS: tuple[tuple[str, str], ...] = (
    ("cyrillic", "U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116"),
    (
        "latin-ext",
        "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, "
        "U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, "
        "U+2113, U+2C60-2C7F, U+A720-A7FF",
    ),
    (
        "latin",
        "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, "
        "U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, "
        "U+FEFF, U+FFFD",
    ),
)


@dataclass(frozen=True, slots=True)
class BundledFamily:
    """One family shipped with the package.

    ``name`` is the family name the font stacks use; ``weight`` the variable
    font's weight range; ``cut`` which of the Google Fonts variable cuts the
    files are (``"wght"``: the weight axis; ``"opsz"``: weight and optical
    size).
    """

    name: str
    slug: str
    weight: str
    cut: str

    def file(self, subset: str) -> str:
        return f"{self.slug}-{subset}-{self.cut}-normal.woff2"

    @property
    def files(self) -> tuple[str, ...]:
        return tuple(self.file(subset) for subset, _ in _SUBSETS)

    @property
    def license(self) -> str:
        return f"{self.slug}-OFL.txt"


BUNDLED_FAMILIES: tuple[BundledFamily, ...] = (
    # The optical-size cut, as the Google Fonts request it replaces asked for
    # (opsz 8..60): headings get the display drawing, body text the text one.
    BundledFamily("Source Serif 4", "source-serif-4", "200 900", "opsz"),
    BundledFamily("Inter", "inter", "100 900", "wght"),
    BundledFamily("Nunito", "nunito", "200 1000", "wght"),
)

_BY_NAME = {family.name.casefold(): family for family in BUNDLED_FAMILIES}

# Every file :func:`font_file` serves: the woff2 files and the license texts.
FONT_FILES: tuple[str, ...] = tuple(
    name for family in BUNDLED_FAMILIES for name in (*family.files, family.license)
)


def stack_families(stack: str | None) -> list[str]:
    """The family names of a CSS ``font-family`` stack, unquoted, in order."""

    names: list[str] = []
    for part in (stack or "").split(","):
        name = part.strip().strip("\"'").strip()
        if name:
            names.append(name)
    return names


def bundled_families(*stacks: str | None) -> list[BundledFamily]:
    """The bundled families the stacks name (CSS family names are
    case-insensitive), each once, in the order they are first named."""

    found: list[BundledFamily] = []
    for stack in stacks:
        for name in stack_families(stack):
            family = _BY_NAME.get(name.casefold())
            if family is not None and family not in found:
                found.append(family)
    return found


def font_face_css(*stacks: str | None, base: str = FONT_BASE) -> str:
    """``@font-face`` rules for the bundled families the stacks name, their
    files at ``base`` (relative to the stylesheet, or a URL ending in ``/``).
    Empty when the stacks name none."""

    families = bundled_families(*stacks)
    if not families:
        return ""
    rules = [
        "/* Typefaces served with the survey (SIL Open Font License 1.1: see the "
        f"*-OFL.txt beside them) — {', '.join(family.name for family in families)}. */"
    ]
    for family in families:
        for subset, unicode_range in _SUBSETS:
            rules.append(
                "@font-face {\n"
                f'  font-family: "{family.name}";\n'
                "  font-style: normal;\n"
                f"  font-weight: {family.weight};\n"
                "  font-display: swap;\n"
                f'  src: url("{base}{family.file(subset)}") format("woff2");\n'
                f"  unicode-range: {unicode_range};\n"
                "}"
            )
    return "\n".join(rules) + "\n"


def font_file(name: str) -> bytes:
    """One bundled font file or license text, by its file name (one of
    :data:`FONT_FILES`), for a host that serves them itself. Any other name
    is a ``KeyError``."""

    if name not in FONT_FILES:
        raise KeyError(name)
    return resources.files(_PACKAGE).joinpath(f"{_DIRECTORY}/{name}").read_bytes()


def font_assets(css: str) -> dict[str, bytes]:
    """The bundled font files ``css`` references at :data:`FONT_BASE`, with
    the license text of each family among them, keyed by their path in a
    bundle (``fonts/<file>``)."""

    assets: dict[str, bytes] = {}
    for family in BUNDLED_FAMILIES:
        used = [name for name in family.files if f"{FONT_BASE}{name}" in css]
        for name in [*used, family.license] if used else []:
            assets[FONT_BASE + name] = font_file(name)
    return assets
