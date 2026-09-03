"""Markdown -> candidate path references.

Everything here is pure string work. Two preprocessing passes run before
extraction, and both MUST preserve line counts so reported line numbers stay
correct: fenced blocks become blank lines, strikethrough spans become spaces.

Only two forms are read. Markdown link targets are deliberately NOT read --
remark-validate-links already does that job well.
"""
import re

from .models import Candidate

FENCE_RE = re.compile(r"^\s*(```|~~~)")
STRIKE_RE = re.compile(r"~~(.+?)~~")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
# [[target]] or [[target|alias]] -- the target is everything before any pipe.
# Requires a proper closing ]] -- an unterminated [[foo is not a candidate.
# Obsidian also requires [[target\|alias]] (backslash-escaped pipe) when a
# wikilink sits inside a markdown table cell, since a bare | would otherwise
# be read as a column separator. The capture group is non-greedy and the
# `\\?` consumes that optional escaping backslash separately, so it lands
# next to the alias delimiter rather than becoming part of the target --
# do NOT "simplify" this back to a greedy `[^\]\n|]+`, that reintroduces a
# trailing backslash into every escaped-pipe target.
WIKILINK_RE = re.compile(r"\[\[([^\]\n|]+?)\\?(?:\|[^\]\n]*)?\]\]")


def strip_code_fences(text: str) -> str:
    """Replace fenced-block content with empty lines, preserving line count.

    Fenced code is example material, not an assertion about the repo -- it is
    the single largest source of false positives if left in.
    """
    out: list[str] = []
    marker: str | None = None
    for line in text.split("\n"):
        match = FENCE_RE.match(line)
        if match:
            found = match.group(1)
            if marker is None:
                marker = found
            elif found == marker:
                marker = None
            out.append("")
            continue
        out.append("" if marker is not None else line)
    return "\n".join(out)


def blank_strikethrough(text: str) -> str:
    """Replace ~~struck~~ spans with spaces of equal length.

    Strikethrough already means "superseded" by convention, so a path inside
    it is expected to be gone.
    """
    return STRIKE_RE.sub(lambda m: " " * len(m.group(0)), text)


def extract_candidates(
    text: str, source: str, vault_mode: bool = False
) -> list[Candidate]:
    cleaned = blank_strikethrough(strip_code_fences(text))
    candidates: list[Candidate] = []
    for lineno, line in enumerate(cleaned.split("\n"), start=1):
        backtick_matches = list(BACKTICK_RE.finditer(line))
        for match in backtick_matches:
            raw = match.group(1).strip()
            if raw:
                candidates.append(
                    Candidate(raw=raw, line=lineno, source=source, form="backtick")
                )
        if vault_mode:
            # Mask backtick spans before scanning for wikilinks, so text
            # already claimed as inline code (e.g. a doc showing `[[x]]`
            # syntax) doesn't also produce a spurious wikilink candidate.
            # Masking with spaces preserves line length/positions, same
            # approach as blank_strikethrough.
            masked = line
            for match in backtick_matches:
                start, end = match.span()
                masked = masked[:start] + " " * (end - start) + masked[end:]
            for match in WIKILINK_RE.finditer(masked):
                raw = match.group(1).strip()
                if raw:
                    candidates.append(
                        Candidate(raw=raw, line=lineno, source=source, form="wikilink")
                    )
    return candidates
