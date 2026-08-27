"""Survey page model for grouping blocks/questions into navigable pages.

In addition to ordinary question pages, a Page can carry a ``kind`` that changes
how the runtime renders it:

* ``"content"``          — a non-terminal page that shows arbitrary HTML
                           (``body``) instead of questions (intro/consent/etc).
* ``"disqualification"`` — a terminal screen shown when the respondent is
                           screened out; records the response as screened-out.
* ``"final"``            — a terminal screen with a custom thank-you ``body``.
* ``"redirect"``         — a terminal screen that redirects to ``redirect_url``
                           (e.g. a panel completion URL).

Terminal pages end the survey when reached (typically gated by ``show_if``);
``content`` pages stay in the normal Next/Prev flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from siamang.core.block import Block
from siamang.core.expression import Expression
from siamang.core.question import Question

#: Page kinds that end the survey when the respondent reaches them.
TERMINAL_KINDS = ("disqualification", "final", "redirect")
#: All recognised page kinds (``None`` == an ordinary question page).
PAGE_KINDS = ("content", *TERMINAL_KINDS)


@dataclass(frozen=True, slots=True)
class Page:
    name: str
    title: str | None = None
    items: list[Question | Block] = field(default_factory=list)
    next_if: list[tuple[str, str]] = field(default_factory=list)
    default_next: str | None = None
    randomize_blocks: bool = False
    show_if: Expression | str | None = None
    hide_if: Expression | str | None = None
    # Custom page kinds (None == ordinary question page).
    kind: str | None = None
    body: str | None = None  # HTML content for content/terminal pages
    redirect_url: str | None = None  # for redirect (or any terminal) pages
    redirect_delay: int | None = None  # seconds before redirect (default 5)

    def __post_init__(self) -> None:
        if self.kind is not None and self.kind not in PAGE_KINDS:
            raise ValueError(f"Unknown page kind: {self.kind!r}. Use one of {PAGE_KINDS} or None.")

    @property
    def is_terminal(self) -> bool:
        """True for kinds that end the survey when reached."""
        return self.kind in TERMINAL_KINDS

    def flatten_questions(self) -> list[Question]:
        questions: list[Question] = []
        for item in self.items:
            if isinstance(item, Block):
                questions.extend(item.flatten_questions())
            else:
                questions.append(item)
        return questions


def ContentPage(
    name: str,
    *,
    body: str,
    title: str | None = None,
    show_if: Expression | str | None = None,
    hide_if: Expression | str | None = None,
) -> Page:
    """A non-terminal page that renders arbitrary HTML (consent/intro/etc.)."""
    return Page(name=name, title=title, kind="content", body=body, show_if=show_if, hide_if=hide_if)


def DisqualificationPage(
    name: str,
    *,
    title: str | None = None,
    body: str | None = None,
    redirect_url: str | None = None,
    redirect_delay: int | None = None,
    show_if: Expression | str | None = None,
    hide_if: Expression | str | None = None,
) -> Page:
    """A terminal screen-out page (records the response as screened-out)."""
    return Page(
        name=name,
        title=title,
        kind="disqualification",
        body=body,
        redirect_url=redirect_url,
        redirect_delay=redirect_delay,
        show_if=show_if,
        hide_if=hide_if,
    )


def FinalPage(
    name: str,
    *,
    title: str | None = None,
    body: str | None = None,
    redirect_url: str | None = None,
    redirect_delay: int | None = None,
    show_if: Expression | str | None = None,
) -> Page:
    """A terminal custom thank-you / final page."""
    return Page(
        name=name,
        title=title,
        kind="final",
        body=body,
        redirect_url=redirect_url,
        redirect_delay=redirect_delay,
        show_if=show_if,
    )


def RedirectPage(
    name: str,
    *,
    redirect_url: str,
    title: str | None = None,
    body: str | None = None,
    redirect_delay: int | None = None,
    show_if: Expression | str | None = None,
) -> Page:
    """A terminal page that redirects to an external URL on completion."""
    return Page(
        name=name,
        title=title,
        kind="redirect",
        body=body,
        redirect_url=redirect_url,
        redirect_delay=redirect_delay,
        show_if=show_if,
    )
