import json

from deadpath.models import Finding
from deadpath.report import FORMATTERS, format_github, format_human, format_json

FINDINGS = [
    Finding(source="README.md", line=12, path="src/gone.py", reason="path does not exist"),
]


def test_human_includes_source_line_and_path():
    out = format_human(FINDINGS)
    assert "README.md:12" in out
    assert "src/gone.py" in out


def test_human_empty_is_explicit():
    out = format_human([])
    assert "no dead paths" in out.lower()


def test_json_round_trips():
    parsed = json.loads(format_json(FINDINGS))
    assert parsed[0]["source"] == "README.md"
    assert parsed[0]["line"] == 12
    assert parsed[0]["path"] == "src/gone.py"


def test_json_empty_is_empty_list():
    assert json.loads(format_json([])) == []


def test_github_annotation_format():
    out = format_github(FINDINGS)
    assert out.startswith("::error file=README.md,line=12::")


def test_formatters_registry_has_all_three():
    assert set(FORMATTERS) == {"human", "json", "github"}


def test_github_annotation_escapes_comma_in_source():
    findings = [
        Finding(
            source="Meeting notes, Jan 2026.md",
            line=3,
            path="src/gone.py",
            reason="path does not exist",
        )
    ]
    out = format_github(findings)
    assert "Meeting notes%2C Jan 2026.md" in out
    # props section is everything between the first "::" and the second "::"
    props, _, _ = out.partition("::")[2].partition("::")
    assert "file=Meeting notes%2C Jan 2026.md" in props
    assert "line=3" in props
    # unescaped comma must not appear in the property section (it would break parsing)
    assert "Meeting notes, Jan 2026.md" not in props


def test_github_annotation_escapes_percent_before_comma_no_double_escape():
    findings = [
        Finding(
            source="100%, done.md",
            line=1,
            path="src/gone.py",
            reason="path does not exist",
        )
    ]
    out = format_github(findings)
    assert "100%25%2C done.md" in out
    assert "%252C" not in out


def test_github_annotation_escapes_newline_in_reason():
    findings = [
        Finding(
            source="README.md",
            line=12,
            path="src/gone.py",
            reason="line one\nline two",
        )
    ]
    out = format_github(findings)
    assert "line one%0Aline two" in out
    assert "\n" not in out.split("::", 2)[2]


def test_github_annotation_plain_case_unchanged():
    out = format_github(FINDINGS)
    assert out == "::error file=README.md,line=12::src/gone.py -- path does not exist"
