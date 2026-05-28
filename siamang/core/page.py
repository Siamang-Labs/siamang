"""Survey page model for grouping blocks/questions into navigable pages."""

from __future__ import annotations

from dataclasses import dataclass, field

from siamang.core.block import Block
from siamang.core.expression import Expression
from siamang.core.question import Question


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

    def flatten_questions(self) -> list[Question]:
        questions: list[Question] = []
        for item in self.items:
            if isinstance(item, Block):
                questions.extend(item.flatten_questions())
            else:
                questions.append(item)
        return questions
