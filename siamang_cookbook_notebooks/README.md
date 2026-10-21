# Siamang Cookbook — self-contained notebooks

Five Jupyter notebooks built with **siamang 0.6.0**, executed top to bottom with their outputs saved
(tables, charts, printed results, a real local deployment with HTTP submissions). Every notebook is
self-contained: codebook, questionnaire, options, theme and analysis all live in its cells — nothing
to import besides the installed package.

## Running

```bash
pip install "siamang[charts]==0.6.0" jupyter requests
jupyter notebook 01_civic_trust.ipynb
```

Run the cells in order: the local server started in a deploy section is stopped at the end of the
notebook.

Some cells print the text of an exception or lint `[error]` lines **on purpose** — they show what the
validator rejects; those outputs start with `EXPECTED (demonstration)` or `deliberately flawed`.
All numbers come from `survey.simulate()` and are meaningless by construction; the point is that every
table is labelled and every test is chosen for you.

Section links use Jupyter's heading anchors (open the notebook in Jupyter / JupyterLab / nbviewer).

## Table of contents


### [`01_civic_trust.ipynb`](01_civic_trust.ipynb) — Civic Trust 2026 — population survey with screening, quotas, raking weights, local deploy loop, tables, report, exports

- [Civic Trust 2026 — screening, quotas, weighting](01_civic_trust.ipynb#Civic-Trust-2026-—-screening,-quotas,-weighting)
  - [1. The codebook](01_civic_trust.ipynb#1.-The-codebook)
  - [2. The questionnaire and the quota plan](01_civic_trust.ipynb#2.-The-questionnaire-and-the-quota-plan)
  - [3. Validation, lint, and smoke tests](01_civic_trust.ipynb#3.-Validation,-lint,-and-smoke-tests)
  - [4. The local deploy loop: what the browser actually stores](01_civic_trust.ipynb#4.-The-local-deploy-loop:-what-the-browser-actually-stores)
  - [5. Analysis on rehearsal data](01_civic_trust.ipynb#5.-Analysis-on-rehearsal-data)
  - [6. Tables, weighted statistics, charts, report, exports](01_civic_trust.ipynb#6.-Tables,-weighted-statistics,-charts,-report,-exports)
  - [7. Stop the local server](01_civic_trust.ipynb#7.-Stop-the-local-server)

### [`02_customer_pulse.ipynb`](02_customer_pulse.ipynb) — Customer Pulse — NPS / satisfaction with branding, access code, offline bundle, sentinel cleanup, combined report

- [Customer Pulse — NPS, satisfaction, branding](02_customer_pulse.ipynb#Customer-Pulse-—-NPS,-satisfaction,-branding)
  - [1. Codebook, questionnaire, options](02_customer_pulse.ipynb#1.-Codebook,-questionnaire,-options)
  - [2. Branding: a preset, overridden](02_customer_pulse.ipynb#2.-Branding:-a-preset,-overridden)
  - [3. A self-contained bundle for kiosks](02_customer_pulse.ipynb#3.-A-self-contained-bundle-for-kiosks)
  - [4. Local deploy loop and the sentinel answers](02_customer_pulse.ipynb#4.-Local-deploy-loop-and-the-sentinel-answers)
  - [5. NPS](02_customer_pulse.ipynb#5.-NPS)
  - [6. Attributes and priorities](02_customer_pulse.ipynb#6.-Attributes-and-priorities)
  - [7. Deliverables: banner, Excel tables, combined report](02_customer_pulse.ipynb#7.-Deliverables:-banner,-Excel-tables,-combined-report)

### [`03_wellbeing_panel.ipynb`](03_wellbeing_panel.ipynb) — Wellbeing Panel — multi-wave panel: shared codebook, panel-id capture, JSON / SPSS / Stata round trips, long and wide files

- [Wellbeing Panel — a multi-wave study](03_wellbeing_panel.ipynb#Wellbeing-Panel-—-a-multi-wave-study)
  - [1. The shared codebook](03_wellbeing_panel.ipynb#1.-The-shared-codebook)
  - [2. Two wave modules](03_wellbeing_panel.ipynb#2.-Two-wave-modules)
  - [3. What the browser stores: local deployment of wave 1](03_wellbeing_panel.ipynb#3.-What-the-browser-stores:-local-deployment-of-wave-1)
  - [4. Two waves of rehearsal data](03_wellbeing_panel.ipynb#4.-Two-waves-of-rehearsal-data)
  - [5. Archive a wave and prove the round trips](03_wellbeing_panel.ipynb#5.-Archive-a-wave-and-prove-the-round-trips)
  - [6. Long file: trends across waves](03_wellbeing_panel.ipynb#6.-Long-file:-trends-across-waves)
  - [7. Wide file: within-person change](03_wellbeing_panel.ipynb#7.-Wide-file:-within-person-change)
  - [8. Report per wave, combined, and the R bundle](03_wellbeing_panel.ipynb#8.-Report-per-wave,-combined,-and-the-R-bundle)

### [`04_framing_experiment.ipynb`](04_framing_experiment.ipynb) — Message Framing — between-subjects A/B experiment: script-assigned arms, string gates, randomization, two-group tests

- [Message Framing — an A/B experiment with randomization](04_framing_experiment.ipynb#Message-Framing-—-an-A/B-experiment-with-randomization)
  - [1. Codebook](04_framing_experiment.ipynb#1.-Codebook)
  - [2. Scripts and the instrument](04_framing_experiment.ipynb#2.-Scripts-and-the-instrument)
  - [3. Local deployment: what a submission looks like](04_framing_experiment.ipynb#3.-Local-deployment:-what-a-submission-looks-like)
  - [4. Rehearsal data](04_framing_experiment.ipynb#4.-Rehearsal-data)
  - [5. Balance checks and treatment effects](04_framing_experiment.ipynb#5.-Balance-checks-and-treatment-effects)
  - [6. Report](04_framing_experiment.ipynb#6.-Report)

### [`05_engine_recipes.ipynb`](05_engine_recipes.ipynb) — Engine recipes — short executed recipes (Part B of the cookbook)

- [Engine recipes — executed](05_engine_recipes.ipynb#Engine-recipes-—-executed)
- [Part B — Engine recipes by pipeline stage](05_engine_recipes.ipynb#Part-B-—-Engine-recipes-by-pipeline-stage)
  - [B1. Authoring patterns](05_engine_recipes.ipynb#B1.-Authoring-patterns)
    - [Reusable label scales and battery factories](05_engine_recipes.ipynb#Reusable-label-scales-and-battery-factories)
    - [Choosing the MultiChoice layout by the data you want back](05_engine_recipes.ipynb#Choosing-the-MultiChoice-layout-by-the-data-you-want-back)
    - [Options with media and per-option visibility](05_engine_recipes.ipynb#Options-with-media-and-per-option-visibility)
    - [Translating the respondent-facing chrome](05_engine_recipes.ipynb#Translating-the-respondent-facing-chrome)
  - [B2. Logic and routing](05_engine_recipes.ipynb#B2.-Logic-and-routing)
    - [Building and testing expressions](05_engine_recipes.ipynb#Building-and-testing-expressions)
    - [Page-level gates must be SurveyJS-exportable](05_engine_recipes.ipynb#Page-level-gates-must-be-SurveyJS-exportable)
    - [Routing: next_if with typed expressions, default_next, skip_to](05_engine_recipes.ipynb#Routing:-next_if-with-typed-expressions,-default_next,-skip_to)
    - [FilterRule for analysis-time filters](05_engine_recipes.ipynb#FilterRule-for-analysis-time-filters)
  - [B3. Quotas and scripts](05_engine_recipes.ipynb#B3.-Quotas-and-scripts)
    - [The quota plan: define, validate, test, attach, monitor](05_engine_recipes.ipynb#The-quota-plan:-define,-validate,-test,-attach,-monitor)
    - [Scripts: factories, custom snippets, context](05_engine_recipes.ipynb#Scripts:-factories,-custom-snippets,-context)
  - [B4. Validation and testing](05_engine_recipes.ipynb#B4.-Validation-and-testing)
    - [Reading lint output](05_engine_recipes.ipynb#Reading-lint-output)
    - [A test file for any survey](05_engine_recipes.ipynb#A-test-file-for-any-survey)
  - [B5. Deployment and configuration](05_engine_recipes.ipynb#B5.-Deployment-and-configuration)
    - [The configuration file from Python](05_engine_recipes.ipynb#The-configuration-file-from-Python)
    - [Which adapters are available, and Supabase SQL by hand](05_engine_recipes.ipynb#Which-adapters-are-available,-and-Supabase-SQL-by-hand)
    - [Reading the preview database](05_engine_recipes.ipynb#Reading-the-preview-database)
  - [B6. Data cleaning](05_engine_recipes.ipynb#B6.-Data-cleaning)
    - [The order of operations](05_engine_recipes.ipynb#The-order-of-operations)
    - [Collapsing codes with descriptive labels](05_engine_recipes.ipynb#Collapsing-codes-with-descriptive-labels)
    - [Mention tables for array-mode MultiChoice](05_engine_recipes.ipynb#Mention-tables-for-array-mode-MultiChoice)
    - [Post-stratification weights without extra libraries](05_engine_recipes.ipynb#Post-stratification-weights-without-extra-libraries)
  - [B7. Analysis and reporting](05_engine_recipes.ipynb#B7.-Analysis-and-reporting)
    - [The four table calls and where the tests come from](05_engine_recipes.ipynb#The-four-table-calls-and-where-the-tests-come-from)
    - [Charts headless, and inside a report](05_engine_recipes.ipynb#Charts-headless,-and-inside-a-report)
