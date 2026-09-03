# Siamang Cookbook — example studies

Four complete studies built with **siamang 0.6.0**, each in its own directory with the survey as
Python modules, tests, scripts and a Jupyter notebook that *imports* those modules and walks the
pipeline with saved outputs, plus a notebook of short recipes.

## Running

```bash
pip install "siamang[charts]==0.6.0" pytest jupyter requests
cd civic_trust
PYTHONPATH=. siamang validate survey.py --strict     # the CLI imports the file by path → put the directory on the path
PYTHONPATH=. python -m pytest -q
PYTHONPATH=. python run_local.py                      # local deploy + HTTP test submissions + quota monitor
PYTHONPATH=. python analysis.py                       # tables, charts, report, exports → out/
jupyter notebook civic_trust.ipynb                    # the same pipeline step by step, with outputs
```

Notebooks add their own directory to `sys.path` in the first cell, so they run from any launcher.
All numbers come from `survey.simulate()` and are meaningless by construction; the point is that
every table is labelled and every test is chosen for you. The narrative version of these studies is
`docs/cookbook-scenarios.md` in the siamang repository.

Links to notebook sections use Jupyter's heading anchors (open the notebook in Jupyter / nbviewer);
links into `.py` files point at line numbers (GitHub / GitLab / most editors).

## Table of contents


### [`civic_trust/`](civic_trust/) — Civic Trust 2026 — population survey with screening, quotas and raking weights

**Notebook [`civic_trust.ipynb`](civic_trust/civic_trust.ipynb)**

- [Civic Trust 2026 — screening, quotas, weighting](civic_trust/civic_trust.ipynb#Civic-Trust-2026-—-screening,-quotas,-weighting)
  - [1. The codebook: codebook.py](civic_trust/civic_trust.ipynb#1.-The-codebook:-codebook.py)
  - [2. The questionnaire and the quota plan: survey.py](civic_trust/civic_trust.ipynb#2.-The-questionnaire-and-the-quota-plan:-survey.py)
  - [3. Validate like the CLI, test like a developer](civic_trust/civic_trust.ipynb#3.-Validate-like-the-CLI,-test-like-a-developer)
  - [4. The local deploy loop: what the browser actually stores](civic_trust/civic_trust.ipynb#4.-The-local-deploy-loop:-what-the-browser-actually-stores)
  - [5. Analysis on rehearsal data](civic_trust/civic_trust.ipynb#5.-Analysis-on-rehearsal-data)
  - [6. Tables, weighted statistics, charts, report](civic_trust/civic_trust.ipynb#6.-Tables,-weighted-statistics,-charts,-report)
  - [7. The script version and shutdown](civic_trust/civic_trust.ipynb#7.-The-script-version-and-shutdown)

**Modules**

- [`codebook.py`](civic_trust/codebook.py) — Codebook for the Civic Trust 2026 study.
  - [Shared label scales](civic_trust/codebook.py#L11)
  - [Screening](civic_trust/codebook.py#L16)
  - [Demographics](civic_trust/codebook.py#L26)
  - [Trust battery (five ordinal items, one construct)](civic_trust/codebook.py#L48)
  - [def _trust()](civic_trust/codebook.py#L49)
  - [Media use: array-mode MultiChoice (one column holding a list of codes)](civic_trust/codebook.py#L70)
  - [Civic activity: wide-mode MultiChoice (one 0/1 column per activity)](civic_trust/codebook.py#L77)
  - [Closing](civic_trust/codebook.py#L84)
  - [The registry: the single source of truth for the study](civic_trust/codebook.py#L89)
  - [`variables = ...`](civic_trust/codebook.py#L90)
- [`survey.py`](civic_trust/survey.py) — Civic Trust 2026 — questionnaire module.
  - [`eligible = ...`](civic_trust/survey.py#L21)
  - [`survey = ...`](civic_trust/survey.py#L25)
  - [`options = ...`](civic_trust/survey.py#L99)
- [`helpers.py`](civic_trust/helpers.py) — Shared helpers for the Civic Trust study (imported by run_local.py, analysis.py and the notebook).
  - [def flatten_responses()](civic_trust/helpers.py#L11)
  - [def rake()](civic_trust/helpers.py#L35)
- [`test_survey.py`](civic_trust/test_survey.py) — Smoke tests for the Civic Trust 2026 instrument — run with `pytest`.
  - [def test_structure_is_valid()](civic_trust/test_survey.py#L10)
  - [def test_eligibility_gate()](civic_trust/test_survey.py#L16)
  - [def test_simulation_respects_gates()](civic_trust/test_survey.py#L23)
  - [def test_simulation_is_reproducible()](civic_trust/test_survey.py#L36)
- [`run_local.py`](civic_trust/run_local.py) — Local deployment loop: deploy, submit test responses over HTTP, collect, monitor quotas.
  - [`TEST_RESPONSES = ...`](civic_trust/run_local.py#L26)
- [`analysis.py`](civic_trust/analysis.py) — Civic Trust 2026 — analysis script.
  - [1. Load](civic_trust/analysis.py#L22)
  - [2. Validate against the codebook, then neutralise declared missing codes](civic_trust/analysis.py#L35)
  - [3. Post-stratification weights (raking helper from helpers.py)](civic_trust/analysis.py#L57)
  - [`CENSUS = ...`](civic_trust/analysis.py#L58)
  - [4. Tables](civic_trust/analysis.py#L68)
  - [5. Charts and report](civic_trust/analysis.py#L102)
  - [6. Exports](civic_trust/analysis.py#L121)

### [`customer_pulse/`](customer_pulse/) — Customer Pulse — NPS / satisfaction with branding and an offline bundle

**Notebook [`customer_pulse.ipynb`](customer_pulse/customer_pulse.ipynb)**

- [Customer Pulse — NPS, satisfaction, branding](customer_pulse/customer_pulse.ipynb#Customer-Pulse-—-NPS,-satisfaction,-branding)
  - [1. One file: codebook, questionnaire, options, theme in survey.py](customer_pulse/customer_pulse.ipynb#1.-One-file:-codebook,-questionnaire,-options,-theme-in-survey.py)
  - [2. A self-contained bundle for kiosks: build_bundle.py](customer_pulse/customer_pulse.ipynb#2.-A-self-contained-bundle-for-kiosks:-build_bundle.py)
  - [3. Local deploy loop and the sentinel answers](customer_pulse/customer_pulse.ipynb#3.-Local-deploy-loop-and-the-sentinel-answers)
  - [4. Analysis step by step: analysis.py](customer_pulse/customer_pulse.ipynb#4.-Analysis-step-by-step:-analysis.py)
  - [5. Deliverables from the script](customer_pulse/customer_pulse.ipynb#5.-Deliverables-from-the-script)

**Modules**

- [`survey.py`](customer_pulse/survey.py) — Customer Pulse — a branded NPS / satisfaction survey in one file.
  - [Codebook](customer_pulse/survey.py#L11)
  - [Questionnaire](customer_pulse/survey.py#L35)
  - [`survey = ...`](customer_pulse/survey.py#L36)
  - [Compiler options (no quotas here)](customer_pulse/survey.py#L73)
  - [`options = ...`](customer_pulse/survey.py#L74)
  - [Branding: start from a preset, override what matters](customer_pulse/survey.py#L81)
  - [`ui = ...`](customer_pulse/survey.py#L82)
- [`build_bundle.py`](customer_pulse/build_bundle.py) — Build a self-contained HTML bundle (kiosk / offline use) without deploying.
- [`analysis.py`](customer_pulse/analysis.py) — Customer Pulse — NPS analysis, client deliverables, combined report.
  - [1. Rehearse the sentinel cleanup real data will need](customer_pulse/analysis.py#L18)
  - [2. NPS](customer_pulse/analysis.py#L42)
  - [3. Attributes and priorities](customer_pulse/analysis.py#L64)
  - [4. Deliverables](customer_pulse/analysis.py#L78)

### [`wellbeing_panel/`](wellbeing_panel/) — Wellbeing Panel — multi-wave panel with codebook round trips

**Notebook [`wellbeing_panel.ipynb`](wellbeing_panel/wellbeing_panel.ipynb)**

- [Wellbeing Panel — a multi-wave study](wellbeing_panel/wellbeing_panel.ipynb#Wellbeing-Panel-—-a-multi-wave-study)
  - [1. The shared codebook: codebook.py](wellbeing_panel/wellbeing_panel.ipynb#1.-The-shared-codebook:-codebook.py)
  - [2. Wave modules: wave1.py and wave2.py](wellbeing_panel/wellbeing_panel.ipynb#2.-Wave-modules:-wave1.py-and-wave2.py)
  - [3. What the browser stores: local deployment of wave 1](wellbeing_panel/wellbeing_panel.ipynb#3.-What-the-browser-stores:-local-deployment-of-wave-1)
  - [4. Two waves of rehearsal data, validated against their codebooks](wellbeing_panel/wellbeing_panel.ipynb#4.-Two-waves-of-rehearsal-data,-validated-against-their-codebooks)
  - [5. Archive a wave and prove the round trips](wellbeing_panel/wellbeing_panel.ipynb#5.-Archive-a-wave-and-prove-the-round-trips)
  - [6. Long file for trends and wide file for within-person change](wellbeing_panel/wellbeing_panel.ipynb#6.-Long-file-for-trends-and-wide-file-for-within-person-change)
  - [7. The script version: analysis_panel.py](wellbeing_panel/wellbeing_panel.ipynb#7.-The-script-version:-analysis_panel.py)

**Modules**

- [`codebook.py`](wellbeing_panel/codebook.py) — Wellbeing Panel — the codebook shared by every wave.
  - [def who5()](wellbeing_panel/codebook.py#L26)
  - [def core_variables()](wellbeing_panel/codebook.py#L42)
- [`wave1.py`](wellbeing_panel/wave1.py) — Wellbeing Panel — wave 1 (baseline).
  - [`capture_pid = ...`](wellbeing_panel/wave1.py#L12)
  - [`variables = ...`](wellbeing_panel/wave1.py#L17)
  - [`survey = ...`](wellbeing_panel/wave1.py#L19)
  - [`options = ...`](wellbeing_panel/wave1.py#L45)
- [`wave2.py`](wellbeing_panel/wave2.py) — Wellbeing Panel — wave 2 (three months later). Adds a job-change question.
  - [`variables = ...`](wellbeing_panel/wave2.py#L15)
  - [`survey = ...`](wellbeing_panel/wave2.py#L18)
  - [`options = ...`](wellbeing_panel/wave2.py#L45)
- [`helpers.py`](wellbeing_panel/helpers.py) — Turn collected runtime payloads into one column per Variable (see the Civic Trust study).
  - [def flatten_responses()](wellbeing_panel/helpers.py#L11)
- [`analysis_panel.py`](wellbeing_panel/analysis_panel.py) — Wellbeing Panel — combine two waves, round-trip the codebook, report the trend.
  - [def prepare()](wellbeing_panel/analysis_panel.py#L20)
  - [1. Two waves of (simulated) responses](wellbeing_panel/analysis_panel.py#L31)
  - [2. Validate each wave against its codebook (role="id" catches duplicates)](wellbeing_panel/analysis_panel.py#L41)
  - [3. Archive wave 1 with its codebook and prove the round trip](wellbeing_panel/analysis_panel.py#L47)
  - [4. Long file: both waves stacked](wellbeing_panel/analysis_panel.py#L64)
  - [5. Wide file: within-person change](wellbeing_panel/analysis_panel.py#L71)
  - [6. Report per wave, combined with a table of contents](wellbeing_panel/analysis_panel.py#L88)
  - [def wave_report()](wellbeing_panel/analysis_panel.py#L89)
  - [7. Hand the long file to R](wellbeing_panel/analysis_panel.py#L104)

### [`framing_experiment/`](framing_experiment/) — Message Framing — between-subjects A/B experiment with randomization

**Notebook [`framing_experiment.ipynb`](framing_experiment/framing_experiment.ipynb)**

- [Message Framing — an A/B experiment with randomization](framing_experiment/framing_experiment.ipynb#Message-Framing-—-an-A/B-experiment-with-randomization)
  - [1. The instrument: survey.py](framing_experiment/framing_experiment.ipynb#1.-The-instrument:-survey.py)
  - [2. Local deployment: one submission per arm](framing_experiment/framing_experiment.ipynb#2.-Local-deployment:-one-submission-per-arm)
  - [3. Rehearsal data and the analysis step by step](framing_experiment/framing_experiment.ipynb#3.-Rehearsal-data-and-the-analysis-step-by-step)
  - [4. The script version and the report](framing_experiment/framing_experiment.ipynb#4.-The-script-version-and-the-report)

**Modules**

- [`survey.py`](framing_experiment/survey.py) — Message Framing Experiment — a between-subjects A/B survey experiment.
  - [Codebook](framing_experiment/survey.py#L9)
  - [`variables = ...`](framing_experiment/survey.py#L30)
  - [Scripts: random assignment, a timer, and submit-time metadata](framing_experiment/survey.py#L34)
  - [`assign = ...`](framing_experiment/survey.py#L35)
  - [`survey = ...`](framing_experiment/survey.py#L52)
  - [`options = ...`](framing_experiment/survey.py#L97)
- [`analysis.py`](framing_experiment/analysis.py) — Message Framing Experiment — balance checks, treatment effects, report.
  - [1. Rehearsal data: simulate() runs no scripts, so assign the arm in pandas](framing_experiment/analysis.py#L14)
  - [2. Exclusions: failed attention checks](framing_experiment/analysis.py#L24)
  - [3. Randomisation / balance check](framing_experiment/analysis.py#L29)
  - [4. Treatment effects](framing_experiment/analysis.py#L33)
  - [5. Report](framing_experiment/analysis.py#L45)

### [`recipes/`](recipes/) — short engine and Cloud recipes, executed

**Notebook [`engine_and_cloud_recipes.ipynb`](recipes/engine_and_cloud_recipes.ipynb)**

- [Engine and Cloud recipes — executed](recipes/engine_and_cloud_recipes.ipynb#Engine-and-Cloud-recipes-—-executed)
- [Part B — Engine recipes by pipeline stage](recipes/engine_and_cloud_recipes.ipynb#Part-B-—-Engine-recipes-by-pipeline-stage)
  - [B1. Authoring patterns](recipes/engine_and_cloud_recipes.ipynb#B1.-Authoring-patterns)
    - [Reusable label scales and battery factories](recipes/engine_and_cloud_recipes.ipynb#Reusable-label-scales-and-battery-factories)
    - [Choosing the MultiChoice layout by the data you want back](recipes/engine_and_cloud_recipes.ipynb#Choosing-the-MultiChoice-layout-by-the-data-you-want-back)
    - [Options with media and per-option visibility](recipes/engine_and_cloud_recipes.ipynb#Options-with-media-and-per-option-visibility)
    - [Translating the respondent-facing chrome](recipes/engine_and_cloud_recipes.ipynb#Translating-the-respondent-facing-chrome)
  - [B2. Logic and routing](recipes/engine_and_cloud_recipes.ipynb#B2.-Logic-and-routing)
    - [Building and testing expressions](recipes/engine_and_cloud_recipes.ipynb#Building-and-testing-expressions)
    - [Page-level gates must be SurveyJS-exportable](recipes/engine_and_cloud_recipes.ipynb#Page-level-gates-must-be-SurveyJS-exportable)
    - [Routing: next_if with typed expressions, default_next, skip_to](recipes/engine_and_cloud_recipes.ipynb#Routing:-next_if-with-typed-expressions,-default_next,-skip_to)
    - [FilterRule for analysis-time filters](recipes/engine_and_cloud_recipes.ipynb#FilterRule-for-analysis-time-filters)
  - [B3. Quotas and scripts](recipes/engine_and_cloud_recipes.ipynb#B3.-Quotas-and-scripts)
    - [The quota plan: define, validate, test, attach, monitor](recipes/engine_and_cloud_recipes.ipynb#The-quota-plan:-define,-validate,-test,-attach,-monitor)
    - [Scripts: factories, custom snippets, context](recipes/engine_and_cloud_recipes.ipynb#Scripts:-factories,-custom-snippets,-context)
  - [B4. Validation and testing](recipes/engine_and_cloud_recipes.ipynb#B4.-Validation-and-testing)
    - [Reading lint output](recipes/engine_and_cloud_recipes.ipynb#Reading-lint-output)
    - [A test file for any survey](recipes/engine_and_cloud_recipes.ipynb#A-test-file-for-any-survey)
  - [B5. Deployment and configuration](recipes/engine_and_cloud_recipes.ipynb#B5.-Deployment-and-configuration)
    - [The configuration file from Python](recipes/engine_and_cloud_recipes.ipynb#The-configuration-file-from-Python)
    - [Which adapters are available, and Supabase SQL by hand](recipes/engine_and_cloud_recipes.ipynb#Which-adapters-are-available,-and-Supabase-SQL-by-hand)
    - [Reading the preview database](recipes/engine_and_cloud_recipes.ipynb#Reading-the-preview-database)
  - [B6. Data cleaning](recipes/engine_and_cloud_recipes.ipynb#B6.-Data-cleaning)
    - [The order of operations](recipes/engine_and_cloud_recipes.ipynb#The-order-of-operations)
    - [Collapsing codes with descriptive labels](recipes/engine_and_cloud_recipes.ipynb#Collapsing-codes-with-descriptive-labels)
    - [Mention tables for array-mode MultiChoice](recipes/engine_and_cloud_recipes.ipynb#Mention-tables-for-array-mode-MultiChoice)
    - [Post-stratification weights without extra libraries](recipes/engine_and_cloud_recipes.ipynb#Post-stratification-weights-without-extra-libraries)
  - [B7. Analysis and reporting](recipes/engine_and_cloud_recipes.ipynb#B7.-Analysis-and-reporting)
    - [The four table calls and where the tests come from](recipes/engine_and_cloud_recipes.ipynb#The-four-table-calls-and-where-the-tests-come-from)
    - [Charts headless, and inside a report](recipes/engine_and_cloud_recipes.ipynb#Charts-headless,-and-inside-a-report)
- [Part C — Siamang Cloud (locally executable parts)](<recipes/engine_and_cloud_recipes.ipynb#Part-C-—-Siamang-Cloud-(locally-executable-parts)>)
  - [C1. Project layout and siamang.yaml](recipes/engine_and_cloud_recipes.ipynb#C1.-Project-layout-and-siamang.yaml)
  - [C2. Analysis pipelines with the Cloud SDK](recipes/engine_and_cloud_recipes.ipynb#C2.-Analysis-pipelines-with-the-Cloud-SDK)
    - [C2.1 Cleaning (scripts/cleaning.py)](<recipes/engine_and_cloud_recipes.ipynb#C2.1-Cleaning-(scripts/cleaning.py)>)
    - [C2.2 Weighting (scripts/weighting.py)](<recipes/engine_and_cloud_recipes.ipynb#C2.2-Weighting-(scripts/weighting.py)>)
    - [C2.3 Tables and the report (scripts/tables.py)](<recipes/engine_and_cloud_recipes.ipynb#C2.3-Tables-and-the-report-(scripts/tables.py)>)
  - [C3. Fieldwork operations](recipes/engine_and_cloud_recipes.ipynb#C3.-Fieldwork-operations)
  - [C4. Automation and integrations](recipes/engine_and_cloud_recipes.ipynb#C4.-Automation-and-integrations)
    - [Schedules (Plus and above)](<recipes/engine_and_cloud_recipes.ipynb#Schedules-(Plus-and-above)>)
    - [Connector tasks (Plus: sheets, excel365, supabase; Pro: storage, warehouses, database, sftp, redcap, http)](<recipes/engine_and_cloud_recipes.ipynb#Connector-tasks-(Plus:-sheets,-excel365,-supabase;-Pro:-storage,-warehouses,-database,-sftp,-redcap,-http)>)
    - [Webhooks (Plus and above): a receiver that verifies signatures](<recipes/engine_and_cloud_recipes.ipynb#Webhooks-(Plus-and-above):-a-receiver-that-verifies-signatures>)
  - [C5. Working from your own machine and the REST API](recipes/engine_and_cloud_recipes.ipynb#C5.-Working-from-your-own-machine-and-the-REST-API)
