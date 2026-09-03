"""Customer Pulse — a branded NPS / satisfaction survey in one file."""

import dataclasses

import siamang as sg
from siamang.core import ContentPage, FinalPage
from siamang.frontend import get_preset

AGREE5 = {1: "Very poor", 2: "Poor", 3: "Fair", 4: "Good", 5: "Excellent"}

# ── Codebook ─────────────────────────────────────────────────────────────────
customer_type = sg.Variable("customer_type", scale="nominal", label="Customer type",
                            labels={1: "New (under 1 year)", 2: "Returning", 3: "Business account"})
product = sg.Variable("product", scale="nominal", label="Product used most",
                      labels={1: "Web app", 2: "Mobile app", 3: "API", 99: "Other"})
nps = sg.Variable("nps", scale="interval", label="Likelihood to recommend (0-10)",
                  dtype="int", valid_range=(0, 10))
attr_price = sg.Variable("attr_price", scale="ordinal", label="Value for money", labels=AGREE5)
attr_quality = sg.Variable("attr_quality", scale="ordinal", label="Product quality", labels=AGREE5)
attr_support = sg.Variable("attr_support", scale="ordinal", label="Customer support", labels=AGREE5)
attr_speed = sg.Variable("attr_speed", scale="ordinal", label="Speed of delivery", labels=AGREE5)
ATTRIBUTES = [attr_price, attr_quality, attr_support, attr_speed]
overall_sat = sg.Variable("overall_sat", scale="ordinal", label="Overall satisfaction",
                          labels={1: "Very dissatisfied", 2: "Dissatisfied", 3: "Neutral",
                                  4: "Satisfied", 5: "Very satisfied"})
channel_pref = sg.Variable("channel_pref", scale="nominal", label="Preferred support channel",
                           labels={1: "Email", 2: "Phone", 3: "Live chat", 4: "Help centre"})
priorities = sg.Variable("priorities", scale="ordinal", label="Improvement priorities",
                         labels={1: "Lower price", 2: "More features", 3: "Better support",
                                 4: "Faster delivery", 5: "Better documentation"})
comment = sg.Variable("comment", scale="nominal", label="What could we do better?")
contact_ok = sg.Variable("contact_ok", scale="nominal", label="May we follow up?",
                         labels={1: "Yes", 2: "No"})

# ── Questionnaire ─────────────────────────────────────────────────────────────
survey = sg.Questionnaire(
    title="Customer Pulse 2026",
    pages=[
        ContentPage("intro", title="Two minutes of your time",
                    body="<p>Tell us how we are doing. Five questions, no wrong answers.</p>"),
        sg.Page("profile", title="About your account", items=[
            sg.SingleChoice("Which best describes you?", var=customer_type,
                            required=True, display="buttons"),
            sg.SingleChoice("Which product do you use most?", var=product,
                            other_specify=True,                 # adds "Other (please specify)"
                            metadata={"other_placeholder": "Tell us which"}),
        ]),
        sg.Page("nps_page", title="The big question", items=[
            sg.NumericInput("How likely are you to recommend us to a friend or colleague?",
                            var=nps, display="slider", step=1, required=True,
                            hint="0 = not at all likely, 10 = extremely likely"),
        ]),
        sg.Page("experience", title="Your experience", items=[
            sg.Matrix("How would you rate the following?", var=ATTRIBUTES,
                      na_option="Not used"),                     # stored as the string "na"
            sg.LikertScale("Overall, how satisfied are you?", var=overall_sat, points=5,
                           left_label="Very dissatisfied", right_label="Very satisfied",
                           required=True),
            sg.SingleChoice("How do you prefer to contact support?", var=channel_pref,
                            none_of_above=True),                 # stored as "__none__"
        ]),
        sg.Page("wishes", title="What next?", items=[
            sg.Ranking("Rank your top three priorities for us", var=priorities, max_ranked=3),
            sg.OpenText("What is the one thing we could do better?", var=comment,
                        multiline=True, max_chars=400),
            sg.SingleChoice("May we contact you about your answers?", var=contact_ok,
                            display="buttons"),
        ]),
        FinalPage("thanks", title="Thank you!", body="<p>We read every answer.</p>"),
    ],
)

# ── Compiler options (no quotas here) ────────────────────────────────────────
options = {
    "one_question_per_page": False,
    "show_progress": True,
    "completion_text": "Thanks — your feedback shapes our roadmap.",
    "metadata": {"wave": "2026-Q3", "estimated_minutes": 2},
}

# ── Branding: start from a preset, override what matters ─────────────────────
ui = dataclasses.replace(
    get_preset("modern"),
    institution_name="Acme Analytics",
    study_subtitle="Customer Pulse 2026",
    logo_text="AA",
    primary_color="#0f766e",
    question_style="carded",
    estimated_minutes=2,
    contact_email="pulse@acme.example",
    privacy_url="https://acme.example/privacy",
    progress_style="dots",
    # Gate the pilot behind an access code (respondents enter it on the first screen)
    require_access_code=True,
    access_codes=["PILOT-2026"],
    access_title="Pilot access",
    access_body="Enter the code from your invitation email.",
    custom_css=".sd-question { border-left: 3px solid #0f766e; }",
)

if __name__ == "__main__":
    survey.validate(strict=True)
    print(f"OK — {len(survey.all_questions())} questions")
