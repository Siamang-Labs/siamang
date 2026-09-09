"""Digital Life & Wellbeing 2026 — example questionnaire.

A compact, self-contained survey that shows the engine's core building blocks
in one readable file: every question type, conditional logic at the page,
question, block and option level (with AND / NOT / isin), block and option
randomization, fieldwork quotas and a small codebook with a missing value.

The platform loads the module-level `survey` object (and the optional `options`
dict for compiler settings and quotas).
"""

from siamang.core import (
    AND,
    NOT,
    Block,
    ContentPage,
    DisqualificationPage,
    FinalPage,
    LikertScale,
    Matrix,
    MissingValue,
    MultiChoice,
    NumericInput,
    OpenText,
    Option,
    Page,
    Questionnaire,
    Quota,
    Ranking,
    RedirectPage,
    Script,
    SingleChoice,
    Variable,
)

# ── Shared label scales (reused across several variables) ─────────────────────
AGREE5 = {1: "Strongly disagree", 2: "Disagree", 3: "Neutral",
          4: "Agree", 5: "Strongly agree"}
FREQ5 = {1: "Never", 2: "Rarely", 3: "Sometimes", 4: "Often", 5: "Always"}
YESNO = {0: "No", 1: "Yes"}

# ── Variables (the codebook lives next to the questions) ──────────────────────
consent = Variable("consent", scale="nominal", label="Consent to take part",
                   labels={1: "Yes, I agree", 2: "No, not now"})
age = Variable("age", scale="ratio", label="Age in years", role="input",
               valid_range=(13, 99))
gender = Variable(
    "gender", scale="nominal", label="Gender",
    labels={1: "Woman", 2: "Man", 3: "Non-binary", 99: "Prefer not to say"},
    # A codebook with a structured missing value: 99 is a refusal, not a real
    # category, so analysis can exclude it cleanly.
    missing=(MissingValue(99, "Prefer not to say", kind="refusal"),),
)
age_group = Variable("age_group", scale="ordinal", label="Age group",
                     labels={1: "16-29", 2: "30-44", 3: "45+"})
region = Variable("region", scale="nominal", label="Type of area",
                  labels={1: "City center", 2: "Suburbs", 3: "Small town",
                          4: "Rural"})
employment = Variable("employment", scale="nominal", label="Employment status",
                      labels={1: "Full-time", 2: "Part-time", 3: "Self-employed",
                              4: "Student", 5: "Not working"})
work_mode = Variable("work_mode", scale="nominal", label="Current work mode",
                     labels={1: "Fully remote", 2: "Hybrid", 3: "On-site"})
commute_minutes = Variable("commute_minutes", scale="ratio",
                           label="One-way commute (minutes)",
                           valid_range=(0, 240))

owns_smartphone = Variable("owns_smartphone", scale="nominal",
                           label="Owns a smartphone", labels=YESNO)
owns_laptop = Variable("owns_laptop", scale="nominal", label="Owns a laptop",
                       labels=YESNO)
owns_tablet = Variable("owns_tablet", scale="nominal", label="Owns a tablet",
                       labels=YESNO)
owns_smartwatch = Variable("owns_smartwatch", scale="nominal",
                           label="Owns a smartwatch", labels=YESNO)
primary_device = Variable("primary_device", scale="nominal",
                          label="Most-used device",
                          labels={1: "Smartphone", 2: "Laptop", 3: "Tablet",
                                  4: "Smartwatch"})

social_freq = Variable("social_freq", scale="ordinal", label="Social media use",
                       labels={1: "Never", 2: "Weekly", 3: "Daily",
                               4: "Many times a day"})
doomscroll = Variable("doomscroll", scale="ordinal",
                      label="I scroll longer than I meant to", labels=AGREE5)
news_source = Variable("news_source", scale="nominal", label="Main source of news",
                       labels={1: "Social media", 2: "News apps", 3: "TV / radio",
                               4: "Friends / family", 5: "I avoid news"})
trust_news = Variable("trust_news", scale="ordinal",
                      label="I trust most of the news I see", labels=AGREE5)
screen_time_hours = Variable("screen_time_hours", scale="ratio",
                             label="Screen time (hours/day)", valid_range=(0, 24))
manage = Variable("manage", scale="nominal",
                  label="Ways of managing screen time",
                  labels={1: "App time limits", 2: "Phone-free meals",
                          3: "Grayscale screen", 4: "Notifications off",
                          99: "None of these"})

feel_rested = Variable("feel_rested", scale="ordinal", label="Wake up rested",
                       labels=FREQ5)
can_focus = Variable("can_focus", scale="ordinal",
                     label="Focus without my phone", labels=FREQ5)
feel_anxious = Variable("feel_anxious", scale="ordinal",
                        label="Anxious about messages", labels=FREQ5)
in_control = Variable("in_control", scale="ordinal",
                      label="In control of my screen time", labels=FREQ5)
sleep_quality = Variable("sleep_quality", scale="ordinal", label="Sleep well",
                         labels=FREQ5)
life_satisfaction = Variable("life_satisfaction", scale="ordinal",
                             label="Overall life satisfaction")
disconnect_rank = Variable("disconnect_rank", scale="nominal",
                           label="What helps you disconnect",
                           labels={1: "Time outdoors", 2: "Exercise",
                                   3: "Seeing people", 4: "A good book",
                                   5: "Switching the phone off"})
nps = Variable("nps", scale="interval",
               label="Likelihood to try a digital detox (0-10)",
               valid_range=(0, 10))
improve = Variable("improve", scale="nominal",
                   label="One change to your digital life")
recontact = Variable("recontact", scale="nominal", label="Open to a follow-up",
                     labels={1: "Yes", 2: "No"})

# ── Survey ────────────────────────────────────────────────────────────────────
survey = Questionnaire(
    title="Digital Life & Wellbeing 2026",
    # One lifecycle script: shuffle the news-source options on show. Block and
    # option randomization is declared inline with randomize / randomize_blocks.
    scripts=[Script.randomize_options("news_source")],
    pages=[
        ContentPage(
            "intro",
            title="About this study",
            body=(
                "<h2>Digital Life &amp; Wellbeing 2026</h2>"
                "<p>A short, anonymous study on how everyday technology use "
                "relates to how we feel. It takes about five minutes and your "
                "answers are only ever reported in aggregate.</p>"
                "<p>Continue to give your consent and begin.</p>"
            ),
        ),
        Page("consent_page", title="Your consent", items=[
            SingleChoice("Do you agree to take part?", consent, required=True,
                         display="buttons"),
        ]),
        # Page-level show_if: a terminal screen-out for anyone who declines.
        DisqualificationPage(
            "no_consent",
            title="No problem",
            show_if=consent.eq(2),
            body="<p>That is completely fine — thanks for stopping by.</p>",
        ),
        Page("screening", title="A quick check", items=[
            NumericInput("How old are you?", age, required=True, unit="years"),
        ]),
        # Page-level show_if on a comparison: under-16s are screened out.
        DisqualificationPage(
            "under_age",
            title="Thanks for your interest",
            show_if=age.lt(16),
            body=("<p>This study is for people aged 16 and over, so we cannot "
                  "include your answers this time.</p>"),
        ),
        Page("about_you", title="About you", items=[
            # An explicit Option list (keeps the refusal code in a sensible place).
            SingleChoice("Which best describes your gender?", gender, choices=[
                Option(1, "Woman"),
                Option(2, "Man"),
                Option(3, "Non-binary"),
                Option(99, "Prefer not to say"),
            ]),
            # Choices taken straight from the variable's labels.
            SingleChoice("Which age group are you in?", age_group, required=True),
            # Same idea, rendered as a dropdown.
            SingleChoice("Which best describes your area?", region,
                         display="dropdown"),
        ]),
        Page("work", title="Work & study", items=[
            SingleChoice("What is your current situation?", employment,
                         required=True),
        ]),
        # Page-level show_if: only people who work see the work-detail page.
        Page("work_detail", title="Your working week",
             show_if=employment.ne(5), items=[
                 SingleChoice("How do you mostly work?", work_mode, required=True),
                 # Question-level show_if with AND + NOT: only employed and
                 # not-fully-remote respondents are asked about a commute.
                 NumericInput("One-way commute time?", commute_minutes, unit="min",
                              show_if=AND(NOT(work_mode.eq(1)), employment.ne(5))),
             ]),
        # randomize_blocks shuffles the two blocks on the page each time.
        Page("devices", title="Your devices", randomize_blocks=True, items=[
            Block(title="What you own", items=[
                # Wide MultiChoice: one yes/no column per device.
                MultiChoice("Which of these do you own?",
                            vars=[owns_smartphone, owns_laptop, owns_tablet,
                                  owns_smartwatch]),
            ]),
            Block(title="What you reach for", items=[
                # Per-question option randomization + an option shown only if the
                # respondent said they own a smartwatch (option-level show_if).
                SingleChoice("Which do you use the most?", primary_device,
                             randomize=True, choices=[
                                 Option(1, "Smartphone"),
                                 Option(2, "Laptop"),
                                 Option(3, "Tablet"),
                                 Option(4, "Smartwatch",
                                        show_if=owns_smartwatch.eq(1)),
                             ]),
            ]),
        ]),
        # randomize_blocks again; the "Social" block also shuffles its own items.
        Page("habits", title="Apps & media", randomize_blocks=True, items=[
            Block(title="Social", randomize=True, items=[
                SingleChoice("How often do you use social media?", social_freq),
                LikertScale("I scroll for longer than I intended", doomscroll,
                            points=5, left_label="Disagree", right_label="Agree",
                            na_option=True),
            ]),
            Block(title="News", items=[
                SingleChoice("Where do you mostly get your news?", news_source),
                # Question-level show_if via isin: only asked of people who
                # actually follow the news.
                LikertScale("I trust most of the news I see", trust_news,
                            points=5, left_label="Disagree", right_label="Agree",
                            show_if=news_source.isin([1, 2, 3])),
            ]),
        ]),
        Page("screen", title="Screen time", items=[
            NumericInput("On a typical day, how many hours on screens?",
                         screen_time_hours, display="slider", unit="h/day", step=1),
            # Array MultiChoice: "None of these" (99) is exclusive, so picking it
            # clears the rest — and an answered response is never an empty "[]".
            MultiChoice("What do you do to manage your screen time?", manage,
                        hint="Select all that apply", exclusive=[99]),
        ]),
        Page("wellbeing", title="How you feel", items=[
            # Matrix: a shared 1-5 frequency scale across five statements.
            Matrix("How often does each apply to you?",
                   var=[feel_rested, can_focus, feel_anxious, in_control,
                        sleep_quality],
                   column_labels=["Never", "Rarely", "Sometimes", "Often",
                                  "Always"]),
            LikertScale("All things considered, how satisfied are you with life?",
                        life_satisfaction, points=7, left_label="Not at all",
                        right_label="Completely"),
            Ranking("Rank what helps you disconnect (most helpful first)",
                    disconnect_rank, max_ranked=5),
        ]),
        Page("closing", title="Almost done", items=[
            NumericInput("How likely are you to try a digital detox? (0-10)",
                         nps, display="slider", step=1),
            OpenText("If you could change one thing about your digital life, "
                     "what would it be?", improve, multiline=True, max_chars=400,
                     placeholder="Optional — a sentence or two"),
            SingleChoice("Happy for us to contact you about a follow-up?",
                         recontact, display="buttons"),
        ]),
        # Terminal redirect for follow-up opt-ins. The URL is the real project
        # page, not a placeholder; everyone else falls through to the thank-you.
        RedirectPage(
            "panel_redirect",
            title="Redirecting",
            show_if=recontact.eq(1),
            redirect_url="https://github.com/hanelias/siamang",
            redirect_delay=4,
            body="<p>Thanks! This survey was built with Siamang — "
                 "sending you on to find out more...</p>",
        ),
        FinalPage(
            "thanks",
            title="Thank you",
            body=("<h3>All done</h3><p>Your answers were recorded and are "
                  "analyzed only in aggregate. Have a mindful day online.</p>"),
        ),
    ],
)

# Compiler settings + a few fieldwork quotas (the platform tracks each cell and
# stops accepting it once the limit is reached).
options = {
    "description": "How everyday technology use relates to wellbeing.",
    "completion_text": "Thank you — your answers make the results better!",
    # The respondent progress bar is off by default (branching makes the page
    # count misleading). Uncomment to show it:
    # "show_progress": True,
    "metadata": {"wave": "2026-Q2", "estimated_minutes": 5},
    "quota": [
        Quota("age_group", 1, 400),
        Quota("age_group", 2, 400),
        Quota("age_group", 3, 400),
    ],
}
