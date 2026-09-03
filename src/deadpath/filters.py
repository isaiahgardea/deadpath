"""Exclusions applied after the gate.

Everything here errs toward excluding. A false positive costs far more than a
missed finding: it is what makes someone uninstall the tool.
"""
import re

from .models import Candidate

# Tokens that mean "this was never meant to exist literally".
PLACEHOLDER_TOKENS = (
    "MMDDYY", "HHMM", "YYYY",
    "<", ">", "{", "}", "[", "]", "*",
)

# Shell and Windows environment-variable syntax: $VAR, ${VAR}, %VAR%.
# Deliberately restricted to the conventional ALL_CAPS variable-name shape
# (env vars are $HOME, $PATH, %APPDATA%, not lowercase) so this doesn't
# reintroduce the bare "$"/"%" over-exclusion — a lowercase path segment
# like SvelteKit's "$lib" or a plain "%" in "100%-coverage.md" must not
# match. "${" is covered again by the bare "{" token above; the explicit
# alternative here is belt-and-braces for "$VAR" without braces.
# The `(?![a-z])` guard on the $VAR form is required, not decorative:
# without it the pattern is only anchored on its left edge, so it happily
# matches a minimal ALL_CAPS *prefix* of an otherwise mixed-case token --
# "$Path/x.ts" matched on "$P", "$Env/foo.py" matched on "$E". The whole
# variable-name token must be uppercase, not just its first run of
# characters. The %VAR% form doesn't need the same guard: it's already
# closed on both ends by a literal "%", so a mixed-case token like
# "%Path%" can't match it in the first place.
VARIABLE_RE = re.compile(r"\$[A-Z_][A-Z0-9_]*(?![a-z])|\$\{|%[A-Z_][A-Z0-9_]*%")

URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://|^www\.")

# Path segments that mean "this is an illustrative placeholder, not a real
# path in this tree". Matched whole-segment, case-insensitively, so a real
# word that merely starts with or contains one of these ("src/pathfinder.py",
# "docs/examples.md") is never caught -- only an exact segment match is.
# Evidence (four-corpora validation pass): remark-validate-links' own README
# uses "/Users/tilde/path/to/repo/readme.md#some-heading" as a worked example.
# "your"/"my"/"example"/"foo"/"bar" are the same idiom in the wild.
#
# "path" and "to" are deliberately NOT single-entry placeholders here: each
# is a common, real directory/package name on its own (Go's "path" and
# "path/filepath" packages, a migration "to/" directory, etc). Only the
# adjacent two-segment idiom "path/to" -- the literal evidence above -- is
# disqualifying, checked separately below.
PLACEHOLDER_SEGMENTS = frozenset({"your", "my", "example", "foo", "bar"})
PLACEHOLDER_SEGMENT_PAIR = ("path", "to")


def is_excluded(candidate: Candidate, allowlist_prefixes: list[str]) -> bool:
    raw = candidate.raw

    # Class A: home-directory / tilde paths describe the *reader's* machine,
    # never a file in the scanned tree. Only a leading "~" is disqualifying --
    # a "~" elsewhere in a path (e.g. "src/~backup/file.py") is not. Evidence:
    # lychee's "~/.config/powershell/Microsoft.PowerShell_profile.ps1".
    if raw.startswith("~"):
        return True

    if any(token in raw for token in PLACEHOLDER_TOKENS):
        return True

    if VARIABLE_RE.search(raw):
        return True

    if URL_RE.search(raw):
        return True

    normalised = raw.replace("\\", "/")

    # Class B: illustrative placeholder paths, matched whole-segment so
    # "path/to" excludes but "pathfinder" and "examples.md" do not.
    segment_list = [s.lower() for s in normalised.split("/") if s]
    if set(segment_list) & PLACEHOLDER_SEGMENTS:
        return True
    if any(
        (segment_list[i], segment_list[i + 1]) == PLACEHOLDER_SEGMENT_PAIR
        for i in range(len(segment_list) - 1)
    ):
        return True

    for prefix in allowlist_prefixes:
        if normalised.startswith(prefix.replace("\\", "/")):
            return True

    return False
