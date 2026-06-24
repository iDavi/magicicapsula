"""user configuration: built-in defaults, a json config file, env overrides.

precedence, low to high:

    default  <  config file  <  environment variable

the config file lives at $XDG_CONFIG_HOME/magicicapsula/config.json (or
~/.config/magicicapsula/config.json) and is a flat json object of key -> value.

adding a new configurable setting is a single entry in _SETTINGS; resolution,
masking, and the `config` command pick it up automatically. no printing here.
"""

import json
import os
from dataclasses import dataclass

APP = "magicicapsula"


@dataclass(frozen=True)
class _Setting:
    env: str | None = None  # environment variable that overrides the file
    default: object = None
    secret: bool = False  # masked by display() / the `config` command


# the registry. one line per setting; add new ones here.
_SETTINGS: dict[str, _Setting] = {
    "password": _Setting(env="MAGICICAPSULA_PASSWORD", secret=True),
}


def config_path() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, APP, "config.json")


def _load_file() -> dict:
    try:
        with open(config_path(), encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_file(data: dict) -> None:
    path = config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def keys() -> list[str]:
    return list(_SETTINGS)


def is_known(key: str) -> bool:
    return key in _SETTINGS


def set_value(key: str, value: str) -> None:
    """Write a setting to the config file. Raises KeyError for unknown keys."""
    if key not in _SETTINGS:
        raise KeyError(key)
    data = _load_file()
    data[key] = value
    _write_file(data)


def unset(key: str) -> bool:
    """Remove a setting from the config file. Returns whether it was present."""
    if key not in _SETTINGS:
        raise KeyError(key)
    data = _load_file()
    existed = key in data
    if existed:
        data.pop(key)
        _write_file(data)
    return existed


def resolve(key: str):
    """Return (value, source) for a setting; source is 'env', 'file', or 'default'."""
    s = _SETTINGS[key]
    if s.env and os.environ.get(s.env):
        return os.environ[s.env], "env"
    data = _load_file()
    if key in data:
        return data[key], "file"
    return s.default, "default"


def get(key: str):
    return resolve(key)[0]


def display(key: str, value, reveal: bool = False) -> str:
    """Human-readable value for `config`, masking secrets unless reveal is set."""
    if value is None:
        return "(not set)"
    if _SETTINGS[key].secret and not reveal:
        return "***"
    return str(value)
