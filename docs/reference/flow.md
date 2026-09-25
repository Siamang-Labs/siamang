# `siamang.flow` reference

`siamang.flow` is the analysis counterpart of the questionnaire document: a
**flow** is a graph of typed nodes (sources, preparation, analysis, charts,
outputs) that a builder stores as JSON, that `FlowRunner` executes in-process,
and that `generate_flow` renders as the Python script a researcher would have
written.

```python
from siamang.flow import FlowRunner, generate_flow, check_flow

check_flow(flow, questionnaire=questionnaire_document)      # -> [FlowIssue]
result = FlowRunner(flow, questionnaire=survey).run(sources={"src": data}, cwd="work")
result.output("xtab", "table").to_frame()
code = generate_flow(flow, questionnaire_document)          # -> str
```

The one rule behind the module: **a node has exactly one implementation, its
template.** The runner executes the rendered template text; the generator
writes the same text into the script. Batch and interactive results cannot
drift apart.

---

## Flow document (`schema_version` 1.0)

| Key | Content |
|-----|---------|
| `name` | slug; the script is `scripts/<name>.py` |
| `title`, `description` | shown in the script docstring |
| `nodes` | `[{id, type, params, position: [x, y], label?}]` |
| `edges` | `[{from: {node, port}, to: {node, port}}]`; edge order is the order of a many-input |
| `outputs` | `{report?: path, files?: [path]}` — what the flow declares it produces |
| `live` | `{enabled, debounce_seconds, tiles: [{node, w, h}]}` |
| `schedule` | cron string (platform) |
| `layout` | builder-owned |

The JSON Schema is `siamang/schemas/flow-1.0.json`; `validate_flow` checks it,
`check_flow` checks the graph.

### Checks (`check_flow`)

`check_flow(flow, *, registry=None, questionnaire=None) -> list[FlowIssue]`
returns errors and warnings with a code and the node concerned:

| Code | Meaning |
|------|---------|
| `UNKNOWN_NODE_TYPE`, `UNKNOWN_PARAM`, `PARAM_REQUIRED`, `PARAM_INVALID` | the node against its spec |
| `PARAM_CONFLICT` (error or warning) | a rule of the spec's `checks` between its parameters: a post-hoc test that does not follow the test chosen, a t-test without the variable its design compares (errors); a choice the node would ignore (warnings) |
| `UNKNOWN_VARIABLE`, `VARIABLE_SCALE` | a variable parameter against the questionnaire's codebook (when given); variables created upstream (`into`, `name`, weight columns, `duration_s`, `partial`) and the arm of a `Script.assign_condition` (nominal unless the codebook declares it) count as known |
| `UNKNOWN_EDGE_NODE`, `UNKNOWN_PORT`, `PORT_TYPE_MISMATCH`, `INPUT_CONNECTED_TWICE`, `INPUT_NOT_CONNECTED` | edges against the ports |
| `CYCLE` | not a DAG |
| `UNREACHABLE_NODE` (warning) | not fed by any source |
| `UNKNOWN_TILE_NODE`, `TILE_NOT_LIVE_TILE` | `live.tiles` |

`resolve_flow` raises `FlowError` on the first error and returns a
`FlowGraph` (nodes, specs, edges, `order`, `inputs`, `params(node)`).

### Execution order

`node_order`: by depth from the sources, then `position` y, then x, then id.
The runner and the generator use the same order.

---

## Node registry

`default_registry()` loads every `siamang/flow/nodes/<category>/<name>.yaml`.
`siamang flow nodes` lists them; `siamang flow nodes --json` (or
`Registry.to_json()`) is what a builder's palette and inspector consume.

| Category | Nodes |
|----------|-------|
| source | `responses`*, `table`*, `file`, `simulated` |
| prepare | `filter`, `select`, `recode`, `missing`, `dedup`, `speeders`, `quality`, `cell_weights`, `rake_weights`, `apply_weight`, `index`, `derive`, `bands`, `explode`, `text_code`, `maxdiff_scores` |
| analyze | `freq`, `crosstab`, `means`, `descriptives`, `correlation`, `correlation_matrix`, `ttest`, `proportion_ci`, `compare_groups`, `paired`, `describe`, `data_check`, `banner`, `nps`, `regression`, `pca`, `factor`, `cluster`, `reliability`, `turf`, `maxdiff`, `conjoint`, `conjoint_shares` |
| visualize | `bar`, `boxplot`, `heatmap`, `scatter` |
| output | `report_section`, `save_report`, `write_table`*, `export_file`, `choice_data`, `conjoint_data`, `live_tile` |

\* platform nodes: they need the project database (`db`). A `source.responses`
/ `source.table` is fed from a snapshot instead (`sources=` in the runner,
`--data` in the script); `output.write_table` is skipped off-platform.

Port types: `SurveyData`, `Table`, `Chart`, `Stat`, `Report`, `Any`. Weights
and flags are columns inside a `SurveyData`.

`prepare.apply_weight` names the weight column (`SurveyData.with_weight`), and
from there each node either uses it and says so in its output, or has no
standard weighted form and says it is unweighted. Weighted: Frequencies,
Crosstab (Fisher's exact test counts respondents), Group means (not N or the
test), Descriptive statistics (not N, skewness or kurtosis), Banner table, Net
Promoter Score, Regression, TURF, MaxDiff, Conjoint, Share of preference,
Principal components, Scale reliability, Correlation and Correlation matrix
with Pearson, the Bar chart, a Heatmap with `by`, and Proportion CI with
`weighted` set. Unweighted and saying so (`"unweighted (the weight '<column>'
is not applied)"` in the stat, or as the chart title's second line): Compare
groups, Correlation and Correlation matrix with Spearman or Kendall, t-test,
Paired tests, Factor analysis, Cluster, Box plot, Scatter plot, a Heatmap
without `by`, Response quality, Code open answers, Data check, and the counts
of MaxDiff scores and Bands. Describe counts rows and adds a
`weighted_n_valid` column. The HB exports carry no weight. The node's own
`help` lists the same, so the palette says what the nodes do.

**Tests chosen by hand.** `analyze.correlation` takes a `method` (`pearson`,
`spearman` — the default — or `kendall`); `analyze.correlation_matrix` (`items`,
`method`, `missing` pairwise | listwise, `adjust` none | holm | bonferroni |
fdr_bh, `layout` matrix | pairs) and `analyze.ttest` (`kind` independent |
paired | one_sample, `y`, `group`, `group_a` / `group_b`, `variances` welch |
student, `y2`, `test_value`, `confidence`) are new; `analyze.means` takes a
`method` (`auto` or `student`, `welch`, `anova`, `welch_anova`, `mannwhitney`,
`kruskal`), a `posthoc` (`none`, `tukey`, `games_howell`, `dunn`) and Dunn's
`adjust` (`holm` | `bonferroni`); `analyze.compare_groups` a `posthoc`
(`none` | `dunn`) and `adjust`; `analyze.crosstab` a `method` (`chi2` |
`fisher`). Their `checks` refuse a post-hoc test that does not follow its test
and a t-test without what its design compares. A stored flow that never set
the new parameters renders exactly the code it rendered before — the defaults
select the templates' old fragments (`when: method=auto & posthoc=none`), and
Group means and Crosstab keep their `test` checkbox with the new `method`
beside it, so `test: true` / `false` keep their meaning. The methods are
described in `siamang.data.inference` (data reference).
`analyze.conjoint_shares` has a `stat` output (base, model, weight) beside its
table.

`analyze.paired` compares answers from the same respondents
(`siamang.data.paired.compare`): `test` is `auto` (Wilcoxon signed-rank for two
`variables`, Friedman for three or more), `wilcoxon`, `mcnemar` or `friedman`;
`yes_codes` (a code or a list) says what counts as yes for McNemar, `zeros`
(`wilcox` | `pratt`) how Wilcoxon treats a respondent who answered both the
same, `p_value` (`auto` | `exact` | `approximate`) how the p-value is found, and
`posthoc` (`holm` | `bonferroni` | `none`) how Friedman's pairwise Wilcoxon
tests are adjusted. Outputs: `table` (descriptives, or McNemar's 2 × 2 table,
with the test as its footer), `pairs` (Friedman's pairwise comparisons; empty,
with a note, for the two-variable tests) and `stat`.

`analyze.factor` runs an exploratory factor analysis
(`siamang.data.factor.analyze`): `items`, `n_factors` (empty: by `criterion`,
`kaiser` or `parallel` from `seed`), `method` (`minres` | `principal` | `ml`),
`rotation` (`varimax` | `promax` | `oblimin` | `none`), `sort`, `hide_below`,
and `scores` with the prefix `into` (default `factor_`). Outputs: `data` (with
`<into>1` … when `scores` is on), `loadings`, `variance`, `correlations` and
`stat`. `check_flow` knows the score variables, so a later node may name
`factor_1`: exactly `n_factors` of them when it is fixed, and up to one fewer
than the items when a rule chooses.
Several nodes expose what the library already computed:

| Node | Engine call | Outputs |
|------|-------------|---------|
| `analyze.descriptives` (Descriptive statistics) | `data.report.descriptives(variables, by=…, detail=…)` | `table`: N, Missing, Mean, SD, Min, Median, Max (+ Q1, Q3, Skewness, Kurtosis) per variable and group; `stat`: missing codes set aside, Weighted N, Effective N, Design effect |
| `analyze.data_check` (Data check) | `data.report.data_check(variables)` | `table`: Severity, Variable, Problem, Rows, Examples, Code; `stat`: Checked, Errors, Warnings |
| `prepare.maxdiff_scores` (MaxDiff scores) | `maxdiff.with_scores(data, question, prefix=…)` | `data` with `<prefix><item code>` per item (default `<question>_score_`); `stat`: respondents scored, unreadable answers |
| `prepare.bands` (Bands) | `bands.bands(data, variable, bins=…, into=…, labels=…, right=…)` | `data` with a labelled ordinal band variable; `stat`: count per band, outside, missing codes |
| `analyze.turf` with `method: fixed` | `turf.evaluate(frame, portfolio, items=…, weight=…, labels=…)` | `table`: reach, unique reach and frequency per option and for the portfolio |
| `prepare.text_code` | `data.report.themes(codeframe, sentiment=…)` | a `stat` output: Coverage, Distinct uncoded answers, and with sentiment the Sentiment split and Net sentiment |

`check_flow` knows the variables these create before a run: `into` of Bands,
and one score variable per item of the named MaxDiff question (its `choices`,
else its first variable's labels), so a later node naming `q_md_score_3` is
checked like any other variable and `q_md_score_9` is `UNKNOWN_VARIABLE`.
`prepare.derive` takes `labels` (code → label) for a formula that yields codes.

`source.simulated` generates its rows with
`siamang.local_simulator.simulate_survey(survey, n=…, seed=…)`: conditions at
every level (page, block, question, answer option), the routing, and the
questionnaire's scripts — an assigned arm is drawn, a `randomize_pages` order
dealt. Quotas are deploy options, not part of the questionnaire, so none
closes in a flow.

Every `visualize.*` node takes **`width`** and **`height`** in inches (2–30,
default 10 × 6) and a **`palette`**; `visualize.heatmap` takes a `cmap` instead
of a palette, and ignores it when it draws a correlation matrix. These size the
matplotlib figure itself rather than the picture of it, so the axis labels keep
their proportion. Resolution is a field on the chart (`SurveyChart.dpi`,
default 150) which `save()` uses unless a caller passes `dpi=` explicitly.

`output.save_report` takes a **`theme`** — the `ReportTheme` fields, as an
object — and `output.report_section` takes a **`layout`**, one entry per
connected item: `{"xtab": {"width": "75%", "align": "left"}}`. Both are checked
by `check_flow`, so a misspelled field or a width like `"wide"` is named before
the run rather than raised inside it, and both reach only the **HTML**: the
Markdown is the report's content and carries no layout. A flow that names no
theme leaves `SIAMANG_REPORT_THEME` to answer.

Which is why `html` defaults to **true**: a node whose `theme` and `layout` are
checked on every run but produce no file anyone can look at is a trap, and the
two parameters describe a document that was not being written. `html: false`
writes the Markdown alone.

`output.save_report` ends the report with a **provenance footer** when the
environment variable `SIAMANG_PROVENANCE` is set (Markdown: questionnaire
version, data snapshot, engine version — whatever ran the flow knows). A
platform sets it per run; a research bundle's `run.sh` exports its
`PROVENANCE.md`. Unset, the report is unchanged (`Report.provenance(None)` is
a no-op).

### A node specification

```yaml
type: analyze.crosstab
category: analyze
title: Crosstab
description: Cross-tabulation with chi-square test and Cramér's V.
inputs:
  data: SurveyData
outputs:
  table: Table
  stat: Stat
params:
  row: {kind: variable, scales: [nominal, ordinal], required: true, label: Rows}
  col: {kind: variable, scales: [nominal, ordinal], required: true, label: Columns}
  pct: {kind: enum, values: [none, row, col, total], default: col}
  test: {kind: bool, default: true}
subtitle: "{row} × {col}"
template: |
  {out.table} = {in.data}.report.crosstab({row!r}, {col!r}, pct={pct!r}, test={test!r})
  {out.stat} = {out.table}.stats
preview: table
```

- `params.kind`: `variable` (with `scales`), `variables`, `enum` (`values`),
  `int` / `float` (`minimum`, `maximum`), `bool`, `string`, `condition`
  (an `Expression` AST), `mapping` (code → value), `targets`
  (variable → {code: share}), `path`, `markdown`, `captions`
  (upstream node id → caption), `json`. `creates: variable | column` marks a
  parameter that names something new for downstream nodes.
- Inputs are a type name or `{type, many, optional}`; `type` may be a list.
- `template`: placeholders `{in.<port>}`, `{out.<port>}` (variable names),
  `{<param>!r}` (the parameter as a Python literal: a condition becomes
  `sg.compare(...)` / `sg.AND(...)`, targets and mappings get typed codes,
  captions become a list aligned with the many-input) and `{node!r}`. A
  template may be a list of fragments, each a string or `{when: <condition>,
  code}`. A condition is `<param>` (set: not empty, not false; a code of 0 is
  set), `<param>=<value>` or `<param>!=<value>`, several joined by `&` when all
  must hold.
- `checks`: rules between parameters, reported by `check_flow` as
  `PARAM_CONFLICT` on the node — `{when: <condition>, require: <condition> |
  [<condition>, …], message, severity: error | warning}`. When `when` holds,
  one of `require` must hold too; without `require`, `when` alone is the
  problem. `Registry.to_json()` does not carry them: a builder gets them from
  `check_flow`.
- `imports`: the import statements the template needs; `platform: true` for
  nodes that need `db`; `snapshot: true` for sources a file can replace.

Variables in the rendered code are `n_<id>` for a single output and
`n_<id>_<port>` for several (`n_xtab_table`, `n_xtab_stat`).

---

## `FlowRunner`

```python
runner = FlowRunner(flow, questionnaire=survey, questionnaire_document=doc)
result = runner.run(sources={"src": data_or_path}, db=None, cwd="work", upto=None)
```

Executes the nodes in order in one namespace. `sources` feeds platform
sources by node id (a `SurveyData` or a snapshot path, read with
`read_snapshot(questionnaire=survey)`); `db` stands in for the platform
module (`as_survey_data`, `write_table`); `cwd` is where relative output
paths land; `upto` runs a node and its ancestors only. With
`raise_on_error=False` the run stops at the first failing node and reports
it instead of raising.

`FlowResult`: `order`, `outputs[node][port]`, `output(node, port=None)`,
`runs` (`NodeRun(node, state, ms, code, error)` with state `ok | skipped |
error`), `tiles` (what `output.live_tile` nodes published), `ok`.

## `siamang.flow.live`

`live.publish(node, *, kind, label, value, metric="value")` is the call
`output.live_tile` makes. Off-platform it only notifies sinks; `with
live.capture() as tiles:` collects them (the runner does this for you),
`add_sink` / `remove_sink` install a platform sink. `metric="rows"` publishes
the row count of a `SurveyData`.

## `generate_flow`

```python
generate_flow(flow, questionnaire=None, *, registry=None, header=None,
              questionnaire_module="survey.questionnaire",
              platform_module="siamang_studio", format=True) -> str
```

Sections: docstring (title, description, `header` with `{schema}` and
`{script}` substituted); imports (isort order, merged per module); a
`--data` argument block when the flow has platform sources; then each node as
`# ── <Title>: <subtitle> ──`, `# studio: <id>` and the rendered template.
A platform source becomes

```python
if args.data:  # research bundle: reproduce from a data snapshot
    from siamang.io import read_snapshot

    n_src = read_snapshot(args.data, questionnaire=survey)
else:  # the platform: project database, scoped to this project
    from siamang_studio import db

    n_src = db.as_survey_data("responses", environment="main", ...)
```

(several sources get `--data-<node>` each); `output.write_table` runs only
without `--data`. The output is a fixed point of `ruff format` and clean
under the engine's `ruff check` rules; run it with
`python scripts/<name>.py --data data/responses.parquet` next to a
`survey/questionnaire.py` (generated with `siamang codegen`).

---

## CLI

```bash
siamang flow check FLOW.json [--questionnaire questionnaire.json]
siamang flow run   FLOW.json --data snapshot [--data node=path …] [--questionnaire …] [--cwd DIR] [--upto NODE]
siamang flow nodes [--json]
siamang codegen    FLOW.json --questionnaire questionnaire.json [-o scripts/name.py]
```
