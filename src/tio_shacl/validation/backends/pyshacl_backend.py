"""pyshacl backend — calls the :pypi:`pyshacl` Python library directly."""

from __future__ import annotations

from rdflib import Graph, Namespace

import pyshacl

from ..runner import ValidationResult, Violation

SH = Namespace("http://www.w3.org/ns/shacl#")


def _extract_violations(report_graph: Graph | None) -> list[Violation]:
    if report_graph is None:
        return []

    out: list[Violation] = []
    for report in report_graph.subjects(SH.conforms, None):
        for v in report_graph.objects(report, SH.result):
            out.append(
                Violation(
                    focus_node=_str_or_none(report_graph.value(v, SH.focusNode)),
                    result_path=_str_or_none(report_graph.value(v, SH.resultPath)),
                    source_shape=_str_or_none(report_graph.value(v, SH.sourceShape)),
                    source_constraint_component=_str_or_none(
                        report_graph.value(v, SH.sourceConstraintComponent)
                    ),
                    severity=_str_or_none(report_graph.value(v, SH.resultSeverity)),
                    value=_str_or_none(report_graph.value(v, SH.value)),
                    message=_str_or_none(report_graph.value(v, SH.resultMessage)),
                )
            )
    return out


def _str_or_none(x: object) -> str | None:
    return str(x) if x is not None else None


class PyshaclBackend:
    """Default backend. No external dependencies beyond the Python package."""

    name = "pyshacl"

    def validate(self, data: Graph, shapes: Graph) -> ValidationResult:
        conforms, report_graph, report_text = pyshacl.validate(
            data_graph=data,
            shacl_graph=shapes,
            advanced=True,
            inference=None,
            meta_shacl=False,
            debug=False,
        )
        return ValidationResult(
            conforms=bool(conforms),
            violations=_extract_violations(report_graph),
            report_text=report_text or "",
        )
