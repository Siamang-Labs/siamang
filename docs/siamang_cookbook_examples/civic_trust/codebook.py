"""Codebook for the Civic Trust 2026 study.

Every Variable is defined exactly once here and imported by the survey
module, the tests, and the analysis scripts, so the codebook can never
drift from the instrument.
"""

import siamang as sg
from siamang.core import MissingValue

# ── Shared label scales ──────────────────────────────────────────────────────
TRUST5 = {1: "No trust at all", 2: "Little trust", 3: "Some trust",
          4: "Quite a lot of trust", 5: "Complete trust"}
YESNO = {0: "No", 1: "Yes"}

# ── Screening ────────────────────────────────────────────────────────────────
consent = sg.Variable("consent", scale="nominal", label="Informed consent",
                      labels={1: "I agree to take part", 2: "I do not agree"})
age = sg.Variable("age", scale="ratio", label="Age (years)", dtype="int",
                  valid_range=(16, 99))
region = sg.Variable(
    "region", scale="nominal", label="Region of residence",
    labels={1: "Capital", 2: "North", 3: "South", 4: "East", 99: "Outside the country"},
)

# ── Demographics ─────────────────────────────────────────────────────────────
gender = sg.Variable(
    "gender", scale="nominal", label="Gender",
    labels={1: "Woman", 2: "Man", 3: "Other", 99: "Prefer not to say"},
    missing=(MissingValue(99, "Prefer not to say", kind="refusal"),),
)
education = sg.Variable(
    "education", scale="ordinal", label="Highest education",
    labels={1: "Primary", 2: "Secondary", 3: "Vocational", 4: "University"},
)
employment = sg.Variable(
    "employment", scale="nominal", label="Employment status",
    labels={1: "Employed full-time", 2: "Employed part-time", 3: "Self-employed",
            4: "Student", 5: "Not working"},
)
work_sector = sg.Variable(
    "work_sector", scale="nominal", label="Sector of employment",
    labels={1: "Public", 2: "Private", 3: "Non-profit"},
)
work_hours = sg.Variable("work_hours", scale="ratio", label="Weekly working hours",
                         dtype="int", valid_range=(0, 80))

# ── Trust battery (five ordinal items, one construct) ────────────────────────
def _trust(name: str, label: str) -> sg.Variable:
    return sg.Variable(
        name, scale="ordinal", label=label,
        # A declared missing code must also appear in the labels (lint MISSING_CODE_NOT_IN_LABELS).
        labels={**TRUST5, 98: "Don't know"},
        missing=(MissingValue(98, "Don't know", kind="dont_know"),),
        construct="institutional_trust", source="ESS Round 10 (adapted)",
    )

trust_govt = _trust("trust_govt", "Trust in the national government")
trust_parliament = _trust("trust_parliament", "Trust in parliament")
trust_courts = _trust("trust_courts", "Trust in the courts")
trust_police = _trust("trust_police", "Trust in the police")
trust_media = _trust("trust_media", "Trust in the news media")
TRUST_ITEMS = [trust_govt, trust_parliament, trust_courts, trust_police, trust_media]

interest = sg.Variable(
    "interest", scale="ordinal", label="Interest in politics",
    labels={1: "Not at all", 2: "A little", 3: "Somewhat", 4: "Quite", 5: "Very"},
)

# ── Media use: array-mode MultiChoice (one column holding a list of codes) ────
news_sources = sg.Variable(
    "news_sources", scale="nominal", label="Main news sources",
    labels={1: "Television", 2: "Newspapers", 3: "News websites", 4: "Social media",
            5: "Radio", 99: "I do not follow the news"},
)

# ── Civic activity: wide-mode MultiChoice (one 0/1 column per activity) ──────
act_vote = sg.Variable("act_vote", scale="nominal", label="Voted in an election", labels=YESNO)
act_petition = sg.Variable("act_petition", scale="nominal", label="Signed a petition", labels=YESNO)
act_protest = sg.Variable("act_protest", scale="nominal", label="Joined a demonstration", labels=YESNO)
act_volunteer = sg.Variable("act_volunteer", scale="nominal", label="Volunteered", labels=YESNO)
ACTIVITIES = [act_vote, act_petition, act_protest, act_volunteer]

# ── Closing ──────────────────────────────────────────────────────────────────
comment = sg.Variable("comment", scale="nominal", label="Open comment")
recontact = sg.Variable("recontact", scale="nominal", label="Willing to be recontacted",
                        labels={1: "Yes", 2: "No"})

# ── The registry: the single source of truth for the study ──────────────────
variables = sg.VariableMap()
variables.add_many([
    consent, age, region, gender, education, employment, work_sector, work_hours,
    *TRUST_ITEMS, interest, news_sources, *ACTIVITIES, comment, recontact,
])
