import json
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

from prepmd.tools.generate_schema import build_project_schema, canonical_schema_json


def test_generated_schema_matches_golden_resource() -> None:
    expected = files("prepmd.resources").joinpath("prepmd.schema.json").read_text(encoding="utf-8")
    generated = canonical_schema_json(build_project_schema())
    assert generated == expected


def test_generate_schema_module_writes_stdout_json() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "prepmd.tools.generate_schema"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["title"] == "ProjectConfig"
    assert "properties" in payload


def test_generate_schema_module_writes_output_file(tmp_path: Path) -> None:
    output = tmp_path / "schema.json"
    subprocess.run(
        [sys.executable, "-m", "prepmd.tools.generate_schema", "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert output.read_text(encoding="utf-8") == files("prepmd.resources").joinpath("prepmd.schema.json").read_text(
        encoding="utf-8"
    )
