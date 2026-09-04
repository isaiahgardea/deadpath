"""Does this candidate point at something that exists?

Resolution order matters: a hit at any stage means resolved. Trying several
bases is what lets the same tool work on a repo (root- and doc-relative) and
an Obsidian vault (vault-root-relative) without separate logic.
"""
import os
from pathlib import Path, PurePosixPath

from .gate import DRIVE_RE
from .models import Candidate


def resolve_candidate(
    candidate: Candidate,
    root: Path,
    doc_path: Path,
    vault_root: Path | None = None,
) -> bool:
    raw = candidate.raw.replace("\\", "/")
    if not raw:
        return True  # nothing to check; never report an empty candidate

    # Absoluteness is judged from the string itself, not from the platform
    # running this process. Path is the OS-native class, so Path.is_absolute()
    # silently means different things per platform:
    # Path("/usr/bin/env").is_absolute() is False on Windows (no drive
    # letter), and a Windows drive path is not absolute under POSIX rules
    # either. Checking both forms explicitly is what lets a POSIX path
    # mentioned in docs be recognised as absolute even when this process
    # runs on Windows, and a Windows path be recognised even on POSIX.
    is_posix_absolute = raw.startswith("/")
    is_windows_absolute = bool(DRIVE_RE.match(raw))

    # Vault mode only: a RELATIVE path written with backslashes is a Windows
    # path into a different tree, not a vault-relative one. Obsidian's own
    # conventions -- wikilinks and vault-relative links -- are always
    # forward-slashed, so the separator is real information here.
    #
    # Found on the first ~1000-file vault run (090426): `Projects\Reaper`
    # flagged three times. It is a real directory under the user's Claude
    # projects folder whose name collides with a real vault directory
    # (`Projects/`), so it resolved against the wrong root and reported a
    # valid reference as broken.
    #
    # Config cannot express this. The normalisation above runs before the
    # allowlist prefix check, so allowlisting `Projects\` would collapse to
    # `Projects/` and silence every legitimate vault link too.
    #
    # Scoped to vault mode deliberately: in repo mode on Windows a
    # backslashed repo-relative path is ordinary and must still be checked.
    if (
        vault_root is not None
        and not is_posix_absolute
        and not is_windows_absolute
        and "\\" in candidate.raw
    ):
        return True

    try:
        if is_posix_absolute or is_windows_absolute:
            native = os.name == "nt" if is_windows_absolute else os.name != "nt"
            if not native:
                # Absolute for a platform OTHER than the one running this
                # process (a Unix path mentioned on Windows, or a drive
                # path mentioned on POSIX) cannot be meaningfully checked
                # from here. Per this module's own precision-over-coverage
                # principle -- the same reasoning that already makes
                # OSError/ValueError resolve rather than flag -- treat it
                # as resolved. Do NOT "fix" this into flagging, and do NOT
                # try to check it with the native Path class instead:
                # Path(raw) on the wrong platform either silently reports
                # is_absolute() == False (the exact live bug this branch
                # exists to fix) or checks a path that can never exist on
                # this filesystem.
                return True
            return Path(raw).exists()

        # Obsidian wikilinks omit the .md extension: [[Notes/Thing]] refers
        # to the file Notes/Thing.md. Vault mode only -- repo mode has no
        # such convention. Only applies when the candidate has no extension
        # of its own; this is an alternate spelling of the same path, tried
        # against every base below, not a new base.
        try_md = vault_root is not None and not PurePosixPath(raw).suffix

        if (root / raw).exists():
            return True
        if try_md and (root / f"{raw}.md").exists():
            return True
        if (doc_path.parent / raw).exists():
            return True
        if try_md and (doc_path.parent / f"{raw}.md").exists():
            return True
        if vault_root is not None and (vault_root / raw).exists():
            return True
        if try_md and (vault_root / f"{raw}.md").exists():
            return True
        return False
    except (OSError, ValueError):
        # An inaccessible (PermissionError etc.) or malformed (embedded
        # null byte, path-too-long) candidate is genuinely uncertain, not
        # evidence the target is missing. Per the module's own precision-
        # over-coverage principle, uncertain resolves rather than flags --
        # do not change this to raise or to return False.
        return True
