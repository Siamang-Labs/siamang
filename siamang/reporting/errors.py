"""What a chart (or an analysis) says when no one has answered yet."""

from __future__ import annotations


class NoAnswersError(ValueError):
    """No respondent answered what a chart draws — a survey with no responses
    yet, or a filter that left none — so there is nothing to draw.

    The message says whose answers are missing, in the codebook's words
    ("No respondent answered Brand."), and is meant to be shown as it is: a
    report writes it where the figure would be, and a dashboard can show an
    empty tile with it instead of an error. It is a ValueError, as these
    charts raised before, so code that caught one still does.

    An analysis that has nothing to work on without answers — a cluster
    analysis, principal components, a reliability or a TURF of no one —
    raises it too, in the same words; there it fails its node as any error
    does, since what comes after needs its result.

    A label that ends a sentence of its own ("Which brands have you heard
    of?") is not followed by a second full stop.
    """

    def __init__(self, message: str) -> None:
        if message.endswith(".") and message[-2:-1] in ("?", "!", ".", "…"):
            message = message[:-1]
        super().__init__(message)


__all__ = ["NoAnswersError"]
