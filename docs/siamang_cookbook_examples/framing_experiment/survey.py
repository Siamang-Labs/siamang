"""Message Framing Experiment — a between-subjects A/B survey experiment."""

import siamang as sg
from siamang.core import ContentPage, DisqualificationPage, FinalPage

AGREE7 = {1: "Strongly disagree", 2: "Disagree", 3: "Somewhat disagree", 4: "Neither",
          5: "Somewhat agree", 6: "Agree", 7: "Strongly agree"}

# ── Codebook ─────────────────────────────────────────────────────────────────
condition = sg.Variable("condition", scale="nominal", label="Experimental condition",
                        labels={1: "Control (statistics frame)", 2: "Treatment (story frame)"},
                        role="grouping")
age = sg.Variable("age", scale="ratio", label="Age", dtype="int", valid_range=(18, 99))
gender = sg.Variable("gender", scale="nominal", label="Gender",
                     labels={1: "Woman", 2: "Man", 3: "Other"})
politics = sg.Variable("politics", scale="ordinal", label="Political orientation (1 left - 7 right)",
                       labels={i: str(i) for i in range(1, 8)})
attention = sg.Variable("attention", scale="nominal", label="Attention check",
                        labels={1: "Strongly disagree", 2: "Disagree", 3: "Somewhat agree",
                                4: "Strongly agree"})
support = sg.Variable("support", scale="ordinal", label="Support for the policy", labels=AGREE7,
                      role="target")
donate = sg.Variable("donate", scale="ratio", label="Hypothetical donation (EUR, 0-100)",
                     dtype="int", valid_range=(0, 100), role="target")
manip_check = sg.Variable("manip_check", scale="ordinal",
                          label="The message focused on one person's story", labels=AGREE7)
issue = sg.Variable("issue", scale="nominal", label="Most important issue",
                    labels={1: "Housing", 2: "Climate", 3: "Health care", 4: "Education"})

variables = sg.VariableMap()
variables.add_many([condition, age, gender, politics, attention, support, donate,
                    manip_check, issue])

# ── Scripts: random assignment, a timer, and submit-time metadata ────────────
assign = sg.Script(
    name="assign_condition", trigger="onInit",
    # utils.shuffle returns a new array; utils.sample(arr, n) returns an array, not an item
    code="if (answers.condition == null) { answers.condition = utils.shuffle([1, 2])[0]; }",
)
timer = sg.Script.timed_question("manip_check", seconds=45)
stamp = sg.Script(
    name="stamp_submission", trigger="onSubmit",
    context={"study": "framing-2026"},
    code="answers.study = context.study; answers.submitted_client_time = utils.now();",
)

STATS_FRAME = ("<h3>Housing in numbers</h3><p>Last year 41,000 households applied for social "
               "housing; 12% received a home within twelve months.</p>")
STORY_FRAME = ("<h3>Maria's year</h3><p>Maria, a nurse and mother of two, spent last year on "
               "a waiting list, moving between relatives' sofas while she waited for a home.</p>")

survey = sg.Questionnaire(
    title="Public Attitudes to Housing Policy",
    variables=variables,
    scripts=[assign, timer, stamp],
    pages=[
        ContentPage("intro", title="About this study",
                    body="<p>You will read a short text and answer a few questions (4 minutes).</p>"),
        sg.Page("demographics", title="About you", items=[
            sg.NumericInput("How old are you?", var=age, required=True),
            sg.SingleChoice("Gender", var=gender, display="buttons"),
            sg.LikertScale("In politics people sometimes talk of left and right. Where would "
                           "you place yourself?", var=politics, points=7,
                           left_label="Left", right_label="Right"),
            sg.SingleChoice("Which issue matters most to you right now?", var=issue,
                            randomize=True),                     # order effects: shuffle
        ]),
        # `condition` is set by the onInit script, not by a question, so the gate must be a
        # brace-less string: validate() only checks {name} tokens and question-bound variables.
        ContentPage("vignette_control", title="Please read carefully", body=STATS_FRAME,
                    show_if="condition = 1"),
        ContentPage("vignette_treatment", title="Please read carefully", body=STORY_FRAME,
                    show_if="condition = 2"),
        sg.Page("outcomes", title="Your view", items=[
            sg.Block(randomize=True, items=[                   # counterbalance the two outcomes
                sg.LikertScale("The government should build more social housing.",
                               var=support, points=7, left_label="Strongly disagree",
                               right_label="Strongly agree", required=True),
                sg.NumericInput("If you received EUR 100 today, how much would you give to a "
                                "housing charity?", var=donate, display="slider", step=5),
            ]),
            sg.SingleChoice("To show you are reading, please select 'Somewhat agree'.",
                            var=attention, required=True),
        ]),
        sg.Page("checks", title="One last question", items=[
            sg.LikertScale("The text I read focused on one person's story.", var=manip_check,
                           points=7, left_label="Strongly disagree", right_label="Strongly agree"),
        ]),
        DisqualificationPage("failed_attention", title="Thank you",
                             body="<p>Unfortunately we cannot use your answers.</p>",
                             show_if=attention.ne(3)),
        FinalPage("thanks", title="Thank you", body="<p>Debrief: the text you read was one of "
                  "two versions assigned at random.</p>"),
    ],
)

options = {"completion_text": "Thank you for taking part.", "metadata": {"design": "2-arm"}}

if __name__ == "__main__":
    survey.validate(strict=True)
    for w in survey.lint(level="strict"):
        print(f"[{w.severity}] {w.code}: {w.message}")
    print("compiled pages:", [p.name for p in survey.pages])
