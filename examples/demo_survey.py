"""AI & Work Attitudes — A showcase survey demonstrating all question types,
advanced branching logic, theming, and the new font presets.

This example creates a realistic sociological survey studying attitudes toward
artificial intelligence in the workplace. It demonstrates:

* All question types: SingleChoice (radio, dropdown, buttons), MultiChoice
  (array + wide), LikertScale, NumericInput (input + slider), OpenText,
  Matrix, Ranking.
* Conditional logic: show_if / hide_if on pages, blocks, questions, and options.
* Composed expressions: AND, OR, NOT, operator overloads.
* Font preset theming: uses the "modern" preset with custom accent color.
* Lifecycle scripts: option randomization, custom validation.
* Quotas: age group and employment type caps.

Run:
    siamang preview examples/demo_survey.py --port 8000 --open

Or programmatically:
    from examples.demo_survey import survey
    survey.deploy(frontend_kwargs={"port": 8000, "open_browser": True})
"""

from __future__ import annotations

import siamang as sg
from siamang import (
    AND,
    NOT,
    OR,
    Block,
    LikertScale,
    Matrix,
    Media,
    MissingValue,
    MultiChoice,
    NumericInput,
    OpenText,
    Option,
    Page,
    Questionnaire,
    Quota,
    Ranking,
    Script,
    SingleChoice,
    Variable,
    VariableMap,
)
from siamang.frontend.theme.ui_config import UIConfig


# ═══════════════════════════════════════════════════════════════════════════════
# VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Screening & Demographics ─────────────────────────────────────────────────

consent = Variable(
    "consent", scale="nominal",
    label="Informed consent",
    labels={1: "Yes, I agree to participate", 0: "No, I do not wish to participate"},
)

age = Variable(
    "age", scale="ratio",
    label="Age in years",
    valid_range=(18, 80),
    description="Self-reported age of the respondent.",
)

gender = Variable(
    "gender", scale="nominal",
    label="Gender identity",
    labels={1: "Male", 2: "Female", 3: "Non-binary", 4: "Prefer to self-describe"},
    missing=(MissingValue(code=9, label="Prefer not to say", kind="refusal"),),
)

education = Variable(
    "education", scale="ordinal",
    label="Highest completed education",
    labels={
        1: "Secondary school or less",
        2: "Vocational / trade qualification",
        3: "Bachelor's degree",
        4: "Master's degree",
        5: "Doctoral degree (PhD)",
    },
)

country = Variable(
    "country", scale="nominal",
    label="Country of residence",
    labels={
        1: "United States", 2: "United Kingdom", 3: "Germany",
        4: "France", 5: "India", 6: "Brazil", 7: "Other",
    },
)

# ─── Employment & Industry ────────────────────────────────────────────────────

employment_status = Variable(
    "employment_status", scale="nominal",
    label="Current employment status",
    labels={
        1: "Full-time employee",
        2: "Part-time employee",
        3: "Freelancer / Self-employed",
        4: "Business owner / Entrepreneur",
        5: "Student (working part-time)",
        6: "Currently seeking employment",
        7: "Not in the labor force",
    },
)

industry = Variable(
    "industry", scale="nominal",
    label="Primary industry",
    labels={
        1: "Technology / IT",
        2: "Finance / Banking",
        3: "Healthcare / Medicine",
        4: "Education / Research",
        5: "Marketing / Advertising",
        6: "Manufacturing / Engineering",
        7: "Creative / Media / Design",
        8: "Government / Public sector",
        9: "Retail / E-commerce",
        10: "Other",
    },
)

years_experience = Variable(
    "years_experience", scale="ratio",
    label="Years of professional experience",
    valid_range=(0, 60),
)

team_size = Variable(
    "team_size", scale="ratio",
    label="Size of immediate team",
    valid_range=(1, 500),
)

remote_work = Variable(
    "remote_work", scale="ordinal",
    label="Remote work frequency",
    labels={
        1: "Fully on-site",
        2: "Mostly on-site (1-2 days remote)",
        3: "Hybrid (3 days remote)",
        4: "Mostly remote (4 days remote)",
        5: "Fully remote",
    },
)

# ─── AI Usage & Familiarity ───────────────────────────────────────────────────

ai_familiarity = Variable(
    "ai_familiarity", scale="ordinal",
    label="Self-assessed AI familiarity",
    labels={
        1: "Never heard of it",
        2: "Heard of it but never used",
        3: "Tried it a few times",
        4: "Use it regularly",
        5: "Expert / build AI systems",
    },
)

# Wide-mode MultiChoice — each tool becomes its own binary column
ai_tool_chatgpt = Variable("ai_tool_chatgpt", scale="nominal", label="ChatGPT", labels={0: "No", 1: "Yes"})
ai_tool_copilot = Variable("ai_tool_copilot", scale="nominal", label="GitHub Copilot", labels={0: "No", 1: "Yes"})
ai_tool_midjourney = Variable("ai_tool_midjourney", scale="nominal", label="Midjourney / DALL-E", labels={0: "No", 1: "Yes"})
ai_tool_grammarly = Variable("ai_tool_grammarly", scale="nominal", label="Grammarly AI", labels={0: "No", 1: "Yes"})
ai_tool_notion = Variable("ai_tool_notion", scale="nominal", label="Notion AI", labels={0: "No", 1: "Yes"})
ai_tool_custom = Variable("ai_tool_custom", scale="nominal", label="Custom / internal AI tool", labels={0: "No", 1: "Yes"})
ai_tool_none = Variable("ai_tool_none", scale="nominal", label="None of the above", labels={0: "No", 1: "Yes"})

ai_frequency = Variable(
    "ai_frequency", scale="ordinal",
    label="How often do you use AI tools at work",
    labels={
        1: "Never",
        2: "Less than once a month",
        3: "A few times a month",
        4: "A few times a week",
        5: "Daily",
        6: "Multiple times a day",
    },
)

ai_hours_saved = Variable(
    "ai_hours_saved", scale="ratio",
    label="Estimated hours saved per week using AI",
    valid_range=(0, 40),
)

# ─── Attitudes & Perceptions (Likert) ────────────────────────────────────────

def _attitude_var(name: str, label: str) -> Variable:
    return Variable(
        name, scale="ordinal", label=label,
        labels={1: "Strongly disagree", 2: "Disagree", 3: "Neutral", 4: "Agree", 5: "Strongly agree"},
    )

att_productivity = _attitude_var("att_productivity", "AI significantly improves my productivity")
att_creativity = _attitude_var("att_creativity", "AI enhances my creative output")
att_quality = _attitude_var("att_quality", "AI improves the quality of my work")
att_learning = _attitude_var("att_learning", "AI helps me learn new skills faster")
att_replacement = _attitude_var("att_replacement", "AI could replace my job within 5 years")
att_inequality = _attitude_var("att_inequality", "AI increases inequality between workers")
att_surveillance = _attitude_var("att_surveillance", "AI-based monitoring at work is concerning")
att_trust = _attitude_var("att_trust", "I trust AI-generated outputs without verification")

# ─── Organizational context ───────────────────────────────────────────────────

org_ai_policy = Variable(
    "org_ai_policy", scale="nominal",
    label="Organization's AI policy",
    labels={
        1: "AI is actively encouraged and supported",
        2: "AI is allowed but not formally supported",
        3: "No official policy exists",
        4: "AI use is restricted or discouraged",
        5: "AI is explicitly banned",
    },
)

org_training = Variable(
    "org_training", scale="nominal",
    label="AI training provided by employer",
    labels={
        1: "Comprehensive training program",
        2: "Some workshops or resources",
        3: "Informal peer learning only",
        4: "No training at all",
    },
)

# ─── Future outlook ──────────────────────────────────────────────────────────

future_optimism = Variable(
    "future_optimism", scale="ordinal",
    label="Optimism about AI's impact on work",
    labels={1: "Very pessimistic", 2: "Somewhat pessimistic", 3: "Neutral", 4: "Somewhat optimistic", 5: "Very optimistic"},
)

# Ranking: most important concerns
concern_rank = Variable(
    "concern_rank", scale="ordinal",
    label="AI concerns ranked by importance",
    labels={
        1: "Job displacement",
        2: "Privacy and surveillance",
        3: "Bias and discrimination",
        4: "Loss of human skills",
        5: "Economic inequality",
        6: "Misinformation",
    },
)

# Skills that will matter most (array-mode MultiChoice)
future_skills = Variable(
    "future_skills", scale="nominal",
    label="Most important future skills",
    labels={
        1: "Critical thinking",
        2: "Creativity and innovation",
        3: "Emotional intelligence",
        4: "Technical AI literacy",
        5: "Adaptability and learning agility",
        6: "Leadership and collaboration",
        7: "Domain expertise",
    },
)

# ─── Open-ended ──────────────────────────────────────────────────────────────

ai_story = Variable("ai_story", scale="nominal", label="Personal AI experience story")
feedback = Variable("feedback", scale="nominal", label="Additional comments")

# ═══════════════════════════════════════════════════════════════════════════════
# VARIABLE MAP
# ═══════════════════════════════════════════════════════════════════════════════

variables = VariableMap()
variables.add_many([
    consent, age, gender, education, country,
    employment_status, industry, years_experience, team_size, remote_work,
    ai_familiarity,
    ai_tool_chatgpt, ai_tool_copilot, ai_tool_midjourney,
    ai_tool_grammarly, ai_tool_notion, ai_tool_custom, ai_tool_none,
    ai_frequency, ai_hours_saved,
    att_productivity, att_creativity, att_quality, att_learning,
    att_replacement, att_inequality, att_surveillance, att_trust,
    org_ai_policy, org_training,
    future_optimism, concern_rank, future_skills,
    ai_story, feedback,
])


# ═══════════════════════════════════════════════════════════════════════════════
# PAGES
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Page 1: Welcome & Consent ────────────────────────────────────────────────

q_consent = SingleChoice(
    "This survey explores how artificial intelligence is changing the way we work. "
    "Your responses are anonymous and will be used for academic research only. "
    "Do you agree to participate?",
    var=consent,
    required=True,
    display="buttons",
    hint=(
        "Participation is voluntary. You may stop at any time. "
        "The survey takes approximately 8-10 minutes to complete."
    ),
)

page_welcome = Page(
    name="welcome",
    title="AI & Work Attitudes Study 2026",
    items=[q_consent],
)


# ─── Page 2: Demographics ─────────────────────────────────────────────────────

q_age = NumericInput(
    "How old are you?",
    var=age,
    required=True,
    display="input",
    step=1,
    unit="years",
)

q_gender = SingleChoice(
    "How do you identify?",
    var=gender,
    required=True,
    display="buttons",
    other_specify=True,
    metadata={"other_label": "Prefer to self-describe", "other_placeholder": "How do you identify?"},
)

q_education = SingleChoice(
    "What is the highest level of education you have completed?",
    var=education,
    display="dropdown",
    required=True,
)

q_country = SingleChoice(
    "In which country do you currently reside?",
    var=country,
    display="dropdown",
    required=True,
)

page_demographics = Page(
    name="demographics",
    title="About You",
    items=[
        Block(title="Demographics", items=[q_age, q_gender, q_education, q_country]),
    ],
    show_if=consent.eq(1),
)


# ─── Page 3: Employment & Work Context ────────────────────────────────────────

q_employment = SingleChoice(
    "Which best describes your current employment situation?",
    var=employment_status,
    required=True,
    display="radio",
    choices=[
        Option(1, "Full-time employee"),
        Option(2, "Part-time employee"),
        Option(3, "Freelancer / Self-employed"),
        Option(4, "Business owner / Entrepreneur"),
        Option(5, "Student (working part-time)", show_if=age.le(35)),
        Option(6, "Currently seeking employment"),
        Option(7, "Not in the labor force"),
    ],
)

q_industry = SingleChoice(
    "What is your primary industry?",
    var=industry,
    display="dropdown",
    required=True,
    # Only show for people who are actually working
    show_if=OR(
        employment_status.eq(1),
        employment_status.eq(2),
        employment_status.eq(3),
        employment_status.eq(4),
    ),
)

q_years_exp = NumericInput(
    "How many years of professional experience do you have?",
    var=years_experience,
    display="slider",
    step=1,
    unit="years",
    show_if=OR(
        employment_status.eq(1),
        employment_status.eq(2),
        employment_status.eq(3),
        employment_status.eq(4),
    ),
)

q_team_size = NumericInput(
    "How many people are on your immediate team?",
    var=team_size,
    display="input",
    step=1,
    hint="Include yourself. If you work alone, enter 1.",
    show_if=OR(
        employment_status.eq(1),
        employment_status.eq(2),
        employment_status.eq(3),
        employment_status.eq(4),
    ),
)

q_remote = SingleChoice(
    "How would you describe your work arrangement?",
    var=remote_work,
    display="radio",
    show_if=OR(
        employment_status.eq(1),
        employment_status.eq(2),
        employment_status.eq(3),
        employment_status.eq(4),
    ),
)

page_employment = Page(
    name="employment",
    title="Your Work",
    items=[q_employment, q_industry, q_years_exp, q_team_size, q_remote],
    show_if=consent.eq(1),
)


# ─── Page 4: AI Usage & Familiarity ──────────────────────────────────────────

q_ai_familiarity = LikertScale(
    "How would you rate your familiarity with AI tools?",
    var=ai_familiarity,
    points=5,
    left_label="Never heard of it",
    right_label="Expert",
    required=True,
)

q_ai_tools = MultiChoice(
    "Which AI tools have you used for work in the past 6 months?",
    vars=[ai_tool_chatgpt, ai_tool_copilot, ai_tool_midjourney,
          ai_tool_grammarly, ai_tool_notion, ai_tool_custom, ai_tool_none],
    randomize=True,
    id="ai_tools_used",
)

q_ai_frequency = SingleChoice(
    "How often do you use AI tools in your work?",
    var=ai_frequency,
    display="radio",
    required=True,
    # Only ask if they've at least tried AI
    show_if=ai_familiarity.ge(3),
)

q_hours_saved = NumericInput(
    "Approximately how many hours per week do AI tools save you?",
    var=ai_hours_saved,
    display="slider",
    step=0.5,
    unit="hours/week",
    hint="Your best estimate is fine. Consider time saved on writing, coding, research, etc.",
    # Only ask frequent users
    show_if=ai_frequency.ge(3),
)

page_ai_usage = Page(
    name="ai_usage",
    title="Your AI Experience",
    items=[
        Block(title="Familiarity", items=[q_ai_familiarity, q_ai_tools]),
        Block(title="Usage patterns", items=[q_ai_frequency, q_hours_saved]),
    ],
    show_if=consent.eq(1),
)


# ─── Page 5: Attitudes Matrix ────────────────────────────────────────────────

q_attitudes_positive = Matrix(
    "To what extent do you agree with the following statements about AI at work?",
    var=[att_productivity, att_creativity, att_quality, att_learning],
    hint="Think about your personal experience over the past year.",
)

q_attitudes_concerns = Matrix(
    "And how do you feel about these potential concerns?",
    var=[att_replacement, att_inequality, att_surveillance, att_trust],
)

page_attitudes = Page(
    name="attitudes",
    title="Your Views on AI",
    items=[
        Block(title="Perceived benefits", items=[q_attitudes_positive]),
        Block(title="Concerns", items=[q_attitudes_concerns]),
    ],
    show_if=AND(consent.eq(1), ai_familiarity.ge(2)),
)


# ─── Page 6: Organizational Context ──────────────────────────────────────────

q_org_policy = SingleChoice(
    "How would you describe your organization's stance on AI?",
    var=org_ai_policy,
    display="radio",
    required=True,
)

q_org_training = SingleChoice(
    "What AI-related training does your employer provide?",
    var=org_training,
    display="radio",
)

page_org = Page(
    name="organization",
    title="AI in Your Organization",
    items=[q_org_policy, q_org_training],
    # Only employed respondents
    show_if=AND(
        consent.eq(1),
        OR(employment_status.eq(1), employment_status.eq(2), employment_status.eq(4)),
    ),
)


# ─── Page 7: Future Outlook ──────────────────────────────────────────────────

q_future_optimism = LikertScale(
    "Overall, how optimistic are you about AI's impact on the future of work?",
    var=future_optimism,
    points=5,
    left_label="Very pessimistic",
    right_label="Very optimistic",
    required=True,
)

q_concerns_rank = Ranking(
    "Please rank the following AI-related concerns from most to least important to you:",
    var=concern_rank,
    max_ranked=6,
    choices=[
        Option(1, "Job displacement and unemployment"),
        Option(2, "Privacy and workplace surveillance"),
        Option(3, "Algorithmic bias and discrimination"),
        Option(4, "Loss of human skills and expertise"),
        Option(5, "Growing economic inequality"),
        Option(6, "Spread of misinformation"),
    ],
)

q_future_skills = MultiChoice(
    "Which skills do you think will be most important in an AI-driven workplace? (choose up to 3)",
    var=future_skills,
    min_answers=1,
    max_answers=3,
    other_specify=True,
    metadata={"other_placeholder": "Name another skill..."},
)

page_future = Page(
    name="future",
    title="Looking Ahead",
    items=[q_future_optimism, q_concerns_rank, q_future_skills],
    show_if=consent.eq(1),
)


# ─── Page 8: Open-Ended ──────────────────────────────────────────────────────

q_ai_story = OpenText(
    "Can you share a specific experience where AI significantly helped or hindered your work?",
    var=ai_story,
    multiline=True,
    max_chars=1500,
    placeholder="For example: 'Last month I used ChatGPT to draft a proposal and it saved me 3 hours, but I had to fact-check everything...'",
    hint="Your story helps us understand real-world AI impact beyond statistics.",
)

q_feedback = OpenText(
    "Any additional thoughts on AI and work that we haven't covered?",
    var=feedback,
    multiline=True,
    max_chars=1000,
    placeholder="Optional — all feedback is appreciated.",
)

page_openended = Page(
    name="open_ended",
    title="Your Story",
    items=[q_ai_story, q_feedback],
    show_if=consent.eq(1),
)


# ═══════════════════════════════════════════════════════════════════════════════
# QUOTAS
# ═══════════════════════════════════════════════════════════════════════════════

quotas = [
    Quota(variable="gender", target_value=1, limit=300),
    Quota(variable="gender", target_value=2, limit=300),
    Quota(variable="employment_status", target_value=1, limit=250),
]


# ═══════════════════════════════════════════════════════════════════════════════
# LIFECYCLE SCRIPTS
# ═══════════════════════════════════════════════════════════════════════════════

# Randomize the order of AI tools to avoid primacy bias
shuffle_ai_tools = Script.randomize_options("ai_tools_used")


# ═══════════════════════════════════════════════════════════════════════════════
# UI CONFIGURATION — using the "modern" font preset with custom colors
# ═══════════════════════════════════════════════════════════════════════════════

ui = UIConfig(
    font_preset="modern",
    primary_color="#6366f1",          # Indigo
    accent_color="#8b5cf6",           # Purple accent
    background_color="#fafafa",
    surface_color="#ffffff",
    radius="8px",
    density="comfortable",
    width="720px",
    question_style="carded",
    institution_name="Digital Society Lab",
    study_subtitle="Understanding AI's impact on modern work",
    privacy_url="https://example.com/privacy",
    contact_email="research@digitalsocietylab.org",
    ethics_statement="This study has been approved by the Ethics Committee (ref: DSL-2026-042).",
    estimated_minutes=10,
    progress_style="both",
    default_theme="light",
    allow_back=True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# QUESTIONNAIRE
# ═══════════════════════════════════════════════════════════════════════════════

survey = Questionnaire(
    title="AI & Work Attitudes Study 2026",
    pages=[
        page_welcome,
        page_demographics,
        page_employment,
        page_ai_usage,
        page_attitudes,
        page_org,
        page_future,
        page_openended,
    ],
    variables=variables,
    scripts=[shuffle_ai_tools],
)


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    survey.validate(strict=False)
    print(survey.preview())

    data = survey.simulate(n=300, seed=42)
    print("\nFirst 5 rows of simulated data:")
    print(data.frame.head())

    print("\nAI familiarity — frequencies:")
    print(data.analysis.frequencies("ai_familiarity", labels=True, normalize=True))

    print("\nEmployment × AI frequency crosstab:")
    print(data.analysis.crosstab("employment_status", "ai_frequency", labels=True))
