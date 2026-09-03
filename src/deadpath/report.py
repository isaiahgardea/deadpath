"""Findings -> output. Three formats: a human read, JSON for tooling, and
GitHub Actions annotations so CI shows findings inline on the diff."""
import json
from collections.abc import Callable
from dataclasses import asdict

from .models import Finding


def format_human(findings: list[Finding]) -> str:
    if not findings:
        return "deadpath: no dead paths found."
    lines = [f"{f.source}:{f.line}  {f.path}  -- {f.reason}" for f in findings]
    plural = "" if len(findings) == 1 else "s"
    lines.append("")
    lines.append(f"{len(findings)} dead path{plural} found.")
    return "\n".join(lines)


def format_json(findings: list[Finding]) -> str:
    return json.dumps([asdict(f) for f in findings], indent=2)


def _escape_property(value: str) -> str:
    """Escape a GitHub workflow-command property value (e.g. file=, line=).

    % must be escaped first, or a later replacement's introduced % gets
    double-escaped (e.g. ',' -> '%2C' then '%' -> '%25' would corrupt it
    into '%252C').
    """
    value = value.replace("%", "%25")
    value = value.replace("\r", "%0D")
    value = value.replace("\n", "%0A")
    value = value.replace(":", "%3A")
    value = value.replace(",", "%2C")
    return value


def _escape_message(value: str) -> str:
    """Escape a GitHub workflow-command message value (text after ::)."""
    value = value.replace("%", "%25")
    value = value.replace("\r", "%0D")
    value = value.replace("\n", "%0A")
    return value


def format_github(findings: list[Finding]) -> str:
    return "\n".join(
        f"::error file={_escape_property(f.source)},line={_escape_property(str(f.line))}"
        f"::{_escape_message(f.path)} -- {_escape_message(f.reason)}"
        for f in findings
    )


FORMATTERS: dict[str, Callable[[list[Finding]], str]] = {
    "human": format_human,
    "json": format_json,
    "github": format_github,
}
