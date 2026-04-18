"""Canonical normalization and hashing for deterministic setup plans."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from prepmd.core.run import SimulationPlan


def normalize_plan(plan: SimulationPlan) -> dict[str, object]:
    """Return canonical payload for deterministic plan hashing."""
    directories = sorted(_relative(path, plan.root_dir) for path in plan.directories)
    files = sorted(
        (
            {
                "path": _relative(item.path, plan.root_dir),
                "content": _normalize_newlines(item.content),
            }
            for item in plan.files
        ),
        key=lambda item: str(item["path"]),
    )
    prepare_files = sorted(
        (
            {
                "path": _relative(item.path, plan.root_dir),
                "variant": item.variant,
            }
            for item in plan.prepare_files
        ),
        key=lambda item: (str(item["path"]), str(item["variant"])),
    )
    return {
        "version": 1,
        "directories": directories,
        "files": files,
        "prepare_files": prepare_files,
    }


def serialize_plan(plan: SimulationPlan) -> str:
    """Serialize canonical plan payload with stable ordering."""
    return json.dumps(normalize_plan(plan), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_plan_sha256(plan: SimulationPlan) -> str:
    """Compute deterministic SHA-256 hash for a setup plan."""
    return hashlib.sha256(serialize_plan(plan).encode("utf-8")).hexdigest()


def _relative(path: Path, root_dir: Path) -> str:
    try:
        normalized = path.relative_to(root_dir)
    except ValueError:
        normalized = path
    return normalized.as_posix()


def _normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")
