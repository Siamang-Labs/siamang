"""Frontend constructor: compile, theme, runtime, client, builder.

Top-level API:

- :class:`SurveySchema` — canonical intermediate representation;
- :class:`SurveyBundle` — assembled output ready to deploy;
- :class:`FrontendBuilder` — orchestrator combining runtime/theme/client;
- :class:`UIConfig` and theme presets;
- :class:`SurveyJSRuntime` (the only runtime in v1.0);
- :class:`LocalClientTemplate`, :class:`SupabaseClientTemplate`.

To build a bundle manually::

    from siamang.frontend import (
        FrontendBuilder, UIConfig, LocalClientTemplate, ClientEnv,
        compile_questionnaire,
    )

    schema = compile_questionnaire(survey, options={"language": "en"})
    builder = FrontendBuilder(ui=UIConfig(primary_color="#2c5f8a"))
    env = ClientEnv(survey_id="abc", backend="local", settings={})
    bundle = builder.build(schema, client=LocalClientTemplate(), env=env)
"""

from siamang.frontend.builder import FrontendBuilder
from siamang.frontend.bundle import SurveyBundle
from siamang.frontend.client import (
    BackendClientTemplate,
    ClientEnv,
    LocalClientTemplate,
    SupabaseClientTemplate,
)
from siamang.frontend.compiler import (
    compile_expression,
    compile_questionnaire,
    expression_variables,
)
from siamang.frontend.runtime import (
    ReactRuntime,
    RuntimeAdapter,
    RuntimeRenderContext,
    SurveyJSRuntime,
)
from siamang.frontend.schema import SurveySchema
from siamang.frontend.theme import THEME_PRESETS, UIConfig, compile_css, get_preset

__all__ = [
    "BackendClientTemplate",
    "ClientEnv",
    "FrontendBuilder",
    "LocalClientTemplate",
    "ReactRuntime",
    "RuntimeAdapter",
    "RuntimeRenderContext",
    "SupabaseClientTemplate",
    "SurveyBundle",
    "SurveyJSRuntime",
    "SurveySchema",
    "THEME_PRESETS",
    "UIConfig",
    "compile_css",
    "compile_expression",
    "compile_questionnaire",
    "expression_variables",
    "get_preset",
]
