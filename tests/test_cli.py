import json
import os
from pathlib import Path

from deadpath.cli import iter_docs, main
from deadpath.config import Config


def make_project(tmp_path, doc_text, extra_dirs=("src",)):
    for name in extra_dirs:
        (tmp_path / name).mkdir(exist_ok=True)
    (tmp_path / "README.md").write_text(doc_text, encoding="utf-8")
    return tmp_path


def test_exit_zero_when_clean(tmp_path, capsys):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x", encoding="utf-8")
    make_project(tmp_path, "see `src/a.py`")
    assert main(["check", str(tmp_path)]) == 0
    assert "no dead paths" in capsys.readouterr().out.lower()


def test_exit_one_when_dead_path_found(tmp_path, capsys):
    make_project(tmp_path, "see `src/gone.py`")
    assert main(["check", str(tmp_path)]) == 1
    assert "src/gone.py" in capsys.readouterr().out


def test_json_format(tmp_path, capsys):
    make_project(tmp_path, "see `src/gone.py`")
    main(["check", str(tmp_path), "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["path"] == "src/gone.py"
    assert parsed[0]["source"] == "README.md"


def test_exclude_glob_skips_file(tmp_path, capsys):
    (tmp_path / "src").mkdir()
    (tmp_path / "CHANGELOG.md").write_text("removed `src/gone.py`", encoding="utf-8")
    (tmp_path / ".deadpath.toml").write_text(
        '[deadpath]\nexclude_globs = ["CHANGELOG.md"]\n', encoding="utf-8"
    )
    assert main(["check", str(tmp_path)]) == 0


def test_prose_idiom_not_reported(tmp_path, capsys):
    make_project(tmp_path, "use `and/or` carefully")
    assert main(["check", str(tmp_path)]) == 0


def test_vault_flag_enables_wikilinks(tmp_path, capsys):
    (tmp_path / "Patterns").mkdir()
    (tmp_path / "note.md").write_text("see [[Patterns/missing]]", encoding="utf-8")
    assert main(["check", str(tmp_path)]) == 0
    assert main(["check", str(tmp_path), "--vault"]) == 1


def test_nonexistent_path_exits_two(tmp_path, capsys):
    bad_path = tmp_path / "typo" / "dir"
    assert main(["check", str(bad_path)]) == 2
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
    assert captured.out.strip() == ""


def test_malformed_config_exits_two_no_traceback(tmp_path, capsys):
    (tmp_path / ".deadpath.toml").write_text("not valid toml [[[", encoding="utf-8")
    assert main(["check", str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
    assert "Traceback" not in captured.err
    assert "Traceback" not in captured.out


def test_foreign_absolute_path_produces_no_finding(tmp_path, capsys):
    # End-to-end regression for Finding 1: gate and resolve were each
    # tested in isolation but never together, which is the gap that let
    # the platform-dependent absolute-path bug through. A backticked
    # absolute path foreign to the platform actually running this suite
    # must produce no finding and exit 0 -- not a false positive from
    # resolve misjudging it as relative.
    (tmp_path / "src").mkdir()
    if os.name == "nt":
        foreign = "/usr/bin/env"
    else:
        foreign = r"C:\Windows\System32\drivers\etc\hosts"
    (tmp_path / "README.md").write_text(
        f"Run it with the `{foreign}` interpreter shebang.\n", encoding="utf-8"
    )
    assert main(["check", str(tmp_path)]) == 0
    assert "no dead paths" in capsys.readouterr().out.lower()


def test_iter_docs_deduplicates_overlapping_scan_globs(tmp_path):
    # Two scan_globs patterns can both match the same file ("docs/*.md" and
    # "docs/**/*.md" both match "docs/a.md") -- the `seen` set exists so it
    # isn't yielded (and later checked) twice. No direct coverage before.
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("x", encoding="utf-8")
    config = Config(scan_globs=["docs/*.md", "docs/**/*.md"])
    docs = list(iter_docs(tmp_path, config))
    assert docs == [tmp_path / "docs" / "a.md"]


def test_vault_mode_via_toml_alone_works_without_vault_flag(tmp_path, capsys):
    # vault_mode set only via .deadpath.toml (no --vault flag) must work
    # end-to-end through check() -- mirrors test_vault_flag_enables_wikilinks
    # but exercises the config-only path instead of the CLI flag.
    (tmp_path / "Patterns").mkdir()
    (tmp_path / "note.md").write_text("see [[Patterns/missing]]", encoding="utf-8")
    (tmp_path / ".deadpath.toml").write_text(
        "[deadpath]\nvault_mode = true\n", encoding="utf-8"
    )
    assert main(["check", str(tmp_path)]) == 1
    assert "Patterns/missing" in capsys.readouterr().out


def test_unreadable_file_is_skipped_with_warning(tmp_path, capsys, monkeypatch):
    make_project(tmp_path, "see `src/a.py`")
    (tmp_path / "src" / "a.py").write_text("x", encoding="utf-8")
    bad_doc = tmp_path / "README.md"

    original_read_text = Path.read_text

    def flaky_read_text(self, *args, **kwargs):
        if self == bad_doc:
            raise PermissionError("permission denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", flaky_read_text)

    assert main(["check", str(tmp_path)]) == 0
    captured = capsys.readouterr()
    assert "README.md" in captured.err
    assert "no dead paths" in captured.out.lower()
