"""Civic Trust 2026 — questionnaire module.

Run `siamang validate survey.py --strict`, `siamang preview survey.py`, or
import `survey` from Python. The module-level `options` dict carries the
compiler settings and the quota plan; `siamang validate` checks it too.
"""

import siamang as sg
from siamang.core import (
    AND, OR, ContentPage, DisqualificationPage, FinalPage, Quota,
)

from codebook import (
    ACTIVITIES, TRUST_ITEMS, age, comment, consent, education, employment, gender,
    interest, news_sources, recontact, region, variables, work_hours, work_sector,
)

PANEL = "https://panel.example.com/return"

# Respondents who consented and are adults see the main questionnaire.
eligible = AND(consent.eq(1), age.ge(18), region.ne(99))
# Page-level show_if must stay SurveyJS-exportable: no isin()/notin() there (see Part B2).
working = OR(employment.eq(1), employment.eq(2), employment.eq(3))

survey = sg.Questionnaire(
    title="Civic Trust 2026",
    variables=variables,
    pages=[
        ContentPage(
            "intro", title="About this study",
            body=("<p>This 8-minute survey asks how much people trust public institutions. "
                  "Answers are anonymous and reported only in aggregate.</p>"),
        ),
        sg.Page("consent_page", title="Your consent", items=[
            sg.SingleChoice("Do you agree to take part?", var=consent,
                            required=True, display="buttons"),
        ]),
        DisqualificationPage(
            "no_consent", title="Thank you", show_if=consent.eq(2),
            body="<p>No problem — thanks for considering it.</p>",
            redirect_url=f"{PANEL}?status=screenout", redirect_delay=5,
        ),
        sg.Page("screener", title="A few questions first", items=[
            sg.NumericInput("How old are you?", var=age, required=True, unit="years"),
            sg.SingleChoice("Where do you currently live?", var=region,
                            required=True, display="dropdown"),
        ]),
        DisqualificationPage(
            "screen_out", title="Thank you for your interest",
            show_if=~eligible,
            body="<p>This study is for adults living in the country.</p>",
            redirect_url=f"{PANEL}?status=screenout", redirect_delay=5,
        ),
        sg.Page("demographics", title="About you", show_if=eligible, items=[
            sg.SingleChoice("Which best describes you?", var=gender),
            sg.SingleChoice("What is your highest level of education?", var=education,
                            required=True),
            sg.SingleChoice("What is your current employment status?", var=employment,
                            required=True),
        ], next_if=[(employment.isin([4, 5]), "attitudes")]),   # skip the work page
        sg.Page("work", title="Your work", show_if=AND(eligible, working), items=[
            sg.SingleChoice("In which sector do you work?", var=work_sector),
            sg.NumericInput("How many hours do you usually work per week?",
                            var=work_hours, unit="hours"),
        ]),
        sg.Page("attitudes", title="Trust in institutions", show_if=eligible, items=[
            sg.Block(title="Institutions", randomize=True, items=[
                sg.Matrix(
                    "How much do you trust each of the following?",
                    var=TRUST_ITEMS,
                    subquestions=["The national government", "Parliament", "The courts",
                                  "The police", "The news media"],
                    # Columns come from the shared labels, including the "Don't know" code 98.
                ),
                sg.LikertScale("How interested are you in politics?", var=interest,
                               points=5, left_label="Not at all", right_label="Very"),
            ]),
            sg.MultiChoice("Where do you mainly get news about politics?", var=news_sources,
                           hint="Select all that apply", max_answers=3, exclusive=[99]),
            sg.MultiChoice("In the last 12 months, have you done any of the following?",
                           vars=ACTIVITIES),
        ]),
        sg.Page("closing", title="Almost done", show_if=eligible, items=[
            sg.OpenText("Is there anything you would like to add?", var=comment,
                        multiline=True, max_chars=500, placeholder="Optional"),
            sg.SingleChoice("May we contact you for a follow-up survey?", var=recontact,
                            display="buttons"),
        ]),
        FinalPage(
            "thanks", title="Thank you",
            body="<p>Your answers have been recorded. You will be returned to the panel.</p>",
            redirect_url=f"{PANEL}?status=complete", redirect_delay=4,
        ),
    ],
)

# Compiler options + the quota plan. `siamang validate` checks the quota cells
# against the codebook; `survey.deploy(**options)` attaches them to the deployment.
options = {
    "language": "en",
    "completion_text": "Thank you for taking part in Civic Trust 2026.",
    "metadata": {"wave": "2026-W1", "estimated_minutes": 8},
    "quota": [
        Quota("region", 1, limit=300),
        Quota("region", 2, limit=250),
        Quota("region", 3, limit=250),
        Quota("region", 4, limit=200),
        Quota("gender", 1, limit=520),
        Quota("gender", 2, limit=520),
    ],
}

if __name__ == "__main__":
    survey.validate(strict=True)
    for w in survey.lint(level="strict"):
        print(f"[{w.severity}] {w.code}: {w.message} ({w.location})")
    print(f"OK — {len(survey.all_questions())} questions on {len(survey.pages)} pages")
