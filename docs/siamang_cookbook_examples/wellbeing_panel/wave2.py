"""Wellbeing Panel — wave 2 (three months later). Adds a job-change question."""

from datetime import datetime, timezone

import siamang as sg
from siamang.core import ContentPage, FinalPage

from codebook import WB_ITEMS, age, core_variables, employment, gender, life_sat, remote_days
from wave1 import capture_pid

# Wave-specific additions are registered on top of the shared codebook.
job_change = sg.Variable("job_change", scale="nominal",
                         label="Changed job since the last wave",
                         labels={1: "Yes", 2: "No"})
variables = core_variables()
variables.add(job_change)

survey = sg.Questionnaire(
    title="Wellbeing Panel — Wave 2",
    variables=variables,
    scripts=[capture_pid],
    deadline=datetime(2027, 1, 31, 23, 59, tzinfo=timezone.utc),
    pages=[
        ContentPage("intro", title="Welcome back", body="<p>Wave 2 of 3. About 5 minutes.</p>"),
        sg.Page("about", title="About you", items=[
            sg.NumericInput("How old are you?", var=age, required=True, unit="years"),
            sg.SingleChoice("Which best describes you?", var=gender),
            sg.SingleChoice("What is your current employment status?", var=employment,
                            required=True),
            sg.SingleChoice("Have you changed jobs since the last survey?", var=job_change,
                            show_if=employment.isin([1, 2])),
            sg.NumericInput("How many days a week do you work from home?", var=remote_days,
                            display="slider", show_if=employment.isin([1, 2])),
        ]),
        sg.Page("wellbeing", title="Over the last two weeks…", items=[
            sg.Matrix("Please indicate for each statement which is closest to how you have "
                      "been feeling.", var=WB_ITEMS),
            sg.NumericInput("All things considered, how satisfied are you with your life "
                            "as a whole?", var=life_sat, display="slider", step=1),
        ]),
        FinalPage("thanks", title="Thank you", body="<p>One more wave to go.</p>"),
    ],
)

options = {"max_responses": 2000, "metadata": {"wave": 2}}
