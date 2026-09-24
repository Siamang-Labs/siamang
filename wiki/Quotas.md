# Quotas

A `Quota` caps the number of accepted responses that match a specific category,
keeping a sample within target proportions (e.g. no more than 200 male and 200 female
respondents). The survey runtime asks the backend whether a respondent's cell is full
as soon as they leave the page that answered it, and ends the interview with the
"quota full" screen when it is.

```python
from siamang.core import Quota
# or: import siamang as sg  →  sg.Quota
```

## `Quota`

```python
@dataclass(frozen=True, slots=True)
class Quota:
    variable: str
    target_value: Any
    limit: int
```

| Field | Type | Description |
| :--- | :--- | :--- |
| `variable` | `str` | Name of the variable to monitor (must match a `Variable.name`). |
| `target_value` | `Any` | The category code to count (e.g. `1` for "Male"). |
| `limit` | `int` | Maximum accepted responses matching `variable == target_value`. |

Each `Quota` describes **one cell** — a single variable/value pair. Build several
quotas to constrain multiple cells or several variables.

### `reached`

```python
def reached(self, answers: list[dict[str, Any]]) -> bool
```

Counts how many rows in `answers` have `row[variable] == target_value` and returns
`True` once that count reaches `limit`. This is the same predicate the backend uses to
decide whether a cell is full.

```python
from siamang.core import Quota

male_cap = Quota("gender", target_value=1, limit=200)

responses = [{"gender": 1}, {"gender": 2}, {"gender": 1}]
male_cap.reached(responses)          # False (2 < 200)
male_cap.reached([{"gender": 1}] * 200)   # True
```

## How enforcement works

Quotas are attached at **deploy time** via the `quota=` option (a document keeps them
in its top-level `quotas`), not stored on the `Questionnaire`. siamang serializes each
quota and hands it to:

- the **backend**, which creates a counter per cell and decides whether a cell is full;
- the **survey runtime**, which learns only *which variables* have quota cells
  (`SURVEY.quotaVars` in the compiled page — not the values or limits).

When a respondent **leaves a page** (Next, or Submit on the last page), the React
runtime takes every quota variable that holds a value it has not already found open —
answered on that page, or set by a script — and calls the transport's
`checkQuota(variable, value)`. For an array `MultiChoice` the value is the list of
chosen codes, and the cell is full when any of them is. The backend answers
`{"ok": true}` or `{"ok": false}`; on `ok: false`, before any routing:

- the interview ends on the closed screen **"Thank you for your interest"** /
  **"We have already reached our target sample for participants like you."**;
- no response is submitted, and the answers saved in the browser are cleared;
- with `UIConfig.quota_full_redirect_url` set, the browser goes there after 3 seconds
  ("Redirecting you now. Continue if you are not redirected."), with `{url:NAME}`
  filled from the entry link — how a panel respondent is sent back as "quota full".

The Next button waits while the checks run. A value found open is not asked about
again unless the respondent changes it. **Nothing but a "full" answer stops
anyone**: no quotas, a transport without `checkQuota`, a failed request (the bundled
transports throw on an HTTP error rather than report "full") and a check that takes
longer than 4 seconds all let the respondent go on.

When the backend rejects the final submission itself (a full response cap, HTTP 409),
the runtime shows the same screen after the retries.

Who counts, and when, is the backend's business:

- **Siamang Studio** counts a cell when a response is completed (not screened out)
  and, for a list answer, counts every cell whose value is in the list.
- The **`local`** backend's `/quota-check` endpoint *claims* a place in the cell when
  it is asked, so it counts respondents when their answer is checked — including
  those who later drop out or are screened out. Use it for development.
- **`supabase`** calls the edge function named by `quota_function` (default
  `quota-check`), which you deploy yourself; without one the check fails and no one
  is stopped.
- **`gsheets`** posts `action: "checkQuota"` to its Apps Script proxy.

```python
from siamang.core import Quota

quotas = [
    Quota("gender", target_value=1, limit=200),
    Quota("gender", target_value=2, limit=200),
    Quota("region", target_value=1, limit=400),   # cap on the capital region
]

survey.deploy(backend="supabase", frontend="vercel", quota=quotas)
```

A quota may also name a variable of a wide `MultiChoice` (`Quota("src_tv", 1, 300)`),
a `Matrix` row, or the arm `Script.assign_condition` draws — every one of them is a
variable of its own.

## Examples

### Equal cells

Cap two genders at the same limit:

```python
import siamang as sg

quotas = [
    sg.Quota("gender", 1, limit=200),
    sg.Quota("gender", 2, limit=200),
]
survey.deploy(backend="supabase", frontend="vercel", quota=quotas)
```

### Constraining several variables

Quotas on different variables are independent — a respondent must clear every cell they
falls into:

```python
quotas = [
    sg.Quota("gender", 1, limit=200),
    sg.Quota("gender", 2, limit=200),
    sg.Quota("region", 1, limit=400),
    sg.Quota("region", 2, limit=400),
]
survey.deploy(backend="supabase", frontend="vercel", quota=quotas)
```

### Tightening a cell between deploys

Quotas live in the deploy call, so adjusting a `limit` is just a code change followed
by another deploy. Note that each deploy provisions a **new survey instance** with
fresh quota counters — counts do not carry over from the previous deployment:

```python
quotas = [
    sg.Quota("gender", 1, limit=150),   # lowered from 200
    sg.Quota("gender", 2, limit=250),   # raised from 200
]
survey.deploy(backend="supabase", frontend="vercel", quota=quotas)
```

> **Backend support.** The check needs a backend that answers `checkQuota`:
> Studio does; `local` claims a place per check (see above) and is not publicly
> reachable, so use it for development and preview; `supabase` needs your own
> `quota-check` edge function. See [[Deployment]].

## See also

- [[Deployment]] — the `deploy()` call where `quota=` is passed.
- [[Question Types|Question-Types]] — the variables a quota monitors.
- [[Variables and Measurement|Variables-and-Measurement]] — variable names and category codes.
- [[Scripts]] — additional respondent-side behaviour via JavaScript.
