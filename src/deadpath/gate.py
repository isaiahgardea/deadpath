"""Positive-evidence gate: is this candidate actually a path?

The burden of proof is deliberately inverted. Rather than flagging anything
not provably prose, a candidate must show positive evidence it is a path.
That single decision is what keeps `and/or`, `TCP/IP` and "the auth/session
boundary" out of the results without maintaining an endless idiom blocklist.
"""
import re
from pathlib import Path, PurePosixPath

from .models import Candidate, ProjectShape

DEFAULT_EXTENSIONS = frozenset(
    {
        ".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go", ".java", ".rb",
        ".c", ".h", ".cpp", ".hpp", ".cs", ".swift", ".kt", ".zig", ".lua",
        ".sh", ".bash", ".ps1", ".bat",
        ".md", ".txt", ".rst", ".adoc",
        ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".env",
        ".html", ".css", ".scss", ".sql", ".xml", ".csv",
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf",
    }
)

DOT_PATH_PREFIXES = ("./", "../")
DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")


def build_project_shape(
    root: Path, extensions: list[str] | None = None
) -> ProjectShape:
    """Top-level directories act as a dictionary of what a path can start with."""
    top = frozenset(
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    )
    exts = frozenset(e.lower() for e in extensions) if extensions is not None else DEFAULT_EXTENSIONS
    return ProjectShape(top_level_dirs=top, extensions=exts)


def is_path_candidate(candidate: Candidate, shape: ProjectShape) -> bool:
    raw = candidate.raw
    if not raw:
        return False

    # Exclusion (design correction): a real path in this corpus never
    # contains a space -- a candidate that does is a shell command line or
    # a prose fragment (e.g. "./scripts/install.sh --tool claude-code
    # --agent video-optimization-specialist"), 11% of the false positives
    # measured against the real vault survey. Checked first so it isn't
    # short-circuited by the dot-prefix rule below.
    if " " in raw:
        return False

    # Rule 2: an explicit path-like prefix is unambiguous on its own --
    # except a bare leading "/", handled separately below.
    if raw.startswith(DOT_PATH_PREFIXES) or DRIVE_RE.match(raw):
        return True

    normalised = raw.replace("\\", "/")

    if raw.startswith("/"):
        # A leading "/" alone is not sufficient evidence: Claude Code slash
        # commands (/start, /design, ...) and HTTP endpoints (/sms/incoming,
        # /api/v1/users -- 4% of the vault survey's false positives) share
        # the exact same shape as a real absolute path. Positive evidence is
        # either a recognised extension anywhere in the path, or three-plus
        # segments. This design correction knowingly costs a small class of
        # legitimate two-segment Unix paths with no extension (e.g.
        # /etc/hosts) -- accepted as the precision/coverage tradeoff this
        # tool deliberately favors (see module docstring).
        segments = [s for s in normalised.split("/") if s]
        if PurePosixPath(normalised).suffix.lower() in shape.extensions:
            return True
        return len(segments) >= 3

    # Design correction: a candidate with no directory component anywhere
    # is a bare filename, not a resolvable reference -- it could be
    # anywhere on disk, most often in a different project entirely. The
    # original survey this tool is built on found bare filenames with a
    # recognised extension were 75% of all false positives ("AI Scout.md"
    # is not checkable without guessing a location). An extension is
    # therefore no longer sufficient on its own -- Rule 1 below only fires
    # once a directory component already exists. Do not restore a bare
    # extension check here; that is exactly the behavior this correction
    # reverses.
    if "/" not in normalised:
        return False

    # Rule 1: a recognised file extension (reachable only once a directory
    # component is already established above).
    if PurePosixPath(normalised).suffix.lower() in shape.extensions:
        return True

    # Rule 3: first segment names a real top-level directory. A separator is
    # required -- a bare word like "docs" is prose far more often than a
    # reference, and matching it would be a large false-positive source.
    first = normalised.split("/", 1)[0]
    if first in shape.top_level_dirs:
        return True

    return False
