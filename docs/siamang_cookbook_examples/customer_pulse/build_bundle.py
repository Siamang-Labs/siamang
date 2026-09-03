"""Build a self-contained HTML bundle (kiosk / offline use) without deploying."""

from pathlib import Path

from siamang.frontend import (
    ClientEnv, FrontendBuilder, LocalClientTemplate, ReactRuntime, compile_css,
    compile_questionnaire,
)

from survey import options, survey, ui

schema = compile_questionnaire(survey, options=options)
builder = FrontendBuilder(runtime=ReactRuntime(), ui=ui)      # ReactRuntime: routing + scripts
bundle = builder.build(
    schema,
    client=LocalClientTemplate(),                              # POSTs to /responses of the host
    env=ClientEnv(survey_id="kiosk-2026", backend="local", settings={}),
    survey=survey,                                             # the React runtime needs it
)
target = Path("out/bundle")
bundle.write_to(target)
print(sorted(p.name for p in target.iterdir()))
print("digest:", bundle.compute_digest())
print("css bytes:", len(compile_css(ui)))                       # inspect the compiled theme
