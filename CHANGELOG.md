# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Interactive charts.** Every chart of `siamang.reporting` says what it draws
  as a Vega-Lite 6 spec (`SurveyChart.vega_lite()`), drawn
  from the numbers its picture is drawn from: inline data of only what the chart
  draws (a scatter plot's points and a box plot's outliers are the plotted
  values, nothing else), the picture's title, axis titles, notes and colors with
  the report Look's text, grid and font, a tooltip on every mark with its value
  as the picture writes it and its base, a legend whose entries hide and show
  their series, zoom where it helps, and a description for a screen reader —
  every form of the Bar chart (percent, Split by grouped, stacked and 100 %,
  Top N with Other, error bars, significance letters, histogram, donut), the
  Likert chart, the heatmaps, the box plot, the scatter plot and the Trend —
  and every kind of Result chart (`siamang.reporting.result_specs`): the means
  and shares with their intervals (a dot and a line per estimate, its base,
  interval and post-hoc letters in the tooltip; Descriptive statistics'
  panels; a profile's lines; a regression's forest, odds ratios on a log
  axis), the bars of MaxDiff, conjoint (part-worths colored and toggled by
  attribute), shares of preference, themes and Key drivers (by the sign of the
  beta), the Net Promoter Score's and sentiment's stacks, a proportion on its
  track, TURF's reach curve (each size's whole portfolio in its tooltip) and
  its options' reach, scree plots (Kaiser's line, parallel analysis), loadings
  and correlation heatmaps (each coefficient's p in its tooltip), the
  Perceptual map (one scale on both axes at any width, each name where the
  picture placed it, zoom, and a **Names on the map** box — off for a map too
  crowded to name its points), Van Westendorp's curves, points and range (a
  line at the price pointed at with every curve's share there; the NMS trial
  curve under them) and Gabor-Granger's demand over its revenue. A renderer a
  later node registers has one when it draws with the shared forms; one that
  draws a figure of its own has none. A row's label is written in narrower
  lines in a chart under 520 pixels wide, and axis titles and subtitles in
  lines a phone's width holds.
  `Report.to_html(standalone=True, interactive=True)` and
  `Report.save("r.html", interactive=True)` draw them in the reader's browser
  with Vega 6.4.0, Vega-Lite 6.4.3 and Vega-Embed 7.3.0, vendored in
  `siamang/reporting/assets/vega` (BSD-3-Clause, with their licenses and a
  README naming the npm sources) and written into the document once, never
  loaded from anywhere; each chart's picture stays for print and for readers
  without scripts. `save("r.md", interactive=True)` writes each figure's spec
  beside it (`r_fig_3.vl.json`). Save report has **Interactive charts in HTML**
  (`interactive`, off: a stored flow renders the code it always did; with *Also
  save HTML* off a check warns), and a Live tile of a chart publishes the spec
  with it (`Tile.spec`). `siamang.reporting.vega` holds what the specs share and
  `write_spec` / `spec_path` for a host that writes a chart's picture itself.
  A legend's selection (`shown`) holds the series shown, so the legend fades the
  entries of the hidden ones, and only a click on an entry toggles; a double
  click on a chart in a report shows every series again. Zoom takes the wheel
  with Ctrl or Cmd held, or a pinch (Shift, which Windows and macOS turn into a
  scroll across, did not zoom there). A tooltip has no row a mark lacks (a
  Trend point's note is on the low-base points alone), a heatmap's written value
  has its cell's tooltip, a mean by group's cell gives the base of its own mean,
  and a Result chart's tooltip names its rows (Region, Term, Theme) and gives
  its base (themes, sentiment, a proportion, PCA loadings; a cluster's as
  `123 respondents (41.0 %)`). A scatter plot's and a box plot's points are
  listed by group and value, not in the data's order, and their specs say
  `usermeta.siamang.respondents`; every spec gives its `title`, and a chart
  that cannot be drawn shorter than a height (a row per label as tall as its
  label, a map, a donut) its `least`. `Report.interactive_figures(html, specs)`
  draws a document's pictures from the specs written beside them (a report
  combined from Markdown). The report lays
  a chart out until it settles (a legend of more rows pushed the title above
  the drawing), keeps titles within the chart's width, gives a phone's width
  the room the menu's button kept, and writes a narrow map's names only where
  they fit. A picture saved from a chart's menu is named by the report and the
  chart (`to_html(..., name=)`), and the document carries the notices of the
  libraries and of what they bundle (`vega.notices()`,
  `assets/vega/THIRD-PARTY-NOTICES.txt`). A donut whose values all sit in its
  slices draws no empty layer (Vega warned of an infinite extent).
- **Coding open answers by hand and by rules: codeframe version 2.** A
  codeframe (`"schema_version": "2.0"`) codes each answer by the first of: a
  coder's decision for its fingerprint (`assignments`: a code, several codes, or
  `[]` — read, and no theme), the themes' rules, nothing (uncoded). The rules run
  at every run, so answers collected after they were written are coded too. The
  file adds `language` (`"en"`), `multiple` (several themes an answer: the theme
  variable is then multiple-choice, a list of codes per answer, with the themes
  as value labels), `max_codes`, `scope` (`clause` or `answer`), `replace`
  (whole words or phrases replaced before the rules read: typos, synonyms), and
  per theme `group` (a net), `exclusive` (*Nothing / Don't know*: kept only when
  no other theme matches), `priority` (which theme a single-theme answer keeps,
  where `max_codes` cuts; ties by order) and `rules` — `include`, `require` (a
  list: any of them; a list of lists: one of each) and `exclude` terms, matched
  within a clause or the whole answer. A term is a word or phrase with `*` for
  word forms (`delay*`), `|` for alternatives (`slow|late`), `not_word` for a
  negated mention only and `A ~N B` for words within N of each other, either
  order, between two punctuation marks — its words split where an answer's are
  (`e-mail` and `n/a` are two words each, quotation marks around it dropped);
  it matches only mentions that are not
  negated (`late` does not match *wasn't late*) unless the negation is its own
  (`don't know`) or the one a `not_` word asks for (`not_friendly staff` finds
  *no friendly staff*). There are no regular expressions (`re:` is refused).
  The words are Unicode — letters, digits and combining marks of any script,
  inner apostrophes kept, case-folded, diacritics kept — so an answer in any
  language is kept and matched; a "word" over 200 characters (a pasted string)
  matches no term. An n't form is one however it is typed: *dont* is *don't*,
  *cannot* and *can not* are *can't*, *do not*, *would not*… are *don't*,
  *wouldn't*…, in the answers and in the terms, so `don't know` finds *I dont
  know* and *I do not know*, and `not` in a term stands for every negation
  written with it (`not happy` finds *wasn't happy*). The negations (*not, no,
  never, n't…*, reaching three words, stopped by the end of a clause and *and,
  or, yet*), clause words (*but, however, although…*) and stop words are
  English. A clause ends at punctuation, at a line break (an answer on several
  lines is read line by line, its fingerprint that of the same words on one),
  at a bullet or `|`, and at `-`, `/`, `·` that do not join two letters (*fast
  - cheap*, but *e-mail*, *n/a*). Only fingerprints of answers are kept: a
  version 2 file with `examples` or an assignment keyed by text is refused, and
  a theme code outside the 32-bit range is an error.
  `siamang.data.text_rules` holds the rules; `text_coding` gains
  `validate(codeframe)` (every error and warning with its path — unknown codes,
  duplicate codes and replacements, empty and unreadable terms, terms that can
  never match: `theme 4 (Mail): include term 'n.a.' can never match: '.' is
  not part of a word — …`, a word a replacement takes away and none writes
  back), `preview(answers, codeframe)` (each distinct
  answer's codes and whether a coder or which rule gave them, with the term and
  the words it matched; counts per theme and net; coverage; and per theme and
  answer `negated`, what reading a negated mention as no match costs the theme
  — *never received my parcel* is not *Parcel* — for a coder to read; 50,000
  distinct answers against 30 themes of 10 terms in a few seconds, a codeframe
  at the limits over a thousand answers in about one, and an answer costs no
  more than its length: a word is looked up by its beginning and end, a term
  tried only where its first word is and only in an answer holding each of
  its words), `explain(text,
  codeframe)` (the words with their negations, the clauses, every rule that
  fired, was vetoed or was blocked by a negation and why, the themes set aside),
  `suggest(answers, n)` (frequent words and two-word phrases of the uncoded
  answers, stop words left out, a negated mention counted apart as
  `not_word`), `coding`, `sources`, and `coverage` gains
  `by_hand`, `by_rules` and `no_theme`. The theme table of a version 2
  codeframe counts respondents: each theme and each net (`Delivery (net)`, a
  respondent once, its themes under it) as a share of those who answered (with
  several themes an answer, `Percentages` says they add up to more than 100 %),
  then `No theme`, `Coded`, `Coded by hand`, `Coded by rules` and `Uncoded`; its
  stats (and the Code open answers node's stat) gain `Coded by hand` and `Coded
  by rules`. `check_flow(..., codeframes={path: document})` knows the theme
  variable a Code open answers node makes — its name when **Theme variable** is
  empty, multiple-choice when the codeframe gives several themes an answer (a
  donut, a Split by, a banner or a Likert chart of it is refused as for a
  multiple-choice question) — and reports a codeframe the run could not apply;
  `resolve_flow`, `FlowRunner` and `generate_flow` take the same `codeframes`,
  so what the check passes the run runs and the generator writes, and
  `read_codeframes(flow, root)` reads them from where the flow runs (as
  `siamang flow check`, `flow run` and `codegen` do). A coder's several themes
  come in the order of the themes. A version 1 codeframe is read and applied
  as before: the same variable, table, chart and generated code.

- **Charts in the report theme's colors: `palette="theme"`.** A `ReportTheme`
  names chart colors — `chart_palette` (a list of hex colors, the series in
  order), `chart_sequential` (magnitude, and the steps of an ordered scale),
  `chart_diverging` (a pair, the low end first), `chart_text_color`,
  `chart_grid_color` and `chart_font` (a font stack; the first face installed
  is used) — and every chart can take them: the Bar chart in all its forms (a
  histogram in the palette's first color, a donut's slices in the palette,
  Top N's Other in the neutral gray, error bars and significance letters in the
  text color), the Box plot, the Heatmap (`cmap="theme"`: the sequential
  color for means, the diverging pair for Spearman, Pearson and Kendall), the
  Scatter plot, the Likert chart, the Trend and every Result chart, Key
  drivers, the Perceptual map and Price sensitivity included (their first two
  colors, the NPS and sentiment's red–gray–blue from the diverging pair, the
  loadings and correlation heatmaps from it too). Each chart node's Palette
  offers `theme`.
  The defaults are a set a reader with protanopia or deuteranopia can tell
  apart: eight colors (`#2a78d6 #eb6834 #335c00 #e08fff #29c2a3 #8f0a5c
  #cc4799 #5233a3`) any two of which are at least 9.5 apart in OKLab (×100)
  under Machado's simulation and 17 with full color vision, each 2:1 on white,
  and blue–red for a scale that diverges; a Trend of more than four lines also
  gives each line's points a shape of its own. An ordered scale's steps are
  each their own color, a sequential color lighter than 2:1 on white (a
  yellow) included, and past the palette a chart's colors keep 2:1; a palette
  or sequential color under 1.3:1 on white is refused (`chart_palette:
  '#ffe8b2' on the charts' white background has a contrast of 1.2:1; a bar or
  a line in it needs at least 1.3:1 to be seen.`). Text written on a fill is white or the theme's text,
  whichever reads better, black where neither reaches 4.5:1. The theme is an
  opt-in: a chart that names a palette of its own — every stored flow's — is
  drawn byte for byte as before. A chart is drawn at its node, before the Save
  report's Look is known, so a report draws each chart of palette `theme` again
  from its parameters in its own theme's colors when they differ from the
  ones it was drawn with (`siamang.reporting.chart_theme.in_report`), in the
  Markdown's figures and the HTML's; at its node the chart takes the look
  `SIAMANG_REPORT_THEME` names, else the defaults. In the theme's colors a Box
  plot's boxes take the palette in the order drawn, undimmed, and a Scatter
  plot's groups in the codebook's order under a legend titled by the
  variable's label. `check_flow` names a bad
  chart color in Save report's Look: `chart_palette: 'purple' is not a hex
  color such as '#2a78d6'.`, `chart_text_color: '#cccccc' on the charts' white
  background has a contrast of 1.6:1; text needs at least 4.5:1.`, `chart_diverging:
  give two colors, the low end first and the high end second, e.g. ['#e34948',
  '#2a78d6'].`

- **Result chart: Key drivers, Perceptual map, Price sensitivity, Cochran's Q
  and the ordinal logit.** `visualize.result_chart` draws the later analyses
  too: Key drivers as `importance` (each driver's share of R²), a Perceptual
  map as `map` (from any of its tables), Price sensitivity as `curves` (Van
  Westendorp's curves and points with the NMS trial curve, or Gabor-Granger's
  demand over revenue) — the charts `drivers.plot`, `correspondence.plot` and
  `pricing.plot` draw, handed to the node whole by `ResultChart.adopt(fig)` —
  and Cochran's Q as `shares` (each variable's yes share with Wilson's
  interval), an ordinal logit as `coefficients` (odds ratios with the table's
  Wald intervals, the thresholds left out). A map whose labels would overlap on
  the figure asked for is drawn taller, and a price chart of two panels at
  least 6 inches tall. `check_flow` knows what those outputs draw; Paired tests with
  Cochran's Q draw `shares` (it said `means`, which the run could not draw).
  The renderers are in `siamang.reporting.method_charts`.

- **Result chart** (`visualize.result_chart`) and `siamang.reporting.result_charts`:
  the chart that suits an analysis's result, drawn from the numbers the
  analysis computed rather than from the data again — Group means with 95 %
  confidence intervals and the compact letter display of their post-hoc test,
  Descriptive statistics, t-test and Paired tests as means with intervals (or
  ± 1 SD), McNemar's yes shares, Proportion CI, the Net Promoter Score's
  stacked groups, TURF's reach curve and a fixed portfolio's reach per option,
  MaxDiff utilities (with intervals), scores and shares, Conjoint importance
  and part-worths, Share of preference, scree plots and loadings heatmaps of
  Principal components and Factor analysis, cluster profiles, a regression's
  coefficients as a forest, the Correlation matrix as a heatmap with its marks,
  and the themes (and sentiment) of Code open answers. The node's one input
  takes several outputs of an analysis — its table, and its stat for the weight
  and a regression's base — and `kind` picks among the charts a result has.
  `check_flow` reads what is connected and says before the run when the chart
  cannot draw it (`RESULT_NOT_DRAWABLE`), when the kind does not suit it
  (`RESULT_KIND`), and when two analyses are connected (`RESULT_SOURCES`, a
  warning); what only the data can tell fails the node with the reason. A chart
  follows the weight of the result it draws and says which in its title. Long
  labels wrap, many rows shrink the font and then grow the figure, and value
  labels stay inside the plot. Later analyses add theirs with
  `register(result_type, kinds, fn)` and `register_output(node_type, port,
  kinds)`. On an odds-ratio axis the minor ticks (1.25, 1.5, 3, …) are named,
  at the tick labels' size, only while the range is too narrow for three major
  ones; on a wide range they ran into 0.5, 1, 2.

- **`siamang.data.intervals`** — the intervals behind a chart's error bars:
  Student's t for a mean, the linearization (Taylor series) interval of a
  weighted mean as `survey::svymean` gives it for `ids = ~1`, and Wilson's
  interval for a share; each says in words when there is no interval to give.

- **Save report: tables to Excel.** `output.save_report` takes `xlsx` (*Also
  save tables to Excel*): every table of the report in `<path>.xlsx` beside it,
  written by the new `Report.save_tables(path)`. Each table gets the sheets its
  own `export_xlsx` writes — a Banner with its significance letters, Group means
  with its post-hoc sheet — a bare DataFrame is written without its index, and a
  table's statistics go under it. Sheets are named by caption, else section
  heading (31 characters, no characters Excel refuses, unique), and a linked
  Contents sheet lists them. Charts are left out. Off by default: a stored flow
  renders the code it did.

- **Likert chart.** `visualize.likert` and `data.plot.likert()`
  (`siamang.reporting.LikertChart`) draw a battery of items on one ordered scale
  as diverging stacked bars centered on the neutral answer — split around the
  center, or drawn apart at the right — or, on an even scale, between the two
  middle answers, with each item's top-2 and bottom-2 shares at the ends and
  the items in order of their top-2 share unless listed. Labels come from the
  codebook; the missing codes and values off the scale are left out and
  counted under the chart with each item's base; shares are weighted when a
  weight is applied. Items with different value labels are refused, naming
  both scales — by `check_flow` before the run when the questionnaire holds
  them, and by the chart otherwise. `chart.table` holds the numbers drawn.

- **Heatmap: Pearson and Kendall.** `visualize.heatmap` and
  `data.plot.heatmap()` take a `method` for the correlation matrix drawn without
  By: `spearman` (the default, drawn as it always was), `pearson` or `kendall`.
  The two new ones are the Correlation matrix table's numbers over the
  respondents who answered every item: the codebook's missing codes left out
  and counted under the plot with N, Pearson weighted when a weight is applied
  (color bar "Weighted Pearson r"), Kendall saying the weight is not applied,
  a pair that cannot be computed a blank cell with the reason. Long labels are
  numbered (`1. label` down, `1`, `2`, … across) and every row is as tall as its
  label. A Method with By is a warning: the heatmap then shows means.

- **Bar chart: Top N, confidence intervals, significance letters, a histogram
  and a donut.** `visualize.bar` and `data.plot.bar()` take `top` (*Top N*: only
  the N answers given most — with Split by, given most overall; for a
  multiple-choice question, the options named most) and `other` (*Combine the
  rest as Other*: one gray bar, last, for the rest — for a multiple-choice
  question the respondents who named any of them, not their sum); `intervals`
  and `confidence` (error bars: Wilson's interval on each percentage — Kish's
  effective base when weighted, the new `siamang.data.intervals.share_interval`
  — and Student's t (weighted, the linearization interval) on each mean by
  group, Group means' interval when it leaves the missing codes out, on bars
  side by side only); `letters`, `level` and `correction` (with Split by, Show percent
  and Layout grouped: the groups of Split by lettered A, B, … in the Banner
  table's order, and over each bar the letters of the groups whose share of that
  answer is significantly lower — the Banner table's column-proportion z-test,
  Bonferroni optional, on the base of those who answered, a group under 30 not
  tested: the comparisons the Tab book prints for the same cells, under the
  letters its banner gives them — the same letters only when Split by is the
  banner's first variable). Layout takes
  `histogram` (an interval or ratio variable in `bins`: `auto`, Freedman and
  Diaconis's width — whole-number answers a whole width, the edges halfway
  between the numbers — a number of bins, or the edges; counts or percent,
  weighted; with Split by, a panel per group sharing bins and scale, at most 12)
  and `donut` (one variable's answers clockwise from the top, each percentage on
  its slice or beside it in a column joined by a line, slices under `min_slice`
  % — 3 by default — combined as Other when there are two or more, the base in
  the middle; with Top N the rest are always Other). The notes under the chart
  say what was left out or combined, the interval's method and level, the
  letters' test, the groups not tested, the bins' rule, answers outside the bins
  given and bins of unequal width. A histogram of a nominal or ordinal
  variable, a donut of a multiple-choice question or with Split by or By, and
  letters or intervals on a stack are refused in a sentence; `check_flow` names
  the first two from the questionnaire, Bins that are not auto, a number or
  increasing edges (`PARAM_INVALID`), Top N with By (an error), and warns of
  parameters a form does not draw — of the intervals and the letters on bars
  only: a histogram or a donut draws neither, and a donut is not told its
  letters are "not on stacks"; By with Show percent is warned of on bars too,
  a histogram's and a donut's own rule on By saying the rest. Each new field is written into the node's
  code only when the choices read it, so a stored flow renders the code and the
  picture it did; the warning `Layout applies only when Split by is set.` now
  reads `Stacked layouts apply only when Split by is set.` The Banner table's
  test is `siamang.reporting.tables.proportion_letters` (with `banner_values`
  and `column_letter`), shared by the Banner table, the Tab book and the chart.

- **Bar chart: percentages, Split by, and largest first.** `visualize.bar` and
  `data.plot.bar()` take `show` (`count` | `percent` of the respondents who
  answered), `split` (Split by: the answers within each group of a second
  variable — the chart of a crosstab, percentages of each group, weighted like
  the Crosstab), `layout` (`grouped` | `stacked` | `stacked_100`) and `sort`
  (`code` | `value`). A multiple-choice question's percentages are of
  respondents and add up to more than 100 %, which the chart says; its options
  overlap, so they are drawn side by side and never stacked. These forms leave
  the codebook's missing codes out of the bars and count them, and write the
  base, the weight and each group's `n` on the chart. A color belongs to its
  answer whatever the order, an ordered scale is one hue light to dark, long
  labels wrap, and a small figure grows taller rather than squash its plot. At
  the defaults the chart and the node's code are what they were; the node's
  checks refuse By with Split by and warn of By with percentages and of a
  Layout without Split by. A multiple-choice question at the defaults, which
  raised `unhashable type: 'list'`, is drawn as counts of respondents.

- **`UIConfig.allow_theme_switch`** — whether the respondent may change the
  survey's light/dark theme. The runtime has always shown that button and
  remembered the choice, which made `default_theme` only ever a starting point:
  a stored value beat it. Set it to `False` and the button is not rendered, the
  stored value is not consulted, and the survey is pinned to `default_theme` —
  the questionnaire is an instrument, and a presentation half the sample can
  change is an uncontrolled variable. It stays `True` by default, because
  reading on a dark screen is an accessibility need rather than a preference.
  `default_theme` is now validated by `UIConfig` like its other enumerations.

- **`theme` and `layout` flow parameters** and per-item placement on `Report`.
  `Report.add()` / `.image()` take a `width`, an `align` and a `break_before`,
  validated where they are written; `output.save_report` takes a `theme` and
  `output.report_section` a `layout` keyed by the item's node, both read by
  `check_flow` so a misspelled field is named on the document rather than raised
  in a run. They are kinds of their own for the same reason `formula` is one.
  The theme travels as plain data in the generated script — no import to add —
  and everything that accepts a theme accepts a mapping too. All of it reaches
  the HTML only: Markdown is the report's content and carries no layout.

- **The respondent's theme is remembered per survey.** The key was the constant
  `siamang_theme`, and `localStorage` is per origin, so every survey served from
  one host shared it: a respondent who chose dark in one study arrived in the
  next one dark. It is now `siamang_theme_<survey id>`, keyed like the saved
  answers beside it by the transport's `survey_id` (the id the runtime read
  before was never set; see the storage entry under *Fixed*), and reading and
  writing it are wrapped: storage does not merely come back empty in a private
  window, it throws.

- **`siamang.reporting.ReportTheme`** and a real HTML document. `Report.to_html()`
  returned a bare `markdown.markdown()` fragment — no `<head>`, no charset, no
  stylesheet — so every caller had to invent a look, which is another way of
  saying the report had none of its own. `to_html(standalone=True)` and
  `save("r.html")` now write a whole document with the theme's stylesheet in it,
  its tables rendered by the table components (so `SurveyTable.to_html()` and its
  `siamang-table` class are finally reached) and its figures in a `<figure>` with
  their caption. The theme is the questionnaire's `UIConfig` shape — one named
  preset plus tokens you may override, stored sparsely — and `academic`,
  `modern` and `humanist` name the same typefaces in both. `Report(theme=…)`,
  `Report.combine(…, theme=…)` and `ReportTheme.from_env()` (via
  `SIAMANG_REPORT_THEME`, mirroring `SIAMANG_PROVENANCE`) are the ways in.
  `to_html()` without `standalone` is unchanged, byte for byte, and Markdown is
  untouched by any of it.

- **Figure geometry on the chart nodes.** `visualize.bar` / `boxplot` /
  `scatter` take `width` and `height` in inches and a `palette`;
  `visualize.heatmap` takes `width`, `height` and `cmap`. `SurveyChart` and the
  `plot` accessor already accepted all of it — the node specifications simply
  never passed it on, so a flow could not change the size of the figure it
  drew. `SurveyChart.dpi` is a field now (default 150) and `save()` falls back
  to it, so whatever writes a figure out can raise the resolution of every
  chart at once without threading an argument through.

- **`MaxDiff`** — best–worst scaling. A few items at a time, and for each set
  the respondent picks the best and the worst; the trade-off is the
  measurement. `siamang.design.maxdiff_design` builds the balanced incomplete
  block design and reports its own balance — how often each item and each pair
  was shown — because a design nobody can check is a design nobody should
  trust. The design is fixed by a seed (derived from the question when none is
  given), so the same questionnaire always asks the same tasks.
- **`siamang.data.choice`** — choice sets and a conditional logit fitted on
  them by maximum likelihood, on numpy and scipy alone. The shape every
  trade-off method needs: alternatives in rows, grouped into the sets one
  choice was made from.
- **`siamang.data.maxdiff`** — counting scores (best minus worst over shown,
  per item and per respondent) and utilities with the shares they imply.
  `report.maxdiff(...)` tabulates both against a base; `analyze.maxdiff` runs
  it from a flow.
- **`Conjoint`** and **`Attribute`** — choice-based conjoint: whole products
  side by side, pick one. `siamang.design.cbc_design` builds the design by
  improving several random starts on D-error, and reports the level balance and
  the task overlap against the floor that is arithmetically forced. A design too
  small to be fitted reports so, and `lint()` says it in words before fieldwork
  rather than after the model fails to converge.
- **`siamang.data.conjoint`** — part-worths in one currency across attributes,
  attribute importance (of the levels tested, which the table says out loud),
  and shares of preference for hypothetical products. `report.conjoint(...)`,
  `analyze.conjoint` and `analyze.conjoint_shares`.
- **`siamang.io.choice.write_maxdiff_choices`** — the choices in the long
  format R's hierarchical-Bayes packages read, with a column dictionary and a
  script, so individual-level utilities can be estimated outside the engine.
  `output.choice_data` and `output.conjoint_data` write it from a flow.
- **`siamang.data.formula`** and **`SurveyData.derive_formula`** — a derived
  variable computed by arithmetic rather than by a condition: the four
  operators, `mean`/`sum`/`min`/`max`/`abs`/`round`/`log`/`coalesce`, and
  `if … then … else`. The formula is text, parsed by hand into a tree and
  evaluated vectorized; nothing is executed, and what cannot be read is
  reported with the character reading stopped at. Missing stays missing —
  dividing by zero gives no value rather than infinity, which would read as a
  number all the way into a report. `formula` is a flow parameter kind, so
  `check_flow` catches a typo before a run; `prepare.derive` runs it.
- **`report.banner(...)`** and **`analyze.banner`** — the cross-break, in the
  shape an agency reads: blocks of columns, a base row, and each cell carrying
  its column percentage, its count and the letters of the columns it is
  significantly higher than. Columns are compared only within a banner
  variable, whose values are mutually exclusive; on weighted data the test uses
  Kish's effective base, and a column under thirty respondents is not tested at
  all. `data.tables.banner` still gives the same numbers in tidy form.
- **`siamang.model`** — the questionnaire as a JSON document.
  `to_document(survey, options)` serializes every core object (`Variable`,
  all seven question types, `Option`, `Media`, `Block`, `Page`,
  `Expression`, `Script`, `Quota`, `UIConfig`, compiler options, deadline)
  into a plain dict; `from_document(doc)` rebuilds them. The round trip is
  lossless: the rebuilt survey compiles to the same `SurveySchema`, and
  re-serializing it returns the same document. Factory-made scripts are
  stored by name and parameters; codebook codes keep their type and order.
- **JSON Schema** for the document format
  (`siamang/schemas/questionnaire-1.0.json`, generated from the dataclasses
  by `scripts/gen_document_schema.py`) and `validate_document()` on top of
  it. `jsonschema` is a new dependency.
- **`siamang model import`** writes a module's `survey` + `options` as a
  document; **`siamang model check`** validates a document the way
  `siamang validate` validates a module.
- **`siamang.codegen`** — `generate_questionnaire(document)` renders a
  document as the Python file a researcher would have written: variables,
  questions, pages (with the page factories), scripts, `survey`, `options`,
  each object marked with `# studio: …`. Output is deterministic, laid out
  like `ruff format` and passed through it when ruff is installed
  (`pip install "siamang[codegen]"`), and converts back to the same
  document with `siamang.model.to_document`. CLI: **`siamang codegen
  questionnaire.json [-o questionnaire.py]`**.
- **Pipeline helpers in `siamang.data`** — `respondents` (`dedup_responses`,
  `completion_time`, `partial_flag`, `speeders`), `weights`
  (`cell_weights`, `rake_weights` with an optional `cap`,
  `effective_sample_size`) and `stats` (`frequencies`, `crosstab`, `chi2`
  on a bare frame). Plain pandas functions that combine with
  `SurveyData.with_frame`; the first two sets were previously only
  available in the Siamang Cloud SDK.
- **`siamang.flow`** — analysis flows. A flow document (`flow-1.0.json`
  schema) is a graph of typed nodes from a YAML **node registry**
  (30 nodes: sources, prepare, analyze, visualize, output; `siamang flow
  nodes`). `check_flow` validates it against the registry and the
  questionnaire's codebook; `FlowRunner` executes it in-process on a
  `SurveyData` or a snapshot, with `live.capture()` collecting the tiles
  `output.live_tile` nodes publish; `generate_flow` renders the script a
  researcher would have written, with a `--data` switch between the
  platform database and a local snapshot. Runner and generator use the
  node templates verbatim, so the script reproduces the runner's report.
  `PyYAML` is a new dependency. CLI: **`siamang flow check | run | nodes`**
  and **`siamang codegen <name>.flow.json --questionnaire …`**.
- `SurveyData.filter(expression)` keeps the rows matching a questionnaire
  condition; `SurveyTable.stats` exposes a table's statistics as a dict;
  `Report.add` accepts a statistics mapping.
- **Snapshots** — `siamang.io.read_snapshot` / `write_snapshot`: a data
  file (Parquet, CSV, Excel, SPSS, Stata) plus `<name>.dictionary.json`,
  read back into a `SurveyData` with the codebook, embedded metadata or the
  questionnaire's variables. Parquet via the new `siamang[parquet]` extra;
  `SurveyDataReader` accepts `.parquet`.
- **Tests chosen by hand, in the engine and in flows.** Until now a flow could
  only take the test Group means chose for it, the chi-square of a crosstab and
  a Spearman correlation, and nothing compared the groups pairwise afterward.
  - **`siamang.data.inference`** (numpy and SciPy only; SciPy 1.11 is enough):
    Pearson (with a Fisher-z interval, and a weighted form whose p and interval
    are on Kish's effective base), Spearman and Kendall tau-b correlations and
    matrices of them, pairwise or listwise; Welch's and Student's, paired and
    one-sample t-tests with the mean difference, its interval, Cohen's d and
    Hedges' g; one-way and Welch's ANOVA with η², Kruskal-Wallis with ε²,
    Mann-Whitney with the rank-biserial r; Tukey's HSD (Tukey-Kramer),
    Games-Howell and Dunn's test; Fisher's exact test — 2 × 2 with the
    conditional odds ratio and its exact interval as R's `fisher.test` defines
    them, larger tables by the Fisher-Freeman-Halton test, summed exactly over
    up to 200,000 tables with the observed margins and otherwise estimated from
    20,000 tables drawn from a fixed seed, so a rerun gives the same p; and
    `adjust_p` (Holm, Bonferroni, Benjamini-Hochberg, as R's `p.adjust`). Data
    that cannot carry a test (one respondent in a group, no variance) raises
    `NotTestable` with a sentence, which the tables print instead of a number.
    "No variance" allows for floating-point rounding (`no_spread`: a range of
    at most 10⁻¹² of the values' size), so three answers of 1.4 — variance
    7e-32 — are refused as three answers of 2 are, rather than giving t = 10¹⁵.
    `without_missing_codes` leaves the codebook's declared missing codes out and
    counts them: every result built on these tests reports `Missing codes left
    out` rather than averaging a "Don't know" coded 99.
  - **`analyze.correlation`** takes a **Method**: `pearson`, `spearman` (the
    default, computed as before) or `kendall` — `data.analysis.correlation(x, y,
    method=…)`. Pearson is weighted when a weight is applied.
  - **`analyze.correlation_matrix`** (new; `data.report.correlation_matrix`,
    `CorrelationMatrixTable`): several variables, Pearson / Spearman / Kendall,
    **Missing answers** pairwise or listwise, **p adjustment** none / holm /
    bonferroni / fdr_bh, and a **Layout**: the lower triangle with `*`, `**`,
    `***` marks, or one row per pair with the coefficient, p, adjusted p and N.
    A pair that cannot be computed reads `n/a` in the matrix and is blank in
    the pairs layout, as a t-test's SD of one answer and a post-hoc pair that
    cannot be compared are blank.
  - **`analyze.ttest`** (new; `data.report.ttest`, `TTestTable`): **Design**
    independent (Welch's by default, Student's under **Variances**; **Group A** /
    **Group B** pick two groups of a grouping with more, and without them such a
    grouping is refused with its groups listed, as are one group named twice
    and a multiple-choice grouping, whose groups overlap),
    paired, or one-sample against a
    **Test value**; a row of N, mean, SD and SE per group, and t, df, p, the mean
    difference with its CI and Cohen's d in the footer.
  - **Group means** takes a **Test** — `auto` (the default: the automatic
    choice, unchanged), `student`, `welch`, `anova`, `welch_anova`,
    `mannwhitney`, `kruskal` — and a **Post-hoc**: `tukey` after ANOVA,
    `games_howell` after Welch's ANOVA, `dunn` after Kruskal-Wallis with a
    **Dunn p adjustment** (holm or bonferroni). The pairs — difference,
    interval, q or z, adjusted p — render under the means table
    (`GroupMeanTable(method=…, posthoc=…, adjust=…)`, `.posthoc_table`,
    `PostHocTable`) and on a second sheet of `export_xlsx`.
  - **Compare groups** takes a **Post-hoc** `dunn` after Kruskal-Wallis
    (`data.analysis.compare_groups`): one entry per pair of groups, by label.
  - **Crosstab** takes a **Test**, `chi2` (default) or `fisher`. It counts
    respondents, as an exact test must, and says so on weighted data.
  - A node specification may declare **`checks`** between its parameters, which
    `check_flow` reports as `PARAM_CONFLICT` on the node — an error for a
    post-hoc test that does not follow the test chosen ("Tukey's HSD follows a
    one-way ANOVA — set Test to anova, or Post-hoc to none."), a warning for a
    parameter the node would ignore. A template's `when` also reads `!=` and
    joins conditions with `&`. A parameter stored as null, `""`, `[]` or `{}`
    takes its default in the rules, the conditions and the code alike, as the
    check already read it.

  Stored flows keep their meaning and their code: Group means and Crosstab keep
  the **Significance test** checkbox (`test`) and the new **Test** sits beside
  it, so `test: true` / `false` mean what they did, a document that never set
  the new parameters renders exactly the code it rendered before, and the
  defaults read the data as they always have. A test chosen by hand leaves the
  codebook's missing codes out of its table and test; put **Missing values**
  before the defaults to have them do the same. The defaults now say when they
  counted a missing code as an answer — `Missing codes counted as answers` in
  the stats of Group means' automatic test and Crosstab's chi-square,
  `missing_codes_counted` in `kruskal`, `mannwhitney` and `spearman`
  (`inference.missing_codes_counted`) — so a result that changes with the Test
  or the Post-hoc chosen says why.
- **Paired tests** — `siamang.data.paired` and the flow node
  **`analyze.paired`** compare answers that come in sets from one respondent:
  **Wilcoxon signed-rank** for two ordered variables (the difference is first
  minus second, as R's `wilcox.test(x, y, paired = TRUE)`, SciPy and the paired
  t-test take it — McNemar's difference in points and Friedman's pairs too;
  zero differences dropped,
  or ranked with `zeros="pratt"`; exact p-value for small samples and the
  tie-corrected normal approximation otherwise, as SciPy 1.13+; `Z`, `r = Z/√n`
  and the matched-pairs rank-biserial correlation), **McNemar** for two yes/no
  variables (`yes` names the codes; exact binomial below 25 discordant pairs,
  chi-square with continuity correction above; both discordant counts, the two
  shares, Cohen's g and the odds ratio), and **Friedman** for three or more
  (tie-corrected chi-square, Kendall's W, and pairwise Wilcoxon tests adjusted
  by Holm or Bonferroni in a `pairs` output, whose N is every respondent
  compared, with the zero differences of each pair beside it). `auto` runs Wilcoxon for two
  variables and Friedman for more. A respondent missing any of the variables
  is left out of all of them, the codebook's missing codes count as missing,
  and the statistics say how many were excluded and which codes were met.
  Nominal variables are refused by Wilcoxon and Friedman, which rank answers.
- **Factor analysis** — `siamang.data.factor` and the flow node
  **`analyze.factor`**: exploratory factor analysis of three or more items,
  extracted by minres (default), iterated principal axis or maximum
  likelihood (with its test of fit); the number of factors fixed, by the
  Kaiser criterion or by parallel analysis from a seed; rotated by varimax,
  promax (power 4) or oblimin (direct quartimin), or not at all. Outputs the
  loadings with communality, uniqueness and per-item MSA (sortable, small
  loadings hideable), the eigenvalues and variance explained, the factor
  correlations, and KMO, Bartlett's test and RMSR; with `scores` it adds
  regression-method factor scores to the data as `factor_1`, `factor_2`, …
  (labeled variables a later node can name). The numbers reproduce the
  `factor_analyzer` package and `psych::fa` / `factanal`; the conventions
  (sign, order, Kaiser normalization) are in the module's docstring. Maximum
  likelihood is started from 14 fixed points (factanal's, minres, 1 − SMC, 0.5
  and ten from a fixed seed) and keeps the lowest objective, so a model with
  more factors than the data carry does not report a local optimum as its fit;
  the stats warn when the starts disagree. Fewer
  than three items, no more respondents than items, a constant item, a
  singular correlation matrix and as many factors as items are refused with
  the reason.
- Both are unweighted and, on weighted data, say
  `Weight: unweighted (the weight 'w' is not applied)` in every table they
  output (factor analysis: the loadings, the variance and the factor
  correlations, each of which a report may show alone); Apply weight's help
  lists them. Their tables are `siamang.reporting.result_table.ResultTable`s: a
  report or a Studio preview shows each with its statistics as a footer, and a
  cell that does not apply is blank rather than `nan`.
- **Flow nodes for what the engine already computed.**
  - **Descriptive statistics** (`analyze.descriptives`, `data.report.descriptives`,
    `siamang.data.descriptives.describe`): N, Missing, Mean, SD, Min, Median and
    Max of several numeric variables, per group with `by`, and Q1, Q3 (type 7),
    skewness and kurtosis (bias-corrected G1, excess G2) with `detail`. The
    codebook's missing codes and values that are not numbers count as missing
    and the stats name them (`Missing codes`, `Not numbers`); a blank or a
    missing code of the group variable is no group (`Not in a group`); a
    multiple-choice group variable gives one overlapping group per option
    (`Groups: overlap: …`). On
    weighted data the mean, SD, median and quartiles are weighted with the Group
    means table's formulas beside a `Weighted N` column, N and Missing stay
    counts, and the stats give `Weighted N`, `Effective N` (Kish), `Design
    effect` and a `Note` that skewness and kurtosis are unweighted. An undefined
    cell (the SD of one answer) is NaN in `to_frame()` and blank when printed.
  - **Data check** (`analyze.data_check`, `data.report.data_check`,
    `siamang.data.checks.check`): `SurveyData.validate()` as a table — Severity,
    Variable, Problem, Rows, Examples (`7 (12), 8 (1)`) and Code, errors first —
    with the columns the codebook lacks, and the variables the data lacks,
    gathered into one row each; stats `Checked`, `Errors`, `Warnings`, `Result:
    no problems found`, and on weighted data that the weight is not applied.
    The weight column and the response metadata (`respondent_id`, `duration_s`,
    `partial`, `url_*`, … — `checks.METADATA_COLUMNS`) are expected beside the
    codebook and named in `Not in the codebook, as expected`, not reported.
  - **MaxDiff scores** (`prepare.maxdiff_scores`,
    `siamang.data.maxdiff.with_scores`): one interval variable per item,
    `<question>_score_<code>` unless a `prefix` is given, labeled `MaxDiff
    score: <item>` with a valid range of −1…1 — each respondent's best minus
    worst over the times the item was shown to them, blank where it never was —
    so preferences feed Crosstab, Cluster and Regression. A `stat` output gives
    `Respondents scored`, `Not scored` and `Unreadable answers`. `check_flow`
    knows the variables before a run, and names a question the questionnaire
    has no MaxDiff question for, with the ones it has (`PARAM_INVALID`).
  - **TURF** reads a fixed portfolio: `method: fixed` with a `portfolio`
    (`siamang.data.turf.evaluate`) gives each option's reach, `unique` reach
    (what dropping it would lose) and frequency, and the portfolio's reach and
    frequency, on the question's base; stat `Search: none: a fixed portfolio`,
    `Reach`, `Frequency`. Its subtitle is `fixed portfolio <options>` (a node
    spec's `subtitle` may now be a list of `{when, text}` variants, given to a
    builder as `subtitles`), a single option's total row reads `The one
    option`, and the check warns that Always include is not read with Search =
    fixed and Portfolio only with it. Paired tests warn that Counts as yes is
    read only by McNemar, and with one variable and Test auto say that paired
    tests compare two or more variables.
  - **Code open answers** has a `stat` output: the theme table's stats now
    carry `Coverage` (`75.0 % of the answers have a theme`), `Distinct uncoded
    answers` and `Percentages`, and with `sentiment` a codeframe built with it
    adds `Negative %`, `Neutral %`, `Positive %` to every row and `Sentiment` /
    `Net sentiment` to the stats (`Sentiment: not in this codeframe` when it has
    none). `data.report.themes(codeframe, sentiment=False)`;
    `text_coding.uncoded_answers()` returns the uncoded texts.
  - **Export file** writes an R bundle for a `.R` path (`<name>.csv`,
    `<name>.dictionary.json` and the `<name>.R` script that reads them with
    factors and `NA` for the missing codes) and the codebook alone for a `.json`
    path. `siamang.io.export_file()` / `EXPORT_FORMATS` do the same outside a
    flow.
  - **Bands** (`prepare.bands`, `siamang.data.bands.bands`): a number cut into
    a labeled ordinal variable (`18 to under 30`, …) after the codebook's
    missing codes are taken out, with a `stat` of the count per band and what
    fell outside. **Derive** takes `labels` for a formula that yields codes.

- **Cochran's Q** in Paired tests (`analyze.paired`, Test `cochran`;
  `siamang.data.paired.cochran`, `cochran_test`): McNemar's question for three
  or more yes/no variables answered by the same respondents — is the share
  saying yes the same for all? `Q = (k − 1)(k ΣCⱼ² − N²) / (k N − ΣRᵢ²)` on
  k − 1 df, as R's `DescTools::CochranQTest` and statsmodels' `cochrans_q`.
  **Counts as yes** is read as for McNemar (empty for 0/1 variables); the table
  gives each variable's yes count and `% yes`, the stats `Q`, `df`, `p`, and the
  `pairs` output a McNemar test of every pair (the two shares, the difference in
  points, both discordant counts, the exact or chi-square p by McNemar's rule)
  adjusted by Holm (default) or Bonferroni (**Pairwise comparisons (Friedman,
  Cochran's Q)**). Listwise, missing codes left out and counted, unweighted and
  saying so, as the other paired tests. `auto` still picks Wilcoxon or Friedman,
  so stored flows render the same code. The check refuses Cochran's Q of two
  variables ("Cochran's Q compares three or more yes/no variables; 2 were given.
  For two, use McNemar.") and McNemar of three now adds "For three or more
  yes/no variables, use Cochran's Q."; the warning for an unread Counts as yes
  reads "Counts as yes is read only by McNemar and Cochran's Q — set Test to
  mcnemar or cochran, or clear it."

- **Ordinal logistic regression** — Regression's **Model** `ordinal`
  (`data.analysis.regression(..., kind="ordinal")`, `siamang.data.ordinal`):
  the proportional-odds (cumulative logit) model of three to 20 ordered
  answers, `logit P(y ≤ j) = θⱼ − xβ` as R's `MASS::polr` (a positive
  coefficient makes the higher answers more likely). Maximum likelihood by
  SciPy's BFGS on the exact gradient, polished by Newton steps on the exact
  Hessian; the table lists each coefficient with its SE, z, p, odds ratio and
  95 % Wald interval, then the thresholds (`Low|Medium`); the stats give the
  answers' order, N, the log-likelihood, McFadden's pseudo-R², the
  likelihood-ratio test, AIC and convergence. It reproduces `polr` and
  `ordinal::clm` on `MASS::housing` (with its frequencies as weights) and
  `wine`. The codebook's missing codes are left out and counted; weights enter
  the likelihood as the logit's do, and the stats say what they sum to when they
  do not average about 1. Too few or too many answers, text codes, constant or
  collinear predictors are refused with the reason; non-convergence and a
  predictor that separates the answers are warned. `auto` never chooses it, so
  stored flows run as before.

- **Key drivers** — `siamang.data.drivers` and the flow node
  **`analyze.drivers`** (Key drivers): each predictor's share of the outcome's
  R², by **Johnson's relative weights** (default; as R's `rwa` and Python's
  `relativeImp`) or the **Shapley value** decomposition (LMG, exact from all
  2^p subset regressions, as `relaimpo::calc.relimp(type = "lmg")`; at most 15
  predictors), shown also as a percentage of R², beside each predictor's
  correlation with the outcome, standardized beta with `lm`'s t-test p, and VIF;
  the stats give R², adjusted R² and the F-test. Weighted through the weighted
  correlation matrix (as `relaimpo` weighs), tests on Kish's effective N;
  listwise, missing codes left out and counted. A nominal predictor with more
  than two answers, a constant or collinear predictor and too few respondents
  are refused with the reason; a VIF of 10 or more and a suppressor are warned.
  `check_flow` refuses fewer than two drivers and more than 15 with Shapley
  before the run ("Key drivers splits R² between two or more predictors; 1 was
  given. …"). `drivers.plot(result)` draws the shares as horizontal bars,
  largest first, a negative beta in a second color, and returns the matplotlib
  Figure; the table (`DriverTable`) carries the result in `analysis`.

- **Perceptual map** — `siamang.data.correspondence` and the flow node
  **`analyze.correspondence`**: simple correspondence analysis of a crosstab of
  two variables (a multiple-choice variable counts each answer) or of a
  brand-image grid (per answer of **Rows**, the respondents checking each 0/1
  **Attribute**; **Counts as yes** for other codes), by the SVD of the
  standardized residuals as `ca::ca` and FactoMineR's `CA`: principal inertias
  and their share of the total, row and column principal coordinates, masses,
  contributions, cos² and quality, in a `table`, `rows` and `columns` output
  and a `stat`. Each dimension is signed so the row contributing most to it is
  positive (packages differ: on `smoke`, FactoMineR mirrors ca's second
  dimension). Weighted counts when a weight applies; the chi-square test of a
  crosstab of single answers counts respondents; missing codes left out and
  counted, empty answers named. `check_flow` says a crosstab needs Columns ("A
  crosstab map crosses Rows with Columns — choose the Columns variable.") and
  an attribute map two or more Attributes before the run.
  `correspondence.plot(result)` draws the symmetric map of the first two (or
  any two) dimensions, one scale on both axes, with labels placed beside their
  points so that they overlap no label or point and read as their own point's
  (a thin line back when they had to move out), wrapped and shrunk as the map
  fills; it returns the matplotlib Figure, and the tables (`MapTable`) carry
  the result in `analysis`.

- **Price sensitivity** — `siamang.data.pricing` and the flow node
  **`analyze.price`**. **Van Westendorp**: the four price questions give the
  too cheap, cheap / not cheap, expensive / not expensive and too expensive
  curves (weighted shares at every price named, joined by straight lines) and
  the PMC, OPP, IPP and PME where they cross — the middle of the stretch where
  two lines run together, none (with a note) where they do not meet — and the
  range of acceptable prices; respondents whose prices are not in order are left
  out and counted (`Inconsistent`). With the two likelihood questions, the
  **Newton-Miller-Smith** trial and revenue curves (calibration 5 → 0.7 … 1 → 0
  by default) and the prices of highest trial and revenue. **Gabor-Granger**:
  purchase intent at set prices gives the demand, revenue per respondent and
  index, arc elasticities and the revenue-maximizing price among those asked;
  respondents answering yes at a higher price but no at a lower one are counted
  (`Not monotone`). Weighted shares; missing codes left out and counted.
  `check_flow` asks for what each method reads and checks the prices against
  the questions before the run ("Prices lists 3 prices for 4 purchase-intent
  questions; give one price per question, in the same order."). `pricing.plot`
  draws the four curves with the points named and the acceptable range shaded
  (the trial curve in a panel below with NMS), or demand above revenue for
  Gabor-Granger — never two scales on one axis — and returns the matplotlib
  Figure; the tables (`PriceTable`) carry the result in `analysis`. On a small
  figure the names stacked at close prices stay a text's height apart,
  crowded price labels turn 45°, and the legend takes two rows below 6.5
  inches wide.

- **Trend** (`visualize.trend`, `data.plot.trend(...)`,
  `siamang.reporting.trend`) — a measure over waves or dates for a tracking
  study, one line per group of *Split by*. *Time* is a wave code (one point
  per code, ordered by code, the codebook's labels on the axis; a wave the
  codebook declares between two found ones is a gap) or a date: a `datetime64`
  column or ISO 8601 text as a platform snapshot writes it
  (`2026-05-25 09:00:00+00:00`, `2026-05-25T09:00:00.000Z`, `2026-05-25`),
  read in UTC and grouped by *Period* — `day`, `week` (ISO weeks, Monday to
  Sunday, labeled `2026-W22`), `month` (`May 2026`), `quarter` (`2026 Q2`)
  or `year`, every period between the first and the last on the axis. The
  *Measure* is the percent choosing the *Answer codes* (a list is a top-2
  box; for a multiple-choice question, any of them), the mean of a
  variable, or the count of respondents; weighted data gives weighted points
  and a weighted base per point. The confidence band is a share's Wilson score
  interval — the Bar chart's, which keeps a width at 0 % and 100 % where the
  normal approximation has none — or the mean's t interval, on Kish's
  effective base when weighted. A percent or a mean under *Minimum base* (30)
  respondents is drawn hollow, without its band (a mean of two respondents'
  t interval runs from −46 to 56 on a 0–10 scale; the value axis fits the
  points and the bands drawn), and noted (`base below 30`, `no respondents`,
  `their weights sum to 0`); a point at 0 % or 100 % is drawn whole on the
  frame; a count is its own base, so *Minimum base* is not read with it (nor
  written into its code) and its table has no `Note`. Outputs: the `chart`,
  and a `table` of period × group with the measure, `Lower 95%`, `Upper 95%`,
  `Base`, `Weighted base`, `Effective base` and `Note`, whose statistics say
  what was measured, how time was read, the missing codes left out and the
  rows without a time or whose text is not a date (`Left out`). The chart is
  drawn as the newer charts are: a color of its own for every line however
  many (past the palette's ten, lighter and darker ones), the bands of up to
  four lines (more would hide one another and the lines: "No bands: the 95%
  intervals of 13 lines would hide one another; the table gives each
  point's."), ticks on whole percents, thousands separated on a count or a
  mean axis, the period labels level — wrapped to the room between two ticks
  as measured — or slanted in as many lines as fit and thinned only when they
  must be, the title and axis titles wrapped to the plot, the legend beside
  it (under it on a figure narrower than 7.5 inches, or when it is taller
  than the plot: `chart_parts.legend_below`, the Bar chart's, now shared), and
  under it the base and what was left out ("Base: 3,790 respondents who
  answered (weighted: 4,646.0); 157 to 201 per point.", "Gaps: no
  respondents in 3 of 39 points.", "Hollow points: fewer than 30
  respondents, drawn without a band (the table gives their intervals).",
  "Bands: 95% confidence intervals.", "Not drawn: 1 point
  whose respondents' weights sum to 0.", "Weighted by 'w'; the bases count
  respondents.", "Left out as missing: …", "Left out: …"); a small figure
  grows taller rather than squeeze its plot. A mean of a nominal or a
  multiple-choice variable, a multiple-choice question as *Time* or *Split
  by*, a missing code named as an answer and a code that is no answer are
  refused in words, and `check_flow` says all but the last before the run
  (the questionnaire settles them), in the same words (`PARAM_CONFLICT`: "Split by needs one answer per
  respondent, and Brands heard of (unaided) allows several: split by one of
  its options after Explode multiple choice, or choose another variable.").
  The Trend draws its own chart, so its table is not a Result chart's result
  (`RESULT_NOT_DRAWABLE`). `check_flow` knows the response timestamps
  (`created_at`, `updated_at`, `started_at`, `submitted_at`:
  `siamang.flow.document.RESPONSE_TIMES`) as variables a node may name — or
  those a platform's data carries, `check_flow(…, response_times=("created_at",
  "updated_at", "started_at"))`, so that a timestamp its responses do not have
  is an unknown variable at the check, not a failed run.

- **Tab book (Excel)** (`output.tabbook`, `siamang.reporting.tabbook.write_tabbook`)
  — every chosen question crossed by a banner in one workbook: a *Contents*
  sheet linking to one sheet per question (named after its variable, at most
  31 characters, unique as Excel compares), and a *Notes* sheet (weight, test,
  alpha, Bonferroni, minimum base, missing codes left out, the date). Each
  sheet has the question's label, Total and every code of each banner
  variable across, the base (unweighted, and weighted when a weight applies),
  counts and/or column or row percentages (`0.0%`), the Banner table's letters
  in their own cells beside the column percentages (a letter compares column
  percentages, so with row percentages or counts only there are none, and the
  check warns), the mean and standard deviation of an interval or ratio
  question, a frozen header and set column widths. The counts are
  `_banner_pair`'s and the letters `BannerTable`'s own test; missing codes
  are left out and said, and a column's base is those in it who answered the
  question. *Questions* empty is every nominal, ordinal and multiple-choice
  variable of the codebook but the banner, the weight, the response
  metadata, open answers and rankings: an `OpenText` question (or words
  without answer labels) went into the client's workbook word for word when
  30 or fewer respondents had typed it — e-mail addresses and phone numbers
  a row each — and a Ranking read 100 % for every option in every column
  (`an open answer: code it first (Code open answers)`, `a ranking: every
  respondent orders every option, so each would be 100 % — derive its first
  choice (Derive) and tabulate that`); named in *Questions*, each is
  tabulated as asked, and `check_flow` warns. `check_flow` also names what
  the run refuses and the flow settles: a multiple-choice or ranking *Banner*
  variable (`… holds multiple-choice answers, and a banner column is a group
  of respondents that no one else is in. Explode it first …`), a *Path* not
  ending in `.xlsx` (`A tab book is an Excel workbook: its path must end in
  .xlsx (got 'outputs/tabbook.xls').`), and warns of one outside `outputs/`
  (`'tabs.xlsx' is not under outputs/, where a run keeps what it writes.`).
  The `stat` output gives `Sheets written`, `Questions skipped` and
  why (`not in the data`, an open answer with no labels, …). On weighted data
  the cells hold the sums of weights as they are and the percentages are of
  those sums, as the Frequencies and Crosstab tables compute them; the
  weighted counts and bases are shown to one decimal (`#,##0.0`), as those
  tables show them. The workbook keeps text as text as Save report's does
  (`siamang.io.excel_text`): a label, an answer or a banner name that begins
  with `=` is never a formula, and its links quote a sheet's name.

- **A transport can say why the answers were not sent.** An error thrown by a
  transport's `submit()` may carry `respondentMessage`, a sentence or two for
  the respondent — why the answers did not go, and what they can do about it —
  which the retry dialog shows in place of the survey's `retry_body` (the
  attempt count follows it). Studio's transport uses it when its captcha could
  not run and the server would not take the answers without it. Any other
  error shows `retry_body` as before.

### Changed

- **The survey's typefaces come with the survey, not from Google Fonts.** Every
  compiled survey linked `fonts.googleapis.com` and so fetched its fonts from
  `fonts.gstatic.com`: each respondent's address and browser went to Google as
  the page opened, before they had read a word — and so did every preview and
  shared link of a platform built on the runtime. The families of the font
  presets — Source Serif 4, Inter and Nunito, SIL Open Font License 1.1 — now
  ship in the package (`siamang/frontend/templates/react/fonts/`: the Google
  Fonts variable fonts in their `latin`, `latin-ext` and `cyrillic` subsets,
  Source Serif 4 with its optical-size axis as the old request had it; 564 KB
  of woff2, the README there gives their source, versions and checksums). The
  stylesheet declares with `@font-face` the bundled families its font stacks
  name, pointing at `fonts/` next to it, and `FrontendBuilder` puts exactly the
  files those rules use in the bundle with each family's license text: 469 KB
  for the `academic` preset, 152 KB for `modern`, 95 KB for `humanist`; a
  respondent downloads only the subsets the page's text needs (for an English
  page the two `latin` files, 171 KB). Both runtimes do it, and neither page
  links or preconnects to a font CDN any longer. A family that is not bundled
  (a stack of `"Roboto", sans-serif`) was never fetched and still is not: it is
  used where the device has it. A host that serves the page another way
  passes where it serves the files as `RuntimeRenderContext.font_base` (or
  `compile_css(ui, font_base=...)`) and serves them with
  `siamang.frontend.theme.fonts.font_file()`.

- **What a survey keeps in the browser: nothing before the respondent starts,
  and nothing for more than a week.** The runtime wrote the interview's id
  (`siamang_interview_<survey id>`) — and a transport's `respondentId()` was
  asked for its own at the same moment — as the page opened, so a visitor who
  only looked left a key behind; the autosave was offered back for a day but
  stayed in the browser for good unless the same survey was opened again, as
  did every other key of every survey on the origin. Now the id is drawn in
  memory and kept at the respondent's first answer or first move between pages
  (Resume and Start over count), when a transport's new optional `onStart()` is
  called too, so it can keep its own from then (a reload before that is a new
  visitor, with nothing of theirs kept or sent). `siamang_kept_<survey id>`
  notes when a survey last wrote, and every survey page that opens drops the
  `siamang_answers_`, `siamang_respondent_`, `siamang_interview_`,
  `siamang_ended_` and `siamang_theme_` keys of each survey on the origin not
  written for 7 days, its own included; a key kept before the note is dated
  when it is first seen and goes a week later. The autosave is offered back
  for that week, not a day, and is removed as soon as the interview is
  submitted or ended by a full quota, as it was. `siamang_done_<survey id>`,
  a host's "one response per browser", is never dropped. A host page that
  should leave nothing in the browser (a preview) sets
  `window.SIAMANG_STORAGE = "memory"`: the runtime then keeps its state in
  memory and does not touch `localStorage`.

### Removed

- `UIConfig.effective_google_fonts_url` and the `"google_fonts"` URL of each
  `FONT_PRESETS` entry: nothing loads the survey's fonts from Google Fonts any
  more (see Changed).

### Fixed

- **An ending page no longer says the answers were recorded while they are
  not.** A survey whose last page is an ending page (`kind` `final`,
  `disqualification` or `redirect`) sends its answers as that page opens, and
  the page showed alone while they went — without the "Submitting" overlay a
  page with questions shows — and stayed as it was when they did not arrive:
  no retry dialog and, after the last attempt, no error screen, so a
  respondent read "thank you, your answers were recorded" over answers that
  were never stored (a server that refused them, a network that dropped them).
  The overlay and the retry dialog now show over an ending page as over any
  other ("Try again", or "Save locally and finish", which keeps the answers in
  the browser and stays on the page), and once the interview is closed (the
  last attempt failed, or the server said the quota is full) the closed screen
  replaces the page.

- **A time with a time zone goes to Excel in UTC.** A workbook cell holds no
  time zone, and pandas refuses to write a time that has one, so a frame with
  timezone-aware times — the response times a platform's data carries — made
  `export_file(data, "coded.xlsx")` (a flow's Export file to `.xlsx`), a
  table's `export_xlsx` and every other workbook `siamang.io.excel_text.
  to_excel` writes fail with *Excel does not support datetimes with
  timezones*. Such a time is now written as the same moment in UTC, without
  the zone — a column of them, one in a column of objects, or the index
  (`excel_text.without_zones`); the frame given is left as it was, and text
  that looks like a formula is still written as text.

- **A missing open answer is not an answer.** A text column that holds its
  missing values as `pd.NA` (a `string` column, `convert_dtypes()`) or `NaT`
  had them read as the texts *<NA>* and *NaT*: `text_coding.normalise` gave
  `<na>`, so the coverage and the theme table of a codeframe counted those
  respondents as having answered (uncoded), and a version 2 rule for *na*
  coded them. Every missing value — `None`, NaN, `pd.NA`, `NaT` — is now
  blank, in version 1 as in version 2. A version 1 codeframe whose theme code
  its theme variable cannot hold (2⁶³ or more) is refused when it is read
  (`CodeframeError`) rather than failing when it is applied.

- **A frequency table of codes with a stray text among them.** Frequencies
  sorted a column's values as they came, and a column holding codes and a
  text as well (1, 2, 3 and "25-34", which an earlier runtime or an import
  can leave) could not be sorted: the table raised `TypeError: '<' not
  supported between instances of 'str' and 'int'` and stopped the report it
  was in. Numbers now come by their value (a number written as text among
  them), then the other texts in order.

- **Clusters can be numbered by an item's mean.** k-means numbers its
  clusters by size, and a flow names them by number with Derive. Two
  segments of close sizes swapped numbers when a few respondents came or
  went, or when the best of ten starts landed on another of several nearly
  equal solutions, and the names landed on the wrong segments: on a
  platform's example, keeping two respondents more made its "Always on"
  segment the one with the fewest hours. Cluster (k-means) gains Number
  clusters by (`kmeans(number_by=…)`, `SurveyData.cluster(number_by=…)`):
  one of the Items, by whose mean the clusters are numbered, lowest first
  (`stats["numbered_by"]`). The check refuses an item that is not among the
  Items. Empty, the clusters are numbered by size and a stored flow renders
  the code it did.

- **A duplicate can be asked to match on more than the battery.** Response
  quality's duplicate check compared the battery alone, and a dozen
  five-point items still let two honest respondents answer alike now and
  then: both were flagged as one person submitting twice, and dropped. On a
  platform's example two such strangers were among 18 duplicates, where 16
  were the repeat submissions. The node gains Duplicates also match on
  (`quality_flags(duplicates_also=…)`, `duplicate_pattern(also=…)`): other
  answers a duplicate must repeat too, such as age and gender. Only the
  battery must be complete; two unanswered questions among the others match.
  Empty, the battery alone decides, and a stored flow renders the code it
  did.

- **k-means keeps the best of ten starts.** `kmeans` (Cluster (k-means),
  `SurveyData.cluster`) ran from one k-means++ seeding, which draws rows by
  position, and stopped in the local optimum that seeding led to. Segments
  that overlap, as real ones do, leave many: the same respondents stored in
  another order (a table read back from a database comes in the order its
  rows are stored) came out as other segments, some of them clearly worse
  (a within-cluster sum of squares up to 6 % higher, the largest segment at
  8 hours a day instead of 5.6). It now runs ten starts, all drawn from the
  one `seed`, and keeps the one with the smallest within-cluster sum of
  squares (the first of equals); `n_init=1` is the single start, with the
  result it always had. A stored flow's clusters can change, to a solution
  at least as tight.

- **A snapshot's codebook describes the arm a script assigns.** No question
  collects the arm `Script.assign_condition` draws, so the codebook
  `read_snapshot` builds from a questionnaire (and a platform's Responses
  node, which builds it the same way) left it out: a flow read the arm as `1`
  and `2` where respondents were shown "Control" and "Treatment", and a Data
  check called it a column the codebook does not know. The codebook now has a
  nominal variable for every arm the questionnaire does not declare, labeled
  with the arms, as Simulated data have had it
  (`local_simulator.with_arm_variables`, used by both). One the codebook
  declares keeps its own entry, and the questionnaire's codebook is not
  changed in place.

- **A Bar chart splits by a group with a blank or a missing code.** Codes read
  back as integers (`read_snapshot`, a platform's data) are nullable `Int64`,
  where a blank is `<NA>`, and so is a declared missing code once the chart
  leaves it out. A Split by such a variable — gender with 99, Prefer not to
  say, declared missing, or any question someone skipped — stopped bars of
  every layout, and a histogram's panels, with `cannot convert to 'bool'-dtype
  NumPy array with missing values`; the same codes as floats drew. A blank or
  a missing code is now in no group, as with floats, and the chart is the one
  the floats draw.

- **A Save report of many charts fits a small sandbox.** Every chart kept its
  matplotlib figure — its drawing buffer, 7 to 12 MB at 150 dpi — for as long
  as the chart existed, closed or not, and a generated script's globals and
  `FlowRunner`'s outputs keep every node's chart: a report of 30 charts on
  20,000 respondents was killed at 512 MB, in runs and in previews, and each
  chart was drawn four times (the Markdown and the HTML, each saved with a
  tight bounding box). A report now renders each chart once, writes the same
  PNG to its Markdown and its HTML, and releases the figure
  (`SurveyChart.png`, `SurveyChart.release`); `FlowRunner` renders each chart
  at its node and releases it, and a preview or a report at that resolution
  writes the kept picture without drawing again. A copy a report draws in its
  own theme's colors is kept as its picture, not as an open figure. A chart
  whose figure the caller asked for (`plot()`, `show()`) is left open. The
  figures are byte for byte those written before. Measured with one CPU and a
  512 MB memory limit: a 40-chart report went from killed at 19 s to written
  in 29 s at 400 MB (its preview likewise).

- **Games-Howell on many groups takes seconds, not minutes.** Each pair's
  interval took SciPy's studentized range quantile at the pair's own Welch df,
  a root found over a double integral: Group means with Welch's ANOVA and
  Games-Howell on 20,000 respondents took 14 s for 12 groups, 37 s for 20 and
  114 s for 30, at a canvas preview's 120 s limit. The quantile is now solved
  by Newton's method from its large-df form, and past 17 distinct df it is
  interpolated in 1/df through 17 solved ones (checked against the 9-point
  interpolation, and solved df by df where they disagree): 2 s, 3 s and 7 s,
  with every number as before to within 1e-10.

- **Reading a snapshot holds one copy of the data, not two.** `read_snapshot`
  restored a codebook's integer codes in a copy of the whole frame, and a
  Parquet read left the Arrow table's buffers in Arrow's pool: loading 20,000
  respondents × 177 columns and raking them peaked at 376 MB, 60 MB of it
  those leftovers, of the 512 MB a sandbox gives a flow. The codes are now
  restored in the frame read, a column at a time, and the pool is handed back
  after a Parquet read: 317 MB for the same frame, value for value.

- **Two Save reports in one folder keep their own figures.** Every report named
  its figures `fig_<n>.png` by the block's place, so `outputs/report.md` and
  `outputs/summary.md` wrote each other's `fig_1.png` and one showed the other's
  charts. `Report.save` names them by the file: `report_fig_1.png`,
  `summary_fig_1.png` (characters other than letters, digits, `.`, `_` and `-`
  become `-`). `to_markdown` takes the `prefix` it uses (default none).

- **An answer has one color in every chart of a report.** The Bar chart's
  split and donut colored an answer by its place among the answers drawn,
  so with Top N, or a donut's small slices combined as Other, every later
  answer moved to another color: one brand was orange in one chart and
  magenta in the next. The color is the answer's place among all the
  answers given. A split without Top N is colored as it was.

- **A number is not drawn a bar per value.** An age (16–99) drawn as percent
  bars, split by, or as a donut made a bar, a legend entry or a slice for each
  of its 84 values (a legend wider than the figure). The newer forms refuse a
  number (interval or ratio, no value labels) with more than 30 values given:
  `Age is a number with 84 different values given, and this chart draws a
  bar for each: layout='histogram' draws its distribution (or band it first
  with Bands).` (`Split by Age is … a group for each: band it first (Bands) to
  compare its ranges.`); `check_flow` warns when the codebook's valid range
  holds more than 30 whole numbers (`Age is a number of up to 84 values, and
  bars draw each value given: Layout histogram draws its distribution.`; `… a
  donut draws a slice for each value given …`) — a
  range of [0, 29.5] or [0.5, 30.5] holds 30 and is not warned of. The
  classic chart is drawn as it always was, and `check_flow` does not warn of
  it. With `top` only the N values given most are drawn, so N is what counts:
  `top=5` draws five ages and Other, their steps of the scale taken among the
  five (among all 84 neighbors read as one color); past 30, `… and top=31
  draws a bar for each of the 31 given most: give top=30 or fewer, or
  layout='histogram' draws its distribution …` (`check_flow`: `… and Top N
  draws a bar for each of the 31 given most: set Top N to 30 or fewer, or
  Layout histogram draws its distribution.`).

- **Nothing to draw is said.** Percent bars of a variable nobody answered (every
  answer a missing code) drew an empty axis ticked `−0%`; they say `No
  respondent answered X.`, as the split and the donut do. A donut every answer
  of which is under `min_slice` was one gray ring called Other; it says `Each
  of the 40 answers to Forty drawn is under 3 % of the respondents who
  answered, so Other would fill the whole ring: draw them as bars
  (layout='grouped'), or lower min_slice.`

- **`check_flow` names a Bar chart split by its own Variable.** It passed the
  check and failed the run; the check says `Split by must be another variable
  than Variable.`

- **Labels and ticks fit the plot as it is laid out.** The Bar chart's
  newer forms fitted the labels under vertical bars to 0.85 of the figure's
  width, but the value axis's title and ticks take their room first (229 of
  360 pt at 5 in): turned labels were drawn over one another, and level ones
  ran together ("metropolitan (n = 4,249)" of two neighbors read as one
  phrase). They are fitted again to the plot as laid out — level ones an em
  apart, turned ones in as many lines as their measured spacing holds — and
  the bars are drawn across when neither can be read. A group's `(n = …)` is
  never broken over two lines, under the bars nor over a histogram's panel.
  A histogram's shared x axis ('0 50,000 100,000150,000…' in two columns at
  10 in) and a count or mean axis of horizontal bars are thinned, a bin at a
  time (0 20,000 40,000 60,000 becomes 0 25,000 50,000), until their labels
  keep half an em apart. The bars' axis is fitted once the values written
  past the bars have lengthened it, and the ticks found are kept when the
  figure is saved (matplotlib chose them again then, by other settings). A histogram split into 8 groups
  at 5 × 4 in had panels 24 pt tall under their wrapped titles: the figure
  grows until each is 72 pt. A mean of thousands reads `41,646.65` on the
  Bar chart and the Result charts' means (Group means, Descriptive
  statistics, t-tests), its axis `40,000`. In the theme's colors the Box
  plot's value title wraps to the plot's height (it ran into the title).

- **Descriptive statistics of an income and an age take a panel each.** Their
  Result chart put both on one axis from 0 to 40,000: the ages sat at 0,
  their intervals invisible and their labels on top of one another. Variables
  whose means reach more than 5 times one another's are drawn a panel each, on
  a scale of their own, a row per group named with its base (`Means by
  Region, each variable on its own scale`).

- **A Heatmap of means by group in the theme's colors leaves the missing
  codes out and keeps its cells.** With `cmap="theme"`, By drew the classic
  form: twelve items of 60 characters made `tight_layout` fail and the
  heatmap a strip with its values on top of one another, and a 1–5 item's
  mean took 99 = Not applicable in (42.00, 23.40). Each cell is now the mean
  of the group's respondents who answered the item, as Group means gives it,
  the missing codes left out and counted; long items are numbered and
  wrapped, each group's base is under its name, and the base and the weight
  are under the chart. A named color map draws what it always drew; the By
  help says that missing codes count as answers there.

- **The Trend's Time offers the responses' timestamps, and names them on the
  axis.** `check_flow` accepted `created_at` as Time and the help named it as
  the main example, but nothing in the node's spec told a builder it could be
  chosen (a picker of the codebook's variables does not list it), and the axis
  read `created_at (day)`. A `variable` parameter may now carry `extra` names
  with labels, in the registry payload as `"extra": [{"name": "created_at",
  "label": "Response date (created_at)"}, …]` (and `submitted_at`,
  `updated_at`, `started_at`); the axis reads `Response date (month)` unless
  the codebook labels the column (`siamang.data.checks.RESPONSE_TIME_LABELS`).

- **The Trend's Confidence band help names Minimum base.** It said a point
  with fewer respondents than "Low base" is drawn without its band; the field
  is *Minimum base* (`min_base`) — "Low base" is the table's statistic.

- **Save report's workbook links a sheet whose name has an apostrophe.** The
  Contents linked a table captioned `Brand's image` to `'Brand's image'!A1`,
  which Excel cannot follow; a sheet's name in a link is quoted with an
  apostrophe inside doubled, `'Brand''s image'!A1`
  (`siamang.io.excel_text.sheet_link`, which the Tab book uses too).

- **Large counts read with their thousands separated.** The newer Bar chart
  wrote bases as `n = 182128`, weighted counts on bars as `18848.4` and count
  ticks as `20000`: counts now separate thousands (`n = 182,128`, `Base:
  30,000 respondents …`, ticks `20,000`), and a weighted count from 100 on is
  written whole (`18,848`; below 100 to one decimal, as before). The Likert
  chart's and the Result charts' `(n = …)` separate thousands too.

- **Sorting a Bar chart split by a scale keeps the scale in order.** With
  Sort = value the answers of an ordinal scale were ordered by how often they
  were given — a 100 % stack read Satisfied, Very satisfied, Neither, … from
  the bottom, its color ramp and top box scrambled. The scale's answers now
  keep their order and the groups go largest first, by their share of the top
  answer (by their total, for counts), noted under the chart (`Groups in
  order of their share of Very satisfied; the answers keep the scale's
  order.`). The Sort help also says that any setting but the defaults draws
  the newer chart, whose look differs from the classic one.

- **Result charts say their base and name things by their labels.** Group
  means (the most harmful: with 24 brands the intervals ran from n = 4 to
  hundreds, unsaid), Descriptive statistics and the t-test label each row
  with its base (`North (n = 97)`; by groups, the legend); Regression, the
  correlation heatmap, MaxDiff and Conjoint say N or the base in a note, and
  the Perceptual map's title adds `N = …`. The Regression forest read `z1`,
  `screen_time_hours` and `Regression coefficients: score`: its terms and
  outcome are named by label and its note says what each nominal predictor
  is compared with (`compared with Region = North`); a PCA's loadings and a
  cluster profile of the table alone use labels too (the tables carry
  `attrs["labels"]`, the regression's `attrs["reference"]`), and Code open
  answers is titled by the question, not its column. Conjoint's part-worths
  keep each attribute's levels in the design's order (price 10, 15, 20, 25
  EUR, not 20, 10, 15, 25).

- **The Likert chart fits a narrow figure and one item.** Every row took the
  height of the tallest label wrapped to 0.3 of the width, so 14 items at 6 ×
  4 inches grew to 6 × 23.75 and 5 items at 5 × 3 to 5 × 12.2; the labels are
  now smaller and wider first. A single item filled a 6-inch plot with one
  bar titled `1 item from Very dissatisfied to Very satisfied`, noted `Items
  in order of their top-2 share`: a row is at most 60 pt, one item is titled
  by its label (its row reads `(n = …)`), and the order note needs two. The
  center line ran through the neutral answer's value (`2|2%`); it runs
  behind it. On an even scale the two middle answers were nearly white on
  white (`#fddbc7`, `#d1e5f0` on 4-point RdBu); they keep a color.

- **What a Likert or Bar chart cannot draw fails its own node, and the flow
  check says it first.** The charts are built lazily, so a chart node
  "succeeded" and the error surfaced on Save report (`Node save
  (output.save_report) failed: A Likert chart draws the answers of a scale
  …`) or in the preview; the runner now builds each chart as its node runs.
  `check_flow` also names, before the run: Likert items with no scale at all
  and a multiple-choice Likert item, a Bar chart split by a question that
  allows several answers, and a stacked layout of one. The Likert chart
  reads a Likert scale question's points when the codebook has no labels or
  valid range — the example project's own 7-point `life_satisfaction` is
  drawn, its ends named `Not at all` and `Completely`.

- **A Result chart of a table alone says how the weight was used.** A
  Regression's, a PCA's, a Cluster's and TURF's chart learned the weight only
  from the Stat: with the table alone connected, a chart beside weighted
  tables had no weight line — and Cluster, whose k-means ignores the weight,
  did not say `unweighted (the weight 'w' is not applied)`. These tables now
  carry it themselves (`DataFrame.attrs["weight"]`: the weight column, or the
  unweighted note of k-means), and the chart reads it.

- **TURF's reach curve shows what each size adds, by label.** Every tick
  held the whole cumulative portfolio of column names, broken mid-word and
  cut after four lines (`streaming_serv / ice_01_subscri / ption, …`), so the
  chart could not show which option each step adds — the point of the curve
  — and a flow's chart named options by variable (`owns_tablet`) while the
  fixed portfolio's used labels. Each size now reads `+ <the option it adds>`
  (a best portfolio that is not the one before plus an option reads `a new
  set` and is listed in full under the chart), words whole, by label:
  `turf.turf(..., labels=)` carries them on the table (`items` keeps the
  column names, so the table prints as before), and the TURF node passes the
  codebook's (`labels=turf.labels_of(data, items)`, a new argument in its
  generated code).

- **The Pearson and Kendall heatmap writes its coefficients at a size its
  cells hold.** It used seaborn's 12-pt annotations whatever the cell: with
  14 items at 10 × 6 inches every neighboring coefficient in a row ran
  together and the white `1.00` spilled out of its cell; at 6 × 4 inches the
  rows' labels, wrapped to five lines, grew the figure into a 6 × 17-inch
  strip. The coefficients are now at most 10 pt and fit their cell, or are
  left to the table below 6 pt (the note says so); the rows' labels get
  smaller and wider before the figure grows (6 × 4 becomes about 6 × 11,
  with its notes). An item with the same answer from everyone has a blank
  diagonal too (it printed `1.00` in an otherwise blank row), the note names
  a pair as the chart names its items (`Trust × Constant`, `1 × 3` when
  numbered, not `x × c`), and no theme gridlines cross the blank cells.

- **A crowded Perceptual map numbers its points.** A dense map (24 brands ×
  13 regions) grown to its cap of 1.2 × its width still printed names over
  names (`Umbrella Pharmaceuticals Over-Scotland`), cut others with `…`, and
  said nothing; its legend cut the row variable's title too. Such a map now
  numbers its points — rows 1, 2, …, then the columns, placed so that no two
  numbers touch — and lists the numbered names under the legend (the figure
  grows taller for the list); `correspondence.plot` does the same when its
  names would overlap (`numbered=None`, or `True` / `False` to choose). The
  legend's titles wrap, and the legend hangs under the x axis's title (at a
  tenth of the plot's height it sat on the title of a short map).

- **The Key drivers and price charts stay clear at the Result chart's
  sizes.** The Key drivers chart kept the row gridlines of seaborn's whitegrid
  theme, which the Result chart sets (and any Bar, Heatmap or Likert chart
  drawn before), so a line struck through every bar and its `57.8 %`; it now
  draws the value axis's lines only, says `N = …` beside R² and wraps its
  title to the room from the plot's left edge. At 5 × 3 inches Gabor-Granger's
  twelve revenue labels ran together (`117.73118.22117.70`), its demand labels
  touched (`24 %24 %`) and `highest revenue at 499` ran past the plot's edge;
  labels that would touch are thinned (the best price's always kept) and the
  note stays inside, the best price's line behind its value. Van Westendorp's
  point names are placed clear of the marked points and inside the plot (the
  IPP marker sat on its name; PMC ran onto the axis's `100`).

- **A Result chart keeps its labels whole and its titles inside the figure.**
  With 16 or more long labels the rows took one line of 7 pt, cut with an
  ellipsis, rather than grow — so MaxDiff items that differ only at the end
  read alike (`The customer service representative resolved my issue…` twice,
  for different items), and Descriptive statistics, Group means and themes
  were cut the same way. Labels are now whole (three lines, four at 8 pt);
  a chart whose rows its height cannot hold grows taller at 9 or 8 pt; only a
  label past four lines is cut, never so that two read alike. The title was
  wrapped to the whole figure but drawn from the plot's left edge, which long
  labels put at a third of the width: on a 6-inch chart it ended at 772 px
  of 600 and the PNG was saved 773 px wide. The title, the axis titles (the
  MaxDiff utilities' `… against <reference item> at 0`) and the notes under
  the plot are wrapped to the plot as it is laid out.

- **Many series get as many colors.** A Result chart took `n` colors of its
  palette, which cycles past its ten: Descriptive statistics by 13 regions
  drew Wales in North East's color, and by 24 groups ten colors for 24
  series. The Bar chart switched to husl's wheel past the palette, whose
  first and last colors (and neighbors) look alike, so the bottom and top
  segments of a 13-group stack could not be told apart. Both now take the
  palette's own colors, then the same lighter, then darker (up to three
  times the palette), and past that hues spaced over the wheel without
  closing it, their lightness alternating.

- **The Bar chart's labels, axis titles and legend no longer print over each
  other.** With many categories or long labels (24 brands of 60 characters,
  13 regions) the turned labels under vertical bars ran into each other, and
  beside horizontal bars two- and three-line labels overlapped in a figure
  that never grew (23 of 24 neighbors overlapped); the title could sit on
  the first label. Labels beside horizontal bars now get a row each —
  smaller (to 8 pt) and wider first, else the figure grows to a row per
  label; vertical bars whose labels cannot be read under them, even turned,
  are drawn horizontally. The axis titles were never wrapped: `% within
  <a whole question> (weighted)` was taller than the figure and ran over the
  Base note. They wrap to the plot's length, and a split's value axis reads
  `% within each group (weighted)` when the Split by label will not fit (the
  note under the plot names the variable). A legend beside the plot that is
  taller than the plot (20 options of three lines) ran off the figure and
  over the notes; it is placed under the plot instead. Turned values of
  neighboring bars that would touch are left to the axis.

- **A percent axis labels its ticks with their own values.** The Bar chart's
  percent axis (Show = percent, or a stacked split) printed its ticks without
  decimals, and when matplotlib chose steps of 2.5 the axis read 0, 2, 5, 8,
  10, 12, 15, 18, 20 % under evenly spaced gridlines; the Likert chart's
  panel of the neutral answer did the same. Their ticks now fall on whole
  percents (steps of 1, 2, 5 or 10).

- **The Proportion CI chart says what the share is of and at what level.**
  It was titled `Proportion` and wrote `confidence interval 59.2 – 72.1 %`
  whatever the Confidence, so a 90 % interval read as a 95 % one and a slide
  with `65.7 %` had no subject. `proportion_ci` returns a `Proportion` — the
  same keys, so its Stat prints as before — that also carries the variable,
  the answer and the confidence; the chart is titled `<variable label>:
  <answer label>` (`Gender: Female`) and writes `90 % confidence interval …`.

- **Excel files write text as text.** openpyxl stores a string beginning with
  `=` as a formula, so an open answer such as `=HYPERLINK("http://…","Click
  me")` shown in a Frequencies table became a live formula in the workbook
  Save report ships — as did a caption or a heading — and a table's own
  `export_xlsx` and the data written to `.xlsx` (Export file, `write_snapshot`)
  did the same; read back, such an answer was blank. Every cell they write
  now keeps its text as a string (`siamang.io.excel_text`). The workbook also
  writes the post-hoc table's statistics under its pairs (the method, which
  way a difference runs, that p is adjusted already), as the report prints
  them, and its Contents names the later analyses' tables without a caption:
  `Perceptual map: Brand × Region — inertia`, `… — rows (Brand)`, `… —
  columns (Region)`, `Price sensitivity: Gabor-Granger — curves`, `Key
  drivers: Liking`, `Paired tests: Cochran's Q` (they all read `Table`).

- **The ordinal logit refuses a nominal outcome, and its thresholds no longer
  break a Markdown table.** Regression with Model = ordinal fitted a nominal
  outcome such as a region in code order (`order = Capital < North < South`),
  with odds ratios and a test and no warning. An outcome the codebook calls
  nominal is now refused — "Region is nominal: its answers (Capital, North,
  South) have no order, and the ordinal model would take one from their
  codes. Use the logit for an outcome of two answers, or recode it onto an
  ordered scale (Recode with Scale = ordinal) first." — and `check_flow` says
  the same before the run (`VARIABLE_SCALE`; a warning when a node upstream
  makes the variable nominal). The thresholds were named as polr names them,
  `Very dissatisfied|Dissatisfied`; in a report's Markdown, Studio's node
  preview and the Reports page the pipe ended the cell, and every number of a
  threshold row moved a column right. They are named `Very dissatisfied /
  Dissatisfied`, and a report's Markdown tables escape a `|` in any label or
  name (`A\|B`).

- **Weighted percentages are of the sums of weights as they are.** The
  Frequencies table rounded each weighted N to one decimal and then took the
  percentages of those rounded numbers, so they could differ in the last digit
  from the Bar chart's and the Likert chart's (18.0 against 17.9) and, with
  small weights, be wrong outright: weights normalized to sum to 1 over 1000
  respondents made every answer 20.0 %, and weights of 0.04, 0.04, 0.04 and
  0.34 gave 0.0 / 25.0 / 75.0 % instead of 8.7 / 17.4 / 73.9 %. The N column
  and the total still show one decimal; `%`, `Cumulative %` and the Weighted
  N of the statistics are now of the unrounded sums (unweighted, the table is
  what it was). The Crosstab of a weighted multiple-choice question divided
  by each group's base rounded to a whole number, which put a group weighing
  1.3 whose respondents all chose an option at 130 %; it divides by the
  unrounded base, and names its columns by the labels of By (`A`, `B`, not
  `1.0`, `2.0`), in the table and in its `Base` statistic.

- **A Perceptual map no longer maps a blank answer as a category.** On the
  data Studio runs flows on — a snapshot read by `read_snapshot`, the
  platform's responses — labeled codes come back as nullable `Int64`, a
  skipped answer as `pd.NA`, and the map counted it: a `<NA>` row or column,
  every respondent in N, `Excluded` 0, and a different inertia, chi-square and
  map than the same responses in memory. Any scalar NA is now no answer.

- **A value a node does not read is not checked.** The t-test's rules "Name
  both groups to compare in Group A and Group B…" had no design condition, and
  the variable checks ran on every parameter: a paired or one-sample t-test
  that still held a Group A, or a Groups naming a variable that had since gone,
  was an error-state flow that could not run, though the run ignores those
  values. `check_flow` now checks a parameter only when the node's code reads
  it with its current choices (`NodeSpec.reads`: a template fragment naming it
  holds for the node's enum and bool choices), and skips an error rule that
  names one it does not read; warnings about ignored values stay. The t-test's
  two rules are scoped to `kind=independent`. The templates write a parameter
  only where it is read, so a builder can tell which fields matter: Group
  means passes `adjust` only with Dunn's test, Paired tests pass `yes` only to
  McNemar, `zeros` to the ranked tests and `posthoc` to Friedman (and `auto`),
  and Factor analysis passes `into` only with `scores` and `seed` only to
  parallel analysis. A template fragment may continue a call another opened,
  and the template renders only the parameters its fragments name.

- **A tiny p-value is no longer printed as 0.** The t-test, Group means (by
  hand and `auto`), Crosstab (χ² and Fisher), the correlation matrix's pairs and
  the post-hoc tables rounded p to four decimals, so a strong effect read
  `p = 0.0` in its statistics and in Studio; every footer printed floats with
  `:.4f` (`p = 0.0000`, `Bartlett p = 0.0000`, and padded `df = 124.9800`); a
  report's statistics line did the same, and its HTML tables used pandas'
  formatting, which turned a p of `3.363e-07` into `0.0` beside a `.md` that
  said `3.363e-07`. A p now keeps four decimals, or below 0.0001 four
  significant digits (`siamang.data.listwise.round_p`); footers and
  `Report.add` lines print a float with up to four decimals and no padding,
  and one below 0.0001 with four significant digits and its exponent
  (`siamang.reporting.tables.stat_text`: `p = 5.8e-07`), so a footer prints
  the p the statistics keep (`7.988e-32`, and `5e-05` rather than `0.0001`);
  a float below 1 that four significant digits hold prints as it is, so the
  footers of Paired tests and factor analysis, whose p keeps four significant
  digits, print it (`p = 0.002343`, `Bartlett p = 0.00227`, not `0.0023`);
  Tukey's and Games-Howell's p below 1e-07 — past which SciPy's studentized
  range is its integration's noise, `1.144e-14` for every strong pair of three
  groups at 297 df — reads `< 1e-07`; Compare groups'
  Dunn lines too; and a report's HTML writes each number as its Markdown does:
  a table component's cells, rounded already, with `str`, and a bare
  DataFrame's floats (a regression's coefficients, a PCA's loadings, a
  cluster's centroids) as tabulate does, with six significant digits
  (`62.263`, `6.15462e-38`) rather than the full `62.26300527031391`. Group
  means of a float32 column (a Stata `float`, Parquet written elsewhere) is
  computed in float64, so its cells read `3.444` in both, not the float32
  `3.444000005722046` that `round(3)` could not hold.

- **An answer weighted 0 no longer changes the weighted SD.** Descriptive
  statistics and Group means scaled the weighted variance by n / (n − 1) with n
  every answer, so a row weighted 0 (or with a blank weight, which counts 0)
  still counted: 1, 2, 3 and a zero-weighted 100 gave SD 0.943 instead of
  1.000, and a group in which one answer carried weight gave SD 0.0 instead of
  none. n is now the answers that carry weight, and below two the SD is
  undefined — blank, as an SD of one answer is. The mean and the quartiles
  already ignored them; Min and Max stay those of every answer, and
  Descriptive statistics' `Note` adds "rows weighted 0 are left out of the
  weighted statistics" when there are any. Group means prints an undefined
  cell blank rather than `nan`, and a table's Markdown prints each column in its
  own type (a count of 4 read `4.0` when every column was a number).

- **The correlation matrix's p adjustment names the pairs it adjusted.** The
  footer said `Bonferroni, over 3 pairs` while a pair with a constant variable
  had no p and was not one of the comparisons, so the printed Bonferroni p
  equaled the raw one. It now counts the pairs with a p: `over the 1 pair
  computed (of 3)`, or `over 3 pairs` when all were.

- **A repeated index label no longer mixes up rows.** Descriptive statistics
  selected rows by label, so on a frame whose index repeats labels (waves
  concatenated without `ignore_index`) each label pulled in every row sharing
  it: N 12 and Missing −6 for six rows, and every group the pooled mean, with
  no error. The weighted correlation matrix and weighted Group means raised
  "Length of values … does not match length of index", and Factor analysis'
  scores "cannot set using a list-like indexer". `describe` and every
  `SurveyTable` now work on the rows numbered by position (a table carries no
  index; the data keeps its own), and the scores are placed by position
  (`Listwise.mask`). So are k-means' clusters (the same error), the weights of
  weighted PCA and reliability (a matmul of 12 weights against 6 rows), the
  weighted `analysis.mean` and `describe_variables()`' `weighted_n_valid`, which
  counted each weight once per row sharing its label. The weighted mean counts
  a missing or non-numeric weight 0, as the rest do: picked by position, the
  weights were summed by numpy, and one answered row without a weight made
  the mean `nan`.

- **A Parquet snapshot gives back its multiple-choice lists.** pandas reads a
  list stored in Parquet as a numpy array, and `read_snapshot` passed it on as
  one, so `multi.is_multi` was false and a generated script run with `--data
  …parquet` failed at Explode ("the truth value of an array … is ambiguous").
  The arrays become the lists they were written as — in `read_snapshot` and in
  `SurveyDataReader().read("….parquet")`, the reader the library documents.

- **A factor score a rule did not keep is empty, not a KeyError.** With
  Factors empty and Add factor scores on, `check_flow` lets a later node name
  `factor_1` … one fewer than the items, since the number is known only after
  the run; when the rule kept fewer, the node reading `factor_2` failed with
  `KeyError: "['factor_2'] not in index"`. The run now makes the ones a node
  downstream names (`factor.analyze(..., read_later=…)`, which the flow
  template fills with `{read_after!r}`), empty, labeled `Factor 2 score (not
  made: the Kaiser criterion kept 1 factor)` and listed in `Scores` (`…;
  factor_2 empty: the Kaiser criterion kept 1 factor`) — so a t-test of one
  reads "not run" beside that label — and no other: the data, its exports and
  its tables gain no empty column nobody reads.

- **A report section captions each output of a node on its own.** Captions and
  layout were keyed by the source node, so a factor analysis's loadings, its
  variance table and its statistics in one section all carried the loadings'
  caption ("Table 5. Factor loadings" three times), and Paired tests' summary
  table carried the pairs' one. A key may now be `<node>.<port>`
  (`"fa.variance"`); the node's own key still answers for an output without
  one, so stored sections render as before.

- **What a node's parameters settle is checked before the run.** Paired tests
  with Test = mcnemar or wilcoxon and three variables, or friedman and two, and
  a t-test of two groups whose Groups had three answers and none named, passed
  `check_flow` and failed only when run. A paired test's variable count is now
  an error of the check, in the words the run refuses it with
  (`paired.count_problem`: "McNemar compares exactly two variables; 3 were
  given."), and the t-test gets a warning naming the answers ("Gender has 3
  answers (1 = Male, 2 = Female, 3 = Other); a t-test compares two — name them
  in Group A and Group B, unless the data this node reads holds only two of
  them."): a filter upstream may leave two, so it does not stop the flow.

- **A made variable of the wrong scale is warned.** `VARIABLE_SCALE` knew only
  the questionnaire's scales, so a Crosstab of a MaxDiff score or a factor
  score (interval) passed the check and ran with one row per distinct float.
  The variables the nodes make now carry the scale each node gives them, and a
  later node naming one its parameter does not take gets a warning ("Parameter
  'row' of xt: 'factor_1' is interval (as the node that makes it gives it),
  expected nominal | ordinal.") — not an error, so a flow saved before runs on.
  The scale is the one the maker nearest upstream gives, walked along the
  edges: a Recode of a derived variable is ratio like its source even when the
  document lists the Recode first.

- **The flow check reads a `{code: label}` codebook as the questionnaire
  does.** The shorthand is a valid codebook, but `check_flow` iterated value
  labels as a list: Explode of such a variable raised `AttributeError: 'str'
  object has no attribute 'get'` out of the check (a Save in Studio answered
  500), and the t-test's "has 3 answers" warning listed the codes in the
  object's order and as written (`3 = East, 1 = North`, `01 = One`) and kept a
  missing code written `3.0` as the answer 3. Both now read the labels as the
  questionnaire does (`1 = North, 2 = South, 3 = East`; `1 = One`) and match a
  missing code by its text (`3.0` is 3). A code the codebook lists in
  `missing_values` is a missing code there too, as the questionnaire and the
  t-test read it: a Region of North, South and `missing_values: [9]` has two
  answers, not three.

- **The flow check says what the code generator cannot write, and a
  parameter of the wrong type is an issue, not an exception.** `check_flow`
  looked only at the top of a condition, so an `and` with a part that is not
  an expression passed it and `generate_flow` raised `FlowError` ("Only
  structured expressions can be used in a flow"), a 500 at Save in Studio.
  Explode of a list, factor scores of `items: 5` and a variable reference with
  no name raised `TypeError` or `KeyError` out of the check itself. Each is now
  `PARAM_INVALID` on its node (`every variable in a condition needs a name.`
  for the last), and a condition that passes the check generates.

- **Fisher's estimate, the R bundle's labels and Mann-Whitney's df are
  described as they are.** Crosstab's Fisher footer said the estimate was
  "as R's fisher.test": the p-values agree, but the engine solves the exact
  interval to full precision while R's root finder stops sooner, so R prints
  limits that differ on sparse tables ([[8, 1], [2, 20]]: 3712.06 against
  3592.50); the footer's `Estimate` now says so. The R bundle's script and its
  documentation said each column's `label` attribute is the question's text; it
  is the variable's codebook label. A test chosen by hand in Group means
  reports df — except Mann–Whitney's U, which has none, as the docs now say.

- A required `Matrix` let the respondent through after one row. The runtime
  called any answer object with a key answered — MaxDiff and conjoint already
  asked for every task, a matrix asked for nothing more — so nine rows of a
  ten-row battery the author had made required could be left empty. Next now
  needs an answer in every row (a row answered "Not applicable" has one; a
  matrix has no conditions on its rows, so every row is asked). With some rows
  answered it says "Please answer every row." — the new
  `UIConfig.required_rows_text`, `{n}` being the rows left — and marks those
  rows until each has an answer, in the error color and with `aria-invalid` on
  their cells; with none it says `required_text`, as before (a row a script set
  to `null` is not an answer). Only Next marks rows: leaving the matrix
  unanswered, or a script's message on it, shows the message alone. Leaving the
  matrix still only asks for an answer at all: focus moves between its cells
  while the respondent works down the rows. A `Script.timed_question`'s
  automatic Next is an ordinary Next and is held the same way, so on a required
  matrix answered in part the respondent stays on the page, finishes the rows
  and presses Next. A `skip_to` on a matrix fires on any row, as before, and
  Studio's walkthrough trace keeps saying so for the skip, while its "answered"
  count now counts a matrix once every row is answered — what Required asks
  for, as it already did for a MaxDiff.
- A matrix could not be answered from the keyboard beyond its first row. The
  arrow keys moved a marker, not the focus — after ↓ the next → answered row 1
  again — and the "Not applicable" column was out of their reach; and Enter or
  Space on any button (a matrix cell, a rating point, a picture choice, the
  dropdown, Previous) pressed Next, so no cell could be chosen and Previous went
  forward. With a required matrix now asking for every row, a respondent without
  a mouse could not finish one. The arrow keys now move the focus from cell to
  cell — ← → along the row, answering it with the cell they reach, the N/A
  column included; ↑ ↓ to the same column of the row below or above — and
  Enter and Space on a button or a link are its own: they choose the cell or
  the point, go back, open the dropdown. So are they on a video or audio player
  (Space plays or pauses — it used to go on, and on the last page to submit
  the survey), on a `<summary>` and on the like in a page's own HTML, and a
  contenteditable region is a text field. Right after the mouse pressed a
  button or a link, while the focus it left there stays, they go on, as they
  always had: in Chromium the key would click again, and a MaxDiff or
  conjoint pick — a toggle — would be taken back. Elsewhere outside a text
  field they still go to the next page.
- The keyboard focus did not show on a chosen matrix cell or MaxDiff pick: the
  inner ring that marks one as chosen replaced the theme's focus ring. The
  arrow keys leave the focus on a chosen cell, and ↑ ↓ onto a row answered the
  same way changed nothing on screen. A chosen cell or pick in focus now shows
  both rings.
- A `SingleChoice` shown as a dropdown could not be answered from the keyboard.
  Enter on its button opened the list with the focus in the search box, and
  there no key worked: the options took no focus, ↓ ↑ and Enter did nothing,
  Esc was ignored and Tab left the list open — a required dropdown held a
  respondent without a mouse for good. The search box is now a combobox over
  the options: ↓ ↑ move along them (`aria-activedescendant`), Enter chooses
  the one they are on and gives the focus back to the button, typing narrows
  the list and puts the keys on its first match, and Esc or Tab away closes
  it. On the button ↓ opens the list and Esc closes it. A list long enough to
  scroll (seven options or more in the default theme) was a Tab stop of its
  own in Chromium 130+, so Tab from the search box left the list open with
  the focus on it, where no key worked and Esc went back a page; it is no
  Tab stop now, the keys work wherever in the open list the focus is, and
  Esc there only closes it.
- Opening a required dropdown said "This question requires an answer." at
  once — shown, and announced by a screen reader (`role="alert"`) — before
  anything could be chosen: the list's search box takes the focus, and the
  button's blur was read as leaving the question. A question is now checked
  when the focus leaves it, not when it moves between its own controls (the
  dropdown's button and search box, one checkbox and the next, a choice and
  its Other box).
- Enter did nothing after a click on a choice: the click leaves the focus on
  its radio button or checkbox (a picture choice's too, and a conjoint's
  "none"), and the runtime left every key to any field it was on, as it does
  to a text field. On a radio button, a checkbox or a slider Enter now goes to
  the next page, as it does elsewhere outside a text field, with the choice
  kept; Space stays the control's own (it checks the radio, checks or unchecks
  the box), and Esc and the digits act as they do elsewhere.
- `validate()` let a question whose id is not its answer key (id `q1`,
  variable `nps_1`) carry as its id a name the answers already hold something
  else under: another question's Other text key (`brand_other`), a matrix's
  row variable, a variable `Script.assign_condition` assigns, a codebook
  variable no question collects that a custom script writes
  (`answers.panel = …`, `[answers.panel, x] = …`, `for (answers.panel of …)`,
  `answers.panel.push(…)` — any assignment, update, `delete`, destructuring
  or loop target, or change in place, `(answers.panel || []).push(…)` and
  `Reflect.set(answers.panel, …)` included, wherever it stands: after
  `if (c)`, `else` or `return`, and after a regular expression that holds a
  quote or `\/\/`), or one of the runtime's `__` keys. The
  compiler rewrites a custom script's `answers["<id>"]` to the key,
  so `answers["brand_other"]` read the note instead of the Other text, and a
  platform keying an old runtime's answers by id moved the Other text into the
  note's column. Such a document is now refused — "Question 'brand_other'
  stores its answer under 'note', but 'brand_other' is also the key question
  'q1' stores its “Other (please specify)” text under. A script that names
  'brand_other' could mean either; give the question another id." — while an
  id that is its question's own key, which nothing renames, stays free, and so
  does a codebook variable nothing writes: the runtime captures no embedded
  data, and the Builder before patch 0043 left such an entry behind whenever a
  question's variable was renamed (id `q2`, variable `comment`, entry `q2`), so
  those documents stay valid. Where such an entry is written by a script — a
  prefill from before patch 0043, when answers were keyed by id, sets
  `answers.q2` meaning the question — the refusal names the other way out,
  the one that keeps the prefill working: "…; give the question another id,
  or, if the codebook entry 'q2' is left over from renaming this question's
  variable, delete that entry so that 'q2' in the script means the question."
- A spread of a question's answer in a custom script — `[...answers.q1]`,
  `Math.max(...answers["q1"])` — was not rewritten to the answer key when the
  id is not the key: the rewrite took the `.` of `...` for some other object's
  `answers`, and the strict lint's stale-id check did not report it either, so
  the script spread `undefined` and failed. It is rewritten like any other
  access now.
- `validate()` rejected a `show_if` / `next_if` on a variable no question
  collects — the arm `Script.assign_condition` writes, or embedded data declared
  in the codebook — as "unknown variables", which made the one thing an
  assignment exists for impossible to publish. Both now count as known
  (`Questionnaire.assigned_variables()`, `Script.assigns`); a name nothing
  writes is still refused. `validate_options` likewise accepts a quota on an
  assigned arm, checking the value against the arm codes — the cell a balanced
  assignment needs — and the piping lint no longer calls an arm piped on the
  first page a forward reference.
- `Script.randomize_pages()` pinned the first and last page and shuffled
  everything between them — a screen-out in the middle of the deck included,
  which put it in front of the questions it is gated on. Every terminal page
  (`disqualification`, `final`, `redirect`) now keeps its own position, along
  with the first and last page; the other pages are dealt into the remaining
  slots.
- `FreqTable`, `CrossTable` and `GroupMeanTable` ignored `SurveyData.weight`
  while the banner, NPS and regression honoured it, so a report built after
  `with_weight()` (the flow's Apply weight node) showed unweighted frequencies,
  crosstabs and means under a weighted heading. They now weight: frequencies
  and crosstab cells are sums of weights with the same percentage
  normalisation, the χ² is computed on counts scaled to the effective (Kish)
  sample size as the banner does, and group means, SDs and medians are
  weighted while N stays the people counted. A weighted frequency table adds an
  `Unweighted N` column and a weighted multiple-choice table an unweighted
  base row; unweighted output is unchanged.
- MaxDiff and conjoint read `SurveyData.weight` for their counts but fitted the
  conditional logit unweighted: `choice_sets()` resolved each row's weight and
  then passed the set weights to the model only when a `weight=` argument was
  given, which no flow node does. So after Apply weight the Score and the
  Utility of one MaxDiff table described two different samples, and conjoint
  part-worths, importance and share of preference were the raw sample's. The
  resolved weight now reaches the model, and `mnl()` rescales set weights to
  sum to Kish's effective number of sets — the estimates are unchanged by the
  scale, the standard errors become those of the effective base rather than of
  the raw rows or of a population total (this also changes the standard errors
  of an explicit `weight=`). The MaxDiff, conjoint and new `ShareTable`
  (`data.report.conjoint_shares`) footers name the `Weight` and give the base as
  `N respondents (W weighted)`; `analyze.conjoint_shares` gains a `stat` output.
- The rest of the analysis now either uses the weight or says it does not.
  `BarChart` draws sums of weights / weighted means and `HeatMap` with `by`
  weighted means (axis or color bar "Weighted …"); `BoxPlot`, `ScatterPlot`
  and the correlation `HeatMap` get a second title line `unweighted (the weight
  'w' is not applied)`, exposed as `SurveyChart.weight_note`. `pca()` and
  `reliability()` take a `weight` and use the weighted covariance matrix (R's
  `cov.wt`; equal weights reproduce the unweighted result), and the `analysis`
  accessor passes the data's weight. `kruskal`, `mannwhitney`, `spearman`,
  `cluster()`, an unweighted `proportion_ci`, and the quality and theme tables
  say `unweighted (the weight 'w' is not applied)`. A weighted
  `proportion_ci` counted respondents who did not answer in its base, as a
  share of 0, and took Kish's `n` over every row, so a routed or skipped
  question got a diluted share and too narrow an interval (weights of 1 did
  not give the unweighted result); its base is now those who answered, as
  for the unweighted share and the weighted frequencies. `describe_variables()` adds
  `weighted_n_valid`; regression, NPS, TURF and a crosstab without a test name
  the weight. Apply weight's description no longer promises "every table and
  statistic downstream": its help lists what is weighted and what is not.
- The simulator (`siamang.local_simulator`, behind `Questionnaire.simulate()`
  and Studio's Test → Simulate) replayed page and question conditions and the
  routing, but answered every question of a hidden block, picked answer options
  their own conditions hide, never filled the arm of `Script.assign_condition`
  — so a page gated on the arm was empty in every row — and knew nothing of
  page shuffles or quotas. Block `show_if` / `hide_if` (nested blocks too) and
  option `show_if` / `hide_if` now apply — in a wide `MultiChoice` too, where
  a hidden option's variable is missing rather than 0, as the runtime stores
  it, and an exclusive choice now stands alone; a question whose options are
  all hidden is left unanswered. `simulate_from_pages()` takes `scripts=` and
  `quotas=`: each assignment draws its arm before the first page by the arms'
  weights (balanced against the quota cells, as the platform picks, when it
  asks to be), `Script.randomize_pages` deals each respondent a page order,
  block shuffles decide which `skip_to` is met first, and a respondent holding
  a value in a full cell ends on the page being left — an answer, or the arm
  drawn before the first page, as the runtime checks it — only completes
  filling a cell.
  `simulate_questionnaire(survey, …, quotas=)` passes the questionnaire's own
  scripts, and `simulate_survey()` returns the `SurveyData` with a codebook
  entry for each arm; the flow's `source.simulated` node now runs it, and so
  does `Questionnaire.simulate(n, seed)` (without quotas, which are compiler
  options). The walk stays deterministic under its seed, and a survey with
  none of these features simulates exactly as before.
- A single-variable question whose `id` differed from its variable's name stored
  the answer under the **id**, while every `show_if` / `next_if`, quota,
  `{answer:…}` and the codebook read the **variable**. Nothing built on such a
  question ever fired in the field, and its column came out under the id.
  `question_output_name` now returns the variable for a question that writes
  one — a `name` no longer overrides it, and `validate()` rejects a
  single-variable question whose `name` is not its variable; matrix, wide,
  MaxDiff and Conjoint items keep their `name` or id — so the runtime's item
  `id`, the answer key, is the variable and `qid` stays the author's id. A
  `skip_to` and a script still
  name questions by id: the compiler emits a `skip_to` that names a question
  as the name of the page holding it (a page name is left alone), translates
  the target of an `onQuestionShow` / `onAnswer` script — the triggers the
  runtime dispatches with a key; a page-scoped target is a page name and is
  left alone — as well as a `randomize_options` / `timed_question` question
  and the two `validate_fields_match` fields to the key, and rewrites the
  `answers["q1"]`, `answers.q1`, `__errors__[…]`, `__options__[…]` and
  `__timers__[…]` accesses of such an id in a custom script's code.
  `lint(level="strict")` reports `SCRIPT_STALE_QUESTION_ID` where a custom
  script still names such an id as a string or a bare identifier the compiler
  does not translate (a comment, or a string that merely mentions the id, does
  not count), and `SCRIPT_TARGET_IS_A_PAGE` / `SCRIPT_TARGET_IS_A_QUESTION`
  where an `onQuestionShow` / `onAnswer` script targets a page or an
  `onPageEnter` / `onPageExit` script targets a question — a target the
  runtime never dispatches those triggers with, so the script never ran;
  `validate()` accepts a target by either name and rejects a document in which
  two questions share a key or a question's id is another question's key.
  Responses collected before this change under such an id are not moved.
- `data.tables.banner` died with "Grouper not 1-dimensional" when a variable was
  used as both a row and a banner column — which is how you read a base
  distribution across the banner. It now builds its own frame instead of
  indexing the original by label.
- `local_simulator` crashed on a half-open `valid_range` such as `(16, None)`,
  treated an unreadable string `hide_if` as met — hiding that question from
  every simulated respondent — and both produced columns of nulls, which look
  exactly like a question nobody reached.
- A `Matrix` cell stored its column's **position + 1**, not a code: a 0–10
  scale was recorded as 1–11, and any codebook not coded 1…n (a recode, a
  "Refused" 9) came out wrong. A cell now stores the code of the row
  variables' codebook that `Matrix.columns()` pairs with its header — by the
  label's text, else by position once the codebook's declared missing codes —
  an N/A, a refusal, a don't know — are set apart (a header naming one of them
  takes its code, wherever the codebook lists it: SPSS-origin codebooks put
  -8 "Don't know" before 0 … 10), else by position over every label when the
  counts match, else 1, 2, 3 … as before. Without headers the columns are the labels in code order,
  less the not_applicable code `na_option` offers in its own column (it was
  offered twice, first in the middle of the scale). Responses already
  collected keep the positions they were stored with.
- A `Matrix`, a `MaxDiff` and a `Conjoint` stored their answers as **one
  object under the question's key** (`{"trust": {"trust_parl": 3, …}}`), while
  every `show_if` / `next_if`, quota, `{answer:…}` and the codebook read the
  variables by name — so a condition on a matrix row or a task never fired.
  Each variable is now a top-level key of the answers (`trust_parl: 2`,
  `md_t1_best: 3`, `md_version: 0`) and nothing is stored under the question's
  key, which stays the handle a script targets. Answers a respondent saved in
  the browser under the old layout are moved to the new one when they resume
  (a saved matrix position becomes its code). Responses already collected keep
  the nested object.
- `{label:x}` piping inserted the raw code: the runtime looked the labels up in
  `window.SURVEY.pages`, which does not exist, so its label index was always
  empty. It reads the pages now — a choice's label, a matrix column's header, a
  MaxDiff item.
- A **wide** `MultiChoice` (one 0/1 variable per choice) stored the list of the
  chosen variables' *names* under the question's id, so its variables stayed
  empty, a condition or quota on them never matched, and `exclusive` — which
  names choice codes — never applied, the options' codes being variable names.
  Each variable is now stored under its own name, `1` when chosen and `0` when
  the question is answered and the option is not (nothing while unanswered,
  nor for an option its own `show_if` / `hide_if` hid: it was not offered.
  The condition is read again after every answer, whatever gives it — a click,
  a Likert digit key, a script — so one given later, on the same page say,
  that offers or hides the option makes it 0 or nothing, and so does another
  wide question's 0 turning into nothing when the condition reads it);
  with one choice per variable, option *i* is choice *i* on variable *i*, so
  `exclusive` works. A saved answer in the old layout is converted when the
  respondent resumes. Responses already collected keep the list.
- **"Other (please specify)", "None of the above" and N/A stored sentinels**
  instead of codes: a `SingleChoice` with Other wrote `{"code": "__other__",
  "text": …}`, a `MultiChoice` with Other always wrote `{"selected": […],
  "otherText": …}` (so `contains` conditions on it never matched, and two such
  questions collided once the object was unwrapped), "None of the above" was
  `"__none__"` and N/A `"na"`. Other now stores a code of the variable —
  `metadata["other_code"]`, default `-66` (`DEFAULT_OTHER_CODE`); a choice with
  that code *is* the Other option — and the typed text goes under
  `<variable>_other` (a wide question: `<name or id>_other`) while Other is
  chosen. "None of the above" stores `metadata["none_code"]`, default `-77`
  (`DEFAULT_NONE_CODE`). N/A stores the variable's `not_applicable` missing code
  (`na_code`) and keeps `"na"` only when the codebook declares none. The
  dropdown display now offers Other at all. `validate()` refuses a code that is
  neither a number nor a string, a None code that is already an answer's, the
  default Other code on a question whose choices use it, and an Other text key
  that is another answer's; the Other text is a variable a condition may read.
  `lint()` reports `ADDED_CODE_WITHOUT_LABEL` and `NA_STORED_AS_TEXT`. Answers
  a respondent saved in the browser with the old sentinels are converted when
  they resume; responses already collected keep them. The Qualtrics importer
  sets `other_code` to the recode of the text-entry choice, which was shown
  twice before — as itself and as the runtime's own "Other".
- A completed response carried the runtime's own state next to the answers:
  `__pages__` (the whole questionnaire, in the respondent's order),
  `__options__`, `__errors__`, `__timers__`. Besides bloating every row, a
  reader that unwraps nested objects one level turned `__options__` into
  columns named after the questions, over the answers. A submission now holds
  the answers and `__status` only.
- **Quotas were never enforced by the survey runtime.** Nothing called the
  transport's `checkQuota`, so cells filled past their limits and nobody was
  turned away. The compiled survey now names its quota variables
  (`SURVEY.quotaVars`, not their values or limits), and when a respondent
  leaves a page the runtime asks `checkQuota(variable, value)` about each of
  them holding a value it has not already found open — a list for a
  `MultiChoice`. On `{ok: false}` the interview ends before routing on the
  "quota full" screen (and `ui.quota_full_redirect_url`, if set), with nothing
  submitted; an error, a transport without `checkQuota` or a check slower
  than 4 s lets the respondent go on. The bundled transports now throw on a
  failed request instead of answering `{ok: false}`, which would have read as
  "full".
- The Qualtrics importer dropped a wide multi-select's exclusive answers
  ("not available when choices are separate variables") and gave it no
  choices. It now keeps the choices beside the variables — choice i on
  variable i — with their exclusive codes and, for a text-entry choice,
  `other_code`, all of which the runtime honors in the wide layout.
- The `body` of an ordinary page with questions was never shown: the runtime
  rendered a body only on engine-kind `"content"` pages (and terminal ones),
  so an introduction above a page's questions silently disappeared. A body is
  now shown above the questions on every page. It is HTML, inserted as the
  author wrote it, with piped answers escaped — as documented; a question's
  text and hint stay plain text.
- The title and body of a terminal page (`final`, `disqualification`,
  `redirect`) were shown as written: `{answer:x}` / `{label:x}` stayed
  literal braces on exactly the page that thanks a respondent by name. They
  are piped now, the body's values escaped, as on every other page.
- `UIConfig(show_title=False)` did not hide the title once a logo or an
  institution was set: the header was shown for them and always included the
  title. The payload now carries `showTitle` apart from `showHeader`, and the
  header leaves the title out when it is false.
- `Script.validate_fields_match` re-checked only when the *second* field
  changed, and never removed its message: correcting the first field left the
  error in place and Next blocked. The script now has no target, so it runs on
  every answer, sets the message on a mismatch and removes it on a match; and
  the runtime shows a script-written message from the store instead of a copy
  taken when Next was pressed, so a cleared message disappears at once.
- A seeded `Script.assign_condition` sent every respondent to the **same arm**,
  and every respondent saw the same MaxDiff/Conjoint design version: both are
  keyed by `answers.__respondent__`, which nothing set. The runtime now sets it
  when the survey loads — the transport's `respondentId()` when it has one,
  else a random id kept in the browser until the interview is submitted (or
  ended by a full quota), so a reload keeps the arm and the design.
- An embedded survey never told the page around it how tall it was, so an
  "auto-height" embed kept its initial height and scrolled inside the page.
  In an iframe the runtime now posts `{type: "siamang:height", height}` to
  its parent on load and whenever its content's height changes.
- The **page dots** (`progress_style="dots"` / `"both"`) jumped to any page,
  forward included: a respondent could skip past unanswered required questions
  and the routing between the current page and the one clicked. A dot now goes
  back only to a page on the path that led to the current one (and not at all
  with `allow_back=False`); a dot ahead, or of a page the routing skipped, is
  disabled. Going back by a dot runs `onPageExit` like Previous and retraces
  the path, which the autosave now keeps, so a resumed interview can still go
  back the way it came.
- A `MultiChoice`'s `min_answers` and a `NumericInput`'s valid range were not
  enforced: Next checked only `required`, the text formats and script messages,
  so one choice of a minimum of two, or 150 on a 1–10 scale, went through; the
  number's "Minimum value is …" / "Maximum value is …" message was the
  component's own and was never rendered. Next now refuses both with those
  messages ("Select at least N more" for the choices), and a number out of
  range is flagged as soon as its field is left. An optional question left
  empty is still not held by its minimum, and neither is an exclusive answer
  ("None of these" clears every other choice, so it is a whole answer by
  itself). The "Select at least N more" hint under the options now also shows
  without `max_answers`, once the question is answered or when it is required,
  until an exclusive answer is picked.
- `Script.timed_question`'s timer was never canceled: a respondent who left
  the page before it ran out had Next pressed for them later, on whatever page
  was showing — the last one included, which submitted the survey. The runtime
  now cancels every timer kept in `answers.__timers__` whenever a page is left
  (Next, Previous, a page dot, Studio's design-mode jump) and when the survey
  is submitted or ended by a full quota; and the next-page hook does nothing
  once the interview is over, while it is being submitted, or on a terminal
  page. A timer still runs once per question.
- `Script.randomize_options(question, seed=…)` ignored its seed: the runtime
  shuffled with `Math.random`, so "same seed, same order" held for nobody and
  a reload reshuffled. The order is now drawn from `"<seed>:<respondent id>"`
  with the FNV-1a/mulberry32 pair a seeded `assign_condition` uses: each
  respondent keeps one order across reloads and resumes, and it can be
  recomputed from the seed and their id. `utils.shuffle(list, seed)` and
  `utils.sample(list, n, seed)` take the optional seed for custom scripts;
  without one they are random as before.
- Shuffling a question's options — `randomize=True` or
  `Script.randomize_options` — moved "None of the above" and a `MultiChoice`'s
  exclusive answers ("None of these") into the middle of the list, and a choice
  that is the question's "Other" (`metadata["other_code"]`) with them; only the
  runtime's own "Other", added after the options, stayed last. The compiler now
  marks those options `"fixed": true` and both shuffles keep them in their
  place, dealing the other options into the remaining positions.
  `utils.shuffleOptions(options, seed?)` does the same for custom scripts.
- A script's **`context`** was only the static dict set on the `Script`: the
  runtime passed an empty object for its own part, so the documented and
  templated uses — `context.startedAt` to flag speeders, the page being left for
  a dwell time — read `undefined`. It now also holds `trigger`, `startedAt`
  (the page load, or for a resumed interview the sitting that saved it — kept
  with the autosave), `respondentId`, `surveyId`, `page`, `pageEnteredAt` and,
  for `onQuestionShow` / `onAnswer`, `question`; a key the `Script` sets itself
  wins. `Script.sandbox` was documented as running the code "in a sandboxed
  iframe" / "no DOM access", and nothing ever applied it: the docs now say it
  is recorded but not applied, and that scripts run as part of the page.
- `progress_style="dots"` showed the bar as well as the dots — the same as
  `"both"` — and `show_progress=False` hid the bar but left the dots of a
  `"dots"` or `"both"` style. The bar (with its text) now shows for `"bar"` and
  `"both"`, the dots for `"dots"` and `"both"`, and `show_progress=False` hides
  both.
- The progress text and the page's section label ("Welcome", "Section *n* of
  *m*", "Final thoughts") were baked into each page by the compiler from its
  place in the document, counting the end pages: a survey ending on a thank-you
  and a screen-out page showed "Section 2 of 4" on its last question page and
  never reached "Final thoughts" or a full bar, and after `randomize_pages` the
  labels traveled with the pages ("Section 3" shown second). The runtime now
  works them out from the pages the respondent answers — visible, in their
  order, without the end pages — and so does the bar's percentage; the page
  dots are one per such page. `UIConfig.show_section_numbers` and
  `show_progress_text`, which nothing read, now apply: without section numbers
  the page has no label and the bar says "Page *n* of *m*" (`page_text`,
  `of_total_text`, until now heard only by screen readers); without progress
  text the bar has none.
- **The runtime's wording is all replaceable.** `UIConfig.estimated_minutes`,
  `of_text`, `select_placeholder`, `selected_text`, `completion_title` and
  `completion_body` were accepted and never used, and about forty phrases were
  English in the runtime or the compiler — "Welcome", "Section n of m", "Final
  thoughts", "Other", "None of the above", "Not applicable", the format
  messages, "Response ID", the closed, full-sample and error screens, the
  redirect notices, the footer's "Privacy" and "Contact research team",
  "Invalid access code…", "Attempt n of 3." and more. `estimated_minutes` now
  shows under the first page's title ("About 12 minutes"); the existing fields
  reach the dropdown, the multiple-choice counter and the completion screen
  (`completion_body` before the `completion_text` option); and `UIConfig`
  gains a field for every other phrase — `welcome_text`, `section_text`,
  `final_section_text`, `estimated_time_text`, `other_text`,
  `other_placeholder`, `none_of_above_text`, `not_applicable_text`,
  `min_choices_text`, `max_reached_text`, `min_value_text`, `max_value_text`,
  `chars_remaining_text`, `search_placeholder`, `no_options_text`,
  `ranking_hint_text`, `ranking_remaining_text`, `invalid_format_text`,
  `invalid_email_text`, `invalid_phone_text`, `invalid_url_text`,
  `invalid_date_text`, `invalid_time_text`, `response_id_text`,
  `submitted_text`, `screen_out_title`, `redirect_countdown_text`,
  `redirect_link_text`, `redirecting_text`, `redirecting_link_text`,
  `quota_full_title`, `quota_full_body`, `closed_title`, `closed_body`,
  `error_title`, `error_body`, `attempt_text`, `privacy_text`, `contact_text`,
  `skip_link_text`, `access_error`, `page_error_title`, `page_error_body`,
  `app_error_title`, `app_error_body`, `reload_action` — all `None` by default,
  which keeps today's English. The document schema admits them; the static
  closed page uses `closed_*` / `quota_full_*` too.
- What the runtime keeps in the browser — the autosave, the theme, the
  interview's id — was keyed by `SURVEY.surveyId`, which the compiler never
  sets, so every survey used `…_siamang_survey`. On a host that serves many
  surveys from one origin (Studio: `study.siamang.org/<survey id>/`) a
  respondent was offered one study's saved answers to resume in another, and
  Studio's transport, which reads `siamang_answers_<survey_id>` to post partial
  responses, never found any. The key is now the transport's `survey_id`
  (`SIAMANG_ENV.survey_id`) unless the host sets `SURVEY.surveyId`; the old
  constant is only the fallback of a page with neither. Progress saved under
  the old key is not offered after the update — it may be another survey's.
- A condition comparing with `None` meant something else in the browser than
  in Python. The compiler wrote `x != None` as `a["x"] !== null`, but the
  runtime has no key for a question nobody answered — its value is
  `undefined` — so "x was answered" held for every respondent who skipped `x`,
  `x = None` held for nobody, and `x in [None, 1]` never matched an empty
  answer. An attention check on a question without codes (screen out when
  `check != None and check != 3`, as Studio writes it) screened out everyone
  who left an optional check empty. Comparisons with `None` are now compiled
  loosely (`== null` / `!= null`, and an unanswered value counts as `null` in
  an `in` list), in the compiled conditions, in the runtime's evaluator of
  expression trees and in its parser of string conditions alike, matching
  `Expression.evaluate`; in a string condition (`"{x} != null"`, as
  `Expression.to_surveyjs()` writes `None`) `null` is now the literal rather
  than a variable of that name, so `{x} in [null, 3]` also holds for an
  answer stored as `null`.
- The runtime asked "Leave site?" when a respondent closed or reloaded a
  survey they had not touched, whenever a script had written a variable at
  load — the arm `Script.assign_condition` draws, an id an `onInit` script
  notes: it counted any answer key in the store as the respondent's. It now
  asks only once the respondent has answered something in this sitting (and
  the interview is not over).
- **A nested block's `show_if`, `hide_if` and `randomize` never reached the
  survey runtime**: the compiler flattened a block's nested blocks into one
  list of questions, so a hidden nested block's questions were shown — and a
  required one among them held Next — while `validate()`, the model and the
  simulator treated them as hidden. Each question inside nested blocks now
  carries those blocks' conditions (`gates` in the payload) and is shown only
  while all of them and its own condition allow it; Studio's walkthrough trace
  lists the nested blocks and says which one hides a question. A nested
  block's `randomize` shuffles its own items, and a shuffling block moves a
  nested block as one item, its questions together and in order (sent as the
  block's `layout`); the simulator deals block shuffles the same way. A block
  without nested blocks compiles exactly as before. In a questionnaire made
  only of blocks, where each block becomes a page, the block's conditions now
  gate its page and its `randomize` shuffles the page's items; the simulator
  walks such a questionnaire on those pages too (it answered every question of
  it, hidden blocks and question conditions notwithstanding), and so does the
  questionnaire document (`to_document`, `siamang model`), which dropped the
  blocks' conditions and shuffle — an owners-only block was shown to everyone
  once the questionnaire was imported — and took loose questions out of their
  blocks.
- `check_flow` reported a node naming the arm of `Script.assign_condition` —
  a crosstab by `condition` — as `UNKNOWN_VARIABLE` unless the questionnaire
  document also declared it in `variables`, although real responses and
  Simulated data carry the column. The arm now counts as known, as it does for
  `validate()`, and is nominal unless the codebook says otherwise.
- The local server (`siamang preview`, `backend="local"`) answered the
  runtime's quota check with `LocalBackend.increment_quota`, which claimed a
  place in the cell for every respondent whose answer was checked — those who
  dropped out afterward or were screened out included — so a cell filled
  before its completes reached the limit. `/quota-check` now only reads
  (`check_quota`, which takes a list and is full when any value's cell is),
  and `store_response` counts a completed response — anything but
  `__status: "screened_out"` — in every cell its answers fill, a list answer
  in the cell of each value it holds, as Studio counts them. Only a variable
  answered with a list (an array `MultiChoice`, a `Ranking`) is counted that
  way: a list posted for a single-answer variable fills no cell, so one
  submission cannot take a place in every cell of it. Both go through the
  survey's cells in one pass, whatever the length of the list posted.
- The autosave of an interview that had ended was written back after it
  ended. It is written 2 s after the last answer, and ending the interview
  (Submit, a full quota on leaving a page or in the reply to a submission)
  removed the saved answers without canceling the save still pending from an
  answer given just before — the usual case. The thank-you or quota-full
  screen was followed by a fresh `siamang_answers_<survey_id>`, the next visit
  within a day offered to resume the finished interview (a second completed
  response when accepted), and Studio's transport, which reads that key for
  partial responses, posted it as one. An ended interview now cancels the
  pending save and writes none afterward; a submission refused as a full
  quota also forgets the saved answers and the interview id, as a full quota
  found on leaving a page does.
- Resuming a survey with `Script.randomize_pages` landed on the wrong page.
  The shuffle deals a new page order at every load, and the autosave kept the
  page's position and the path but not the order they count in, so the
  resumed interview applied the old position to the new order: the
  respondent landed on a page already answered, pages before it they had
  never reached were never shown, others were shown twice, and a "completed"
  response lacked required answers. The autosave now keeps the page order
  (`pageOrder`, the pages' names) and Resume restores it when it names the
  survey's pages; progress saved by an earlier runtime resumes as before.
- A Likert answered with a digit key (1–9, when no field has the focus) was
  written past the runtime's answer handling: it was not autosaved, ran no
  `onAnswer` script and left the question's error on screen. It is now
  answered as a click answers it. On a scale that starts at 0 the digit is
  still the point's value, and a digit the scale does not have (5 on 0–4)
  answers nothing; it stored that value.
- **Generated code ran what an author's text put after a line break.** A flow
  node's banner comment (`# ── Report section: <heading>`) carries its
  parameters as written, and the questionnaire module marks each definition
  `# studio: <question id>` (a variable's, a page's name). A heading or an id
  holding a line break ended the comment there, and what followed was
  module-level code: it ran on import — in a platform's flow run and on the
  machine of whoever runs a research bundle (`environment/run.sh`). Every line
  break and control character on a comment line is now a space; the text
  itself still reaches the report and the questionnaire as written.
- **An object-form codebook meant what its text happened to list first.** The
  shorthand `{"0": "No trust at all", …, "10": "Complete trust", "-1": "Not
  applicable"}` was read in the order of its JSON text, and nothing keeps that
  order: Postgres `jsonb` lists keys by length ("-1" between "9" and "10"), a
  browser lists the whole-number keys first. The order is the one a choice
  shows its options in and a matrix lines its headers up with, so the same
  document stored in `jsonb` offered "Not applicable" between 9 and 10, and a
  matrix headed `0` … `10`, "Not applicable" over it stored -1 for "10" and 10
  for "Not applicable" — where a browser's copy of that document, a preview,
  stored 10 and -1. The shorthand is now read in one order whatever its text
  lists: codes 0 and up ascending, then the negative codes from -1 down, then
  text codes as listed — for whole-number codes the order a browser gives the
  codebook read back from `jsonb`. The list form keeps the author's order as
  before. A hand-written document whose object lists its codes in another
  order (5 … 1, or -8 before 0) is now read in this one — its options, a
  matrix's positions and a MaxDiff's implied design (one with no stored
  `design`) with it; writing the codebook as a list in the object's order
  keeps the earlier reading.
- **The theme table's uncoded share was a share of the coded answers.** One
  uncoded answer in four read as 33.3 %. `Coded` and `Uncoded` are now shares of
  everyone who answered (75.0 % and 25.0 %); the theme rows stay shares of the
  coded answers, and the stats say which is which (`Percentages`).
- **TURF's frequency was unweighted beside a weighted reach.** On weighted data
  the mean number of the portfolio's options a reached respondent chose is now
  weighted like the reach; unweighted results are unchanged.
- **The R bundle's script lost answers.** `source("dir/import_survey.R")` from
  any other directory failed to find its CSV (it looked in the working
  directory); a multiple-choice column (`1;3`) and every code without a value
  label became `NA` in `factor()`; a text answer "NA" became missing; and on a
  non-UTF-8 locale labels were read in the wrong encoding. The script now finds
  its files beside itself under `Rscript` and `source()`, reads the CSV as UTF-8
  with only empty cells missing, keeps multiple-choice columns as text, gives an
  unlabeled code a level of its own, leaves missing codes out of the levels and
  sets each column's `label` attribute. Its dictionary is now
  `<name>.dictionary.json` (was `<name>_dictionary.json`), the name every other
  export uses, so `read_snapshot("<name>.csv")` finds it.

## [0.6.0] — 2026-08-30

Runtime documentation-parity release: everything the docs describe for the
respondent experience now actually runs in the browser.

### Added

- **Routing in the respondent runtime**: `Question.skip_to`,
  `Page.next_if`, and `Page.default_next` are compiled into the React
  payload and executed — skip_to of the first answered visible question
  wins, then the first matching `next_if` rule, then `default_next`, then
  the next visible page. Targets may be page names or question ids; a jump
  to a page hidden by its own gates falls through to the next visible page
  in document order. "Previous" retraces the actual visited path.
- **String conditions**: plain-string gates in the SurveyJS dialect
  (`"{age} >= 18"`, `"age >= 18"`, `and`/`or`/`not`, `in [..]`,
  `contains`, `empty`/`notempty`, parentheses) are now parsed and
  evaluated by the React runtime, for page/block/question/option gates and
  string `next_if` rules. An unparsable string keeps the historical
  always-visible behaviour (with a console warning); as a routing
  condition it counts as not matched.
- **All seven script triggers dispatched**: `onPageEnter`, `onPageExit`,
  `onQuestionShow` (when a question first becomes visible), and
  `onRandomize` now fire alongside `onInit`/`onAnswer`/`onSubmit`. Script
  writes into `answers` sync back to the reactive store, which makes the
  documented `answers.__options__` / `__pages__` / `__errors__` /
  `__timers__` contracts real: `Script.randomize_options` reorders
  options, `Script.randomize_pages` reorders navigation,
  `Script.validate_fields_match` messages render under the field and block
  "Next" until resolved, `Script.timed_question` auto-advances via the new
  `window.siamangNext` hook.
- **Author-declared randomization**: `Question.randomize`,
  `Block.randomize`, and `Page.randomize_blocks` are applied once per
  respondent at load time (standalone questions keep their positions).
- **Choice behaviours**: `MultiChoice.exclusive` codes clear — and are
  cleared by — other selections; `SingleChoice.none_of_above` appends the
  documented option (sentinel code `__none__`, mirroring `__other__`).
- **Matrix**: `subquestions` override row labels; `na_option` adds the
  "Not applicable" column (stored as `"na"`, same as `LikertScale`).
- `SurveyData.create_index(method="sum")` (row sum, `min_count=1`);
  `"mean"` remains the default.

### Fixed

- Option-level `show_if`/`hide_if` never gated anything: the
  `isVisibleGated` helper that the option renderer called was not defined.
- `siamang deploy` now loads `~/.siamang.toml` automatically, as
  documented — defaults, profiles (`--profile`), and stored credentials
  apply without an explicit `--config`.
- Environment credential overlays (`SIAMANG_*`, `VERCEL_TOKEN`,
  `NETLIFY_AUTH_TOKEN`, legacy `SURVLIB_*`) now apply even when no config
  file exists on disk.
- Question components re-render when their option order or option gates
  change (previously blocked by the memo comparator).

### Changed

- **License**: switched from MIT to dual licensing. Noncommercial use is
  free under the **PolyForm Noncommercial License 1.0.0** (`LICENSE`);
  commercial use now requires a separate commercial license
  (`LICENSE-COMMERCIAL.md`). Versions up to and including 0.5.0 remain
  available under the MIT License.
- Build: `setuptools>=77` is now required (PEP 639 license metadata).

### Known limitations

- `simulate()` still ignores routing (`next_if`/`skip_to`) — it models
  visibility gates only.
- `Questionnaire.preview()` (the Python method) returns a one-line
  summary; use `siamang preview` for the real rendered survey.
- `validate()` checks that `skip_to` targets exist but does not include
  `skip_to` edges in reachability/cycle detection.
- The alternative SurveyJS runtime does not evaluate the new routing
  payload; the default React runtime does.

## [0.5.0] — 2026-05-28

### Added

- **Theming system**: `UIConfig` with `font_preset` (classic, modern, humanist),
  `accent_color`, and CSS custom properties for full visual customization.
- **"Other (specify)"** option for `SingleChoice` and `MultiChoice` questions
  via `other_specify=True`.
- **Answers store**: lightweight reactive store (`useSyncExternalStore`) replacing
  top-level `useState` — eliminates full-tree re-renders on every keystroke.
- **Compiled visibility**: `show_if`/`hide_if` conditions compiled to JS functions
  at load time (no more per-render AST interpretation).
- **Hooks decomposition**: `useSurveyNav`, `useSubmission`, `useAutosave`,
  `useLifecycleScripts`, `useKeyboardShortcuts`, `useTheme`.
- Supabase backend now uses a single shared `responses` table with `survey_id`
  column (consistent with local SQLite backend).
- Environment variable naming: `SIAMANG_SUPABASE_*` with backward-compatible
  fallback to legacy `SURVLIB_SUPABASE_*`.
- Script factory functions now use `json.dumps()` for parameter escaping
  (prevents injection from special characters in IDs/messages).

### Changed

- Development status set to **Beta** (honest reflection of current test coverage).
- Slider component: adaptive tick rendering (≤20 steps → labeled ticks,
  >20 steps → end-labels only). Fixes the "wall of numbers" bug.
- Frontend JS globals renamed: `window.SIAMANG_ENV` / `window.SIAMANG_TRANSPORTS`
  (runtime falls back to legacy `SURVLIB_*` names for backward compatibility).

### Fixed

- Supabase backend/frontend mismatch: frontend now POSTs `{survey_id, data}`
  matching the shared table schema (previously sent `{survey_id, payload}` to
  a per-survey table that didn't have a `survey_id` column).
- Slider rendering bug: no longer outputs 61 `<option>` elements for range 0–60.

### Removed

- Per-survey table creation (`responses_{survey_id}`) in Supabase backend —
  replaced by shared `responses` table.
- `BUILD.md` reference removed from MANIFEST.in (file never existed).

## [0.4.1] — 2026-04-15

### Added

- Initial public structure with core survey engine, React frontend, CLI,
  local SQLite backend, and Supabase/Vercel deployment support.
