from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from prepmd.cli.main import app

UPDATE_GOLDEN_ENV = "UPDATE_GOLDEN"
IGNORED_DYNAMIC_FILES = {".prepmd_state.json"}


@dataclass(frozen=True, slots=True)
class GoldenScenario:
    name: str
    project_name: str
    config_text: str
    config_filename: str = "config.yaml"
    mock_download_path: str | None = None


@dataclass(frozen=True, slots=True)
class GoldenSnapshot:
    tree_listing: str
    text_files: dict[str, str]


def assert_setup_matches_golden(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: GoldenScenario,
    golden_root: Path,
) -> None:
    project_root = _run_setup(tmp_path=tmp_path, monkeypatch=monkeypatch, scenario=scenario)
    snapshot = _collect_snapshot(project_root)
    scenario_golden = golden_root / scenario.name
    if _update_mode_enabled():
        _write_snapshot(snapshot=snapshot, scenario_golden=scenario_golden)
    _assert_snapshot(snapshot=snapshot, scenario_golden=scenario_golden)


def _run_setup(*, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: GoldenScenario) -> Path:
    if scenario.mock_download_path is not None:
        mock_download_path = scenario.mock_download_path
        monkeypatch.setattr(
            "prepmd.core.run.PDBHandler.get_or_download",
            lambda _self, _pdb_id: Path(mock_download_path),
        )
    scenario_root = tmp_path / scenario.name
    output_dir = scenario_root / "output"
    config_path = scenario_root / scenario.config_filename
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(scenario.config_text, encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["setup", str(config_path.resolve()), "--output-dir", str(output_dir.resolve())],
    )
    assert result.exit_code == 0, result.output
    return output_dir / scenario.project_name


def _collect_snapshot(project_root: Path) -> GoldenSnapshot:
    tree_entries: list[str] = []
    text_files: dict[str, str] = {}
    for path in sorted(project_root.rglob("*"), key=lambda value: value.as_posix()):
        relative = path.relative_to(project_root).as_posix()
        if relative in IGNORED_DYNAMIC_FILES:
            continue
        if path.is_dir():
            tree_entries.append(f"{relative}/")
            continue
        tree_entries.append(relative)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text_files[relative] = _normalize_text(text)

    return GoldenSnapshot(
        tree_listing="".join(f"{entry}\n" for entry in tree_entries),
        text_files=text_files,
    )


def _assert_snapshot(*, snapshot: GoldenSnapshot, scenario_golden: Path) -> None:
    tree_path = scenario_golden / "tree.txt"
    files_path = scenario_golden / "files"
    assert tree_path.exists(), f"Missing golden tree snapshot: {tree_path}"
    assert files_path.exists(), f"Missing golden files snapshot: {files_path}"

    expected_tree = _normalize_text(tree_path.read_text(encoding="utf-8"))
    assert snapshot.tree_listing == expected_tree

    expected_files = sorted(path.relative_to(files_path).as_posix() for path in files_path.rglob("*") if path.is_file())
    actual_files = sorted(snapshot.text_files)
    assert actual_files == expected_files

    for relative_path, actual_contents in snapshot.text_files.items():
        expected_contents = _normalize_text((files_path / relative_path).read_text(encoding="utf-8"))
        assert actual_contents == expected_contents


def _write_snapshot(*, snapshot: GoldenSnapshot, scenario_golden: Path) -> None:
    tree_path = scenario_golden / "tree.txt"
    files_path = scenario_golden / "files"
    scenario_golden.mkdir(parents=True, exist_ok=True)
    tree_path.write_text(snapshot.tree_listing, encoding="utf-8")
    if files_path.exists():
        shutil.rmtree(files_path)
    for relative_path, contents in snapshot.text_files.items():
        destination = files_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(contents, encoding="utf-8")


def _normalize_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").replace("\\", "/")


def _update_mode_enabled() -> bool:
    value = os.getenv(UPDATE_GOLDEN_ENV, "")
    return value.lower() in {"1", "true", "yes", "on"}
