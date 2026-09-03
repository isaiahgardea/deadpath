import os
from pathlib import Path

from deadpath.models import Candidate
from deadpath.resolve import resolve_candidate


def cand(raw):
    return Candidate(raw=raw, line=1, source="d.md", form="backtick")


def test_repo_root_relative_resolves(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x", encoding="utf-8")
    doc = tmp_path / "README.md"
    doc.write_text("x", encoding="utf-8")
    assert resolve_candidate(cand("src/a.py"), tmp_path, doc)


def test_doc_relative_resolves(tmp_path):
    sub = tmp_path / "docs"
    sub.mkdir()
    (sub / "sibling.md").write_text("x", encoding="utf-8")
    doc = sub / "index.md"
    doc.write_text("x", encoding="utf-8")
    assert resolve_candidate(cand("sibling.md"), tmp_path, doc)


def test_missing_path_does_not_resolve(tmp_path):
    doc = tmp_path / "README.md"
    doc.write_text("x", encoding="utf-8")
    assert not resolve_candidate(cand("src/nope.py"), tmp_path, doc)


def test_directory_resolves(tmp_path):
    (tmp_path / "src").mkdir()
    doc = tmp_path / "README.md"
    doc.write_text("x", encoding="utf-8")
    assert resolve_candidate(cand("src"), tmp_path, doc)


def test_vault_root_resolves_when_provided(tmp_path):
    vault = tmp_path / "vault"
    (vault / "Patterns").mkdir(parents=True)
    (vault / "Patterns" / "p.md").write_text("x", encoding="utf-8")
    docdir = vault / "Daily"
    docdir.mkdir()
    doc = docdir / "note.md"
    doc.write_text("x", encoding="utf-8")
    # Not resolvable from the doc's own directory; only from the vault root.
    assert not resolve_candidate(cand("Patterns/p.md"), docdir, doc)
    assert resolve_candidate(cand("Patterns/p.md"), docdir, doc, vault_root=vault)


def test_backslash_paths_are_normalised(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x", encoding="utf-8")
    doc = tmp_path / "README.md"
    doc.write_text("x", encoding="utf-8")
    assert resolve_candidate(cand(r"src\a.py"), tmp_path, doc)


def test_empty_candidate_resolves(tmp_path):
    doc = tmp_path / "README.md"
    doc.write_text("x", encoding="utf-8")
    assert resolve_candidate(cand(""), tmp_path, doc)


def test_null_byte_candidate_resolves_rather_than_raises(tmp_path, monkeypatch):
    # On Python 3.13+ (verified here on 3.14.6), pathlib.Path.exists() has
    # been rewritten to delegate to os.path.exists(), whose implementation
    # (genericpath.exists) already catches ValueError internally -- so an
    # embedded null byte no longer raises out of exists(), it just yields
    # False. That means a literal null byte can't be used to exercise the
    # ValueError branch on this interpreter. Monkeypatch Path.exists to
    # raise ValueError directly instead, so the branch is genuinely tested
    # regardless of interpreter-version quirks (same rationale as the
    # PermissionError test below: the trigger condition can't be reliably
    # produced, so we test the exception-handling behavior directly).
    #
    # The patch only raises for the exact candidate path under test and
    # delegates every other call to the real Path.exists -- a blanket,
    # unconditional patch of Path.exists intercepts pytest's own internal
    # exists() calls (used while formatting a traceback for a propagating
    # exception) and can crash the test run with an INTERNALERROR.
    doc = tmp_path / "README.md"
    doc.write_text("x", encoding="utf-8")
    target = tmp_path / "src" / "a\x00b.py"
    real_exists = Path.exists

    def raise_value_error(self, *args, **kwargs):
        if self == target:
            raise ValueError("embedded null character in path")
        return real_exists(self, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", raise_value_error)
    assert resolve_candidate(cand("src/a\x00b.py"), tmp_path, doc)


def test_vault_mode_implicit_md_extension_resolves(tmp_path):
    # Obsidian wikilinks omit the .md extension: [[Notes/Thing]] refers to
    # Notes/Thing.md. Only Notes/Thing.md exists on disk; the bare
    # extensionless candidate should still resolve in vault mode.
    vault = tmp_path / "vault"
    (vault / "Notes").mkdir(parents=True)
    (vault / "Notes" / "Thing.md").write_text("x", encoding="utf-8")
    doc = vault / "Daily" / "note.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("x", encoding="utf-8")
    assert resolve_candidate(cand("Notes/Thing"), vault, doc, vault_root=vault)


def test_repo_mode_implicit_md_extension_does_not_resolve(tmp_path):
    # Same setup, but vault_root=None (repo mode) -- the .md fallback must
    # be vault-only and must NOT apply here.
    (tmp_path / "Notes").mkdir()
    (tmp_path / "Notes" / "Thing.md").write_text("x", encoding="utf-8")
    doc = tmp_path / "README.md"
    doc.write_text("x", encoding="utf-8")
    assert not resolve_candidate(cand("Notes/Thing"), tmp_path, doc)


def test_candidate_with_extension_unaffected_by_md_fallback(tmp_path):
    # A candidate that already has an extension should not be affected by
    # the implicit-.md fallback -- it should behave exactly as before:
    # resolve only if the literal path exists.
    vault = tmp_path / "vault"
    (vault / "Notes").mkdir(parents=True)
    (vault / "Notes" / "Thing.txt").write_text("x", encoding="utf-8")
    doc = vault / "Daily" / "note.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("x", encoding="utf-8")
    # Thing.md does not exist, only Thing.txt -- Thing.md candidate must
    # not resolve just because Notes/Thing.md.md or similar might exist.
    assert not resolve_candidate(cand("Notes/Thing.md"), vault, doc, vault_root=vault)


def test_permission_error_resolves_rather_than_raises(tmp_path, monkeypatch):
    # See the comment on test_null_byte_candidate_resolves_rather_than_raises
    # above for why this patch is scoped to the exact target path rather
    # than raising unconditionally for every Path.exists() call.
    doc = tmp_path / "README.md"
    doc.write_text("x", encoding="utf-8")
    target = tmp_path / "src" / "a.py"
    real_exists = Path.exists

    def raise_permission_error(self, *args, **kwargs):
        if self == target:
            raise PermissionError("mocked EACCES")
        return real_exists(self, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", raise_permission_error)
    assert resolve_candidate(cand("src/a.py"), tmp_path, doc)


# --- Finding 1: platform-dependent absolute-path resolution ---------------
#
# Path.is_absolute() means different things per platform: on Windows,
# Path("/usr/bin/env").is_absolute() is False (no drive letter), so before
# the fix an ordinary prose mention of a Unix path fell through to the
# relative branch, joined onto root as "C:\usr\bin\env", found nothing, and
# was falsely reported dead -- reproduced live:
#   $ echo 'Run it with the `/usr/bin/env` interpreter shebang.' > README.md
#   $ deadpath check .
#   README.md:1  /usr/bin/env  -- path does not exist
# The mirror case breaks on POSIX: PurePosixPath("C:/Users/x").is_absolute()
# is False there, so a Windows path mentioned in docs would be falsely
# flagged in CI (which runs ubuntu-latest).
#
# Absoluteness must therefore be judged from the string, not the platform.
# A path absolute for a *different* platform than the one running cannot be
# meaningfully checked here, so per this module's precision-over-coverage
# bias it must resolve (not flag) rather than being misjudged as relative.


def test_foreign_absolute_path_resolves_without_flagging(tmp_path):
    # Selects whichever of the two documented example candidates is
    # "foreign" (absolute for a platform other than the one running this
    # suite) so the test exercises the actual fixed branch -- and asserts
    # the correct outcome -- regardless of which OS runs it, rather than
    # depending on real-disk state for a system file that happens to exist
    # on most machines of that OS.
    doc = tmp_path / "README.md"
    doc.write_text("x", encoding="utf-8")
    if os.name == "nt":
        # POSIX-absolute; foreign here. This is the exact live repro above.
        foreign = "/usr/bin/env"
    else:
        # Windows-drive-absolute; foreign here.
        foreign = r"C:\Windows\System32\drivers\etc\hosts"
    assert resolve_candidate(cand(foreign), tmp_path, doc)


def test_native_absolute_path_that_exists_resolves(tmp_path):
    # An absolute path that genuinely exists on the platform actually
    # running the suite must still resolve -- the fix must not turn every
    # absolute path into an unconditional pass. tmp_path is always native.
    (tmp_path / "exists.txt").write_text("x", encoding="utf-8")
    doc = tmp_path / "README.md"
    doc.write_text("x", encoding="utf-8")
    absolute = str(tmp_path / "exists.txt")
    assert resolve_candidate(cand(absolute), tmp_path, doc)


def test_native_absolute_path_that_does_not_exist_is_reported(tmp_path):
    # Mirror of the above: a native absolute path that does NOT exist must
    # still be reported -- native absolute-path checking must keep working.
    doc = tmp_path / "README.md"
    doc.write_text("x", encoding="utf-8")
    absolute = str(tmp_path / "does-not-exist.txt")
    assert not resolve_candidate(cand(absolute), tmp_path, doc)
