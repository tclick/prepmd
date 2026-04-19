"""Setup command implementation."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Literal, cast
from zipfile import ZIP_DEFLATED, ZipFile

import yaml
from loguru import logger
from rich.console import Console
from rich.table import Table

from prepmd import __version__
from prepmd.config.loader import ConfigLoader
from prepmd.config.models import ProjectConfig
from prepmd.config.validators.pipeline import ValidationPipeline
from prepmd.config.versioning import LATEST_CONFIG_VERSION
from prepmd.core.plan_fingerprint import compute_plan_sha256
from prepmd.core.reporting import NullReporter, Reporter
from prepmd.core.run import SetupStateStore, SimulationPlan, apply_plan, build_plan
from prepmd.exceptions import SetupApplyError
from prepmd.models.results import RunResult

console = Console()
SECRET_ENV_KEY_NAMES = (
    "GITHUB_TOKEN",
    "API_TOKEN",
    "AUTH_TOKEN",
    "BEARER_TOKEN",
    "SECRET_KEY",
    "API_KEY",
    "ACCESS_KEY",
    "PRIVATE_KEY",
    "SESSION_KEY",
    "SESSION_TOKEN",
    "COOKIE",
    "PASSWORD",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AZURE_CLIENT_SECRET",
    "DATABASE_URL",
    "DB_PASSWORD",
    "GCP_SERVICE_ACCOUNT_KEY",
)
SECRET_ENV_SUFFIXES = (
    "_TOKEN",
    "_SECRET",
    "_PASSWORD",
    "_PASS",
    "_API_KEY",
    "_ACCESS_KEY",
    "_PRIVATE_KEY",
    "_CREDENTIALS",
)
ENV_SNAPSHOT_KEYS = (
    "HOME",
    "USER",
    "USERNAME",
    "PATH",
    "PWD",
    "SHELL",
    "VIRTUAL_ENV",
    "CONDA_PREFIX",
    "CI",
    "GITHUB_ACTIONS",
)


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

    def render(self, *, log_format: Literal["text", "json"]) -> tuple[str, str]:
        if log_format == "json":
            payload = [{"event": _log_event_name(message), "message": message} for message in self.messages]
            return "logs.jsonl", "\n".join(json.dumps(item, sort_keys=True) for item in payload)
        return "logs.txt", "\n".join(self.messages)


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
    log_format: Literal["text", "json"] = "text",
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
    pdb_cache_payload, cache_path = _pdb_cache_payload(config)
    cache_hit_before_apply = cache_path.exists() if cache_path is not None else None
    pdb_cache_payload["status"] = _cache_status(cache_hit_before_apply=cache_hit_before_apply)
    if plan_out is not None:
        _write_text(plan_out, plan_json)

    reporter = CapturingReporter()
    manifest_json: str | None = None
    state_json: str | None = None
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
        result = apply_plan(
            plan,
            reporter=reporter,
            state_store=state_store,
            resume=resume and not overwrite,
            offline=config.protein.offline,
        )
        root = result.root_dir
        state_json = (root / ".prepmd_state.json").read_text(encoding="utf-8")
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
        log_name, logs_content = reporter.render(log_format=log_format)
        env_json = _json_text(_environment_payload(plan_sha256=plan_sha256))
        _write_debug_bundle(
            debug_bundle=debug_bundle,
            input_extension=input_extension,
            raw_config_text=raw_config_text,
            resolved_config_yaml=resolved_config_yaml,
            plan_json=plan_json,
            plan_preview=_build_plan_preview(plan),
            plan_sha256=plan_sha256,
            manifest_json=manifest_json,
            env_json=env_json,
            state_json=state_json,
            schema_ref_json=_json_text(_schema_reference_payload()),
            pdb_cache_json=_json_text(pdb_cache_payload),
            logs_file_name=log_name,
            logs_content=logs_content,
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
    loaded: object
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

    def _hash_file(path: Path) -> dict[str, object] | None:
        if not path.exists():
            return None
        return {
            "path": _relative_path(path, output_dir),
            "sha256": _sha256_bytes(path.read_bytes()),
        }

    with ThreadPoolExecutor() as executor:
        hashed = list(executor.map(_hash_file, generated_files))
    files: list[dict[str, object]] = [entry for entry in hashed if entry is not None]
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
                plan.config.protein.pdb_ids,
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
    pdb_ids: dict[str, str | None],
) -> dict[str, object]:
    if pdb_id is not None:
        return {"source": "pdb_id", "pdb_id": pdb_id}

    variant_ids: dict[str, str] = {}
    for variant, variant_id in sorted(pdb_ids.items()):
        if variant_id is not None:
            variant_ids[variant] = variant_id.upper()
    if variant_ids:
        return {"source": "pdb_id", "variants": variant_ids}

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
    env: dict[str, str] = {}
    for key in ENV_SNAPSHOT_KEYS:
        value = os.environ.get(key)
        if value is None:
            continue
        env[key] = "***REDACTED***" if _is_secret_env_key(key) else value
    secret_env_names = sorted(key for key in os.environ if _is_secret_env_key(key))
    return {
        "plan_sha256": plan_sha256,
        "prepmd_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "argv": sys.argv,
        "environment": env,
        "redacted_secret_environment_variables": secret_env_names,
    }


def _write_debug_bundle(
    *,
    debug_bundle: Path,
    input_extension: str,
    raw_config_text: str,
    resolved_config_yaml: str,
    plan_json: str,
    plan_preview: str,
    plan_sha256: str,
    manifest_json: str | None,
    env_json: str,
    state_json: str | None,
    schema_ref_json: str,
    pdb_cache_json: str,
    logs_file_name: str,
    logs_content: str,
    command_text: str,
) -> None:
    debug_bundle.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(debug_bundle, mode="w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr(f"config.input.{input_extension}", _redact_text(raw_config_text))
        bundle.writestr("config.resolved.yaml", _redact_text(resolved_config_yaml))
        bundle.writestr("plan.json", _redact_text(plan_json))
        bundle.writestr("plan.preview.txt", _redact_text(plan_preview))
        bundle.writestr("plan.sha256", f"{plan_sha256}\n")
        if manifest_json is not None:
            bundle.writestr("manifest.json", _redact_text(manifest_json))
        if state_json is not None:
            bundle.writestr(".prepmd_state.json", _redact_text(state_json))
        bundle.writestr("schema_reference.json", _redact_text(schema_ref_json))
        bundle.writestr("pdb_cache_status.json", _redact_text(pdb_cache_json))
        bundle.writestr("env.json", _redact_text(env_json))
        bundle.writestr(logs_file_name, _redact_text(logs_content))
        if command_text:
            bundle.writestr("command.txt", _redact_text(command_text))


def _build_plan_preview(plan: SimulationPlan) -> str:
    lines = [
        f"project_name: {plan.config.project_name}",
        f"root_dir: {plan.root_dir}",
        f"directories: {len(plan.directories)}",
        f"files: {len(plan.files) + len(plan.prepare_files)}",
        "",
        "[directories]",
    ]
    lines.extend(_relative_path(path, plan.root_dir) for path in plan.directories)
    lines.append("")
    lines.append("[files]")
    lines.extend(_relative_path(planned.path, plan.root_dir) for planned in plan.files)
    lines.extend(_relative_path(planned.path, plan.root_dir) for planned in plan.prepare_files)
    return "\n".join(lines)


def _schema_reference_payload() -> dict[str, object]:
    schema_resource = files("prepmd.resources").joinpath("prepmd.schema.json")
    schema_text = schema_resource.read_text(encoding="utf-8")
    return {
        "schema_version": LATEST_CONFIG_VERSION,
        "schema_file": "prepmd.resources/prepmd.schema.json",
        "schema_sha256": _sha256_bytes(schema_text.encode("utf-8")),
    }


def _pdb_cache_payload(config: ProjectConfig) -> tuple[dict[str, object], Path | None]:
    pdb_id = config.protein.pdb_id
    if pdb_id is None and any(value for value in config.protein.pdb_ids.values()):
        cache_dir = (
            Path(config.protein.pdb_cache_dir).expanduser()
            if config.protein.pdb_cache_dir
            else Path.home() / ".cache" / "prepmd" / "pdb"
        )
        return {
            "status": "variant_specific",
            "cache_dir": str(cache_dir),
            "cache_path": None,
            "pdb_id": None,
        }, None
    if pdb_id is None:
        return {"status": "not_applicable", "cache_dir": None, "cache_path": None, "pdb_id": None}, None
    cache_dir = (
        Path(config.protein.pdb_cache_dir).expanduser()
        if config.protein.pdb_cache_dir
        else Path.home() / ".cache" / "prepmd" / "pdb"
    )
    ext = ".cif" if config.protein.structure_format == "mmcif" else ".pdb"
    cache_path = cache_dir / f"{pdb_id.upper()}{ext}"
    payload: dict[str, object] = {
        "status": "unknown",
        "cache_dir": str(cache_dir),
        "cache_path": str(cache_path),
        "pdb_id": pdb_id.upper(),
    }
    return payload, cache_path


def _cache_status(*, cache_hit_before_apply: bool | None) -> str:
    if cache_hit_before_apply is None:
        return "not_applicable"
    if cache_hit_before_apply:
        return "hit"
    return "miss"


def _redact_text(text: str) -> str:
    redacted = text
    for alias in _home_path_aliases():
        redacted = redacted.replace(alias, "$HOME")
    return redacted


def _home_path_aliases() -> tuple[str, ...]:
    home = Path.home()
    aliases = {
        str(home),
        home.as_posix(),
        os.path.normpath(str(home)),
    }
    return tuple(sorted(aliases, key=len, reverse=True))


def _is_secret_env_key(name: str) -> bool:
    normalized = name.upper()
    return normalized in SECRET_ENV_KEY_NAMES or any(normalized.endswith(suffix) for suffix in SECRET_ENV_SUFFIXES)


def _log_event_name(message: str) -> str:
    return message.lstrip().partition(" ")[0] or "log"


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
