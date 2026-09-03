"""Config loading. Deliberately small -- four knobs and nothing else, because
every extra option is a decision a user has to make before the tool works."""
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_SCAN_GLOBS = ["**/*.md"]
CONFIG_FILENAME = ".deadpath.toml"


class ConfigError(Exception):
    """Raised when the config file exists but can't be read or parsed."""


@dataclass
class Config:
    scan_globs: list[str] = field(default_factory=lambda: list(DEFAULT_SCAN_GLOBS))
    allowlist_prefixes: list[str] = field(default_factory=list)
    exclude_globs: list[str] = field(default_factory=list)
    vault_mode: bool = False
    extensions: list[str] | None = None


def load_config(root: Path) -> Config:
    path = root / CONFIG_FILENAME
    data: dict = {}
    if path.is_file():
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle).get("deadpath", {})
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"Could not parse {path}: {exc}") from exc
        except OSError as exc:
            raise ConfigError(f"Could not read {path}: {exc}") from exc
    return Config(
        scan_globs=data.get("scan_globs", list(DEFAULT_SCAN_GLOBS)),
        allowlist_prefixes=data.get("allowlist_prefixes", []),
        exclude_globs=data.get("exclude_globs", []),
        vault_mode=data.get("vault_mode", False),
        extensions=data.get("extensions"),
    )
