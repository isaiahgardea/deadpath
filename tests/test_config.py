import pytest

from deadpath.config import Config, ConfigError, load_config


def test_defaults_when_no_file(tmp_path):
    cfg = load_config(tmp_path)
    assert cfg.scan_globs == ["**/*.md"]
    assert cfg.allowlist_prefixes == []
    assert cfg.exclude_globs == []
    assert cfg.vault_mode is False
    assert cfg.extensions is None


def test_reads_toml(tmp_path):
    (tmp_path / ".deadpath.toml").write_text(
        "\n".join(
            [
                "[deadpath]",
                'scan_globs = ["docs/**/*.md"]',
                'allowlist_prefixes = ["staging/"]',
                'exclude_globs = ["CHANGELOG.md"]',
                "vault_mode = true",
                'extensions = [".zig"]',
            ]
        ),
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.scan_globs == ["docs/**/*.md"]
    assert cfg.allowlist_prefixes == ["staging/"]
    assert cfg.exclude_globs == ["CHANGELOG.md"]
    assert cfg.vault_mode is True
    assert cfg.extensions == [".zig"]


def test_partial_config_keeps_other_defaults(tmp_path):
    (tmp_path / ".deadpath.toml").write_text(
        "\n".join(
            [
                "[deadpath]",
                'exclude_globs = ["CHANGELOG.md"]',
            ]
        ),
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.exclude_globs == ["CHANGELOG.md"]
    assert cfg.scan_globs == ["**/*.md"]
    assert cfg.allowlist_prefixes == []
    assert cfg.vault_mode is False
    assert cfg.extensions is None


def test_malformed_toml_raises_config_error(tmp_path):
    (tmp_path / ".deadpath.toml").write_text("not valid toml [[[", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(tmp_path)
