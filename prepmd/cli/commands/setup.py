"""Setup command implementation."""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from zipfile import ZIP_DEFLATED, ZipFile

import yaml
from loguru import logger
from rich.console import Console
from rich.table import Table

from prepmd import __version__
from prepmd.config.loader import ConfigLoader
from prepmd.config.validators.pipeline import ValidationPipeline
from prepmd.core.plan_fingerprint import compute_plan_sha256
from prepmd.core.reporting import NullReporter, Reporter
from prepmd.core.run import SetupStateStore, SimulationPlan, apply_plan, build_plan
from prepmd.exceptions import SetupApplyError
from prepmd.models.results import RunResult

console = Console()


class CapturingReporter:
    """Reporter wrapper that records run logs for debug bundles."""

    def __init__(self, delegate: Reporter | None = None) -> None:
        self._delegate = delegate or NullReporter()
        self.messages: list[str] = []

    def on_start(self, total_steps: int) -> None:
        self.messages.append(f"start total_steps={total_steps}")
        self._delegate.on_start(total_steps)

    def on_step(self, current_step: int, total_steps: int, message: str) -> None:
        self.messages.append(f"step {current_step}/{total_steps} {message}")
        self._delegate.on_step(current_step, total_steps, message)

    def on_log(self, message: str) -> None:
        self.messages.append(f"log {message}")
        self._delegate.on_log(message)

    def on_error(self, error: BaseException) -> None:
        self.messages.append(f"error {error}")
        self._delegate.on_error(error)

    def on_finish(self, result: RunResult) -> None:
        self.messages.append("finish")
        self._delegate.on_finish(result)


def setup_project(
    config_path: Path,
    *,
    output_dir: Path | None = None,
    dry_run: bool = False,
    offline: bool | None = None,
    plan_out: Path | None = None,
    manifest: Path | None = None,
    debug_bundle: Path | None = None,
    resume: bool = False,
    overwrite: bool = False,
) -> None:
    """Load config and scaffold project directories."""
    config = ConfigLoader().load_project_config(config_path)
    if offline is not None:
        config.protein.offline = offline
    raw_config, raw_config_text, input_extension = _load_raw_config(config_path)
    resolved_output_dir, output_source = _resolve_output_dir(raw_config, config.output_dir, output_dir)
    config.output_dir = str(resolved_output_dir)
    ValidationPipeline().validate(config)

    plan = build_plan(config)
    plan_sha256 = compute_plan_sha256(plan)
    plan_payload = _build_plan_payload(plan)
    plan_json = _json_text(plan_payload)
    if plan_out is not None:
        _write_text(plan_out, plan_json)

    reporter = CapturingReporter()
    manifest_json: str | None = None
    if dry_run:
        root = plan.root_dir
        logger.info(f"Dry-run complete for {root}")
    else:
        if overwrite and plan.root_dir.exists():
            expected_root = resolved_output_dir / config.project_name
            if plan.root_dir != expected_root:
                raise SetupApplyError(
                    f"Refusing to overwrite unexpected project root: {plan.root_dir} (expected {expected_root})"
                )
            shutil.rmtree(plan.root_dir)
        state_store = SetupStateStore.create(
            plan.root_dir,
            config_sha256=_sha256_bytes(raw_config_text.encode("utf-8")),
            plan_sha256=plan_sha256,
            resume=resume and not overwrite,
        )
        result = apply_plan(plan, reporter=reporter, state_store=state_store, resume=resume and not overwrite)
        root = result.root_dir
        generated_files = _planned_output_files(plan)
        manifest_payload = _build_manifest(
            plan=plan,
            config_path=config_path,
            raw_config_text=raw_config_text,
            generated_files=generated_files,
            output_source=output_source,
            plan_sha256=plan_sha256,
        )
        manifest_path = manifest if manifest is not None else resolved_output_dir / "manifest.json"
        _write_text(manifest_path, _json_text(manifest_payload))
        manifest_json = _json_text(manifest_payload)
        logger.info(f"Project created at {root}")

    if debug_bundle is not None:
        resolved_config_yaml = yaml.safe_dump(config.model_dump(mode="json"), sort_keys=True)
        env_json = _json_text(_environment_payload(plan_sha256=plan_sha256))
        _write_debug_bundle(
            debug_bundle=debug_bundle,
            input_extension=input_extension,
            raw_config_text=raw_config_text,
            resolved_config_yaml=resolved_config_yaml,
            plan_json=plan_json,
            manifest_json=manifest_json,
            env_json=env_json,
            logs_text="\n".join(reporter.messages),
            command_text=" ".join(sys.argv),
        )

    table = Table(title="prepmd setup")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Mode", "dry-run" if dry_run else "apply")
    table.add_row("Project", config.project_name)
    table.add_row("Engine", config.engine.name)
    table.add_row("Path", str(root))
    table.add_row("Plan steps", str(plan.total_steps))
    console.print(table)


def _load_raw_config(config_path: Path) -> tuple[dict[str, object], str, str]:
    text = config_path.read_text(encoding="utf-8")
    suffix = config_path.suffix.lower()
    loaded: Any
    if suffix in {".yaml", ".yml"}:
        loaded = yaml.safe_load(text) or {}
    elif suffix == ".toml":
        loaded = tomllib.loads(text)
    else:  # pragma: no cover - supported formats already enforced in ConfigLoader
        loaded = {}
    data = cast(dict[str, object], loaded) if isinstance(loaded, dict) else {}
    return data, text, suffix.lstrip(".") or "txt"


def _resolve_output_dir(
    raw_config: dict[str, object], config_output_dir: str, cli_output_dir: Path | None
) -> tuple[Path, str]:
    if cli_output_dir is not None:
        source = "cli"
        selected = cli_output_dir
    elif "output_dir" in raw_config:
        source = "config"
        selected = Path(config_output_dir)
    else:
        source = "default"
        selected = Path(config_output_dir)
    return selected.expanduser().resolve(), source


def _build_plan_payload(plan: SimulationPlan) -> dict[str, object]:
    return {
        "project_name": plan.config.project_name,
        "root_dir": str(plan.root_dir),
        "directories": [str(path) for path in plan.directories],
        "files": [
            {"path": str(planned.path), "sha256": _sha256_bytes(planned.content.encode("utf-8"))}
            for planned in plan.files
        ],
        "prepare_files": [{"path": str(planned.path), "variant": planned.variant} for planned in plan.prepare_files],
    }


def _planned_output_files(plan: SimulationPlan) -> tuple[Path, ...]:
    static_files = [planned.path for planned in plan.files]
    prepare_files = [planned.path for planned in plan.prepare_files]
    return tuple(sorted(static_files + prepare_files))


def _build_manifest(
    *,
    plan: SimulationPlan,
    config_path: Path,
    raw_config_text: str,
    generated_files: tuple[Path, ...],
    output_source: str,
    plan_sha256: str,
) -> dict[str, object]:
    output_dir = Path(plan.config.output_dir).expanduser().resolve()
    files = [
        {
            "path": _relative_path(path, output_dir),
            "sha256": _sha256_bytes(path.read_bytes()),
        }
        for path in generated_files
        if path.exists()
    ]
    files.sort(key=lambda item: str(item["path"]))
    return {
        "manifest_version": 1,
        "created_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "plan_sha256": plan_sha256,
        "prepmd": {"version": __version__},
        "python": {"version": platform.python_version()},
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "platform": platform.platform(),
        },
        "inputs": {
            "config_path": str(config_path.resolve()),
            "config_sha256": _sha256_bytes(raw_config_text.encode("utf-8")),
            "pdb": _pdb_input_payload(
                plan.config.protein.pdb_file,
                plan.config.protein.pdb_files,
                plan.config.protein.pdb_id,
            ),
        },
        "config_resolution": {
            "output_dir": {
                "value": str(output_dir),
                "source": output_source,
            }
        },
        "outputs": {
            "output_dir": str(output_dir),
            "files": files,
        },
    }


def _pdb_input_payload(
    pdb_file: str | None,
    pdb_files: dict[str, str | None],
    pdb_id: str | None,
) -> dict[str, object]:
    if pdb_id is not None:
        return {"source": "pdb_id", "pdb_id": pdb_id}

    if pdb_file is not None:
        path = Path(pdb_file).expanduser()
        payload: dict[str, object] = {"source": "file", "path": str(path)}
        if path.exists():
            payload["sha256"] = _sha256_bytes(path.read_bytes())
        return payload

    variants: dict[str, object] = {}
    for variant, path_str in sorted(pdb_files.items()):
        if path_str is None:
            continue
        path = Path(path_str).expanduser()
        item: dict[str, object] = {"path": str(path)}
        if path.exists():
            item["sha256"] = _sha256_bytes(path.read_bytes())
        variants[variant] = item
    return {"source": "file", "variants": variants}


def _environment_payload(*, plan_sha256: str) -> dict[str, object]:
    return {
        "plan_sha256": plan_sha256,
        "prepmd_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "argv": sys.argv,
    }


def _write_debug_bundle(
    *,
    debug_bundle: Path,
    input_extension: str,
    raw_config_text: str,
    resolved_config_yaml: str,
    plan_json: str,
    manifest_json: str | None,
    env_json: str,
    logs_text: str,
    command_text: str,
) -> None:
    debug_bundle.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(debug_bundle, mode="w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr(f"config.input.{input_extension}", raw_config_text)
        bundle.writestr("config.resolved.yaml", resolved_config_yaml)
        bundle.writestr("plan.json", plan_json)
        if manifest_json is not None:
            bundle.writestr("manifest.json", manifest_json)
        bundle.writestr("env.json", env_json)
        bundle.writestr("logs.txt", logs_text)
        if command_text:
            bundle.writestr("command.txt", command_text)


def _relative_path(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base))
    except ValueError:
        return str(path.resolve())


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_text(payload: dict[str, object]) -> str:
    return f"{json.dumps(payload, indent=2, sort_keys=True)}\n"


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
