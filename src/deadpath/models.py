"""Shared dataclasses. Kept in one module so no other module imports another
just for a type, which keeps the pipeline stages independently testable."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    """A string that might be a path reference, before any judgement."""
    raw: str
    line: int
    source: str
    form: str  # "backtick" | "wikilink"


@dataclass(frozen=True)
class Finding:
    source: str
    line: int
    path: str
    reason: str


@dataclass(frozen=True)
class ProjectShape:
    """The facts about a project that the gate needs to judge candidates."""
    top_level_dirs: frozenset[str]
    extensions: frozenset[str]
