from deadpath.filters import is_excluded
from deadpath.models import Candidate


def cand(raw):
    return Candidate(raw=raw, line=1, source="d.md", form="backtick")


def test_template_placeholders_excluded():
    for raw in [
        "Daily Notes/MMDDYY.md",
        "logs/run-HHMM.log",
        "reports/YYYY/summary.md",
        "src/<component>/index.ts",
        "src/{name}/index.ts",
        "logs/*.log",
        "$HOME/.config/app.toml",
        "%APPDATA%/app/config.json",
        "people/[Name]/profile.md",
    ]:
        assert is_excluded(cand(raw), []), raw


def test_urls_excluded():
    for raw in ["https://example.com/a.md", "http://x.io/b", "www.example.com/c"]:
        assert is_excluded(cand(raw), []), raw


def test_allowlist_prefix_excluded():
    assert is_excluded(cand("staging/pending.md"), ["staging/"])


def test_allowlist_normalises_separators():
    assert is_excluded(cand(r"staging\pending.md"), ["staging/"])


def test_ordinary_path_not_excluded():
    assert not is_excluded(cand("src/auth/session.ts"), ["staging/"])


def test_dollar_lib_alias_not_excluded():
    # Regression: bare "$" token over-excluded any path containing a dollar
    # sign, including SvelteKit's $lib alias, which is not variable syntax.
    assert not is_excluded(cand("src/$lib/utils.ts"), [])


def test_shell_variable_still_excluded():
    assert is_excluded(cand("$HOME/.config/app.toml"), [])


def test_windows_variable_still_excluded():
    assert is_excluded(cand("%APPDATA%/app/config.json"), [])


def test_bare_percent_not_variable_syntax_not_excluded():
    # Regression: bare "%" token over-excluded any path with a percent
    # sign, including non-variable uses like a percentage in a filename.
    assert not is_excluded(cand("docs/100%-coverage.md"), [])


def test_leading_tilde_excluded():
    # Class A: home-directory paths describe the *reader's* machine, never
    # a file in the scanned tree. Evidence: lychee's
    # "~/.config/powershell/Microsoft.PowerShell_profile.ps1".
    assert is_excluded(cand("~/.config/app.toml"), [])


def test_non_leading_tilde_not_excluded():
    # A "~" elsewhere in a path is not disqualifying -- only a leading one.
    assert not is_excluded(cand("src/~backup/file.py"), [])


def test_placeholder_segment_path_to_excluded():
    # Class B: illustrative placeholder paths. Evidence: remark-validate-links'
    # "/Users/tilde/path/to/repo/readme.md#some-heading".
    assert is_excluded(cand("/Users/tilde/path/to/repo/readme.md"), [])


def test_placeholder_segment_your_excluded():
    assert is_excluded(cand("docs/your/thing.md"), [])


def test_placeholder_segment_substring_not_excluded():
    # Whole-segment matching only: "pathfinder" starts with "path" but is
    # not the segment "path", and "examples.md" contains "example" as a
    # substring but is not the segment "example".
    assert not is_excluded(cand("src/pathfinder.py"), [])
    assert not is_excluded(cand("docs/examples.md"), [])


def test_ordinary_path_still_not_excluded_with_new_rules():
    assert not is_excluded(cand("src/auth/session.ts"), [])


def test_dollar_prefixed_mixed_case_path_not_excluded():
    # Regression: VARIABLE_RE had no trailing boundary, so it matched a
    # minimal uppercase prefix inside an otherwise mixed-case token --
    # "$Path/thing.ts" matched on "$P" even though the whole token isn't
    # the conventional ALL_CAPS variable-name shape the comment describes.
    assert not is_excluded(cand("$Path/thing.ts"), [])
    assert not is_excluded(cand("$Env/foo.py"), [])


def test_home_variable_still_excluded_with_tightened_regex():
    # Must not regress the genuine ALL_CAPS case this regex exists for.
    assert is_excluded(cand("$HOME/.config/app.toml"), [])
