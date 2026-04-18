"""Manifest and debug-bundle helpers for CLI runs."""

from __future__ import annotations

import hashlib
import json
import logging
import platform
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from prepmd import __version__
from prepmd.config.models import ProjectConfig
from prepmd.core.run import PlannedFile, SimulationPlan
from prepmd.models.results import RunResult

HASH_CHUNK_SIZE = 1024 * 1024
LOGGER = logging.getLogger(__name__)


def build_manifest(
    config: ProjectConfig,
    plan: SimulationPlan,
    generated_files: tuple[PlannedFile, ...],
    *,
    dry_run: bool,
) -> dict[str, object]:
    """Build deterministic reproducibility manifest content."""
    return {
        "prepmd_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "mode": "dry_run" if dry_run else "apply",
        "config_hash": _hash_text(stable_json(config.model_dump(mode="json"))),
        "input": _input_fingerprint(config),
        "generated_files": [
            {
                "path": _relative_to_root(file.path, plan.root_dir),
                "sha256": _hash_text(file.content),
            }
            for file in sorted(generated_files, key=lambda item: str(item.path))
        ],
    }


def plan_preview(plan: SimulationPlan, generated_files: tuple[PlannedFile, ...]) -> str:
    """Render a plain-text preview of the planned filesystem actions."""
    lines = [
        f"root: {plan.root_dir}",
        f"directories: {len(plan.directories)}",
        f"files: {len(generated_files)}",
        "",
        "[directories]",
    ]
    lines.extend(str(path) for path in plan.directories)
    lines.append("")
    lines.append("[files]")
    lines.extend(str(file.path) for file in generated_files)
    return "\n".join(lines)


def read_generated_files(plan: SimulationPlan) -> tuple[PlannedFile, ...]:
    """Read generated file content from an applied plan."""
    generated: list[PlannedFile] = []
    for planned_file in plan.files:
        generated.append(PlannedFile(planned_file.path, _read_text(planned_file.path)))
    for prepare_file in plan.prepare_files:
        generated.append(PlannedFile(prepare_file.path, _read_text(prepare_file.path)))
    return tuple(sorted(generated, key=lambda item: str(item.path)))


def write_manifest(path: Path, manifest: dict[str, object]) -> None:
    """Write manifest JSON on disk."""
    path.write_text(stable_json(manifest), encoding="utf-8")


def write_debug_bundle(
    bundle_path: Path,
    *,
    config: ProjectConfig,
    manifest: dict[str, object],
    plan_text: str,
    logs: list[str],
    run_result: RunResult | None,
) -> None:
    """Create zip archive with deterministic troubleshooting artifacts."""
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    run_result_payload: dict[str, object] = (
        {
            "success": run_result.success,
            "steps": [
                {"name": step.name, "success": step.success, "message": step.message, "metadata": step.metadata}
                for step in run_result.steps
            ],
        }
        if run_result is not None
        else {"success": None, "steps": []}
    )
    env_payload: dict[str, object] = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "argv": sys.argv,
    }

    with ZipFile(bundle_path, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("config.json", stable_json(config.model_dump(mode="json")))
        archive.writestr("manifest.json", stable_json(manifest))
        archive.writestr("plan_preview.txt", plan_text)
        archive.writestr("logs.txt", "\n".join(logs))
        archive.writestr("run_result.json", stable_json(run_result_payload))
        archive.writestr("environment.json", stable_json(env_payload))


def stable_json(payload: object) -> str:
    """Serialize payload as stable JSON for deterministic artifacts."""
    return json.dumps(payload, indent=2, sort_keys=True)


def _hash_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _input_fingerprint(config: ProjectConfig) -> dict[str, object]:
    protein = config.protein
    variant_hashes = {
        variant: _safe_hash(Path(path)) if path else None for variant, path in sorted(protein.pdb_files.items())
    }
    return {
        "pdb_id": protein.pdb_id.upper() if protein.pdb_id else None,
        "pdb_id_hash": _hash_text(protein.pdb_id.upper()) if protein.pdb_id else None,
        "pdb_file": protein.pdb_file,
        "pdb_file_hash": _safe_hash(Path(protein.pdb_file)) if protein.pdb_file else None,
        "variant_pdb_file_hashes": variant_hashes,
    }


def _safe_hash(path: Path) -> str | None:
    try:
        return _hash_file(path) if path.is_file() else None
    except OSError as exc:
        LOGGER.warning("Failed to hash %s: %s", path, exc)
        return None


def _relative_to_root(path: Path, root_dir: Path) -> str:
    try:
        return str(path.relative_to(root_dir))
    except ValueError:
        return str(path)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Failed to read generated file {path}") from exc
