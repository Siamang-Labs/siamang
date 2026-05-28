"""Step 1: Survey Design and Variable Specification.

This script defines the research variables and builds a multi-page survey exploring
attitudes toward remote work and digital surveillance among IT professionals.
It showcases:
1. Strict sociological variable definitions with scales and missing values.
2. Structured Questionnaire layout using Pages and Blocks.
3. Complex routing logic (show_if/hide_if).
"""

from __future__ import annotations

import siamang as sg
from siamang import (
    AND,
    OR,
    Block,
    LikertScale,
    Matrix,
    MissingValue,
    MultiChoice,
    NumericInput,
    OpenText,
    Page,
    Questionnaire,
    SingleChoice,
    Variable,
    VariableMap,
)

# ═══════════════════════════════════════════════════════════════════════════════
# 1. VARIABLES & CODEBOOK DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════

# Informed consent
consent = Variable(
    "consent",
    scale="nominal",
    label="Informed Consent",
    labels={1: "I agree to participate", 0: "I do not agree"},
)

# Demographics
age = Variable(
    "age",
    scale="ratio",
    label="Age",
    dtype="int",
    valid_range=(18, 75),
    description="Respondent age in years.",
)

gender = Variable(
    "gender",
    scale="nominal",
    label="Gender Identity",
    labels={1: "Male", 2: "Female", 3: "Non-binary", 4: "Prefer to self-describe"},
    missing=(MissingValue(code=9, label="Prefer not to say", kind="refusal"),),
)

# Professional Profile
it_role = Variable(
    "it_role",
    scale="nominal",
    label="IT Role",
    labels={
        1: "Software Engineer / Developer",
        2: "Data Scientist / Analyst",
        3: "DevOps / Infrastructure",
        4: "Product / Project Manager",
        5: "Other",
    },
)

experience = Variable(
    "experience",
    scale="ratio",
    label="Years of Experience",
    dtype="int",
    valid_range=(0, 50),
)

# Remote Work Frequency
remote_freq = Variable(
    "remote_freq",
    scale="ordinal",
    label="Remote Work Frequency",
    labels={
        1: "Never (Fully on-site)",
        2: "Occasionally (1-2 days/week remote)",
        3: "Hybrid (3 days/week remote)",
        4: "Mostly remote (4 days/week remote)",
        5: "Fully remote",
    },
)

# Digital Surveillance / Monitoring variables
surv_keystroke = Variable(
    "surv_keystroke",
    scale="ordinal",
    label="Keystroke logging / activity tracking",
    labels={1: "Strongly disagree", 2: "Disagree", 3: "Neutral", 4: "Agree", 5: "Strongly agree"},
)
surv_camera = Variable(
    "surv_camera",
    scale="ordinal",
    label="Webcam monitoring / periodic screenshots",
    labels={1: "Strongly disagree", 2: "Disagree", 3: "Neutral", 4: "Agree", 5: "Strongly agree"},
)
surv_git = Variable(
    "surv_git",
    scale="ordinal",
    label="Git commit frequency metrics",
    labels={1: "Strongly disagree", 2: "Disagree", 3: "Neutral", 4: "Agree", 5: "Strongly agree"},
)

# Job Satisfaction & Autonomy
satisfaction = Variable(
    "satisfaction",
    scale="ordinal",
    label="Overall Job Satisfaction",
    labels={1: "Very dissatisfied", 2: "Dissatisfied", 3: "Neutral", 4: "Satisfied", 5: "Very satisfied"},
)

autonomy = Variable(
    "autonomy",
    scale="ordinal",
    label="Workplace Autonomy",
    labels={1: "Very low", 2: "Low", 3: "Moderate", 4: "High", 5: "Very high"},
)

# Open-ended story
story = Variable(
    "story",
    scale="nominal",
    label="Experience with algorithmic management",
    description="Respondent narrative on surveillance or algorithmic management.",
)

# Aggregate all variables into a VariableMap registry
variables = VariableMap()
variables.add_many([
    consent,
    age,
    gender,
    it_role,
    experience,
    remote_freq,
    surv_keystroke,
    surv_camera,
    surv_git,
    satisfaction,
    autonomy,
    story,
])

# ═══════════════════════════════════════════════════════════════════════════════
# 2. QUESTIONNAIRE STRUCTURE (PAGES & BLOCKS)
# ═══════════════════════════════════════════════════════════════════════════════

# Page 1: Welcome & Consent
q_consent = SingleChoice(
    text="Welcome to the IT Workplace Study 2026. This academic survey explores the intersection "
         "of remote work, autonomy, and digital monitoring. Your responses are anonymous. "
         "Do you agree to participate?",
    var=consent,
    required=True,
    display="buttons",
)
page_welcome = Page(name="welcome", title="Consent Gate", items=[q_consent])

# Page 2: Demographics
q_age = NumericInput("How old are you?", var=age, required=True, unit="years")
q_gender = SingleChoice(
    "How do you identify your gender?",
    var=gender,
    required=True,
    display="radio",
    other_specify=True,
)
page_demographics = Page(
    name="demographics",
    title="Demographic Profile",
    items=[Block(title="Personal Information", items=[q_age, q_gender])],
    show_if=consent.eq(1),
)

# Page 3: Professional Profile
q_role = SingleChoice("What is your primary professional role?", var=it_role, required=True, display="dropdown")
q_exp = NumericInput("How many years of professional experience do you have?", var=experience, required=True, unit="years")
q_remote = SingleChoice("What is your current remote work arrangement?", var=remote_freq, required=True, display="radio")
page_professional = Page(
    name="professional",
    title="Professional Profile",
    items=[q_role, q_exp, q_remote],
    show_if=consent.eq(1),
)

# Page 4: Surveillance Matrix (Only shown to hybrid/remote workers)
q_surv = Matrix(
    text="To what extent do you agree that the following monitoring methods are acceptable at work?",
    var=[surv_keystroke, surv_camera, surv_git],
)
page_surveillance = Page(
    name="surveillance",
    title="Workplace Monitoring",
    items=[q_surv],
    # Show only if respondent works hybrid or remote (remote_freq >= 2)
    show_if=AND(consent.eq(1), remote_freq.ge(2)),
)

# Page 5: Satisfaction & Autonomy
q_sat = LikertScale("How would you rate your overall job satisfaction?", var=satisfaction, points=5)
q_aut = LikertScale("How much autonomy do you feel you have over your daily work tasks?", var=autonomy, points=5)
page_outcomes = Page(
    name="outcomes",
    title="Job Outcomes",
    items=[q_sat, q_aut],
    show_if=consent.eq(1),
)

# Page 6: Open-ended Experience
q_story = OpenText(
    text="Optional: Please share any specific experiences you have had with digital tracking, "
         "activity metrics, or algorithmic management at your current or past IT jobs.",
    var=story,
    multiline=True,
    max_chars=1000,
    placeholder="Write your story here...",
)
page_story = Page(
    name="story_page",
    title="Your Story",
    items=[q_story],
    show_if=consent.eq(1),
)

# ═══════════════════════════════════════════════════════════════════════════════
# 3. CONSTRUCTING THE QUESTIONNAIRE
# ═══════════════════════════════════════════════════════════════════════════════

survey = Questionnaire(
    title="IT Workplace, Autonomy & Monitoring Study 2026",
    pages=[
        page_welcome,
        page_demographics,
        page_professional,
        page_surveillance,
        page_outcomes,
        page_story,
    ],
    variables=variables,
)

if __name__ == "__main__":
    # Validate the survey design
    survey.validate(strict=True)
    print("✓ Survey validated successfully!")
    print(survey.preview())
