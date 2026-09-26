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
| `PARAM_CONFLICT` (error or warning) | a rule of the spec's `checks` between its parameters: a post-hoc test that does not follow the test chosen, a t-test without the variable its design compares (errors); a choice the node would ignore (warnings). And what the parameters settle before any data: Paired tests with a number of variables its test cannot compare (`McNemar compares exactly two variables; 3 were given.` — an error), and a t-test of two groups whose Groups has more than two answers in the codebook (its missing codes left out) with Group A and Group B empty (a warning: a filter upstream may leave two) |
| `UNKNOWN_VARIABLE`, `VARIABLE_SCALE` | a variable parameter against the questionnaire's codebook (when given); variables created upstream (`into`, `name`, weight columns, `duration_s`, `partial`) and the arm of a `Script.assign_condition` (nominal unless the codebook declares it) count as known. A variable a node makes has the scale that node gives it (Derive its Scale, ratio by default; Recode its Scale or the source's where it reads it; an index interval; Bands ordinal; a cluster, themes, quality flags and Explode's columns nominal; the quality score ratio; factor and MaxDiff scores interval) — the maker nearest upstream of the node reading it, along the edges, whatever order the document lists them in — and one of the wrong scale is a `VARIABLE_SCALE` warning — an error only for the codebook's own |
| `UNKNOWN_EDGE_NODE`, `UNKNOWN_PORT`, `PORT_TYPE_MISMATCH`, `INPUT_CONNECTED_TWICE`, `INPUT_NOT_CONNECTED` | edges against the ports |
| `CYCLE` | not a DAG |
| `UNREACHABLE_NODE` (warning) | not fed by any source |
| `UNKNOWN_TILE_NODE`, `TILE_NOT_LIVE_TILE` | `live.tiles` |

A parameter the node's code does not read with its current choices is not
checked: `NodeSpec.reads(name, params)` is true when a template fragment that
names the parameter (as `{name!r}` or in its `when`) holds for the node's
choices — the `<param>=<value>` / `<param>!=<value>` terms of that `when` on an
`enum` or `bool` parameter other than `name` — or when no fragment names it,
or when it is required. So a paired t-test that still holds a Group A, or a
Groups naming a variable that has since gone, is no error: the run ignores
them. An error rule of `checks` that names such a parameter is skipped for the
same reason; a warning rule is still given, since saying that a value is
ignored is what one is for.

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
| analyze | `freq`, `crosstab`, `means`, `descriptives`, `correlation`, `correlation_matrix`, `ttest`, `proportion_ci`, `compare_groups`, `paired`, `describe`, `data_check`, `banner`, `nps`, `regression`, `drivers`, `correspondence`, `price`, `pca`, `factor`, `cluster`, `reliability`, `turf`, `maxdiff`, `conjoint`, `conjoint_shares` |
| visualize | `bar`, `boxplot`, `heatmap`, `likert`, `scatter`, `result_chart` |
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
Principal components, Scale reliability, Key drivers (its tests on Kish's
effective N), Perceptual map (its chi-square test counts respondents), Price
sensitivity, Correlation and Correlation matrix
with Pearson, the Bar chart (counts, percentages and Split by), a Heatmap with `by` or with Pearson, the Likert chart, Proportion CI with
`weighted` set, the Trend and the Tab book (Excel). Unweighted and saying so (`"unweighted (the weight '<column>'
is not applied)"` in the stat, or as the chart title's second line): Compare
groups, Correlation and Correlation matrix with Spearman or Kendall, t-test,
Paired tests, Factor analysis, Cluster, Box plot, Scatter plot, a Heatmap
without `by` with Spearman or Kendall, Response quality, Code open answers, Data check, and the counts
of MaxDiff scores and Bands. Describe counts rows and adds a
`weighted_n_valid` column. A Result chart follows the result it draws — weighted
where that result is, and its title says which. The HB exports carry no weight. The node's own
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
table. `analyze.regression`'s **Model** takes `ordinal` beside `auto`, `ols`
and `logit`: the proportional-odds model of ordered answers
(`siamang.data.ordinal`), thresholds and coefficients in its `table`, the fit
in its `stat`; `auto` never picks it.

`analyze.paired` compares answers from the same respondents
(`siamang.data.paired.compare`): `test` is `auto` (Wilcoxon signed-rank for two
`variables`, Friedman for three or more), `wilcoxon`, `mcnemar`, `friedman` or
`cochran` (Cochran's Q, three or more yes/no variables);
`yes_codes` (a code or a list) says what counts as yes for McNemar and Cochran's
Q, `zeros`
(`wilcox` | `pratt`) how Wilcoxon treats a respondent who answered both the
same, `p_value` (`auto` | `exact` | `approximate`) how the p-value is found, and
`posthoc` (`holm` | `bonferroni` | `none`) how Friedman's pairwise Wilcoxon
tests and Cochran's pairwise McNemar tests are adjusted. Outputs: `table`
(descriptives, McNemar's 2 × 2 table, or Cochran's yes count per variable,
with the test as its footer), `pairs` (Friedman's or Cochran's pairwise
comparisons; empty, with a note, for the two-variable tests) and `stat`.
`check_flow` refuses Cochran's Q of two variables and McNemar of three before
the run, and warns of a Counts as yes that neither McNemar nor Cochran's Q
reads.

`analyze.drivers` (Key drivers, `siamang.data.drivers.analyze`) splits the R²
of `y` on `predictors` between the predictors: `method` `relative_weights`
(Johnson's, the default) or `shapley` (the LMG decomposition, exact, at most 15
predictors). Outputs: `table` (Rank, Driver, r, Beta, Beta p, VIF, the
importance and its % of R², largest first — a `DriverTable` whose `analysis` is
the whole result, which `drivers.plot` draws) and `stat`. `check_flow` refuses
fewer than two predictors, and more than 15 with `shapley`, before the run.

`analyze.correspondence` (Perceptual map, `siamang.data.correspondence.analyze`)
is a simple correspondence analysis. `layout` `crosstab` (default) crosses
`row` with `column` (respondents in each pair of answers; a multiple-choice
variable counts each answer chosen); `attributes` counts, for each answer of
`row`, the respondents who ticked each of `attributes` (0/1 variables;
`yes_codes` says what a tick is). `dimensions` (default 2) is how many
dimensions the point tables show. Outputs: `table` (each dimension's singular
value, principal inertia, % and cumulative %, the statistics as its footer),
`rows` and `columns` (mass, quality, inertia %, and per dimension the principal
coordinate, contribution % and cos²) and `stat` (total inertia, the first two
dimensions' %, the chi-square test of a crosstab of single answers, weight,
excluded rows, missing codes). The tables are `MapTable`s whose `analysis` is
the result, which `correspondence.plot` draws. `check_flow` says before the
run that a crosstab needs Columns, an attribute map Attributes (two or more),
and warns of Counts as yes on a crosstab.

`analyze.price` (Price sensitivity, `siamang.data.pricing`) has two `method`s.
`van_westendorp` reads `too_cheap`, `cheap`, `expensive` and `too_expensive`
(the four price questions) and, for the Newton-Miller-Smith extension,
`likelihood_cheap` and `likelihood_expensive` with a `calibration` (code →
probability; empty: 5 → 0.7 … 1 → 0); `gabor_granger` reads `intent` (a
purchase-intent question per price), `price_points` (their prices, same order)
and `yes_codes`. Outputs: `table` (the price points, or the demand per price),
`curves` (every curve at every price named; for Gabor-Granger the demand table
again) and `stat`. Both `table` and `curves` are `PriceTable`s whose `analysis`
is the result, which `pricing.plot` draws. `check_flow` asks for the four
questions, both likelihood questions or neither, the questions and prices of
Gabor-Granger, one price per question (numbers, different, not negative) and
four different Van Westendorp questions, and warns of a calibration without
the likelihood questions.

`analyze.factor` runs an exploratory factor analysis
(`siamang.data.factor.analyze`): `items`, `n_factors` (empty: by `criterion`,
`kaiser` or `parallel` from `seed`), `method` (`minres` | `principal` | `ml`),
`rotation` (`varimax` | `promax` | `oblimin` | `none`), `sort`, `hide_below`,
and `scores` with the prefix `into` (default `factor_`). Outputs: `data` (with
`<into>1` … when `scores` is on), `loadings`, `variance`, `correlations` and
`stat`. `check_flow` knows the score variables, so a later node may name
`factor_1`: exactly `n_factors` of them when it is fixed, and up to one fewer
than the items when a rule chooses — and then the run makes the scores of the
factors kept and, of the rest, the ones a node downstream names (the template
passes them as `read_later={read_after!r}`: `FlowGraph.read_after`), empty,
labelled `Factor 3 score (not made: the Kaiser criterion kept 2 factors)` and
named in the stat's `Scores`, so a later node reading one finds an empty
variable that says why. No other empty score reaches the data. A template may
name `{read_after!r}` as it names `{node!r}`: the variables the node makes that
a node downstream of it reads. The prefix itself is not a variable (`into`
has no `creates`), so a node that names `factor_` is `UNKNOWN_VARIABLE`.
Several nodes expose what the library already computed:

| Node | Engine call | Outputs |
|------|-------------|---------|
| `analyze.descriptives` (Descriptive statistics) | `data.report.descriptives(variables, by=…, detail=…)` | `table`: N, Missing, Mean, SD, Min, Median, Max (+ Q1, Q3, Skewness, Kurtosis) per variable and group; `stat`: missing codes set aside, Weighted N, Effective N, Design effect |
| `analyze.data_check` (Data check) | `data.report.data_check(variables)` | `table`: Severity, Variable, Problem, Rows, Examples, Code; `stat`: Checked, Errors, Warnings |
| `prepare.maxdiff_scores` (MaxDiff scores) | `maxdiff.with_scores(data, question, prefix=…)` | `data` with `<prefix><item code>` per item (default `<question>_score_`); `stat`: respondents scored, unreadable answers |
| `prepare.bands` (Bands) | `bands.bands(data, variable, bins=…, into=…, labels=…, right=…)` | `data` with a labelled ordinal band variable; `stat`: count per band, outside, missing codes |
| `analyze.turf` with `method: fixed` | `turf.evaluate(frame, portfolio, items=…, weight=…, labels=…)` | `table`: reach, unique reach and frequency per option and for the portfolio |
| `prepare.text_code` | `data.report.themes(codeframe, sentiment=…)` | a `stat` output: Coverage, Distinct uncoded answers, and with sentiment the Sentiment split and Net sentiment |
| `output.export_file` | `siamang.io.export_file(data, path)` | `.R` writes the R bundle (CSV, dictionary, import script), `.json` the codebook alone |

`check_flow` knows the variables these create before a run: `into` of Bands,
and one score variable per item of the named MaxDiff question (its `choices`,
else its first variable's labels), so a later node naming `q_md_score_3` is
checked like any other variable and `q_md_score_9` is `UNKNOWN_VARIABLE`. A
`question` the questionnaire has no MaxDiff question for is `PARAM_INVALID`,
with the ones it has: `Parameter 'question' of sc: no MaxDiff question named
'q_mdx'; this questionnaire has: q_md, maxdiff_mx_t1_best.` (by id, name, or
the runtime's `maxdiff_<first variable>` for a question with neither).
`prepare.derive` takes `labels` (code → label) for a formula that yields codes.

`source.simulated` generates its rows with
`siamang.local_simulator.simulate_survey(survey, n=…, seed=…)`: conditions at
every level (page, block, question, answer option), the routing, and the
questionnaire's scripts — an assigned arm is drawn, a `randomize_pages` order
dealt. Quotas are deploy options, not part of the questionnaire, so none
closes in a flow.

`visualize.bar` draws counts or percentages and the chart of a crosstab:
**`show`** (`count` | `percent` of the respondents who answered), **`split`**
(Split by: the answers within each group of a second variable, as column
percentages), **`layout`** (`grouped` | `stacked` | `stacked_100`, with Split
by) and **`sort`** (`code` | `value`, largest first). A document that sets none
of them renders the code it always did (`when: show=count & split=None &
sort=code` is the old line); `by` is written only while Show is count, so a
builder hides it for percentages. Its `checks`: By with Split by is an error
(`By draws the mean of Variable in each group and Split by its answers in each
group — clear one of them.`); By with Show percent (`By (the mean in each
group) is not drawn when Show is percent; to show the answers in each group,
use Split by.`) and a stacked Layout without Split by (`Stacked layouts apply
only when Split by is set.`) are warnings.

It also takes **`top`** (*Top N*) and **`other`** (*Combine the rest as
Other*), **`intervals`** (*Confidence intervals*) with **`confidence`**,
**`letters`** (*Significance letters*) with **`level`** and **`correction`**
(*Multiple comparisons*), and two more Layouts: **`histogram`** with **`bins`**
(`auto`, a number, or edges separated by commas) and **`donut`** with
**`min_slice`** (*Other below (%)*, default 3). Each is written into the code
only when the choices read it — the call of each form is two fragments, its
head and its closing parenthesis, with a line for each of these between them
(`top=`, `other=True`, `intervals=True, confidence=`, `letters=True, level=,
correction=`) — so a stored flow, which sets none, renders the code it always
did, and a builder shows each field only where it applies: Top N except in a
histogram, Other except in a histogram or a donut, Confidence with the
intervals on grouped bars, Significance letters with Show percent and Layout
grouped (their Level and Multiple comparisons once they are ticked), Bins in a
histogram, Other below (%) in a donut; a histogram reads no By, Sort,
Horizontal or Show values, a donut no By, Show, Split by or Horizontal. The
checks: Top N with By is an error (`Top N keeps the answers given most, and with
By the bars are means of groups — clear one of them.`); warnings name what a
form does not draw: `Combine the rest as Other applies with Top N — set Top
N.`, `Top N keeps the answers given most; a histogram draws bins of a number, so
it is not applied.`, `By (the mean in each group) is not drawn in a histogram;
for a histogram of each group, use Split by.`, `By (the mean in each group) is
not drawn in a donut, which shows the shares of Variable's answers.`, `Split by
is not drawn in a donut, which shows one variable's answers as the parts of a
whole; Layout stacked_100 shows the answers within each group.`, `Confidence
intervals are drawn on bars side by side (Layout grouped) only.`, `Confidence
intervals are drawn for percentages and for means by group; counts have none —
set Show to percent.`, `Significance letters compare the groups of Split by —
set Split by.`, `Significance letters are drawn on bars side by side (Layout
grouped), not on stacks.` and `Significance letters compare percentages, as the
Banner table's do — set Show to percent.` Bins that are not auto, a whole
number from 1 to 100 or increasing edges are `PARAM_INVALID` before the run
(`Parameter 'bins' of n: The bins' edges must increase from one to the next,
and 40 is followed by 20.`).

`visualize.heatmap` takes a **`method`** for the correlation matrix drawn
without By: `spearman` (the default; the old line is its fragment, `when:
method=spearman`), `pearson` (weighted when a weight is applied) or `kendall`,
the last two with the codebook's missing codes left out, as Correlation matrix
leaves them out. With By the heatmap shows means, and a Method other than
spearman is a warning: `Method applies to the correlation matrix drawn without
By; with By the heatmap shows means.`

`visualize.likert` (Likert chart) draws a battery of items on one scale as
diverging stacked bars: `items` (ordinal or interval), `neutral` (`split` |
`side`), `sort` (`top2` | `listed`), `show_values`, `title`, `width`, `height`
and a diverging `palette` (`RdBu`, `BrBG`, `PuOr`, `RdYlBu`, `PiYG`,
`coolwarm`). With the questionnaire, `check_flow` compares the items' value
labels (missing codes aside) and reports items on different scales as
`PARAM_CONFLICT` before the run: `n: The items of a Likert chart must share one
scale, and these do not: Trust: Acme has 1 = No trust, 2 = Low, 3 = Medium,
4 = High, 5 = Full; Overall satisfaction has 1 = Very dissatisfied, …. Draw
them in separate charts, or recode them onto one scale first.` An item's scale is
its value labels, else a valid range of 2–11 whole numbers, else the points of
the Likert scale question that asks it (its left and right labels at the ends);
items with none of these (`n: A Likert chart draws the answers of a scale, and
none of the items has value labels (or a valid range of whole numbers) in the
codebook, or a Likert scale question, to say what the scale is.`) and a
multiple-choice item are errors too. For `visualize.bar` the check names a Split
by that allows several answers (`n: Split by needs one answer per respondent,
and <label> allows several: draw it as the Variable, or split by one of its
options after Explode multiple choice.`) and a stacked layout of a
multiple-choice variable (`n: <label> allows several answers, so its options
overlap and cannot be stacked: draw them side by side (Layout = grouped).`),
a histogram of a nominal or ordinal variable (`n: A histogram draws the
distribution of a number, and Region is nominal: draw its answers as bars
(Layout = grouped).`) or of a multiple-choice one (`n: <label> allows several
answers; a histogram draws one number per respondent.`), and a donut of a
multiple-choice variable (`n: <label> allows several answers, so its shares add
up to more than 100 % and are not the parts of a whole: draw them as bars
(Layout = grouped).`).
Items the codebook does not hold (made upstream) are checked when the chart is
drawn — and the runner draws every chart as its node runs, so what a chart
cannot draw fails that node, not the Save report or the preview after it.

Every `visualize.*` node takes **`width`** and **`height`** in inches (2–30,
default 10 × 6) and a **`palette`**; `visualize.heatmap` takes a `cmap` instead
of a palette, and ignores it when it draws a correlation matrix. Every palette
offers **`theme`** (a heatmap's `cmap` takes the word): the chart colours,
text colour, grid and face of the Look of the Save report the chart is saved
through (`ReportTheme`'s `chart_*` fields, reporting reference §1b), which the
report draws the chart in when it is rendered — the chart was drawn at its node
before the Look was known, in the look `SIAMANG_REPORT_THEME` names, else the
defaults, eight colours any two of which readers with protanopia or
deuteranopia can tell apart. A named palette is drawn as it always was. These size the
matplotlib figure itself rather than the picture of it, so the axis labels keep
their proportion. Resolution is a field on the chart (`SurveyChart.dpi`,
default 150) which `save()` uses unless a caller passes `dpi=` explicitly.

`visualize.result_chart` (Result chart) draws the chart that suits an
analysis's result from the numbers the analysis computed
(`siamang.reporting.result_charts`, reporting reference §4): Group means with
their confidence intervals and post-hoc letters, a scree plot, TURF's reach
curve, a regression's forest. Its one input, `result`, takes Tables and Stats
and several edges (`many`): connect the analysis's table — the `variance` or
`loadings` of a PCA or factor analysis — and its stat too where the table does
not say what the chart should (the weight of a regression, PCA, cluster or
TURF, and the base of a regression's intervals). `kind` is `auto` (the chart
the result suits) or `means`, `means_sd`, `interval`, `stacked`, `reach`,
`items`, `utilities`, `scores`, `shares`, `importance`, `partworths`, `scree`,
`loadings`, `profile`, `coefficients`, `heatmap`, `sentiment`, `map` (Perceptual
map, from any of its tables), `curves` (Price sensitivity, from its table or
curves); `title`, `width`, `height` and `palette` as the other chart nodes (Key
drivers — `importance` — the Perceptual map and Price sensitivity keep their
own colours and title lines). `check_flow` reads what is
connected before the run, from the node types and parameters upstream:

- `RESULT_NOT_DRAWABLE` (error): `rc: A Result chart cannot draw the table
  output of Frequencies (fr); it draws the results of Group means, …`, or, for a
  stat alone, `rc: The stat output of Regression (reg) only tells a chart its
  weight and base; connect the output it draws, table, too.`
- `RESULT_KIND` (error): `rc: Kind 'scree' does not suit the loadings output of
  Principal components (pca), which draws 'loadings'; its variance output draws
  'scree'.` What an output draws follows its parameters: TURF's table draws
  `reach`, or `items` with `method: fixed`; MaxDiff's `scores` only with
  `method: counts`; Paired tests' McNemar and Cochran's Q tables `shares`; Code open answers'
  `sentiment` only with `sentiment` ticked.
- `RESULT_SOURCES` (warning): `rc: The results connected come from m, n; a
  Result chart draws one of them — the table output of Group means (m).`

What only the data can tell — a codeframe without sentiment asked to draw it —
fails the node with the reason (`ResultChartError: There is no sentiment to
draw: this codeframe was built without sentiment.`).

`output.save_report` takes a **`theme`** — the `ReportTheme` fields, as an
object — and `output.report_section` takes a **`layout`**, one entry per
connected item: `{"xtab": {"width": "75%", "align": "left"}}`, keyed like
`captions` (`"fa.loadings"` for one output of a node with several). Both are checked
by `check_flow`, so a misspelled field or a width like `"wide"` is named before
the run rather than raised inside it, and both reach only the **HTML**: the
Markdown is the report's content and carries no layout — except the theme's
chart colours, which colour the report's charts of palette `theme` in the
Markdown's figures and the HTML's alike. `check_flow` names a bad one as
`PARAM_INVALID` (`Parameter 'theme' of save: chart_palette: 'purple' is not a
hex colour such as '#2a78d6'.`, `… chart_text_color: '#cccccc' on the charts'
white background has a contrast of 1.6:1; text needs at least 4.5:1.`). A flow that names no
theme leaves `SIAMANG_REPORT_THEME` to answer.

`output.save_report` also takes **`xlsx`** (*Also save tables to Excel*, off by
default): every table of the report in `<path>.xlsx` beside the Markdown, written
by `Report.save_tables` — a sheet per table as its own export writes it (a
Banner's letters, Group means' post-hoc sheet), its statistics under it, named by
its caption or section heading, and a Contents sheet first; charts are left out.
The workbook lands where the report does, so it stays under the flow's outputs. A
document that does not set it renders the code it always did.

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

`visualize.trend` (**Trend**) draws a measure over waves or dates with
`data.plot.trend` (`siamang.reporting.trend`): `time` (a wave code, or a date
column or ISO 8601 text, read in UTC), `period` (`day` | `week` — ISO weeks,
Monday to Sunday, `2026-W22` — | `month` | `quarter` | `year`, default
`month`; not used for a wave code), `measure` (`percent` | `mean` | `count`),
`variable` and `codes` (a JSON code or list, read with `percent` only; checked
by the node's `checks`), `by`, `band` (not read with `count`), `min_base`
(30; not read with `count`, a count being its own base), `title`, `width`,
`height`, `palette`. `check_flow` says what the questionnaire settles and the
run refuses, in the run's words (`PARAM_CONFLICT`): the mean of a nominal or a
multiple-choice question, a multiple-choice question as `time` or `by`, a
missing code among `codes`. Outputs: `chart`, and `table` —
the chart's `.table`, period × group with the measure, its interval and the
bases — for a report or a Live tile; the Trend draws its own chart, so the
table is not a Result chart's result (`RESULT_NOT_DRAWABLE`). `check_flow`
knows the response
timestamps a platform's frame carries (`document.RESPONSE_TIMES`:
`created_at`, `updated_at`, `started_at`, `submitted_at`) as variables any
node may name.

`output.tabbook` (**Tab book (Excel)**) writes every chosen question crossed
by a banner as a workbook with `siamang.reporting.tabbook.write_tabbook`:
`questions` (empty: every nominal, ordinal and multiple-choice variable of the
codebook except the banner, the weight, the response metadata, open answers —
an `OpenText` question, or words without answer labels: `an open answer: code
it first (Code open answers)` — and rankings: `a ranking: every respondent
orders every option, so each would be 100 % — derive its first choice (Derive)
and tabulate that`; named, any is tabulated as asked), `banner`,
`percentages` (`column` | `row` | `none`), `counts`, `letters` with `level`
and `correction` (read only with the letters), `means`, `path` (default
`outputs/tabbook.xlsx`). Its `stat` output: `Workbook`, `Sheets written`,
`Questions skipped`, `Skipped` (each with its reason), `Banner`,
`Percentages`, `Test` and on weighted data `Weight`. Percentages `none` with
Counts off is a `PARAM_CONFLICT`; letters with Percentages other than `column`
a warning, since the letters compare column percentages and are shown only
beside them.

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
  (upstream node id → caption, or `<node>.<port>` → caption for one output of
  a node with several in the section; the output's own key wins, the node's
  answers for its other outputs), `json`. `creates: variable | column` marks a
  parameter whose value is the name of something new for downstream nodes — a
  name, not a prefix: names a node derives from a prefix (Explode's columns,
  factor scores, MaxDiff scores) are counted by `check_flow` itself. A
  `variable` parameter may name `extra: {name: label}`: names beyond the
  codebook's variables a builder's picker should offer, with what to call
  them — the Trend's Time offers the responses' timestamps (`created_at:
  Response date (created_at)`, `submitted_at`, `updated_at`, `started_at`),
  which `check_flow` knows though no codebook declares them. The registry
  payload carries them as `"extra": [{"name": …, "label": …}]`.
- Inputs are a type name or `{type, many, optional}`; `type` may be a list.
- `template`: placeholders `{in.<port>}`, `{out.<port>}` (variable names),
  `{<param>!r}` (the parameter as a Python literal: a condition becomes
  `sg.compare(...)` / `sg.AND(...)`, targets and mappings get typed codes,
  captions become a list aligned with the many-input) and `{node!r}`. A
  template may be a list of fragments, each a string or `{when: <condition>,
  code}`. A condition is `<param>` (set: not empty, not false; a code of 0 is
  set), `<param>=<value>` or `<param>!=<value>`, several joined by `&` when all
  must hold. The fragments are joined line by line, so one may continue a call
  another opened — Paired tests pass `yes` only for McNemar and Factor analysis
  `into` only with `scores` — and a parameter is written only where it is read
  (`NodeSpec.reads`). A parameter stored as null, `""`, `[]` or `{}` is not set: the
  check, the conditions, the rendered code and the subtitle all read its default
  (`FlowGraph.params`, `document.resolved_params`), so a cleared field can
  neither pass the check and then choose no fragment, nor mean something the
  check did not see.
- `checks`: rules between parameters, reported by `check_flow` as
  `PARAM_CONFLICT` on the node — `{when: <condition>, require: <condition> |
  [<condition>, …], message, severity: error | warning}`. When `when` holds,
  one of `require` must hold too; without `require`, `when` alone is the
  problem. `Registry.to_json()` does not carry them: a builder gets them from
  `check_flow`.
- `subtitle`: the one-line summary, `"{row} × {col}"`, or a list of variants —
  `{when: <condition>, text}` or a plain string — of which the first that
  holds is used (TURF: `fixed portfolio {portfolio}` for `method=fixed`, `up to
  {max_size}, {method}` otherwise). `to_json()` gives the plain one as
  `subtitle` and the list as `subtitles`.
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

A chart is drawn at its node, so what it cannot draw fails that node; it is
rendered to a PNG at its own `dpi` there and its figure released
(`SurveyChart.release`): the run keeps every node's output, and the figures of
a thirty-chart report did not fit a 512 MB sandbox. The chart keeps its
picture — `save("x.png")` and a report at that resolution write it without
drawing again — and `plot()` draws it again when you want the Axes.

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
