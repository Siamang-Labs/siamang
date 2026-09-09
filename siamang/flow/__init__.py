"""siamang.flow — analysis flows: a node graph that runs and that becomes a script.

    >>> from siamang.flow import FlowRunner, generate_flow, default_registry
    >>> result = FlowRunner(flow, questionnaire=survey).run(sources={"src": data})
    >>> code = generate_flow(flow, questionnaire_document)

Nodes come from a registry of YAML specifications (``siamang/flow/nodes``);
each carries the Python template that both the runner and the generator use.
"""

from siamang.flow import live
from siamang.flow.codegen import FLOW_CODEGEN_VERSION, generate_flow
from siamang.flow.document import (
    FLOW_SCHEMA_VERSION,
    FlowError,
    FlowGraph,
    FlowIssue,
    check_flow,
    node_order,
    resolve_flow,
    validate_flow,
)
from siamang.flow.registry import (
    NodeSpec,
    ParamSpec,
    PortSpec,
    Registry,
    RegistryError,
    default_registry,
)
from siamang.flow.runner import FlowResult, FlowRunner, NodeRun
from siamang.flow.template import render_condition, render_node

__all__ = [
    "FLOW_CODEGEN_VERSION",
    "FLOW_SCHEMA_VERSION",
    "FlowError",
    "FlowGraph",
    "FlowIssue",
    "FlowResult",
    "FlowRunner",
    "NodeRun",
    "NodeSpec",
    "ParamSpec",
    "PortSpec",
    "Registry",
    "RegistryError",
    "check_flow",
    "default_registry",
    "generate_flow",
    "live",
    "node_order",
    "render_condition",
    "render_node",
    "resolve_flow",
    "validate_flow",
]
