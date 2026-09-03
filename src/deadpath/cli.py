"""Pipeline orchestration and command-line entry point.

The pipeline is deliberately linear and short-circuiting: extract -> gate ->
filter -> resolve. A candidate that fails any earlier stage never reaches the
filesystem, which keeps the expensive stage the smallest.
"""
import argparse
import sys
from collections.abc import Iterator
from fnmatch import fnmatch
from pathlib import Path

from .config import Config, ConfigError, load_config
from .extract import extract_candidates
from .filters import is_excluded
from .gate import build_project_shape, is_path_candidate
from .models import Finding
from .report import FORMATTERS
from .resolve import resolve_candidate


def iter_docs(root: Path, config: Config) -> Iterator[Path]:
    # Note on dialects: scan_globs use pathlib.Path.glob semantics, where `*`
    # does not cross a `/` and `**` does. exclude_globs are matched with
    # fnmatch.fnmatch instead, whose `*` DOES cross `/` -- so an exclude of
    # "docs/*.md" also excludes "docs/sub/x.md". This mismatch is known and
    # deliberate, not a bug; changing it is a separate semantic decision.
    seen: set[str] = set()
    for pattern in config.scan_globs:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if rel in seen:
                continue
            if any(
                fnmatch(rel, exclude_pattern)
                for exclude_pattern in config.exclude_globs
            ):
                continue
            seen.add(rel)
            yield path


def check(root: Path, config: Config) -> list[Finding]:
    shape = build_project_shape(root, config.extensions)
    vault_root = root if config.vault_mode else None
    findings: list[Finding] = []

    for doc in iter_docs(root, config):
        try:
            text = doc.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(f"warning: could not read {doc}: {exc}", file=sys.stderr)
            continue
        source = doc.relative_to(root).as_posix()
        for candidate in extract_candidates(text, source, config.vault_mode):
            if not is_path_candidate(candidate, shape):
                continue
            if is_excluded(candidate, config.allowlist_prefixes):
                continue
            if resolve_candidate(candidate, root, doc, vault_root):
                continue
            findings.append(
                Finding(
                    source=source,
                    line=candidate.line,
                    path=candidate.raw,
                    reason="path does not exist",
                )
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="deadpath",
        description="Find path references in your docs that no longer exist.",
    )
    parser.add_argument("command", choices=["check"])
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument(
        "--format", choices=sorted(FORMATTERS), default="human"
    )
    parser.add_argument(
        "--vault",
        action="store_true",
        help="Obsidian vault mode: resolve from the vault root and read wikilinks.",
    )
    args = parser.parse_args(argv)

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    try:
        config = load_config(root)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.vault:
        config.vault_mode = True

    findings = check(root, config)
    print(FORMATTERS[args.format](findings))
    return 1 if findings else 0


def run() -> None:
    sys.exit(main())
