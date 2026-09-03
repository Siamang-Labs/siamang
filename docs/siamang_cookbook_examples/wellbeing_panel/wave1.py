"""Wellbeing Panel — wave 1 (baseline)."""

from datetime import datetime, timezone

import siamang as sg
from siamang.core import ContentPage, FinalPage

from codebook import WB_ITEMS, age, core_variables, employment, gender, life_sat, remote_days

# The panel provider appends ?pid=<member id> to the survey link; an onInit script
# copies it into the answers so it is stored with every submission.
capture_pid = sg.Script(
    name="capture_panel_id", trigger="onInit",
    code="answers.panel_id = new URLSearchParams(window.location.search).get('pid') || 'unknown';",
)

variables = core_variables()          # wave 1 uses the core codebook as-is

survey = sg.Questionnaire(
    title="Wellbeing Panel — Wave 1",
    variables=variables,
    scripts=[capture_pid],
    deadline=datetime(2026, 10, 31, 23, 59, tzinfo=timezone.utc),
    pages=[
        ContentPage("intro", title="Welcome back", body="<p>Wave 1 of 3. About 5 minutes.</p>"),
        sg.Page("about", title="About you", items=[
            sg.NumericInput("How old are you?", var=age, required=True, unit="years"),
            sg.SingleChoice("Which best describes you?", var=gender),
            sg.SingleChoice("What is your current employment status?", var=employment,
                            required=True),
            sg.NumericInput("How many days a week do you work from home?", var=remote_days,
                            display="slider", show_if=employment.isin([1, 2])),
        ]),
        sg.Page("wellbeing", title="Over the last two weeks…", items=[
            sg.Matrix("Please indicate for each statement which is closest to how you have "
                      "been feeling.", var=WB_ITEMS),
            sg.NumericInput("All things considered, how satisfied are you with your life "
                            "as a whole?", var=life_sat, display="slider", step=1,
                            hint="0 = extremely dissatisfied, 10 = extremely satisfied"),
        ]),
        FinalPage("thanks", title="Thank you", body="<p>See you next quarter.</p>"),
    ],
)

options = {"max_responses": 2000, "metadata": {"wave": 1}}
