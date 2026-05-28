"""Configuration: ~/.siamang.toml loader, profiles, secret hardening."""

from siamang.config.loader import Config, ConfigError, load, save, use_profile, current
from siamang.config.secrets import check_permissions

__all__ = [
    "Config",
    "ConfigError",
    "check_permissions",
    "current",
    "load",
    "save",
    "use_profile",
]
