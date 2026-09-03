"""Wellbeing Panel — the codebook shared by every wave.

`core_variables()` returns a *fresh* VariableMap each time, so each wave module
can register its own additions without touching the others.
"""

import siamang as sg
from siamang.core import MissingValue

WHO5 = {0: "At no time", 1: "Some of the time", 2: "Less than half the time",
        3: "More than half the time", 4: "Most of the time", 5: "All of the time"}

panel_id = sg.Variable("panel_id", scale="nominal", label="Panel member ID", dtype="str",
                       role="id")                      # role="id" → DUPLICATE_ID checks
age = sg.Variable("age", scale="ratio", label="Age (years)", dtype="int", valid_range=(18, 90))
gender = sg.Variable("gender", scale="nominal", label="Gender",
                     labels={1: "Woman", 2: "Man", 3: "Other", 99: "Prefer not to say"},
                     missing=(MissingValue(99, "Prefer not to say", kind="refusal"),))
employment = sg.Variable("employment", scale="nominal", label="Employment status",
                         labels={1: "Employed", 2: "Self-employed", 3: "Unemployed",
                                 4: "Retired", 5: "Other"})
remote_days = sg.Variable("remote_days", scale="ratio", label="Days per week working from home",
                          dtype="int", valid_range=(0, 7))


def who5(name: str, label: str) -> sg.Variable:
    return sg.Variable(name, scale="ordinal", label=label, labels=WHO5,
                       construct="wellbeing_who5", source="WHO-5 Well-Being Index")


wb_cheerful = who5("wb_cheerful", "I have felt cheerful and in good spirits")
wb_calm = who5("wb_calm", "I have felt calm and relaxed")
wb_active = who5("wb_active", "I have felt active and vigorous")
wb_rested = who5("wb_rested", "I woke up feeling fresh and rested")
wb_interest = who5("wb_interest", "My daily life has been filled with things that interest me")
WB_ITEMS = [wb_cheerful, wb_calm, wb_active, wb_rested, wb_interest]

life_sat = sg.Variable("life_sat", scale="interval", label="Life satisfaction (0-10)",
                       dtype="int", valid_range=(0, 10))


def core_variables() -> sg.VariableMap:
    vm = sg.VariableMap()
    vm.add_many([panel_id, age, gender, employment, remote_days, *WB_ITEMS, life_sat])
    return vm
