"""Canonical intermediate representation of a compiled survey.

`SurveySchema` is what every backend, frontend runtime, and theme adapter
receives. It is a frozen dataclass that can be serialised to JSON or to a
SurveyJS-compatible payload via ``to_surveyjs()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class SurveySchema:
    title: str
    pages: list[dict[str, Any]]
    variables: dict[str, dict[str, Any]]
    language: str = "en"
    description: str | None = None
    completion_text: str = "Thank you for your participation!"
    show_progress: bool = True
    allow_back: bool = True
    one_question_per_page: bool = False
    deadline: datetime | None = None
    max_responses: int | None = None
    quotas: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_surveyjs(self) -> dict[str, Any]:
        """Render the schema as a SurveyJS-compatible payload."""

        payload: dict[str, Any] = {
            "title": self.title,
            "locale": self.language,
            "pages": [self._strip_internal(page) for page in self.pages],
            "showProgressBar": "top" if self.show_progress else "off",
            "showPrevButton": self.allow_back,
            "completedHtml": f"<h3>{self.completion_text}</h3>",
        }
        if self.description:
            payload["description"] = self.description
        if self.one_question_per_page:
            payload["questionsOnPageMode"] = "questionPerPage"
        return payload

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_version": 1,
            "title": self.title,
            "language": self.language,
            "description": self.description,
            "completion_text": self.completion_text,
            "show_progress": self.show_progress,
            "allow_back": self.allow_back,
            "one_question_per_page": self.one_question_per_page,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "max_responses": self.max_responses,
            "pages": self.pages,
            "variables": self.variables,
            "quotas": self.quotas,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def _strip_internal(page: dict[str, Any]) -> dict[str, Any]:
        """Drop siamang-internal keys before handing to SurveyJS."""

        skip = {"_quota_variable", "_meta"}
        return {key: value for key, value in page.items() if key not in skip}
