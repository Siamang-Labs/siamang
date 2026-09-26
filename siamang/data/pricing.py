"""Price sensitivity: what respondents would pay — Van Westendorp and Gabor-Granger.

Two question designs, one node (``analyze.price``, Price sensitivity):

**Van Westendorp's price sensitivity meter** (Van Westendorp 1976). Each
respondent names four prices: at what price the product would be *so cheap*
that they would doubt its quality (too cheap), *a bargain* (cheap), *getting
expensive* (expensive) and *so expensive* that they would not consider it (too
expensive). :func:`van_westendorp` turns the answers into cumulative curves and
reads four price points where they cross.

- **Who counts.** Respondents who answered all four (the codebook's missing
  codes count as not answered) and whose prices are in order, too cheap ≤
  cheap ≤ expensive ≤ too expensive. Answers out of that order are a
  misunderstood question, not a price; those respondents are dropped and
  counted (``Inconsistent``), as R's ``pricesensitivitymeter`` does with
  ``validate = TRUE``. A negative price is refused.
- **The curves**, at each price p named by anyone (the *price grid*), as
  shares of the (weighted) respondents: *too cheap* — too-cheap price ≥ p;
  *cheap* — cheap price ≥ p, and *not cheap* = 100 % − cheap (cheap price < p);
  *expensive* — expensive price ≤ p, and *not expensive* = 100 % − expensive;
  *too expensive* — too-expensive price ≤ p. Between two prices of the grid a
  curve is the straight line joining them, as the curves are drawn.
- **The points** are where two of those lines cross: the *point of marginal
  cheapness* (PMC) where too cheap meets not cheap; the *optimal price point*
  (OPP) where too cheap meets too expensive; the *indifference price point*
  (IPP) where not cheap meets not expensive (the same price at which cheap
  meets expensive); the *point of marginal expensiveness* (PME) where not
  expensive meets too expensive. PMC to PME is the *range of acceptable
  prices*. In each pair one curve falls and the other rises, so their
  difference only falls: it is zero on one price, or on an interval of prices
  when the lines run together — then the point is that interval's middle. When
  the lines do not meet within the prices named, the point is not given and
  the statistics say which curve lies above the other throughout.
- **Newton-Miller-Smith** (Newton, Miller & Smith 1993), when the survey also
  asked how likely the respondent would be to buy at their *cheap* and at their
  *expensive* price (the whole analysis is then of the respondents who answered
  those too, so the points and the trial curve share one base): each answer
  becomes a probability by ``calibration`` (by
  default the usual five-point one: 5 → 0.7, 4 → 0.5, 3 → 0.3, 2 → 0.1,
  1 → 0), and each respondent's purchase probability is 0 below their
  too-cheap price and above their too-expensive price, 0 *at* them (unless the
  cheap or expensive price is the same), the stated probability at their cheap
  and expensive prices (their mean where the two prices are equal), and the
  straight line between. The mean over the respondents is the *trial* curve,
  and price × trial the *revenue* per respondent; the prices of the grid with
  the highest of each are reported.

**Gabor-Granger** (Gabor & Granger 1966). Each respondent says whether they
would buy at each of a set of prices — a variable per price. :func:`gabor_granger`
gives the demand at each price (the weighted share saying yes, by ``yes``
codes: 1 for 0/1 variables, or a top-two box of a likelihood scale), the
revenue per respondent (price × demand) with an index (the highest = 100), the
arc elasticity between neighbouring prices, and the revenue-maximising price
among those asked. A respondent missing any price is left out (a sequential
design that skips prices after a yes or a no should fill in the implied
answers first); one who would buy at a higher price but not at a lower one is
counted (``Not monotone``) and kept as answered.

**Weights.** Every share is a share of the weights (a missing weight counts 0);
N stays the number of respondents. :func:`plot` draws the curves with the price
points, or the demand and revenue curves.
"""

from __future__ import annotations

import textwrap
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.data.listwise import distinct, label_of, listwise, rounded
from siamang.reporting.result_table import ResultTable

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData

METHODS = ("van_westendorp", "gabor_granger")
#: The usual five-point calibration of a purchase likelihood (Newton, Miller &
#: Smith): definitely would buy … definitely would not.
CALIBRATION = {5: 0.7, 4: 0.5, 3: 0.3, 2: 0.1, 1: 0.0}

#: The four price points: key, name, and the curves that meet there.
POINTS = (
    ("PMC", "Point of marginal cheapness", "too cheap = not cheap"),
    ("OPP", "Optimal price point", "too cheap = too expensive"),
    ("IPP", "Indifference price point", "not cheap = not expensive"),
    ("PME", "Point of marginal expensiveness", "not expensive = too expensive"),
)
_CURVES_OF = {
    "PMC": ("too_cheap", "not_cheap"),
    "OPP": ("too_cheap", "too_expensive"),
    "IPP": ("not_expensive", "not_cheap"),
    "PME": ("not_expensive", "too_expensive"),
}
CURVE_NAMES = {
    "too_cheap": "Too cheap",
    "cheap": "Cheap",
    "not_cheap": "Not cheap",
    "expensive": "Expensive",
    "not_expensive": "Not expensive",
    "too_expensive": "Too expensive",
}

#: The chart's colours: cheapness in blue, expensiveness in orange (a pair
#: distinguishable with every common colour-vision deficiency); "too" solid,
#: "not" dashed.
CHEAP_COLOUR, EXPENSIVE_COLOUR = "#2a78d6", "#eb6834"
_INK, _MUTED, _RULE, _BAND = "#333333", "#767676", "#bdbdbd", "#efefef"


@dataclass
class PriceTable(ResultTable):
    """A price sensitivity table; ``analysis`` is the whole result, which a chart draws."""

    analysis: PriceSensitivity | None = None


@dataclass(frozen=True, slots=True)
class PriceSensitivity:
    """What :func:`van_westendorp` or :func:`gabor_granger` found.

    ``table`` holds the price points (Van Westendorp) or the demand at each
    price (Gabor-Granger), ``curves`` the curves at every price of the grid,
    ``stats`` the statistics; ``prices`` and ``shares`` (curve → % at each
    price) are the numbers the chart draws, ``points`` the prices found.
    """

    method: str
    table: PriceTable
    curves: PriceTable
    stats: dict[str, Any]
    prices: np.ndarray
    shares: dict[str, np.ndarray]
    points: dict[str, float | None]
    n: int
    weight: str | None = None
    notes: list[str] = field(default_factory=list)


# ── array level ──────────────────────────────────────────────────────────────


def curves(
    too_cheap: Any,
    cheap: Any,
    expensive: Any,
    too_expensive: Any,
    weights: Any = None,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """The price grid and the six Van Westendorp curves on it, in % of the
    (weighted) respondents. The answers are taken as they are (consistent)."""

    answers = [np.asarray(values, dtype=float) for values in (too_cheap, cheap, expensive,
                                                               too_expensive)]  # fmt: skip
    w = np.ones(len(answers[0])) if weights is None else np.asarray(weights, dtype=float)
    total = float(w.sum())
    grid = np.unique(np.concatenate(answers))
    tc, ch, ex, te = answers

    def share(mask: np.ndarray) -> np.ndarray:
        return (mask * w[None, :]).sum(axis=1) / total * 100

    shares = {
        "too_cheap": share(tc[None, :] >= grid[:, None]),
        "cheap": share(ch[None, :] >= grid[:, None]),
        "expensive": share(ex[None, :] <= grid[:, None]),
        "too_expensive": share(te[None, :] <= grid[:, None]),
    }
    shares["not_cheap"] = 100 - shares["cheap"]
    shares["not_expensive"] = 100 - shares["expensive"]
    return grid, shares


def intersection(
    prices: Any, falling: Any, rising: Any
) -> tuple[float | None, float | None, str | None]:
    """Where the line through ``falling`` meets the line through ``rising``.

    Both are given at ``prices`` (increasing) and joined by straight lines; the
    first never rises and the second never falls, so their difference only
    falls. Returns the price where it is zero — the middle of the prices where
    it is, when the lines run together — and the curves' value there; or None,
    None and ``"above"`` / ``"below"`` when ``falling`` stays above (below)
    ``rising`` over all the prices.
    """

    p = np.asarray(prices, dtype=float)
    d = np.asarray(falling, dtype=float) - np.asarray(rising, dtype=float)
    if len(p) == 0:
        return None, None, None
    if d[0] < 0:
        return None, None, "below"
    if d[-1] > 0:
        return None, None, "above"
    first = int(np.argmax(d <= 0))  # the first price where the difference is 0 or less
    if d[first] == 0 or first == 0:
        start = float(p[first])
    else:
        start = float(
            p[first - 1] + (p[first] - p[first - 1]) * d[first - 1] / (d[first - 1] - d[first])
        )
    last = len(d) - 1 - int(np.argmax(d[::-1] >= 0))  # the last where it is 0 or more
    if d[last] == 0 or last == len(d) - 1:
        end = float(p[last])
    else:
        end = float(p[last] + (p[last + 1] - p[last]) * d[last] / (d[last] - d[last + 1]))
    price = (start + end) / 2
    value = float(np.interp(price, p, np.asarray(falling, dtype=float)))
    return price, value, None


def trial(
    too_cheap: Any,
    cheap: Any,
    expensive: Any,
    too_expensive: Any,
    at_cheap: Any,
    at_expensive: Any,
    prices: Any,
    weights: Any = None,
) -> np.ndarray:
    """The Newton-Miller-Smith trial curve at ``prices``, in %: the (weighted)
    mean of each respondent's purchase probability, which is ``at_cheap`` at
    their cheap price, ``at_expensive`` at their expensive price, 0 at and
    beyond their too-cheap and too-expensive prices, and linear between."""

    tc, ch, ex, te, pc, pe = (
        np.asarray(values, dtype=float)
        for values in (too_cheap, cheap, expensive, too_expensive, at_cheap, at_expensive)
    )
    grid = np.asarray(prices, dtype=float)
    w = np.ones(len(tc)) if weights is None else np.asarray(weights, dtype=float)
    total = np.zeros(len(grid))
    for i in range(len(tc)):
        knots: dict[float, list[float]] = {}
        for price, value, stated in (
            (tc[i], 0.0, False),
            (ch[i], pc[i], True),
            (ex[i], pe[i], True),
            (te[i], 0.0, False),
        ):
            knots.setdefault(float(price), []).append(value if stated else np.nan)
        xs = sorted(knots)
        ys = []
        for x in xs:
            stated = [v for v in knots[x] if not np.isnan(v)]
            # A price that is also the cheap or expensive one carries the stated
            # probability (their mean when both), not the implied 0.
            ys.append(float(np.mean(stated)) if stated else 0.0)
        curve = np.interp(grid, xs, ys, left=0.0, right=0.0)
        total += w[i] * curve
    return total / float(w.sum()) * 100


# ── on survey data ───────────────────────────────────────────────────────────


def price_problem(params: dict[str, Any]) -> str | None:
    """What the node's parameters settle before any data, or None: the prices
    of a Gabor-Granger design against its questions, and four different
    Van Westendorp questions — what the run would refuse, in its words."""

    method = params.get("method")
    if method == "gabor_granger":
        intent = params.get("intent")
        prices = params.get("price_points")
        if isinstance(intent, list) and intent and prices not in (None, "", []):
            return _prices_problem(prices, len(intent))
    if method == "van_westendorp":
        names = [params.get(key) for key in ("too_cheap", "cheap", "expensive", "too_expensive")]
        named = [name for name in names if isinstance(name, str) and name]
        twice = [name for name in dict.fromkeys(named) if named.count(name) > 1]
        if twice:
            return (
                f"{', '.join(twice)} answers more than one of the four price questions; "
                "each is its own variable."
            )
    return None


def _prices_problem(prices: Any, count: int) -> str | None:
    if not isinstance(prices, list | tuple):
        return "Prices is a list of numbers, one per purchase-intent question, e.g. [5, 7.5, 10]."
    if not all(isinstance(value, int | float) and not isinstance(value, bool) for value in prices):
        return "Prices must all be numbers, one per purchase-intent question."
    if len(prices) != count:
        return (
            f"Prices lists {len(prices)} {'price' if len(prices) == 1 else 'prices'} for "
            f"{count} purchase-intent {'question' if count == 1 else 'questions'}; give one "
            "price per question, in the same order."
        )
    if count < 2:
        return "A Gabor-Granger demand curve needs two or more prices."
    if len(set(prices)) != len(prices):
        return "Each price can be asked once; Prices lists one twice."
    if any(value < 0 for value in prices):
        return "Prices cannot be negative."
    return None


def van_westendorp(
    data: SurveyData,
    *,
    too_cheap: str,
    cheap: str,
    expensive: str,
    too_expensive: str,
    likelihood_cheap: str | None = None,
    likelihood_expensive: str | None = None,
    calibration: dict[Any, float] | None = None,
) -> PriceSensitivity:
    """Van Westendorp's price sensitivity meter from the four price questions,
    with the Newton-Miller-Smith trial and revenue curves when the two
    purchase-likelihood questions are given. See the module's docstring."""

    questions = [too_cheap, cheap, expensive, too_expensive]
    if any(not name for name in questions):
        raise ValueError(
            "Van Westendorp needs all four price questions: too cheap, cheap, expensive "
            "and too expensive."
        )
    nms = [name for name in (likelihood_cheap, likelihood_expensive) if name]
    if len(nms) == 1:
        raise ValueError(
            "Newton-Miller-Smith needs both likelihood questions — at the cheap and at the "
            "expensive price — or neither."
        )
    columns = [*questions, *nms]
    distinct(columns)
    rows = listwise(data, columns)
    values = rows.frame[questions].to_numpy(dtype=float)
    if np.any(values < 0):
        raise ValueError("A price cannot be negative; check the price questions' answers.")
    weights = _weights(data, rows.mask)
    ordered = np.all(np.diff(values, axis=1) >= 0, axis=1)
    inconsistent = int((~ordered).sum())
    values = values[ordered]
    w = weights[ordered] if weights is not None else None
    n = int(len(values))
    stats: dict[str, Any] = {"Method": "Van Westendorp price sensitivity meter", "N": n}
    stats["Inconsistent"] = inconsistent
    if inconsistent:
        stats["Inconsistent because"] = (
            "their prices are not in the order too cheap ≤ cheap ≤ expensive ≤ too expensive; "
            "left out"
        )
    if n == 0 or (w is not None and w.sum() <= 0):
        raise ValueError(
            "No respondent answered all four price questions in order (too cheap ≤ cheap ≤ "
            f"expensive ≤ too expensive): {rows.n} answered all four, {inconsistent} of them "
            "out of order."
        )
    grid, shares = curves(*values.T, weights=w)
    points: dict[str, float | None] = {}
    point_rows = []
    notes = []
    for key, name, meet in POINTS:
        falling, rising = _CURVES_OF[key]
        price, value, side = intersection(grid, shares[falling], shares[rising])
        points[key] = price
        point_rows.append(
            {
                "Point": f"{name} ({key})",
                "Price": rounded(price, 2),
                "Share %": rounded(value, 1),
                "Where": meet,
            }
        )
        if price is None and side is not None:
            first, second = meet.split(" = ")
            notes.append(
                f"{key}: {first} stays {side} {second} at every price named, so they do not meet"
            )
        stats[key] = rounded(price, 2)
    if points["PMC"] is not None and points["PME"] is not None:
        stats["Range of acceptable prices"] = f"{_price(points['PMC'])} – {_price(points['PME'])}"
    frame = pd.DataFrame(
        {
            "Price": [_number(p) for p in grid],
            **{
                f"{CURVE_NAMES[key]} %": [rounded(v, 1) for v in shares[key]]
                for key in ("too_cheap", "cheap", "not_cheap", "expensive", "not_expensive",
                            "too_expensive")
            },
        }
    )  # fmt: skip
    if nms:
        mapping = _calibration(calibration)
        likelihood = rows.frame[nms].to_numpy(dtype=float)[ordered]
        unknown = sorted({_number(v) for v in likelihood.ravel() if _number(v) not in mapping})
        if unknown:
            raise ValueError(
                f"The likelihood answers include {', '.join(map(str, unknown[:6]))}, which the "
                f"calibration does not turn into a probability ({_calibration_text(mapping)}); "
                "give Calibration a probability for each answer code."
            )
        at_cheap = np.array([mapping[_number(v)] for v in likelihood[:, 0]])
        at_expensive = np.array([mapping[_number(v)] for v in likelihood[:, 1]])
        trial_curve = trial(*values.T, at_cheap, at_expensive, grid, weights=w)
        revenue = grid * trial_curve / 100
        shares["trial"] = trial_curve
        shares["revenue"] = revenue
        frame["Trial %"] = [rounded(v, 1) for v in trial_curve]
        frame["Revenue per respondent"] = [rounded(v, 2) for v in revenue]
        best_trial = int(np.argmax(trial_curve))
        best_revenue = int(np.argmax(revenue))
        points["trial"] = float(grid[best_trial])
        points["revenue"] = float(grid[best_revenue])
        point_rows.append(
            {
                "Point": "Highest trial (NMS)",
                "Price": _number(grid[best_trial]),
                "Share %": rounded(trial_curve[best_trial], 1),
                "Where": "the highest mean purchase probability",
            }
        )
        point_rows.append(
            {
                "Point": "Highest revenue (NMS)",
                "Price": _number(grid[best_revenue]),
                "Share %": rounded(trial_curve[best_revenue], 1),
                "Where": "the highest price × trial",
            }
        )
        stats["Highest trial (NMS)"] = _number(grid[best_trial])
        stats["Trial % at it"] = rounded(trial_curve[best_trial], 1)
        stats["Highest revenue (NMS)"] = _number(grid[best_revenue])
        stats["Revenue per respondent at it"] = rounded(revenue[best_revenue], 2)
        stats["Calibration"] = _calibration_text(mapping)
    if notes:
        stats["Note"] = "; ".join(notes)
    _weight_stats(stats, data, w)
    rows.report(
        stats, "any of the price or likelihood questions" if nms else "any of the price questions"
    )
    footer = {key: stats[key] for key in ("Method", "N") if key in stats}
    footer["Curves"] = "% of the respondents at each price named"
    if data.weight is not None:
        footer["Weight"] = data.weight
    result = PriceSensitivity(
        method="van_westendorp",
        table=PriceTable(data=data, frame=pd.DataFrame(point_rows), footer=dict(stats)),
        curves=PriceTable(data=data, frame=frame, footer=footer),
        stats=stats,
        prices=grid,
        shares=shares,
        points=points,
        n=n,
        weight=data.weight,
        notes=notes,
    )
    result.table.analysis = result
    result.curves.analysis = result
    return result


def gabor_granger(
    data: SurveyData,
    intent: list[str],
    *,
    prices: Sequence[float],
    yes: Any = None,
) -> PriceSensitivity:
    """Gabor-Granger: the demand at each of ``prices`` from the purchase-intent
    questions ``intent`` (one per price, in the same order), yes by the codes
    ``yes`` (empty: 1 for 0/1 variables). See the module's docstring."""

    intent = list(intent or [])
    if isinstance(prices, np.ndarray):
        prices = prices.tolist()
    problem = _prices_problem(prices, len(intent))
    if problem:
        raise ValueError(problem)
    distinct(intent)
    rows = listwise(data, intent, numeric=False)
    order = np.argsort(np.asarray(prices, dtype=float), kind="stable")
    grid = np.asarray(prices, dtype=float)[order]
    questions = [intent[i] for i in order]
    codes = _yes_codes(data, rows.frame, questions, yes)
    said = np.column_stack(
        [rows.frame[name].isin(codes).to_numpy(dtype=bool) for name in questions]
    ) if rows.n else np.zeros((0, len(questions)), dtype=bool)  # fmt: skip
    weights = _weights(data, rows.mask)
    n = rows.n
    if n == 0 or (weights is not None and weights.sum() <= 0):
        raise ValueError("No respondent answered every purchase-intent question.")
    w = weights if weights is not None else np.ones(n)
    demand = (said * w[:, None]).sum(axis=0) / w.sum() * 100
    revenue = grid * demand / 100
    best = int(np.argmax(revenue))
    top = float(revenue[best])
    index = revenue / top * 100 if top > 0 else np.zeros(len(grid))
    elasticity: list[float | None] = [None]
    for k in range(1, len(grid)):
        q0, q1 = demand[k - 1], demand[k]
        if q0 + q1 == 0:
            elasticity.append(None)
            continue
        change_q = (q1 - q0) / ((q1 + q0) / 2)
        change_p = (grid[k] - grid[k - 1]) / ((grid[k] + grid[k - 1]) / 2)
        elasticity.append(rounded(change_q / change_p, 2))
    # A respondent who would buy at a higher price but not at a lower one.
    not_monotone = int(np.any(said[:, 1:] & ~said[:, :-1], axis=1).sum())
    frame = pd.DataFrame(
        {
            "Price": [_number(p) for p in grid],
            "Question": [label_of(data, name) for name in questions],
            "Would buy %": [rounded(v, 1) for v in demand],
            "Revenue per respondent": [rounded(v, 2) for v in revenue],
            "Revenue index": [rounded(v, 1) for v in index],
            "Elasticity": elasticity,
        }
    )
    stats: dict[str, Any] = {
        "Method": "Gabor-Granger",
        "Counts as yes": _codes_text(data, questions, codes),
        "Prices": len(grid),
        "N": n,
        "Revenue-maximising price": _number(grid[best]),
        "Would buy % at it": rounded(demand[best], 1),
        "Revenue per respondent at it": rounded(revenue[best], 2),
    }
    if top <= 0:
        stats["Note"] = "no respondent would buy at any price asked, so there is no revenue"
    stats["Not monotone"] = not_monotone
    if not_monotone:
        stats["Not monotone because"] = (
            "they would buy at a higher price but not at a lower one; their answers are used "
            "as given"
        )
    stats["Elasticity"] = "arc elasticity from the price before"
    _weight_stats(stats, data, weights)
    rows.report(stats, "any of the purchase-intent questions")
    table = PriceTable(data=data, frame=frame, footer=dict(stats))
    curves_table = PriceTable(data=data, frame=frame.copy(), footer=dict(stats))
    result = PriceSensitivity(
        method="gabor_granger",
        table=table,
        curves=curves_table,
        stats=stats,
        prices=grid,
        shares={"demand": demand, "revenue": revenue},
        points={"revenue": float(grid[best])},
        n=n,
        weight=data.weight,
    )
    table.analysis = result
    curves_table.analysis = result
    return result


def _weights(data: SurveyData, mask: np.ndarray | None) -> np.ndarray | None:
    if data.weight is None:
        return None
    if data.weight not in data.frame.columns:
        raise KeyError(f"column not found: {data.weight!r}")
    values = pd.to_numeric(data.frame[data.weight], errors="coerce").fillna(0.0)
    values = values.to_numpy(dtype=float)
    if mask is not None:
        values = values[mask]
    if np.any(values < 0):
        raise ValueError(f"The weight column {data.weight!r} has negative values.")
    return values


def _weight_stats(stats: dict[str, Any], data: SurveyData, weights: np.ndarray | None) -> None:
    if data.weight is None or weights is None:
        return
    stats["Weight"] = data.weight
    stats["Weighted N"] = rounded(float(weights.sum()), 1)


def _number(value: Any) -> Any:
    value = float(value)
    return int(value) if value.is_integer() else value


def _price(value: float) -> str:
    return (
        f"{value:.2f}".rstrip("0").rstrip(".") if not float(value).is_integer() else f"{value:.0f}"
    )


def _calibration(calibration: dict[Any, float] | None) -> dict[Any, float]:
    if not calibration:
        return dict(CALIBRATION)
    mapping: dict[Any, float] = {}
    for code, probability in calibration.items():
        key = _number(code) if _is_number(code) else code
        value = float(probability)
        if not 0 <= value <= 1:
            raise ValueError(
                f"Calibration turns {code} into {probability}; a probability is between 0 and 1."
            )
        mapping[key] = value
    return mapping


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _calibration_text(mapping: dict[Any, float]) -> str:
    return ", ".join(f"{code} → {value:g}" for code, value in sorted(mapping.items(),
                                                                       reverse=True))  # fmt: skip


def _yes_codes(data: SurveyData, frame: pd.DataFrame, names: list[str], yes: Any) -> list[Any]:
    if yes is not None and yes != [] and yes != "":
        return list(yes) if isinstance(yes, list | tuple | set) else [yes]
    values: set[Any] = set()
    for name in names:
        values.update(_number(v) if _is_number(v) else v for v in frame[name].tolist())
    if values <= {0, 1}:
        return [1]
    shown = ", ".join(str(v) for v in sorted(values, key=lambda v: (str(type(v)), v))[:8])
    raise ValueError(
        f"Gabor-Granger needs to know which answer means would buy: the questions hold "
        f"{shown}. Name that code (or a list of codes, such as a top-two box) in Counts as yes "
        "— `yes` outside a flow."
    )


def _codes_text(data: SurveyData, names: list[str], codes: list[Any]) -> str:
    texts = []
    for code in codes:
        label = next(
            (
                str(data.variables[name].labels[code])
                for name in names
                if data.variables is not None
                and name in data.variables
                and code in (data.variables[name].labels or {})
            ),
            None,
        )
        texts.append(f"{code} = {label}" if label else str(code))
    return ", ".join(texts)


# ── the chart ────────────────────────────────────────────────────────────────


def plot(
    result: PriceSensitivity,
    *,
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
) -> Any:
    """The chart of ``result``: for Van Westendorp the four curves (too cheap
    and not cheap in blue, not expensive and too expensive in orange; "too"
    solid, "not" dashed, named in a legend), the four points marked on them and
    named above the plot at their prices, and the range of acceptable prices
    shaded — and below it, when the NMS questions were asked, the trial curve
    with its highest trial and highest revenue; for Gabor-Granger the demand
    curve above the revenue per respondent, the best price marked on both. Two
    measures are never drawn on two scales of one axis: each gets its panel,
    sharing the price axis. Returns the matplotlib Figure."""

    from matplotlib.figure import Figure

    width = figsize[0] if figsize else 10.0
    nms = "trial" in result.shares
    panels = 2 if result.method == "gabor_granger" or nms else 1
    height = figsize[1] if figsize else (6.0 if panels == 1 else 8.5)
    fig = Figure(figsize=(width, height))
    if panels == 1:
        axes = [fig.add_subplot(1, 1, 1)]
    else:
        axes = list(fig.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": (3, 2)}))
    legend = result.method == "van_westendorp"
    if legend:
        _draw_van_westendorp(result, axes[0], fig)
        heading = title or "Price sensitivity (Van Westendorp)"
        if nms:
            _draw_trial(result, axes[1])
    else:
        _draw_gabor_granger(result, axes)
        heading = title or "Price sensitivity (Gabor-Granger)"
    for ax in axes:
        _style(ax)
    if panels == 2:
        axes[0].set_xlabel("")
        axes[0].tick_params(labelbottom=False)
    lines = [textwrap.fill(heading, max(int(width * 0.85 * 72 / (12 * 0.55)), 30))]
    lines.append(f"N = {result.n}")
    if result.weight:
        lines[-1] += f", weighted by '{result.weight}'"
    axes[0].set_title("\n".join(lines), fontsize=12, color=_INK, loc="left", pad=12)
    if legend:
        # Under the whole figure, where no curve runs.
        fig.legend(
            *axes[0].get_legend_handles_labels(),
            loc="lower center", ncol=4, frameon=False, fontsize=9,
        )  # fmt: skip
    fig.tight_layout(rect=(0, 0.05 if legend else 0, 1, 1))
    if legend:
        _label_points(result, axes, fig)
    return fig


def _style(ax: Any) -> None:
    ax.grid(axis="y", color="#e6e6e6", linewidth=0.8)
    ax.grid(axis="x", visible=False)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(_RULE)
    ax.tick_params(labelsize=9, colors=_INK)


_LINES = (
    ("too_cheap", CHEAP_COLOUR, "-"),
    ("not_cheap", CHEAP_COLOUR, "--"),
    ("not_expensive", EXPENSIVE_COLOUR, "--"),
    ("too_expensive", EXPENSIVE_COLOUR, "-"),
)


def _draw_van_westendorp(result: PriceSensitivity, ax: Any, fig: Any) -> None:
    prices = result.prices
    low, high = result.points.get("PMC"), result.points.get("PME")
    if low is not None and high is not None:
        ax.axvspan(low, high, color=_BAND, zorder=0, linewidth=0)
    for key, colour, style in _LINES:
        ax.plot(
            prices, result.shares[key], color=colour, linestyle=style, linewidth=2,
            label=CURVE_NAMES[key], zorder=2,
        )  # fmt: skip
    ax.set_ylim(0, 108)
    span = float(prices.max() - prices.min()) or 1.0
    ax.set_xlim(float(prices.min()) - 0.02 * span, float(prices.max()) + 0.02 * span)
    ax.set_ylabel("% of respondents", fontsize=10, color=_INK)
    ax.set_xlabel("Price", fontsize=10, color=_INK)
    for key, _, _ in POINTS:
        price = result.points.get(key)
        if price is None:
            continue
        falling = _CURVES_OF[key][0]
        value = float(np.interp(price, prices, result.shares[falling]))
        ax.plot([price, price], [0, value], color=_MUTED, linewidth=0.8, zorder=1)
        ax.scatter([price], [value], s=36, color=_INK, zorder=4, edgecolor="white", linewidth=1)


def _label_points(result: PriceSensitivity, axes: list[Any], fig: Any) -> None:
    """Name the price points above their panel at their prices: the four
    Van Westendorp points, and with NMS the highest trial and revenue."""

    items = [
        (price, f"{key} {_price(price)}")
        for key, _, _ in POINTS
        if (price := result.points.get(key)) is not None
    ]
    _stacked(axes[0], fig, items, 104, 6)
    if len(axes) > 1 and "trial" in result.shares:
        top = axes[1].get_ylim()[1]
        items = [
            (price, f"{name} {_price(price)}")
            for key, name in (("trial", "highest trial"), ("revenue", "highest revenue"))
            if (price := result.points.get(key)) is not None
        ]
        _stacked(axes[1], fig, items, top * 0.93, top * 0.1)


def _stacked(ax: Any, fig: Any, items: list[tuple[float, str]], y: float, step: float) -> None:
    """Write each text centred at its price at height ``y``, one ``step`` lower
    for each text it would otherwise touch."""

    if not hasattr(fig.canvas, "get_renderer"):
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        FigureCanvasAgg(fig)
    renderer = fig.canvas.get_renderer()
    fig.canvas.draw()
    placed: list[tuple[float, float, int]] = []
    for price, text in items:
        label = ax.text(price, y, text, fontsize=9, color=_INK, ha="center", va="center")
        width = label.get_window_extent(renderer).width
        centre = float(ax.transData.transform((price, 0))[0])
        level = 0
        while any(
            level == other_level and abs(centre - other) < (width + other_width) / 2 + 6
            for other, other_width, other_level in placed
        ):
            level += 1
        placed.append((centre, width, level))
        label.set_y(y - step * level)
        label.set_bbox({"facecolor": "white", "edgecolor": "none", "pad": 1.5})


def _draw_trial(result: PriceSensitivity, ax: Any) -> None:
    prices = result.prices
    trial_curve = result.shares["trial"]
    ax.plot(prices, trial_curve, color=_INK, linewidth=2, label="Trial (NMS)")
    top = max(float(trial_curve.max()) if len(prices) else 1.0, 1.0)
    ax.set_ylim(0, top * 1.4)
    for key, marker in (("trial", "o"), ("revenue", "D")):
        price = result.points.get(key)
        if price is None:
            continue
        value = float(np.interp(price, prices, trial_curve))
        ax.plot([price, price], [value, top * 1.3], color=_MUTED, linewidth=0.8, zorder=1)
        ax.scatter([price], [value], s=40, marker=marker, color=_INK, zorder=4)
    ax.set_ylabel("Trial (% would buy)", fontsize=10, color=_INK)
    ax.set_xlabel("Price", fontsize=10, color=_INK)


def _draw_gabor_granger(result: PriceSensitivity, axes: list[Any]) -> None:
    prices = result.prices
    demand, revenue = result.shares["demand"], result.shares["revenue"]
    best = result.points["revenue"]
    top_ax, bottom_ax = axes
    top_ax.plot(prices, demand, color=CHEAP_COLOUR, linewidth=2, marker="o", markersize=6)
    for price, value in zip(prices, demand, strict=True):
        top_ax.annotate(
            f"{value:.0f} %", (price, value), xytext=(0, 8), textcoords="offset points",
            ha="center", fontsize=9, color=_INK,
        )  # fmt: skip
    top_ax.set_ylim(0, max(float(demand.max()) * 1.2, 10.0))
    top_ax.set_ylabel("Would buy (%)", fontsize=10, color=_INK)
    step = float(np.min(np.diff(prices))) if len(prices) > 1 else 1.0
    colours = [EXPENSIVE_COLOUR if price == best else "#f5b48f" for price in prices]
    bottom_ax.bar(prices, revenue, width=step * 0.6, color=colours, edgecolor="white")
    for price, value in zip(prices, revenue, strict=True):
        bottom_ax.annotate(
            f"{value:.2f}", (price, value), xytext=(0, 4), textcoords="offset points",
            ha="center", fontsize=9, color=_INK,
        )  # fmt: skip
    bottom_ax.set_ylim(0, max(float(revenue.max()) * 1.25, 1e-9))
    bottom_ax.set_ylabel("Revenue per respondent", fontsize=10, color=_INK)
    bottom_ax.set_xlabel("Price", fontsize=10, color=_INK)
    bottom_ax.set_xticks(prices)
    bottom_ax.set_xticklabels([_price(p) for p in prices])
    top_ax.axvline(best, color=_MUTED, linewidth=0.8, zorder=0)
    top_ax.annotate(
        f"highest revenue at {_price(best)}", (best, 0), xytext=(4, 4),
        textcoords="offset points", fontsize=9, color=_INK,
    )  # fmt: skip


__all__ = [
    "CALIBRATION",
    "CURVE_NAMES",
    "METHODS",
    "POINTS",
    "PriceSensitivity",
    "PriceTable",
    "curves",
    "gabor_granger",
    "intersection",
    "plot",
    "price_problem",
    "trial",
    "van_westendorp",
]
