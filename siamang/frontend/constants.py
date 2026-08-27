"""Pinned versions and constants for the frontend bundle."""

from __future__ import annotations

# SurveyJS engine version we pin. `survey-core` and `survey-js-ui` v2 are
# the public CDN-distributed packages; v1.9.x versions never existed on the
# CDN. Update both URLs together when bumping.
SURVEYJS_VERSION = "2.5.23"

SURVEYJS_JS_CDN = "https://unpkg.com/survey-core@{version}/survey.core.min.js"
SURVEYJS_UI_CDN = "https://unpkg.com/survey-js-ui@{version}/survey-js-ui.min.js"
SURVEYJS_CSS_CDN = "https://unpkg.com/survey-core@{version}/survey-core.min.css"

BUNDLE_FORMAT_VERSION = 1


def surveyjs_js_url(version: str = SURVEYJS_VERSION) -> str:
    return SURVEYJS_JS_CDN.format(version=version)


def surveyjs_ui_url(version: str = SURVEYJS_VERSION) -> str:
    return SURVEYJS_UI_CDN.format(version=version)


def surveyjs_css_url(version: str = SURVEYJS_VERSION) -> str:
    return SURVEYJS_CSS_CDN.format(version=version)
