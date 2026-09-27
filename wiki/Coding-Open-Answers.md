# Coding Open Answers

An open question ("Why did you give that score?") gives you text. To count it,
each answer needs a **theme**. `siamang.data.text_coding` does that from a
**codeframe** — a JSON file of themes, the answers you coded by hand, and rules
that code the rest — with no model and no network, so the same file gives the
same numbers at every run. This page shows how to write one, check it and use
it.

---

## How an answer is coded

Each answer is coded by the first of:

1. **Your decision.** The codeframe keeps the themes you gave an answer, by its
   fingerprint — sixteen hex characters of a hash of the answer's text, case,
   spacing and Unicode form set aside. It never keeps the text itself. You can
   decide an answer has one theme, several, or none (`[]`: read, and belongs to
   no theme).
2. **The rules.** Each theme can have terms that code the answers nobody
   decided — including the ones collected after you wrote the rules, because the
   rules run at every run.
3. **Nothing.** The answer is *uncoded*: left for you to read.

A blank answer is not an answer and is never coded.

---

## A first codeframe

```python
import pandas as pd
from siamang.core import Variable, VariableMap
from siamang.data import SurveyData, text_coding

answers = [
    "The delivery was late",
    "Box arrived damaged, and two days late",
    "The driver was rude",
    "Nothing",
    "wasn't late, all fine",
    "Great!",
    "",
]
variables = VariableMap()
variables.add(Variable("why", "nominal", label="Why that score?", dtype="str"))
data = SurveyData(frame=pd.DataFrame({"why": answers}), variables=variables)

codeframe = {
    "schema_version": "2.0",
    "variable": "why",
    "multiple": True,  # several themes an answer
    "themes": [
        {"code": 1, "label": "Late delivery", "group": "Delivery",
         "rules": {"include": ["late", "delay*"]}},
        {"code": 2, "label": "Damaged", "group": "Delivery",
         "rules": {"include": ["damag*", "broken|broke"]}},
        {"code": 3, "label": "Rude staff",
         "rules": {"include": ["rude", "unfriendly"], "require": ["staff", "driver", "courier"]}},
        {"code": 9, "label": "Nothing / Don't know", "exclusive": True,
         "rules": {"include": ["nothing", "don't know"]}},
    ],
    # "Great!" read by a coder: no theme.
    "assignments": {text_coding.fingerprint("Great!"): []},
}

print(text_coding.validate(codeframe).ok)   # True
cf = text_coding.parse(codeframe)
coded = text_coding.apply(data, cf)
print(coded.frame["why_theme"].tolist())
# [[1], [1, 2], [3], [9], None, [], None]
print(coded.report.themes(cf).to_markdown())
```

```text
| Theme | N | % |
|---|---|---|
| Delivery (net) | 2 | 33.3 |
| Late delivery | 2 | 33.3 |
| Damaged | 1 | 16.7 |
| Nothing / Don't know | 1 | 16.7 |
| Rude staff | 1 | 16.7 |
| No theme | 1 | 16.7 |
| Coded | 5 | 83.3 |
| Coded by hand | 1 | 16.7 |
| Coded by rules | 4 | 66.7 |
| Uncoded | 1 | 16.7 |

Variable = why; Answered = 6; Themes = 4; Coverage = 83.3 % of the answers are coded; Coded by hand = 1; Coded by rules = 4; Distinct uncoded answers = 1; Percentages = of the respondents who answered; a respondent can have several themes, so the themes add up to more than 100 %; Nets = a net counts a respondent once, however many of its themes they have
```

Six people answered. *wasn't late, all fine* is uncoded: its only mention of
*late* is negated. The net **Delivery** counts the respondent with both of its
themes once. With `"multiple": true` the theme variable holds a list of codes
per answer — a multiple-choice variable, which frequencies, crosstabs, the Bar
chart and the tab book read as they read a multiple-choice question.

Save the codeframe as `analysis/why.codeframe.json` and
`text_coding.load(path)` reads it back.

---

## The file

| Field | What it is |
|-------|------------|
| `variable` | The open-text variable. |
| `into` | The theme variable (default `<variable>_theme`). |
| `language` | `"en"`. The words the rules know — negations, clause words, stop words — are English. |
| `multiple` | `true`: several themes an answer (a multiple-choice variable). `false` (default): one theme (a nominal variable). |
| `max_codes` | The most themes the rules give an answer; `0` (default) for no cap. |
| `scope` | Where the rules read: `"clause"` (default) or `"answer"`. A theme's own `rules.scope` wins. |
| `replace` | `[{"from": "delievery", "to": "delivery"}]`: whole words or phrases replaced before the rules read — typos, synonyms. |
| `themes` | `code`, `label`, and optionally `definition`, `group` (the net it belongs to), `exclusive`, `priority` and `rules`. |
| `assignments` | Your decisions: `{fingerprint: code, [codes] or []}`. |

A theme's `rules` are `include`, `require` and `exclude` terms. The theme
matches in a clause (or, with scope `answer`, in the whole answer) when an
`include` term matches there, the `require` terms have a match there — a list is
"any of these"; a list of lists is "one of each list" — and no `exclude` term
matches there.

---

## Writing terms

| Term | Matches | Does not match |
|------|---------|----------------|
| `late` | *It was LATE!* | *latest*, *wasn't late* |
| `delay*` | *delay*, *delays*, *delayed* | *relay* |
| `slow\|late` | *slow* or *late* | |
| `customer service` | *the customer service was bad* | *service to the customer* |
| `staff ~3 rude` | *the staff were very rude*, *rude staff* | *rude. The staff* |
| `not_late` | *wasn't late*, *never late* | *it was late* |
| `don't know` | *I don't know* | *I don't really know* (write `don't ~2 know`) |

- `*` stands for any letters of a word, anywhere in it (`*charg*`).
- `|` gives alternatives at one place of a phrase: `customer serv*|support`.
- `~N` finds two words (or phrases) within N words of each other, in either
  order, in one sentence.
- A term matches a mention that is **not negated**. `not_word` matches only a
  negated one. A negation written in the term (`not late`, `no problems`,
  `don't know`) is the term's own.
- There are no regular expressions: `re:` is refused.

**Negation.** *not, no, never, cannot, without, nothing, none, nobody, neither,
nor, hardly, barely* and every *n't* form (also typed without the apostrophe:
*dont*, *wasnt*, *cant*…) negate the next three words, stopping at punctuation
and at *and, or, yet, but, however, although, though, whereas, except, plus*.
So in *not cheap, and fast* only *cheap* is negated.

**Clauses** end at punctuation and at *but, however, although, though,
whereas, except, plus*. In *Delivery was quick but the box was damaged*, a theme
that requires *delivery* and includes *damaged* does not match in clause scope
— they are in different clauses — and does with `"scope": "answer"`.

**Other languages.** Words are Unicode: *Цена*, *café*, *नमस्ते* are words, and
terms in them match. Only negation is English — an answer in another language
is never lost, it just has no negation read in it.

---

## Several themes, exclusive themes, priority

When several themes match an answer:

1. an **exclusive** theme (*Nothing / Don't know*) is kept only if no other
   theme matched;
2. the themes are ranked by **priority** (highest first; ties by their order in
   the file);
3. `max_codes` keeps that many; a codeframe with `"multiple": false` keeps one.

Your own decisions are kept as you made them (a single-theme codeframe keeps the
highest-ranked of several).

---

## Checking your rules

`validate` lists every problem with its place in the file:

```python
found = text_coding.validate({**codeframe, "themes": codeframe["themes"] + [
    {"code": 4, "label": "Mail", "rules": {"include": ["e-mail", "re:mail"]}}]})
for issue in found.errors + found.warnings:
    print(issue.level, issue.path, issue.message)
```

```text
error ('themes', 4, 'rules', 'include', 1) theme 4 (Mail): include term 're:mail': regular expressions are not supported: write the words, with * for word forms (delay*), | for alternatives (slow|late) and ~N for words near each other (staff ~3 rude)
warning ('themes', 4, 'rules', 'include', 0) theme 4 (Mail): include term 'e-mail' can never match: '-' is not part of a word — the answers are split into words there, so write the parts as separate words
```

`explain` shows how one answer is read and why it got its themes:

```python
e = text_coding.explain("The delivery wasn't late, but the box was broken", cf)
e["clauses"]   # ['the delivery wasn't late', 'the box was broken']
e["codes"]     # [2]
[(r["label"], r["status"], r["term"]) for r in e["rules"]]
# [('Late delivery', 'negation', 'late'), ('Damaged', 'fired', 'broken|broke')]
```

Each rule is `fired`, `vetoed` (a `require` missing or an `exclude` present,
with the reason) or `negation` (the words are there, negated). `dropped` lists
the themes that matched and were set aside — an exclusive theme, a cut by
priority — and why.

`preview` codes a whole list of answers with their counts and gives, per
distinct answer, its codes, whether they came from you or from a rule (with the
term and the words it matched), and the counts per theme, per net and overall:

```python
p = text_coding.preview({"The delivery was late": 12, "Great!": 3, "meh": 1}, cf)
p["coverage"]
# {'answered': 16, 'coded': 15, 'uncoded': 1, 'by_hand': 3, 'by_rules': 12,
#  'no_theme': 3, 'percent_coded': 93.8}
```

It is fast enough to run as you edit: 50,000 different answers against 30
themes of 10 terms each take a few seconds.

---

## Finding new themes

`suggest` lists the words and two-word phrases that come up most in the answers
still uncoded, with how many people used each and an example:

```python
text_coding.suggest({"The app crashes": 3, "app crashes all the time": 2}, 5, codeframe=cf)
# {'words': [{'term': 'app', 'count': 5, 'example': 'The app crashes'}, ...],
#  'phrases': [{'term': 'app crashes', 'count': 5, 'example': 'The app crashes'}]}
```

English stop words are left out, and a word mostly met negated comes as
`not_word` — a term you can paste as it is.

---

## In a flow

The **Code open answers** node (`prepare.text_code`) applies a codeframe file
and hands on the data with the theme variable, the theme table and its
statistics (coverage, coded by hand and by rules). A codeframe that gives
several themes an answer makes a multiple-choice variable, so a later chart or
tab book treats it as one. See [[Reporting Tables|Reporting-Tables]] for the
table.

---

## Version 1 codeframes

A codeframe with `"schema_version": "1.0"` — one theme per decided answer, no
rules — is read and applied exactly as before: the same variable, the same
table (theme shares of the coded answers) and the same generated code.

---

## See also

- [[Working with Data|Working-with-Data]]
- [[Reporting Tables|Reporting-Tables]]
- [[Analysis]]
