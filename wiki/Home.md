# siamang, siamang Cloud & Siamang Studio

**siamang** is a *research-as-code* framework for sociological surveys. You define
variables, questionnaires, and logic in **pure Python** — then validate, preview,
simulate, deploy, collect, and analyze, all from a single pipeline. The engine has
no GUI and no lock-in: a survey is just a Python module you can version, test, and
reuse. (Siamang Studio, below, has a GUI — and it writes engine code.)

**siamang Cloud** is the managed platform built on the siamang engine: keep your
surveys as code in hosted projects, deploy them with one click, collect responses,
run analysis, and share reports — all from your browser.

**Siamang Studio** is the visual survey platform on the same engine: build the
questionnaire, publish it, collect responses, analyze them on a node canvas and
write the report — all by mouse, with every questionnaire and analysis
downloadable as Python that runs without Studio.

> This wiki has **three parts**. Use the sidebar to navigate.
>
> - 🎛️ **Siamang Studio** — the visual platform, no code required. Start at **[[Studio Overview|Studio-Overview]]**.
> - 📚 **Library** — the `siamang` Python package. Start at **[[Quickstart]]**.
> - ☁️ **siamang Cloud** — the hosted research-as-code platform. Start at **[[Cloud Overview|Cloud-Overview]]**.

### Which part do I need?

| You… | Go to |
| :--- | :--- |
| want to build and run surveys in the browser without writing code | 🎛️ [[Siamang Studio\|Studio-Overview]] — start with the [[Quick Start\|Studio-Quick-Start]] |
| downloaded a `questionnaire.py` or a research bundle from Studio and want to run it | 📚 [[Installation]], then [[CLI Reference\|CLI-Reference]] and [[Reproducibility\|Studio-Reproducibility]] |
| write surveys as Python and want them versioned in Git | 📚 [[Quickstart]] and ☁️ [[Cloud Overview\|Cloud-Overview]] |
| came here from Studio's **Documentation** menu | 🎛️ [[Studio Overview\|Studio-Overview]] |

---

## Install & hello survey

```bash
pip install siamang
```

```python
from siamang.core import Variable, LikertScale, SingleChoice, Page, Questionnaire

satisfaction = Variable(
    "satisfaction", scale="ordinal", label="Overall satisfaction",
    labels={1: "Very dissatisfied", 2: "Dissatisfied",
            3: "Neutral", 4: "Satisfied", 5: "Very satisfied"},
)
remote_freq = Variable(
    "remote_freq", scale="ordinal", label="Remote work frequency",
    labels={1: "Never", 2: "1-2 days/week", 3: "3-4 days/week", 4: "Fully remote"},
)

survey = Questionnaire(
    title="Work Attitudes Study",
    pages=[Page("main", items=[
        LikertScale("How satisfied are you with your role?", var=satisfaction, points=5),
        SingleChoice("How often do you work remotely?", var=remote_freq),
    ])],
)

data = survey.simulate(n=200)                       # synthetic respondents
print(data.report.freq("satisfaction").to_markdown())  # publication-ready table
```

```bash
siamang validate my_survey.py
siamang preview  my_survey.py        # local preview at http://127.0.0.1:8000
siamang deploy   my_survey.py --backend supabase --frontend vercel
```

---

## Feature matrix

| Area | Capabilities |
| :--- | :--- |
| **Core** | Variables (nominal/ordinal/interval/ratio), 7 question types, pages & blocks, skip logic (`show_if`/`hide_if`), quotas, validation |
| **Reporting** | Declarative tables (`FreqTable`, `CrossTable`, `GroupMeanTable`) and charts (`BarChart`, `BoxPlot`, `HeatMap`, `LikertChart`, `ScatterPlot`, `TrendChart` over waves or dates) with automatic labels and statistical tests, in a report theme's chart colors when asked (`palette="theme"`); the chart of an analysis's result from its own numbers (`result_charts`); composable `Report` documents, their tables in Excel; a tab book of every question by a banner (`write_tabbook`) |
| **Analysis** | Tests chosen for you or by hand — t-tests, ANOVA and Welch's ANOVA, Mann-Whitney and Kruskal-Wallis with Tukey, Games-Howell and Dunn post-hoc tests, chi-square and Fisher's exact test, Pearson, Spearman and Kendall correlations and matrices, Wilcoxon, McNemar, Friedman and Cochran's Q for paired answers; descriptives, factor analysis, PCA, reliability, regression (linear, logistic, ordinal logit), clustering, key drivers (relative weights, Shapley), perceptual maps (correspondence analysis), price sensitivity (Van Westendorp with NMS, Gabor-Granger) — each weighted or saying it is not ([[Analysis]]) |
| **Open answers** | Codeframes applied with no model and no network: answers coded by hand (kept as fingerprints, never texts), rules for the rest — words, word forms, alternatives, negation, proximity, clauses — several themes an answer, nets and exclusive themes ([[Coding Open Answers\|Coding-Open-Answers]]) |
| **Scripts** | Inline JavaScript for survey-side behaviour — 7 trigger points |
| **Frontend** | SurveyJS and React 18 runtimes, dark mode, auto-save, access codes, 6 theme presets |
| **Deploy** | Local SQLite, Supabase, Google Sheets backends; Local, Vercel, Netlify frontends |
| **Data I/O** | CSV, Excel, SPSS, Stata, R — SPSS/Stata round-trip labels and missing values; CSV/Excel carry data only (labels via the JSON dictionary) |
| **Cloud** | Hosted survey projects, one-click deploy, response collection, live dashboards, scheduled analysis, shareable reports, team roles and plans |
| **Studio** | Visual questionnaire builder, environments and permanent links, panel returns, email invitations, response database, node-based analysis canvas, live tiles, reports, version history, research bundles, AI assistant |

---

## 📚 Library — start here

| Page | What it covers |
| :--- | :--- |
| [[Installation]] | Install, extras (`charts`/`gsheets`/`dev`), requirements |
| [[Quickstart]] | Your first survey end to end |
| [[Core Concepts\|Core-Concepts]] | Research-as-code philosophy and the data model |
| [[Question Types\|Question-Types]] | All 7 question types with examples |
| [[Pages Blocks and Structure\|Pages-Blocks-and-Structure]] | Pages, page kinds, blocks, questionnaires |
| [[Visibility and Branching\|Visibility-and-Branching]] | The Expression DSL (`show_if`, `compare`, `AND`/`OR`) |
| [[Reporting Tables\|Reporting-Tables]] · [[Reporting Charts\|Reporting-Charts]] · [[Report Document\|Report-Document]] | Tables, charts, composable reports |
| [[Deployment]] · [[CLI Reference\|CLI-Reference]] | Backends/frontends and the command line |

See the full list in the sidebar, or the manual **[[API Reference Index\|API-Reference-Index]]**.

## ☁️ siamang Cloud — start here

| Page | What it covers |
| :--- | :--- |
| [[Cloud Overview\|Cloud-Overview]] | What the platform does and who it's for |
| [[Cloud Quick Start\|Cloud-Quick-Start]] | Create a project and deploy your first survey |
| [[Your First Project\|Cloud-Your-First-Project]] | Start from the example or an empty project |
| [[Organizations & Team\|Cloud-Organizations-and-Team]] | Workspaces, inviting people, and roles |
| [[Using the Web App\|Cloud-Web-App]] | The web interface, screen by screen |
| [[Deploying a Survey\|Cloud-Deploying-a-Survey]] | Publish a survey and share its public link |
| [[Viewing & Exporting Data\|Cloud-Viewing-and-Exporting-Data]] | Browse responses and export your data |
| [[Analysis & Reports\|Cloud-Analysis-and-Reporting]] | Run analysis, view reports and dashboards |
| [[Project Config (siamang.yaml)\|Cloud-siamang-yaml]] · [[Analysis SDK\|Cloud-Analysis-SDK]] | Configure projects and write analysis scripts |
| [[Plans & Billing\|Cloud-Subscription-Tiers]] | Plans, limits, and team roles |
| [[FAQ & Troubleshooting\|Cloud-FAQ-and-Troubleshooting]] | Common questions and fixes |

## 🎛️ Siamang Studio — start here

| Page | What it covers |
| :--- | :--- |
| [[Studio Overview\|Studio-Overview]] | What Studio does, who it is for, and the full table of contents |
| [[Quick Start\|Studio-Quick-Start]] | From sign-up to your first responses and your first table |
| [[Key Concepts\|Studio-Key-Concepts]] | Organizations, projects, Saves, deployments, flows — the vocabulary |
| [[Tutorial: A Study from Start to Finish\|Studio-Tutorial-End-to-End]] | One realistic study through every stage |
| [[The Builder\|Studio-Builder-Overview]] · [[Question Types\|Studio-Question-Types]] · [[Logic and Branching\|Studio-Logic-and-Branching]] | Building the questionnaire |
| [[Publishing and Environments\|Studio-Publishing-and-Environments]] · [[Email Invitations\|Studio-Email-Invitations]] | Getting the survey to respondents |
| [[Responses and the Data Tab\|Studio-Responses-and-Data]] · [[Data Exports\|Studio-Data-Exports]] | Your data and every export format |
| [[Analysis Flows\|Studio-Flows]] · [[Node Reference\|Studio-Node-Reference]] · [[Reports\|Studio-Reports]] | Analysis on the canvas and the report |
| [[Reproducibility\|Studio-Reproducibility]] | Download .py, research bundles, citation |
| [[Plans, Trial and Billing\|Studio-Plans-and-Billing]] · [[FAQ and Troubleshooting\|Studio-FAQ-and-Troubleshooting]] | Plans, limits, and fixes |

---

*This wiki lives in the [`wiki/`](https://github.com/hanelias/siamang/tree/main/wiki) folder
of the `siamang` repository and is published to the GitHub Wiki. To edit, change the
source files and re-run the sync script — see [`wiki/README.md`](https://github.com/hanelias/siamang/blob/main/wiki/README.md).*
