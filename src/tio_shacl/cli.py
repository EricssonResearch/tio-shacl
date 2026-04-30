"""Command-line interface for tio-shacl.

Subcommands:

- ``tio-shacl validate <file>``   — validate a single RDF file
- ``tio-shacl test [-s <suite>]`` — run one or all test suites
- ``tio-shacl report [-o <out>]`` — emit a report in ``markdown`` or ``json``
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

import tio_shacl

from .validation import TestOrchestrator, ValidationRunner
from .validation.orchestrator import SuiteReport

# -----------------------------------------------------------------------------
# Global results cache (populated by ``test``, consumed by ``report``)
# -----------------------------------------------------------------------------

# We store reports in a process-scoped list so that ``report`` called right
# after ``test`` (e.g. in a Makefile or CI pipeline) can use them. A separate
# on-disk cache is intentionally out of scope for the public release.
_LAST_REPORTS: list[SuiteReport] = []


# -----------------------------------------------------------------------------
# Report formatters
# -----------------------------------------------------------------------------


def _format_markdown(reports: list[SuiteReport]) -> str:
    lines: list[str] = ["# TIO-SHACL Validation Report", ""]
    total_passed = sum(r.passed for r in reports)
    total = sum(r.total for r in reports)
    lines.append(f"**Overall:** {total_passed}/{total} cases passed across {len(reports)} suites.")
    lines.append("")
    lines.append("| Suite | Passed | Failed | Total |")
    lines.append("|-------|-------:|-------:|------:|")
    for r in reports:
        lines.append(f"| {r.suite_name} | {r.passed} | {r.failed} | {r.total} |")
    lines.append("")

    # Detail per failed case
    any_failures = any(r.failed for r in reports)
    if any_failures:
        lines.append("## Failures")
        lines.append("")
        for r in reports:
            failed = [o for o in r.outcomes if not o.passed]
            if not failed:
                continue
            lines.append(f"### {r.suite_name}")
            lines.append("")
            for o in failed:
                status = "should conform" if o.expected_conforms else "should violate"
                lines.append(f"- `{o.path.name}` — {status}, got conforms={o.actual_conforms}")
            lines.append("")
    return "\n".join(lines)


def _format_json(reports: list[SuiteReport]) -> str:
    return json.dumps(
        {
            "tio_spec_version": tio_shacl.__tio_spec_version__,
            "tio_shacl_version": tio_shacl.__version__,
            "summary": {
                "suites": len(reports),
                "total": sum(r.total for r in reports),
                "passed": sum(r.passed for r in reports),
                "failed": sum(r.failed for r in reports),
            },
            "suites": [
                {
                    "name": r.suite_name,
                    "passed": r.passed,
                    "failed": r.failed,
                    "total": r.total,
                    "cases": [
                        {
                            "path": str(o.path),
                            "expected_conforms": o.expected_conforms,
                            "actual_conforms": o.actual_conforms,
                            "violations": o.violations,
                            "passed": o.passed,
                        }
                        for o in r.outcomes
                    ],
                }
                for r in reports
            ],
        },
        indent=2,
    )


# -----------------------------------------------------------------------------
# Click CLI
# -----------------------------------------------------------------------------


@click.group(
    help=(
        "TIO-SHACL: validate RDF intents against the TM Forum Intent Ontology "
        "SHACL shapes."
    ),
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(
    version=tio_shacl.__version__,
    prog_name="tio-shacl",
    message=f"%(prog)s %(version)s (TIO spec {tio_shacl.__tio_spec_version__})",
)
def main() -> None:
    """Root command."""


# ------------------------------ validate -------------------------------------


@main.command("validate", help="Validate a single RDF file.")
@click.argument(
    "path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
)
@click.option(
    "--ontology-dir",
    "-O",
    "ontology_dirs",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help=(
        "Additional directory whose .ttl files are loaded into the ontology "
        "graph. Repeat for multiple directories, e.g. one for TIO and one "
        "for a custom catalogue. Overrides TIO_ONTOLOGY_DIR when given."
    ),
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Print the full SHACL report for each violation.",
)
def validate_cmd(path: Path, ontology_dirs: tuple[Path, ...], verbose: bool) -> None:
    runner = ValidationRunner(
        ontology_dirs=list(ontology_dirs) if ontology_dirs else None,
    )
    result = runner.validate_file(path)

    if result.conforms:
        click.echo(f"✓ {path}: conforms")
        return

    click.echo(f"✗ {path}: {len(result.violations)} violation(s)")
    for i, v in enumerate(result.violations, 1):
        msg = v.message or "(no message)"
        focus = v.focus_node or "?"
        click.echo(f"  [{i}] {focus} — {msg}")

    if verbose:
        click.echo("")
        click.echo(result.report_text)

    sys.exit(1)


# -------------------------------- test ---------------------------------------


@main.command("test", help="Run validation test suites.")
@click.option(
    "--suite",
    "-s",
    default=None,
    help="Limit to a single test suite (module name).",
)
@click.option(
    "--workers",
    "-w",
    default=1,
    show_default=True,
    type=int,
    help="Number of parallel workers.",
)
def test_cmd(suite: str | None, workers: int) -> None:
    global _LAST_REPORTS
    orch = TestOrchestrator(workers=workers)

    if suite:
        suites = [s for s in orch.discover_test_suites() if s.name == suite]
        if not suites:
            click.echo(f"error: no suite named {suite!r}", err=True)
            sys.exit(2)
        reports = [orch.run_test_suite(suites[0])]
    else:
        reports = orch.run_all()

    _LAST_REPORTS = reports

    for r in reports:
        marker = "✓" if r.failed == 0 else "✗"
        click.echo(f"{marker} {r.suite_name}: {r.passed}/{r.total} passed")

    total = sum(r.total for r in reports)
    passed = sum(r.passed for r in reports)
    failed = total - passed
    click.echo("")
    click.echo(f"Summary: {passed}/{total} passed across {len(reports)} suite(s)")
    if failed:
        sys.exit(1)


# ------------------------------- report --------------------------------------


@main.command("report", help="Emit a report from the most recent 'test' run.")
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    default="markdown",
    show_default=True,
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output file. Defaults to stdout.",
)
def report_cmd(fmt: str, output: Path | None) -> None:
    if not _LAST_REPORTS:
        click.echo(
            "error: no report data — run 'tio-shacl test' first in the same process",
            err=True,
        )
        sys.exit(2)

    if fmt == "json":
        text = _format_json(_LAST_REPORTS)
    else:
        text = _format_markdown(_LAST_REPORTS)

    if output:
        output.write_text(text)
        click.echo(f"wrote {output}")
    else:
        click.echo(text)


if __name__ == "__main__":  # pragma: no cover
    main()
