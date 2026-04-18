from prepmd.config.models import ProjectConfig, ProteinConfig
from prepmd.core.plan_fingerprint import compute_plan_sha256
from prepmd.core.run import build_plan


def test_plan_sha256_is_deterministic_across_runs() -> None:
    first = ProjectConfig(
        project_name="deterministic-demo", output_dir="/tmp/run-a", protein=ProteinConfig(pdb_file="/tmp/in.pdb")
    )
    second = ProjectConfig(
        project_name="deterministic-demo",
        output_dir="/tmp/run-b",
        protein=ProteinConfig(pdb_file="/tmp/in.pdb"),
    )

    first_plan = build_plan(first)
    second_plan = build_plan(second)

    assert compute_plan_sha256(first_plan) == compute_plan_sha256(second_plan)


def test_plan_sha256_normalizes_newlines() -> None:
    cfg = ProjectConfig(
        project_name="newline-demo", output_dir="/tmp/newline", protein=ProteinConfig(pdb_file="/tmp/in.pdb")
    )
    base_plan = build_plan(cfg)
    first_file = base_plan.files[0]
    crlf_plan = base_plan.__class__(
        config=base_plan.config,
        root_dir=base_plan.root_dir,
        directories=base_plan.directories,
        files=(first_file.__class__(path=first_file.path, content="a\r\nb\r\n"),),
        prepare_files=(),
    )
    lf_plan = base_plan.__class__(
        config=base_plan.config,
        root_dir=base_plan.root_dir,
        directories=base_plan.directories,
        files=(first_file.__class__(path=first_file.path, content="a\nb\n"),),
        prepare_files=(),
    )

    assert compute_plan_sha256(crlf_plan) == compute_plan_sha256(lf_plan)
