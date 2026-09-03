from deadpath.extract import (
    strip_code_fences,
    blank_strikethrough,
    extract_candidates,
)


def test_strip_code_fences_preserves_line_count():
    text = "before\n```\nfenced `a/b.py`\n```\nafter"
    out = strip_code_fences(text)
    assert len(out.split("\n")) == len(text.split("\n"))
    assert "a/b.py" not in out
    assert "before" in out and "after" in out


def test_blank_strikethrough_removes_content_keeps_length():
    text = "see ~~`old/gone.py`~~ now"
    out = blank_strikethrough(text)
    assert "old/gone.py" not in out
    assert len(out) == len(text)


def test_extract_backtick_candidate_with_line_number():
    text = "line one\nsee `src/auth/session.ts` here\n"
    cands = extract_candidates(text, "README.md")
    assert len(cands) == 1
    assert cands[0].raw == "src/auth/session.ts"
    assert cands[0].line == 2
    assert cands[0].source == "README.md"
    assert cands[0].form == "backtick"


def test_extract_ignores_fenced_content():
    text = "```\n`src/a.py`\n```\n"
    assert extract_candidates(text, "README.md") == []


def test_extract_multiple_on_one_line():
    text = "`a/b.py` and `c/d.py`"
    cands = extract_candidates(text, "doc.md")
    assert [c.raw for c in cands] == ["a/b.py", "c/d.py"]


def test_wikilinks_only_in_vault_mode():
    text = "see [[Patterns/gmail-tracking]]"
    assert extract_candidates(text, "n.md") == []
    cands = extract_candidates(text, "n.md", vault_mode=True)
    assert len(cands) == 1
    assert cands[0].raw == "Patterns/gmail-tracking"
    assert cands[0].form == "wikilink"


def test_wikilink_alias_takes_target_not_alias():
    text = "see [[Patterns/gmail-tracking|the pattern]]"
    cands = extract_candidates(text, "n.md", vault_mode=True)
    assert cands[0].raw == "Patterns/gmail-tracking"


def test_unterminated_wikilink_produces_no_candidate():
    text = "see [[foo not closed"
    cands = extract_candidates(text, "n.md", vault_mode=True)
    assert cands == []


def test_wikilink_inside_backtick_span_not_double_counted():
    text = "add Obsidian-style `[[Note Name]]` links"
    cands = extract_candidates(text, "n.md", vault_mode=True)
    assert len(cands) == 1
    assert cands[0].form == "backtick"
    assert cands[0].raw == "[[Note Name]]"


def test_wikilink_escaped_pipe_in_table_cell_strips_backslash():
    # Obsidian requires \| (not bare |) to escape the alias delimiter when a
    # wikilink sits inside a markdown table cell, since a bare | would be
    # read as a column separator. The backslash belongs to the delimiter,
    # not the target -- it must not end up in the extracted path.
    text = r"[[Projects/King Vault/Overview\|King Vault]]"
    cands = extract_candidates(text, "n.md", vault_mode=True)
    assert len(cands) == 1
    assert cands[0].raw == "Projects/King Vault/Overview"


def test_wikilink_unescaped_pipe_still_works():
    text = "see [[Patterns/gmail-tracking|the pattern]]"
    cands = extract_candidates(text, "n.md", vault_mode=True)
    assert len(cands) == 1
    assert cands[0].raw == "Patterns/gmail-tracking"


def test_wikilink_plain_no_alias_still_works():
    text = "see [[Notes/Thing]]"
    cands = extract_candidates(text, "n.md", vault_mode=True)
    assert len(cands) == 1
    assert cands[0].raw == "Notes/Thing"


def test_wikilink_escaped_pipe_in_full_table_row():
    text = r"| [[Projects/King Vault/Overview\|King Vault]] | active |"
    cands = extract_candidates(text, "README.md", vault_mode=True)
    assert len(cands) == 1
    assert cands[0].raw == "Projects/King Vault/Overview"
    assert cands[0].form == "wikilink"
