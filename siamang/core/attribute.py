"""An attribute of a product, and the levels it can take.

A conjoint question does not offer options; it offers whole products, and a
product is one level of every attribute at once — "Acme, £15, large, two-year
warranty". That is a shape :class:`~siamang.core.option.Option` cannot carry: an
option is a code and a label, and a profile is a row of them.

Levels *are* options, though, which is why they are reused rather than
reinvented: a level has a code and a label, and may carry an image for the same
reason an answer option may.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from siamang.core.option import Option


@dataclass(frozen=True, slots=True)
class Attribute:
    """One dimension a product varies on, and the values it takes.

    ``name`` is what the analysis calls it and must be a plain identifier,
    because it becomes a column prefix in the part-worth table. ``label`` is
    what the respondent reads.
    """

    name: str
    levels: list[Option] = field(default_factory=list)
    label: str | None = None

    def __post_init__(self) -> None:
        if not self.name or not str(self.name).strip():
            raise ValueError("Attribute.name must not be empty.")
        if not self.name.isidentifier():
            raise ValueError(
                f"Attribute name {self.name!r} must be a plain identifier: it becomes a "
                "column name in the results."
            )
        if len(self.levels) < 2:
            raise ValueError(
                f"Attribute {self.name!r} needs at least two levels — one level is a constant, "
                "and a constant cannot be traded off against anything."
            )
        if any(not isinstance(level, Option) for level in self.levels):
            raise TypeError(f"Attribute {self.name!r} levels must be Option instances.")
        seen: set[Any] = set()
        for level in self.levels:
            if level.code in seen:
                raise ValueError(
                    f"Attribute {self.name!r} has two levels with code {level.code!r}."
                )
            seen.add(level.code)

    @property
    def codes(self) -> list[Any]:
        return [level.code for level in self.levels]

    def label_of(self, code: Any) -> str:
        for level in self.levels:
            if level.code == code:
                return level.label
        return str(code)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "levels": [level.to_dict() for level in self.levels],
        }
        if self.label is not None:
            payload["label"] = self.label
        return payload
