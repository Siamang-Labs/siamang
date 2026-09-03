"""Local deployment loop: deploy, submit test responses over HTTP, collect, monitor quotas.

This is exactly what `siamang preview` does, driven from Python so it can be
scripted (and unit-tested).
"""

import requests

import siamang as sg
from codebook import variables
from helpers import flatten_responses
from survey import options, survey




# 1. Deploy locally (SQLite + a background FastAPI server), quotas attached via **options
result = survey.deploy(
    backend_kwargs={"path": "out/survey.db"},
    frontend_kwargs={"host": "127.0.0.1"},
    **options,
)
print("survey_id:", result.survey_id, "url:", result.url)

# 2. Submit a few responses the way the browser runtime does
TEST_RESPONSES = [
    {"consent": 1, "age": 34, "region": 1, "gender": 2, "education": 4, "employment": 1,
     "work_sector": 2, "work_hours": 40,
     "matrix_trust_govt": {"trust_govt": 2, "trust_parliament": 3, "trust_courts": 4,
                           "trust_police": 4, "trust_media": 98},
     "interest": 4, "news_sources": [3, 4], "multi_act_vote": ["act_vote", "act_petition"],
     "comment": "Interesting survey.", "recontact": 1,
     "__options__": {}, "__pages__": [], "__errors__": {}},
    {"consent": 1, "age": 61, "region": 3, "gender": 1, "education": 2, "employment": 5,
     "matrix_trust_govt": {"trust_govt": 3, "trust_parliament": 3, "trust_courts": 3,
                           "trust_police": 5, "trust_media": 2},
     "interest": 2, "news_sources": [1], "multi_act_vote": ["act_vote"], "recontact": 2,
     "__options__": {}, "__pages__": [], "__errors__": {}},
    {"consent": 1, "age": 17, "region": 2, "__status": "screened_out",
     "__options__": {}, "__pages__": [], "__errors__": {}},
]
for answers in TEST_RESPONSES:
    r = requests.post(f"{result.url}/responses",
                      json={"survey_id": result.survey_id, "responses": answers}, timeout=5)
    print(r.status_code, r.json())

# 3. Collect and normalise
raw = result.collect()
print("raw columns:", list(raw.columns))
flat = flatten_responses(raw, survey)
flat = flat.drop(columns=["_response_id", "_submitted_at"])
data = sg.SurveyData(frame=flat, variables=variables, questionnaire=survey)
print(data.frame[["age", "region", "trust_media", "act_vote", "act_petition", "news_sources"]])
print("issues:", [(i.code, i.variable) for i in data.validate()])

# 4. Quota monitoring: the same predicate the backend uses, on the collected rows
records = data.frame.to_dict("records")
for cell in options["quota"]:
    print(f"{cell.variable}={cell.target_value}: "
          f"{sum(r.get(cell.variable) == cell.target_value for r in records)}/{cell.limit}"
          f"{'  FULL' if cell.reached(records) else ''}")

# The backend's own counter (atomic check-and-increment) — also reachable over HTTP
print(result.backend_ref.check_quota(result.survey_id, "region", 1))
print(requests.post(f"{result.url}/quota-check",
                    json={"survey_id": result.survey_id, "variable": "region", "value": 1},
                    timeout=5).json())

result.frontend_ref.stop()
