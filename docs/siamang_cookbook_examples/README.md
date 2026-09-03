# Siamang Cookbook — example studies

Four complete studies built with **siamang 0.6.0**, each in its own directory with the
survey as Python modules, tests, scripts and a Jupyter notebook that imports those modules
and walks the pipeline with saved outputs.

| Directory | Study | Modules | Notebook |
| :--- | :--- | :--- | :--- |
| `civic_trust/` | Population survey with screening, quotas, raking weights | `codebook.py`, `survey.py`, `helpers.py`, `run_local.py`, `analysis.py`, `test_survey.py` | `civic_trust.ipynb` |
| `customer_pulse/` | NPS / satisfaction with branding and an offline bundle | `survey.py`, `build_bundle.py`, `analysis.py` | `customer_pulse.ipynb` |
| `wellbeing_panel/` | Multi-wave panel with codebook round trips | `codebook.py`, `wave1.py`, `wave2.py`, `helpers.py`, `analysis_panel.py` | `wellbeing_panel.ipynb` |
| `framing_experiment/` | Between-subjects A/B experiment with randomization | `survey.py`, `analysis.py` | `framing_experiment.ipynb` |
| `recipes/` | Short engine and Cloud recipes, executed | — | `engine_and_cloud_recipes.ipynb` |

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

Notebooks add their own directory to `sys.path` in the first cell, so they run from any
launcher. All numbers come from `survey.simulate()` and are meaningless by construction;
the point is that every table is labelled and every test is chosen for you.
