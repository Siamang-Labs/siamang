"""Likert chart: a battery of items on one ordered scale as diverging bars.

Each item is one bar. Its answers below the middle of the scale stack to the
left of a centre line, those above it to the right, so an item's lean is its
bar's position and a battery reads at a glance. The middle is the neutral
answer of an odd scale (``neutral="split"`` draws it half on either side of the
centre, ``"side"`` apart in a panel of its own at the right) or, on an even
scale, the line between the two middle answers. The shares of the two answers
at either end — the top-2 and bottom-2 boxes, one answer each on a scale of two
or three — are written at the ends of every bar, and ``sort="top2"`` puts the
item with the largest top-2 share first.

The scale is the codebook's: the items' value labels with their missing codes
left out, which must be the same for every item — a chart that put "Agree" of
one item beside "Satisfied" of another would read as one scale and not be
one, so it is refused and the message names both. Answers with a missing code
(a 9 "Don't know") and answers not on the scale are left out of the bars and
counted under the chart, with each item's base. On weighted data the shares
are sums of weights (a Frequencies table's weighted percentages of each item).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from siamang.reporting.chart_parts import (
    VALUE_SIZE,
    Footnote,
    axes_points,
    chars_in,
    code_order,
    code_text,
    font_size,
    ink_on,
    left_out_note,
    percent_axis,
    row_major,
    text_width,
    wrap,
)
from siamang.reporting.charts import SurveyChart

NEUTRALS = ("split", "side")
SORTS = ("top2", "listed")
#: A neutral answer's colour: a grey, so the middle reads as neither side.
NEUTRAL_GREY = "#bdbdbd"


@dataclass
class Scale:
    """The ordered answers of a battery and where its middle is."""

    codes: list[Any]
    labels: dict[Any, str]
    negative: list[Any]
    positive: list[Any]
    neutral: Any = None

    @property
    def box(self) -> int:
        """How many answers the top and bottom boxes hold: two, or one on a
        scale too short for two on a side."""
        return min(2, len(self.negative))

    @property
    def top(self) -> list[Any]:
        return self.positive[-self.box :]

    @property
    def bottom(self) -> list[Any]:
        return self.negative[: self.box]


@dataclass
class LikertChart(SurveyChart):
    """Diverging stacked bars of items that share one ordered scale.

    Parameters
    ----------
    columns : list[str]
        The items, each with one answer per respondent on the same scale.
    neutral : str
        ``"split"`` (the neutral answer half on either side of the centre) or
        ``"side"`` (apart, at the right). A scale with an even number of
        answers has none, and the centre falls between its middle two.
    sort : str
        ``"top2"`` (the largest top-2 share first) or ``"listed"``.
    show_values : bool
        Write each answer's share in its segment where it fits.
    """

    columns: list[str] = field(default_factory=list)
    neutral: str = "split"
    sort: str = "top2"
    show_values: bool = True
    palette: str = "RdBu"
    _table: Any = field(init=False, repr=False, default=None)

    @property
    def table(self) -> pd.DataFrame:
        """The numbers drawn: per item, the share of each answer (%), top-2,
        bottom-2 and N (and the weighted N on weighted data), in chart order."""
        self._ensure_built()
        return self._table.copy()

    def _build(self) -> None:
        import matplotlib.pyplot as plt

        from siamang.reporting import chart_theme

        if self.neutral not in NEUTRALS:
            raise ValueError(f"neutral must be one of {', '.join(NEUTRALS)}; got {self.neutral!r}.")
        if self.sort not in SORTS:
            raise ValueError(f"sort must be one of {', '.join(SORTS)}; got {self.sort!r}.")
        columns = list(dict.fromkeys(self.columns))
        if not columns:
            raise ValueError("A Likert chart needs at least one item.")
        unknown = [name for name in columns if name not in self.data.frame.columns]
        if unknown:
            raise ValueError(f"No variable {unknown[0]!r} in the data.")
        scale = likert_scale(self.data, columns)
        counted = _count(self, columns, scale)
        rows, notes = counted["rows"], counted["notes"]
        if self.sort == "top2":
            rows.sort(key=lambda row: (-row["top"], row["bottom"], row["index"]))

        labels = [_label(self.data, name) for name in columns]
        stem, rests = _stem(labels)
        names = dict(zip(columns, rests, strict=True))
        self._table = _table(rows, scale, names, weighted=self.data.weight is not None)

        chart_theme.set_theme(style="whitegrid")
        side = self.neutral == "side" and scale.neutral is not None
        if side:
            fig, (ax, aside) = plt.subplots(
                1,
                2,
                figsize=self.figsize,
                sharey=True,
                # No wspace here: a GridSpec with one is not laid out by
                # tight_layout, and the notes would run into the plot.
                gridspec_kw={"width_ratios": [5, 1]},
            )
        else:
            fig, ax = plt.subplots(figsize=self.figsize)
            aside = None
        self._fig, self._ax = fig, ax
        colours = _colours(self.palette, scale)
        shares = np.array([[row["shares"][code] for code in scale.codes] for row in rows])
        count = len(rows)
        at = np.arange(count, dtype=float)
        position = {code: index for index, code in enumerate(scale.codes)}
        half = (
            shares[:, position[scale.neutral]] / 2.0
            if scale.neutral is not None and not side
            else np.zeros(count)
        )
        lefts: dict[Any, np.ndarray] = {}
        edge = -half.copy()
        for code in reversed(scale.negative):
            edge = edge - shares[:, position[code]]
            lefts[code] = edge.copy()
        edge = half.copy()
        for code in scale.positive:
            lefts[code] = edge.copy()
            edge = edge + shares[:, position[code]]
        if scale.neutral is not None and not side:
            lefts[scale.neutral] = -half
        handles = {}
        for code in scale.codes:
            target = aside if side and code == scale.neutral else ax
            left = lefts.get(code, np.zeros(count))
            handles[code] = target.barh(
                at,
                shares[:, position[code]],
                left=left,
                height=0.66,
                color=colours[code],
                edgecolor="white",
                linewidth=0.8,
                label=scale.labels[code],
            )

        reach = max(
            float(np.max(half + shares[:, [position[c] for c in scale.positive]].sum(axis=1))),
            float(np.max(half + shares[:, [position[c] for c in scale.negative]].sum(axis=1))),
            1.0,
        )
        limit = float(np.ceil(reach / 10.0) * 10.0)
        # As many ticks as the axis holds without crowding (about 40 pt each).
        room = self.figsize[0] * 72.0 * (0.45 if side else 0.55)
        step = next(
            (step for step in (10.0, 20.0, 25.0, 50.0) if (2 * (limit // step) + 1) * 40.0 <= room),
            50.0,
        )
        ticks = np.arange(-(limit // step), limit // step + 1) * step  # 0 among them
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"{abs(value):.0f}%" for value in ticks])
        # Over the bars, under the values: the neutral answer's value sits on it.
        ax.axvline(0.0, color=chart_theme.text("0.25"), linewidth=0.9, zorder=2.5)
        ax.grid(False)
        ax.grid(True, axis="x", color=chart_theme.grid("0.88"), linewidth=0.8)
        ax.set_axisbelow(True)
        # One item's label is the title; its row says only its base.
        shown = [names[row["name"]] if len(columns) > 1 else "" for row in rows]
        label_size, ticklabels, row_pt = _item_labels(
            shown, [row["n"] for row in rows], self.figsize
        )
        ax.set_yticks(at)
        ax.set_yticklabels(ticklabels, fontsize=label_size)
        ax.set_ylim(count - 0.5, -0.5)
        ax.set_xlabel("% of respondents" + (" (weighted)" if self.data.weight else ""))
        # One item is titled by its own label (its row then says only its base).
        single = _label(self.data, columns[0]) if len(columns) == 1 else ""
        title = self.title or stem or single or _fallback_title(columns, scale)
        title = wrap(title, chars_in(self.figsize[0] * 72.0 * 0.85, font_size("axes.titlesize")))
        if self.data.weight is not None:
            self._weighted()
        ax.set_title(title, pad=18)
        if aside is not None:
            aside.grid(False)
            aside.grid(True, axis="x", color=chart_theme.grid("0.88"), linewidth=0.8)
            aside.set_axisbelow(True)
            top = float(np.max(shares[:, position[scale.neutral]]))
            aside.set_xlim(0, max(10.0, np.ceil(top * 1.35 / 10.0) * 10.0))
            percent_axis(aside.xaxis)  # whole percents: 2.5 is not "2%"
            aside.set_title(wrap(scale.labels[scale.neutral], 14), fontsize=10)
            aside.tick_params(axis="y", left=False)

        items = [handles[code] for code in scale.codes]
        legend_labels = [wrap(scale.labels[code], 18) for code in scale.codes]
        entry = max(text_width(text, 9.0) for text in legend_labels) + 30.0
        columns_fit = max(1, min(len(items), int((self.figsize[0] * 72.0 - 20.0) // entry)))
        legend = fig.legend(
            row_major(items, columns_fit),
            row_major(legend_labels, columns_fit),
            loc="lower center",
            ncol=columns_fit,
            frameon=False,
            fontsize=9,
        )
        footnote = Footnote(fig, notes, legend=legend, axes=ax, least=count * row_pt)
        footnote.apply()
        # Few items do not stretch over a tall figure: a row is at most 60 pt.
        spare = axes_points(ax)[1] - count * max(row_pt, 60.0)
        if spare > 1:
            footnote.least = count * max(row_pt, 60.0)
            fig.set_figheight(fig.get_figheight() - spare / 72.0)
            footnote.apply()
        self._annotate(ax, aside, rows, scale, shares, lefts, colours, limit)
        footnote.apply()

    def _annotate(
        self,
        ax: Any,
        aside: Any,
        rows: list[dict[str, Any]],
        scale: Scale,
        shares: np.ndarray,
        lefts: dict[Any, np.ndarray],
        colours: dict[Any, Any],
        limit: float,
    ) -> None:
        """The top-2 and bottom-2 shares in columns at the two ends, and each
        answer's share in its segment where it fits."""

        from matplotlib.transforms import blended_transform_factory

        from siamang.reporting import chart_theme

        size = VALUE_SIZE
        width_pt = axes_points(ax)[0]
        room_pt = text_width("100%", size) + 10.0
        # The axis runs past the longest bar by the room a total needs.
        pad = room_pt * 2.0 * limit / max(width_pt - 2.0 * room_pt, 1.0)
        ax.set_xlim(-limit - pad, limit + pad)
        box = "Top-2" if scale.box == 2 else "Top box"
        low_box = "Bottom-2" if scale.box == 2 else "Bottom box"
        header = blended_transform_factory(ax.transData, ax.transAxes)
        for x, text, align in ((-limit - pad, low_box, "left"), (limit + pad, box, "right")):
            ax.text(
                x,
                1.005,
                text,
                transform=header,
                ha=align,
                va="bottom",
                fontsize=size,
                color=chart_theme.text("0.25"),
            )
        for index, row in enumerate(rows):
            ax.text(
                -limit - pad * 0.9,
                index,
                f"{row['bottom']:.0f}%",
                ha="left",
                va="center",
                fontsize=size,
                color=chart_theme.text("0.15"),
            )
            ax.text(
                limit + pad * 0.9,
                index,
                f"{row['top']:.0f}%",
                ha="right",
                va="center",
                fontsize=size,
                color=chart_theme.text("0.15"),
            )
        if not self.show_values:
            return
        span = 2.0 * (limit + pad)
        position = {code: i for i, code in enumerate(scale.codes)}
        band_pt = axes_points(ax)[1] / max(len(rows), 1) * 0.66
        for code in scale.codes:
            target = aside if aside is not None and code == scale.neutral else ax
            for index in range(len(rows)):
                value = shares[index, position[code]]
                text = f"{value:.0f}%"
                if target is ax:
                    length = value / span * width_pt
                    middle = lefts[code][index] + value / 2.0
                else:
                    low, high = target.get_xlim()
                    length = value / (high - low) * axes_points(target)[0]
                    middle = value / 2.0
                if value <= 0 or length < text_width(text, size) + 5 or band_pt < size + 2:
                    continue
                label = target.text(
                    middle,
                    index,
                    text,
                    ha="center",
                    va="center",
                    fontsize=size,
                    color=ink_on(colours[code]),
                    zorder=4,
                )
                if code == scale.neutral and target is ax:
                    # The centre line runs behind the neutral answer's value.
                    label.set_bbox({"facecolor": colours[code], "edgecolor": "none", "pad": 1.0})


def likert_scale(data: Any, columns: list[str]) -> Scale:
    """The scale ``columns`` share, from the codebook; a ``ValueError`` that
    names two items whose scales differ, or says why there is none."""

    scales = {name: _answers(data, name) for name in columns}
    if not any(scales.values()):
        raise ValueError(
            "A Likert chart draws the answers of a scale, and none of the items has "
            "value labels (or a valid range of whole numbers) in the codebook, or a "
            "Likert scale question, to say what the scale is."
        )
    first = columns[0]
    for name in columns[1:]:
        if _key(scales[name]) != _key(scales[first]):
            raise ValueError(
                "The items of a Likert chart must share one scale, and these do not: "
                f"{_label(data, first)} has {_describe(scales[first])}; "
                f"{_label(data, name)} has {_describe(scales[name])}. Draw them in "
                "separate charts, or recode them onto one scale first."
            )
    labels = scales[first]
    codes = sorted(labels, key=code_order)
    if len(codes) < 2:
        raise ValueError(
            f"A Likert chart needs a scale of at least two answers; {_label(data, first)} "
            f"has {_describe(labels)}."
        )
    middle = len(codes) // 2
    if len(codes) % 2:
        return Scale(codes, labels, codes[:middle], codes[middle + 1 :], codes[middle])
    return Scale(codes, labels, codes[:middle], codes[middle:])


def _answers(data: Any, name: str) -> dict[Any, str]:
    """An item's labelled answers without its missing codes, else the whole
    numbers of its valid range, else the points of the Likert scale question
    that asks it (``Not at all``, ``2``, … ``6``, ``Completely``)."""

    variables = data.variables
    variable = variables[name] if variables and name in variables else None
    if variable is None:
        return {}
    missing = set(variable.missing_values)
    labels = {
        code: str(label) for code, label in (variable.labels or {}).items() if code not in missing
    }
    if labels:
        return labels
    bounds = variable.valid_range
    if bounds and all(float(bound).is_integer() for bound in bounds):
        low, high = (int(bound) for bound in bounds)
        if 2 <= high - low + 1 <= 11:
            return {code: str(code) for code in range(low, high + 1) if code not in missing}
    question = _scale_question(data, name)
    if question is not None:
        points = [code for code in question.values if code not in missing]
        named = {code: str(code) for code in points}
        if points and question.left_label:
            named[points[0]] = str(question.left_label)
        if points and question.right_label:
            named[points[-1]] = str(question.right_label)
        return named
    return {}


def _scale_question(data: Any, name: str) -> Any:
    """The LikertScale question of the data's questionnaire that asks ``name``."""

    from siamang.core.question import LikertScale

    questionnaire = getattr(data, "questionnaire", None)
    if questionnaire is None:
        return None
    for question in questionnaire.all_questions():
        if isinstance(question, LikertScale) and question.var.name == name:
            return question
    return None


def _key(labels: dict[Any, str]) -> list[tuple[str, str]]:
    return [
        (code_text(code), " ".join(labels[code].split()).casefold())
        for code in sorted(labels, key=code_order)
    ]


def _describe(labels: dict[Any, str]) -> str:
    if not labels:
        return "no value labels"
    parts = [f"{code_text(code)} = {labels[code]}" for code in sorted(labels, key=code_order)]
    if len(parts) > 6:
        parts = [*parts[:3], "…", *parts[-2:]]
    return ", ".join(parts)


def _label(data: Any, name: str) -> str:
    variables = data.variables
    if variables and name in variables:
        return variables[name].label or name
    return name


def _stem(labels: list[str]) -> tuple[str, list[str]]:
    """The words every label starts with, up to a separator (``"Trust: Acme"``,
    ``"Trust: Globex"`` → ``"Trust"``, ``["Acme", "Globex"]``), or no stem."""

    if len(labels) < 2:
        return "", labels
    prefix = os.path.commonprefix(labels)
    best = -1
    chosen = ""
    for separator in (": ", " - ", " – ", " — ", "? "):
        found = prefix.rfind(separator)
        if found > best:
            best, chosen = found, separator
    if best <= 0:
        return "", labels
    rests = [label[best + len(chosen) :].strip() for label in labels]
    if not all(rests):
        return "", labels
    stem = prefix[:best].strip() + ("?" if chosen == "? " else "")
    return stem, rests


def _item_labels(
    labels: list[str], bases: list[int], figsize: tuple[float, float]
) -> tuple[float, list[str], float]:
    """The items' labels (their base kept whole), their size and a row's
    height: the largest size and narrowest column — 11 pt in 0.3 of the width,
    down to 8 pt in 0.45 — at which every row fits the figure's height grown by
    at most 60 %; else the smallest, the figure growing by what it lacks. A
    narrow figure no longer balloons into a strip of three-line rows."""

    width_pt, height_pt = figsize[0] * 72.0, figsize[1] * 72.0
    base = font_size("ytick.labelsize")
    tries = ((base, 0.3), (base - 1, 0.3), (base - 1, 0.4), (9.0, 0.4), (8.0, 0.45))
    room = height_pt * 0.55 * 1.6
    for size, share in tries:
        width = chars_in(share * width_pt, size)
        texts = [_with_base(label, n, width) for label, n in zip(labels, bases, strict=True)]
        row = max(text.count("\n") + 1 for text in texts) * size * 1.2 + 10.0
        if len(texts) * row <= room:
            break
    return size, texts, row


def _with_base(label: str, n: int, width: int) -> str:
    """``label`` wrapped, its "(n = …)" kept whole on the last line or the next."""

    base = f"(n = {n:,})"
    if not label:
        return base
    text = wrap(label, width)
    last = text.rsplit("\n", 1)[-1]
    return f"{text} {base}" if len(last) + 1 + len(base) <= width else f"{text}\n{base}"


def _fallback_title(columns: list[str], scale: Scale) -> str:
    low, high = scale.labels[scale.codes[0]], scale.labels[scale.codes[-1]]
    items = "item" if len(columns) == 1 else "items"
    return f"{len(columns)} {items} from {low} to {high}"


def _colours(palette: str, scale: Scale) -> dict[Any, Any]:
    """A diverging palette over the scale, its neutral answer grey (``"theme"``:
    the report theme's diverging pair)."""

    from siamang.reporting import chart_theme

    count = len(scale.codes)
    if scale.neutral is None and count >= 4:
        # An even scale has no middle colour: the two middle ones of a palette
        # of as many are nearly white, and "Agree" vanished. Sampled two wider
        # with the two middle ones dropped, the inner answers keep a colour.
        wide = chart_theme.diverging_palette(palette, count + 2)
        colours = wide[: count // 2] + wide[count // 2 + 2 :]
    else:
        colours = chart_theme.diverging_palette(palette, count)
    by_code = dict(zip(scale.codes, colours, strict=True))
    if scale.neutral is not None:
        by_code[scale.neutral] = chart_theme.neutral(NEUTRAL_GREY)
    return by_code


def _count(chart: LikertChart, columns: list[str], scale: Scale) -> dict[str, Any]:
    """Each item's shares of the scale's answers, and the notes to write."""

    from siamang.data import multi
    from siamang.data.inference import without_missing_codes

    data = chart.data
    for name in columns:
        if multi.is_multi(data.frame[name]):
            raise ValueError(
                f"{_label(data, name)} allows several answers; a Likert chart draws items "
                "with one answer each on a scale."
            )
    source, left_out = without_missing_codes(data.frame, columns, data.variables)
    source = source.reset_index(drop=True)
    weights = None
    if data.weight is not None:
        if data.weight not in data.frame.columns:
            raise ValueError(f"Weight column '{data.weight}' not found in frame.")
        weights = pd.to_numeric(data.frame[data.weight], errors="coerce").fillna(0.0).to_numpy()
    rows, empty, off = [], [], []
    for index, name in enumerate(columns):
        series = source[name]
        weight = weights if weights is not None else np.ones(len(series))
        hits = {code: (series == code).fillna(False).to_numpy(dtype=bool) for code in scale.codes}
        on = np.logical_or.reduce(list(hits.values()))
        stray = series.notna().to_numpy(dtype=bool) & ~on
        if stray.any():
            values = sorted(pd.unique(series[stray]), key=code_order)
            shown = ", ".join(code_text(value) for value in values[:5])
            off.append(
                f"{_label(data, name)}: {int(stray.sum())} ({shown}{', …' if len(values) > 5 else ''})"
            )
        total = float(weight[on].sum())
        if not on.any() or total <= 0:
            empty.append(_label(data, name))
            continue
        shares = {code: float(weight[hits[code]].sum()) / total * 100.0 for code in scale.codes}
        rows.append(
            {
                "name": name,
                "index": index,
                "shares": shares,
                "top": sum(shares[code] for code in scale.top),
                "bottom": sum(shares[code] for code in scale.bottom),
                "n": int(on.sum()),
                "weighted": total,
            }
        )
    if not rows:
        raise ValueError("None of the items has an answer on the scale.")

    def listed(codes: list[Any]) -> str:
        return ", ".join(f"{code_text(code)} = {scale.labels[code]}" for code in codes)

    top_name = "Top-2" if scale.box == 2 else "Top box"
    bottom_name = "bottom-2" if scale.box == 2 else "bottom box"
    ordered = chart.sort == "top2" and len(columns) > 1
    notes = [
        "Base: the respondents who answered each item on the scale (n beside it)."
        + (f" Items in order of their {top_name.lower()} share." if ordered else ""),
        f"{top_name}: {listed(scale.top)}; {bottom_name}: {listed(scale.bottom)}.",
    ]
    if scale.neutral is None:
        notes.append(
            "No neutral answer: the centre falls between "
            f"{listed([scale.negative[-1]])} and {listed([scale.positive[0]])}."
        )
    elif chart.neutral == "split":
        notes.append(f"The neutral answer ({listed([scale.neutral])}) is split around the centre.")
    else:
        notes.append(
            f"The neutral answer ({listed([scale.neutral])}) is drawn apart, at the right."
        )
    if weights is not None:
        notes.append(f"Weighted by '{data.weight}'; n counts respondents.")
    note = left_out_note(left_out, data.variables)
    if note:
        notes.append(note)
    if off:
        notes.append("Not on the scale, left out: " + "; ".join(off) + ".")
    if empty:
        notes.append("No answer on the scale, not drawn: " + ", ".join(empty) + ".")
    return {"rows": rows, "notes": notes}


def _table(
    rows: list[dict[str, Any]], scale: Scale, names: dict[str, str], *, weighted: bool
) -> pd.DataFrame:
    records = []
    for row in rows:
        record: dict[str, Any] = {"Item": names[row["name"]]}
        for code in scale.codes:
            record[scale.labels[code]] = round(row["shares"][code], 1)
        record["Top-2" if scale.box == 2 else "Top box"] = round(row["top"], 1)
        record["Bottom-2" if scale.box == 2 else "Bottom box"] = round(row["bottom"], 1)
        record["N"] = row["n"]
        if weighted:
            record["Weighted N"] = round(row["weighted"], 1)
        records.append(record)
    return pd.DataFrame(records)


__all__ = ["NEUTRALS", "SORTS", "LikertChart", "Scale", "likert_scale"]
