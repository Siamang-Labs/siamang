"""The formats a theme's tokens may take.

A survey's colors, type sizes, widths and font stacks (:class:`UIConfig`) are
written into its stylesheet as the values of CSS custom properties
(``--siamang-primary: #2c5f8a;``). Written as they are, a value could end the
declaration and the rule and start its own (``red;} body{background:
url(https://…)} :root{``): load anything from anywhere, read the page through
attribute selectors, restyle every page — what ``custom_css`` is for, and
gated as such by a host. So each token has a strict format, checked when the
:class:`UIConfig` is made:

* a **color** is ``#rgb``, ``#rgba``, ``#rrggbb``, ``#rrggbbaa``, ``rgb()``,
  ``rgba()``, ``hsl()``, ``hsla()``, ``hwb()``, ``lab()``, ``lch()``,
  ``oklab()`` or ``oklch()`` of numbers, or a CSS color name
  (``rebeccapurple``, ``transparent``, ``currentColor``, a system color);
* a **length** is a number with a unit (``15.5px``, ``1.1rem``, ``60%``),
  ``0``, ``calc()``, ``min()``, ``max()`` or ``clamp()`` of those, or a CSS-wide
  keyword or sizing keyword (``auto``, ``none``, ``medium``…);
* a **line height** is also a number alone (``1.6``) or ``normal``;
* a **font stack** is family names separated by commas, each a name in
  quotes or unquoted words (``"Source Serif 4", Georgia, serif``).

None of them can hold ``;``, ``{``, ``}``, ``<``, ``>``, ``\\``, ``@`` or a
function other than the color and math functions named — so no ``url()``.
:func:`css_value` is the stylesheet's second line: whatever reaches it that
is not in its format is replaced by the default.
"""

from __future__ import annotations

import re
from collections.abc import Callable

#: CSS Color 4 named colors, ``transparent``, ``currentcolor`` and the system
#: colors, in lower case (CSS keywords are ASCII case-insensitive).
NAMED_COLORS = frozenset(
    """
    aliceblue antiquewhite aqua aquamarine azure beige bisque black
    blanchedalmond blue blueviolet brown burlywood cadetblue chartreuse
    chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan
    darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta
    darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen
    darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink
    deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen
    fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey
    honeydew hotpink indianred indigo ivory khaki lavender lavenderblush
    lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow
    lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen
    lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime
    limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid
    mediumpurple mediumseagreen mediumslateblue mediumspringgreen
    mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin
    navajowhite navy oldlace olive olivedrab orange orangered orchid
    palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff
    peru pink plum powderblue purple rebeccapurple red rosybrown royalblue
    saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue
    slateblue slategray slategrey snow springgreen steelblue tan teal thistle
    tomato turquoise violet wheat white whitesmoke yellow yellowgreen
    transparent currentcolor
    accentcolor accentcolortext activetext buttonborder buttonface buttontext
    canvas canvastext field fieldtext graytext highlight highlighttext linktext
    mark marktext selecteditem selecteditemtext visitedtext
    """.split()  # noqa: SIM905 - one long list, written as words
)

_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
# rgb(0 0 0 / 50%), rgba(0, 0, 0, .5), hsl(210deg 40% 30%), oklch(0.6 0.1 250 / 0.8):
# numbers with a percent sign or an angle unit, `none`, commas and one slash.
_COLOR_ARG = rf"(?:{_NUMBER}(?:%|deg|grad|rad|turn)?|none)"
_COLOR_FUNCTION = re.compile(
    r"^(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(\s*"
    rf"{_COLOR_ARG}(?:\s*,\s*{_COLOR_ARG}|\s+{_COLOR_ARG})*"
    rf"(?:\s*/\s*{_COLOR_ARG})?\s*\)$",
    re.IGNORECASE,
)

_UNITS = (
    "px|em|rem|ex|rex|ch|rch|cap|rcap|ic|ric|lh|rlh|%|vw|vh|vi|vb|vmin|vmax|"
    "svw|svh|lvw|lvh|dvw|dvh|cqw|cqh|cqi|cqb|cqmin|cqmax|cm|mm|q|in|pt|pc"
)
_LENGTH = re.compile(rf"^(?:{_NUMBER}(?:{_UNITS})|[+-]?0+(?:\.0*)?)$", re.IGNORECASE)
_LENGTH_KEYWORDS = frozenset(
    {
        "auto",
        "none",
        "normal",
        "inherit",
        "initial",
        "unset",
        "revert",
        "min-content",
        "max-content",
        "fit-content",
        "xx-small",
        "x-small",
        "small",
        "medium",
        "large",
        "x-large",
        "xx-large",
        "xxx-large",
        "smaller",
        "larger",
    }
)
# Inside calc()/min()/max()/clamp(): lengths and numbers, + - * /, commas,
# parentheses and the math functions themselves — nothing else.
_MATH_FUNCTION = re.compile(r"^(?:calc|min|max|clamp)\(", re.IGNORECASE)
_MATH_TOKEN = re.compile(
    rf"\s*(?:{_NUMBER}(?:{_UNITS})?|(?:calc|min|max|clamp)?\(|\)|[-+*/,])",
    re.IGNORECASE,
)
_PLAIN_NUMBER = re.compile(rf"^{_NUMBER}$")

# A family in quotes: anything but quotes, backslashes, line breaks and the
# characters that end a declaration, a rule or a <style>.
_QUOTED_FAMILY = re.compile(r"""^(?:"[^"'\\;{}<>()@\r\n\f]+"|'[^"'\\;{}<>()@\r\n\f]+')$""")
# Unquoted: identifiers separated by spaces (Segoe UI, -apple-system, system-ui,
# Times New Roman), letters of any script.
_IDENT = r"-?(?:[^\W\d]|_)[\w-]*"
_UNQUOTED_FAMILY = re.compile(rf"^{_IDENT}(?:\s+{_IDENT})*$")
_FORBIDDEN = re.compile(r"[;{}<>\\@]|/\*|\*/")


def color_problem(value: object) -> str | None:
    """Why ``value`` is not a theme color, or None when it is one."""

    if not isinstance(value, str):
        return f"a color is text, got {type(value).__name__}"
    text = value.strip()
    if _HEX.match(text) or _COLOR_FUNCTION.match(text) or text.lower() in NAMED_COLORS:
        return None
    if text.startswith("#"):
        return "a hex color has 3, 4, 6 or 8 hex digits after the #, e.g. #2c5f8a"
    return (
        "not a color: use #rrggbb (e.g. #2c5f8a), rgb(), hsl() or a CSS color name; "
        "nothing else can be written into the stylesheet"
    )


def _math_ok(text: str) -> bool:
    depth = 0
    pos = 0
    while pos < len(text):
        match = _MATH_TOKEN.match(text, pos)
        if not match or match.end() == pos:
            return text[pos:].strip() == "" and depth == 0
        token = match.group(0).strip()
        if token.endswith("("):
            depth += 1
        elif token == ")":
            depth -= 1
            if depth < 0:
                return False
        pos = match.end()
    return depth == 0


def length_problem(value: object, *, unitless: bool = False) -> str | None:
    """Why ``value`` is not a theme length (``unitless``: a line height, which
    may also be a number alone), or None when it is one."""

    if not isinstance(value, str):
        if unitless and isinstance(value, int | float) and not isinstance(value, bool):
            return None
        return f"a length is text, got {type(value).__name__}"
    text = value.strip()
    if _LENGTH.match(text) or text.lower() in _LENGTH_KEYWORDS:
        return None
    if unitless and _PLAIN_NUMBER.match(text):
        return None
    if _MATH_FUNCTION.match(text) and _math_ok(text):
        return None
    if _PLAIN_NUMBER.match(text):
        return f"{text} is a number without a unit: write {text}px (or rem, em, %)"
    return (
        "not a length: a number with a unit (e.g. 16px, 1.1rem, 60%), "
        "calc(), min(), max() or clamp() of those" + (", or a number alone" if unitless else "")
    )


def font_stack_problem(value: object) -> str | None:
    """Why ``value`` is not a font stack, or None when it is one."""

    if not isinstance(value, str):
        return f"a font stack is text, got {type(value).__name__}"
    if _FORBIDDEN.search(value) or "(" in value or ")" in value:
        return (
            "a font stack is family names separated by commas, e.g. "
            '"Source Serif 4", Georgia, serif — no ; { } < > ( ) \\ @ or url()'
        )
    families = [part.strip() for part in value.split(",")]
    if not families or any(not family for family in families):
        return "a font stack names at least one family, separated by commas"
    for family in families:
        if not (_QUOTED_FAMILY.match(family) or _UNQUOTED_FAMILY.match(family)):
            return (
                f"{family!r} is not a family name: put a name with digits or "
                'punctuation in quotes, e.g. "Source Serif 4"'
            )
    return None


#: How each kind of token is checked.
CHECKS: dict[str, Callable[[object], str | None]] = {
    "color": color_problem,
    "length": length_problem,
    "line_height": lambda value: length_problem(value, unitless=True),
    "font": font_stack_problem,
}


def css_value(value: object, kind: str, default: str) -> str:
    """``value`` as written into a stylesheet: itself when it is in the
    format of ``kind`` (a key of :data:`CHECKS`), else ``default``."""

    if value is None or CHECKS[kind](value) is not None:
        return default
    return str(value).strip()


def css_text(css: str) -> str:
    """A stylesheet that can be inlined in a ``<style>`` element: ``</``
    written ``<\\/`` (a backslash escape CSS reads as the ``/`` itself, in a
    string, a ``url()`` or a comment alike), so no ``</style`` in a custom
    stylesheet or anywhere else can end the element."""

    return css.replace("</", "<\\/")
