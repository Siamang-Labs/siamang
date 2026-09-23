"""Script — injectable JavaScript behavior for surveys.

Scripts allow researchers to add custom dynamic behavior without modifying
the core runtime. Examples:
- Randomize answer options based on previous answers
- Shuffle page order
- Show timed questions
- Custom validation (e.g., password confirmation)
- External API calls (e.g., verify postal code)
- A/B test assignment
- Dynamic piped text
- Custom event tracking

Each script runs at a specified trigger point and has access to:
- answers: current respondent answers
- utils: built-in helper functions (shuffle, sample, etc.)
- api: { get, post } for external HTTP calls
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_VALID_TRIGGERS = {
    "onInit",  # Runs once when survey loads (before first page)
    "onPageEnter",  # Runs when a page becomes visible
    "onPageExit",  # Runs when leaving a page
    "onQuestionShow",  # Runs when a question becomes visible (show_if resolved)
    "onAnswer",  # Runs when any answer changes
    "onSubmit",  # Runs before submission (can modify answers)
    "onRandomize",  # Runs to determine randomization
}


@dataclass(frozen=True, slots=True)
class Script:
    """A JavaScript snippet that runs at a specific trigger point.

    Args:
        code: JavaScript source code (string)
        trigger: When to run. One of: onInit, onPageEnter, onPageExit,
                onQuestionShow, onAnswer, onSubmit, onRandomize
        name: Optional identifier (shown in logs, useful for debugging)
        target: Optional scope — page name or question ID to limit scope.
                If None, runs globally at the trigger point.
        context: Optional dict of static data passed to the script at runtime
        sandbox: If True, run in a restricted scope (no DOM access)

    Example:
        Script(
            name="shuffle_options",
            trigger="onRandomize",
            target="q_trust",
            code=\"\"\"
                // Randomize question options on every show
                answers.__options__['q_trust'] = utils.shuffle(
                    answers.__options__['q_trust']
                );
            \"\"\"
        )
    """

    code: str
    trigger: str = "onPageEnter"
    name: str | None = None
    target: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    sandbox: bool = True

    def __post_init__(self) -> None:
        if self.trigger not in _VALID_TRIGGERS:
            allowed = ", ".join(sorted(_VALID_TRIGGERS))
            raise ValueError(f"Unknown trigger '{self.trigger}'. Allowed triggers: {allowed}.")
        if not self.code.strip():
            raise ValueError("Script code must not be empty.")
        if self.name is not None and not self.name.strip():
            raise ValueError("Script name must not be empty when provided.")

    @property
    def assigns(self) -> str | None:
        """The variable this script writes for every respondent, or None.

        Only ``assign_condition`` says so — its parameters ride in ``context`` —
        and that is enough for the questionnaire to treat the arm as a known
        variable: a page may branch on it and a quota may balance it although
        no question collects it.
        """
        context = self.context or {}
        variable = context.get("variable")
        if (
            (self.name or "").startswith("assign_")
            and isinstance(variable, str)
            and isinstance(context.get("arms"), list)
        ):
            return variable
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "trigger": self.trigger,
            "name": self.name,
            "target": self.target,
            "context": self.context,
            "sandbox": self.sandbox,
        }

    @classmethod
    def randomize_options(cls, question_id: str, seed: str | None = None) -> Script:
        """Factory: create a script that randomizes answer options for a question."""
        qid = json.dumps(question_id)
        code = f"""
            const qid = {qid};
            const opts = answers.__options__?.[qid];
            if (opts && Array.isArray(opts)) {{
                answers.__options__[qid] = utils.shuffle(opts);
            }}
        """
        return cls(
            name=f"randomize_{question_id}",
            trigger="onQuestionShow",
            target=question_id,
            code=code,
            context={"seed": seed} if seed else {},
        )

    @classmethod
    def randomize_pages(cls) -> Script:
        """Factory: shuffle the page order on init.

        The first page (welcome), the last page and every terminal page — a
        screen-out, a thank-you, a redirect, wherever it sits — keep their
        place; the remaining pages are shuffled among the remaining slots. A
        screen-out is gated on the questions before it, so a shuffle that
        moved it would show it before the answers it depends on exist.
        """
        code = """
            // Shuffle the pages a respondent can be routed through. The first
            // (welcome) and last page and every terminal page keep their own
            // position: the pages between them are dealt into the other slots.
            const pages = answers.__pages__ || [];
            const terminal = { disqualification: true, final: true, redirect: true };
            const pinned = pages.map((p, i) =>
                i === 0 || i === pages.length - 1 || !!(p && terminal[p.kind]));
            const movable = pages.filter((p, i) => !pinned[i]);
            if (movable.length > 1) {
                const shuffled = utils.shuffle(movable);
                let next = 0;
                answers.__pages__ = pages.map((p, i) => (pinned[i] ? p : shuffled[next++]));
            }
        """
        return cls(
            name="randomize_pages",
            trigger="onInit",
            code=code,
        )

    @classmethod
    def assign_condition(
        cls,
        variable: str,
        arms: Sequence[tuple[int | str, str] | tuple[int | str, str, int]],
        seed: str | None = None,
        balance: bool = False,
    ) -> Script:
        """Factory: draw each respondent into one experimental arm.

        Randomization shuffles *order*; this makes a *choice*. One arm is
        drawn per respondent before the first page and written to ``variable``,
        so ordinary routing (``show_if`` / ``next_if``) can branch on it, a
        quota can balance it, and the analysis can group by it.

        Args:
            variable: where the drawn arm's code is stored.
            arms: ``(code, label)`` or ``(code, label, weight)`` — weights are
                positive integers and default to 1, so equal arms need none.
            seed: draw deterministically. With a seed the same respondent id
                always lands in the same arm, which is what makes a fielded
                assignment reproducible from the generated ``.py``.
            balance: keep the arms level against the live quota counters
                instead of trusting the draw. Each respondent is sent to the
                arm furthest behind its own quota target, which is what stops
                one arm completing while another starves — an independent
                draw drifts, and differential screen-out pulls the arms apart
                much faster than drift does. Needs a quota cell per arm on
                ``variable``; the draw above stays as the fallback, so a
                missing quota or an unreachable backend costs balance, not a
                session. Not compatible with a reproducible ``seed``: the
                assignment then depends on who answered first.

        Example:
            Script.assign_condition("condition", [(1, "Control"), (2, "Treatment")])
        """
        if not variable or not _IDENTIFIER_RE.match(variable):
            raise ValueError(
                f"Assignment variable {variable!r} is not a valid name: "
                "letters, digits and underscore, not starting with a digit."
            )
        prepared: list[tuple[int | str, str, int]] = []
        for arm in arms:
            code, label, weight = (arm[0], arm[1], arm[2] if len(arm) > 2 else 1)  # type: ignore[misc]
            if not str(label).strip():
                raise ValueError(f"Arm {code!r} has no label.")
            if int(weight) < 1:
                raise ValueError(
                    f"Arm {code!r} has weight {weight}; weights are positive integers."
                )
            prepared.append((code, str(label), int(weight)))
        if len(prepared) < 2:
            raise ValueError("An assignment needs at least two arms.")
        codes = [str(code) for code, _, _ in prepared]
        if len(set(codes)) != len(codes):
            raise ValueError("Arm codes must be distinct: they are what lands in the data.")
        if balance and seed is not None:
            raise ValueError(
                "A balanced assignment cannot also be seeded: the arm depends on "
                "who answered before, so it is not reproducible from the seed. "
                "Drop the seed, or drop balance=True."
            )

        var = json.dumps(variable)
        weights = json.dumps([weight for _, _, weight in prepared])
        values = json.dumps([code for code, _, _ in prepared])
        # The local draw above has already written an arm, so the respondent is
        # never left without one. This only replaces it when the backend can say
        # which arm is furthest behind its quota; the runtime holds the first
        # page while it answers, and gives up after its own timeout.
        balance_js = (
            """
                const balanced = await api.pickQuota(variable, values);
                if (balanced !== undefined && balanced !== null) {
                    answers[variable] = balanced;
                }"""
            if balance
            else ""
        )
        # Deterministic when seeded: a 32-bit FNV-1a hash of "<seed>:<respondent>"
        # feeds a mulberry32 draw, so the same respondent always lands in the
        # same arm on a re-run and the assignment is reproducible from the .py.
        code_js = f"""
            const variable = {var};
            if (answers[variable] === undefined || answers[variable] === null) {{
                const values = {values};
                const weights = {weights};
                const total = weights.reduce((a, b) => a + b, 0);
                const seed = context.seed;
                let draw;
                if (seed === undefined || seed === null || seed === "") {{
                    draw = Math.random();
                }} else {{
                    const key = String(seed) + ":" + String(
                        answers.__respondent__ || answers.respondent_id || ""
                    );
                    let h = 2166136261;
                    for (let i = 0; i < key.length; i++) {{
                        h ^= key.charCodeAt(i);
                        h = Math.imul(h, 16777619);
                    }}
                    let t = (h + 0x6D2B79F5) | 0;
                    t = Math.imul(t ^ (t >>> 15), 1 | t);
                    t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
                    draw = ((t ^ (t >>> 14)) >>> 0) / 4294967296;
                }}
                let cut = draw * total;
                let chosen = values[values.length - 1];
                for (let i = 0; i < values.length; i++) {{
                    cut -= weights[i];
                    if (cut < 0) {{ chosen = values[i]; break; }}
                }}
                answers[variable] = chosen;{balance_js}
            }}
        """
        context: dict[str, Any] = {
            "variable": variable,
            "arms": [list(arm) for arm in prepared],
        }
        if seed is not None:
            context["seed"] = seed
        if balance:
            context["balance"] = True
        return cls(
            name=f"assign_{variable}",
            trigger="onInit",
            code=code_js,
            context=context,
        )

    @classmethod
    def validate_fields_match(
        cls, field_a: str, field_b: str, message: str = "Fields do not match."
    ) -> Script:
        """Factory: validate that two answer fields have the same value."""
        fa = json.dumps(field_a)
        fb = json.dumps(field_b)
        msg = json.dumps(message)
        code = f"""
            const fa = {fa};
            const fb = {fb};
            if (answers[fa] !== undefined &&
                answers[fb] !== undefined &&
                answers[fa] !== answers[fb]) {{
                answers.__errors__[fb] = {msg};
            }}
        """
        return cls(
            name=f"validate_match_{field_a}_{field_b}",
            trigger="onAnswer",
            target=field_b,
            code=code,
        )

    @classmethod
    def timed_question(cls, question_id: str, seconds: int = 30) -> Script:
        """Factory: show a question for limited time, then auto-advance."""
        qid = json.dumps(question_id)
        timeout_ms = seconds * 1000
        code = f"""
            const qid = {qid};
            const timeout = {timeout_ms};
            if (!answers.__timers__) answers.__timers__ = {{}};
            if (!answers.__timers__[qid]) {{
                answers.__timers__[qid] = setTimeout(() => {{
                    if (window.siamangNext) window.siamangNext();
                }}, timeout);
            }}
        """
        return cls(
            name=f"timed_{question_id}",
            trigger="onQuestionShow",
            target=question_id,
            code=code,
        )
