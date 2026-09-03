from deadpath.gate import build_project_shape, is_path_candidate
from deadpath.models import Candidate, ProjectShape


def shape(dirs=("src", "docs"), exts=(".py", ".ts", ".md")):
    return ProjectShape(
        top_level_dirs=frozenset(dirs),
        extensions=frozenset(exts),
    )


def cand(raw):
    return Candidate(raw=raw, line=1, source="d.md", form="backtick")


def test_extension_passes():
    assert is_path_candidate(cand("anything/here.py"), shape())


def test_dot_slash_prefix_passes():
    assert is_path_candidate(cand("./local-thing"), shape())


def test_parent_prefix_passes():
    assert is_path_candidate(cand("../sibling/thing"), shape())


def test_windows_drive_passes():
    assert is_path_candidate(cand(r"C:\Users\example\file"), shape())


def test_first_segment_matching_top_level_dir_passes():
    assert is_path_candidate(cand("src/nonexistent"), shape())


def test_prose_idioms_are_rejected():
    for idiom in ["and/or", "TCP/IP", "input/output", "he/she", "24/7", "N/A"]:
        assert not is_path_candidate(cand(idiom), shape()), idiom


def test_bare_word_rejected_even_if_it_names_a_directory():
    # "docs" alone is a word far more often than a reference.
    assert not is_path_candidate(cand("docs"), shape())


def test_unknown_first_segment_without_extension_rejected():
    assert not is_path_candidate(cand("unknown/thing"), shape())


def test_empty_rejected():
    assert not is_path_candidate(cand(""), shape())


def test_build_project_shape_finds_top_level_dirs(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / ".hidden").mkdir()
    (tmp_path / "file.txt").write_text("x", encoding="utf-8")
    built = build_project_shape(tmp_path)
    assert "src" in built.top_level_dirs
    assert ".hidden" not in built.top_level_dirs
    assert "file.txt" not in built.top_level_dirs


def test_build_project_shape_honors_extension_override(tmp_path):
    built = build_project_shape(tmp_path, extensions=[".zig"])
    assert built.extensions == frozenset({".zig"})


def test_build_project_shape_empty_extensions_list_is_not_default(tmp_path):
    built = build_project_shape(tmp_path, extensions=[])
    assert built.extensions == frozenset()


def test_extension_match_is_case_insensitive():
    assert is_path_candidate(cand("anything/HERE.PY"), shape())


def test_backslash_path_reaches_extension_rule():
    assert is_path_candidate(cand(r"src\file.py"), shape())


def test_backslash_path_reaches_top_level_dir_rule():
    assert is_path_candidate(cand(r"src\nonexistent"), shape())


def test_slash_commands_are_rejected():
    # /start, /design etc. are Claude Code slash commands, not paths: a
    # single segment with no extension after the leading slash.
    for slash_command in ["/start", "/design"]:
        assert not is_path_candidate(cand(slash_command), shape()), slash_command


def test_multi_segment_absolute_paths_pass():
    # Three-plus segments is treated as positive evidence on its own.
    # /etc/hosts (two segments, no extension) moved to
    # test_two_segment_leading_slash_without_extension_rejected below --
    # see the design-correction report for why.
    assert is_path_candidate(cand("/usr/bin/env"), shape())


def test_single_segment_absolute_path_with_extension_passes():
    # One segment, but it has a recognised extension -- positive evidence.
    assert is_path_candidate(cand("/README.md"), shape())


# --- Design correction: bare filenames, spaces, and bare endpoints ---------
# Corrects the false-positive rate measured against a real 1,000-file
# corpus: bare filenames were 75% of all findings, space-containing
# fragments 11%, and extension-less leading-slash endpoints 4%.


def test_bare_filename_with_extension_rejected():
    # A bare filename is a mention, not a resolvable reference -- it could
    # be anywhere on disk, most often in a different project entirely. This
    # was the single largest false-positive class in the vault survey.
    assert not is_path_candidate(cand("mixcheck.py"), shape())
    assert not is_path_candidate(cand("CLAUDE.md"), shape())
    assert not is_path_candidate(cand("king-tracker.jsx"), shape())


def test_filename_with_directory_component_still_passes():
    # The same filename, once it carries a directory component, is
    # unambiguous evidence again -- this is what the fix must NOT break.
    assert is_path_candidate(cand("src/mixcheck.py"), shape())


def test_command_line_with_spaces_rejected():
    # Real paths in this corpus never contain a space; command lines and
    # prose fragments do. Checked ahead of the dot-prefix rule so a
    # leading "./" doesn't short-circuit past it.
    assert not is_path_candidate(
        cand(
            "./scripts/install.sh --tool claude-code "
            "--agent video-optimization-specialist"
        ),
        shape(),
    )


def test_http_endpoint_rejected():
    # /sms/incoming is an HTTP route, not a filesystem path: leading slash,
    # two segments, no extension.
    assert not is_path_candidate(cand("/sms/incoming"), shape())


def test_two_segment_leading_slash_without_extension_rejected():
    # /etc/hosts is a genuine Unix path, but a two-segment, extension-less
    # leading-slash candidate is indistinguishable from an HTTP endpoint
    # like /sms/incoming or /api/v1/users -- the chosen tradeoff favors
    # precision and costs this class of legitimate short system paths.
    assert not is_path_candidate(cand("/etc/hosts"), shape())


def test_idiom_rejections_still_hold_after_directory_component_fix():
    for idiom in ["and/or", "TCP/IP", "input/output"]:
        assert not is_path_candidate(cand(idiom), shape()), idiom
