"""Configuration versioning and migration support."""

from typing import Any

LATEST_CONFIG_VERSION = 1


def migrate_config(
    data: dict[str, Any],
    target_version: int = LATEST_CONFIG_VERSION,
) -> dict[str, Any]:
    """Return migrated config payload.

    Current implementation is a no-op because only v1 exists.
    """
    _ = target_version
    return data
