# prepmd

`prepmd` is a Typer + Rich CLI for scaffolding molecular dynamics simulation projects with:

- apo/holo variant support and multiple replicas
- engine support for Amber, NAMD, Gromacs, CHARMM, and OpenMM
- configurable force fields and water models (defaults: `ff19sb` + `OPC3`)
- default protocol stages for tapered minimization, NVT heating, tapered NPT equilibration, and
  multiple 100-ns production runs

## Backend architecture (CLI + GUI shared)

`prepmd` now uses a UI-agnostic backend in `prepmd.core.run`:

- `build_plan(config) -> SimulationPlan` builds a deterministic in-memory plan (no filesystem writes)
- `apply_plan(plan, reporter)` applies the plan to disk with progress callbacks
- `run_setup(config, reporter)` validates then runs plan + apply

Reporter callbacks power both frontends:

- CLI uses Rich progress/log rendering.
- GUI can call `ConsoleWidget.run_backend_setup(...)` for direct backend execution and progress callbacks.
- Existing GUI subprocess mode remains available via `ConsoleWidget.run_cli(...)`.

## Quick start

```bash
prepmd prepare --project-name demo --output-dir . --pdb-file /path/to/input.pdb
```

Preview only (no project writes):

```bash
prepmd prepare --project-name demo --output-dir . --pdb-file /path/to/input.pdb --dry-run
```

or use a YAML/TOML config:

```bash
prepmd init --format yaml
prepmd setup /path/to/config.yaml
```

Both `prepare` and `setup` write `manifest.json` into the generated project root on apply runs.
The manifest includes environment metadata, config hash, input fingerprinting, and generated-file checksums.
Use `--debug-bundle /path/to/debug.zip` to collect config, plan preview, manifest, logs, and environment details.

You can also merge config file values with CLI overrides:

```bash
prepmd prepare --config /path/to/config.toml --engine gromacs --replicas 3
```

Water-box geometry can be selected from the CLI:

```bash
prepmd prepare --project-name demo --output-dir . --pdb-file /path/to/input.pdb --box-shape cubic --box-side-length 12.0
prepmd prepare --project-name demo --output-dir . --pdb-file /path/to/input.pdb --box-shape truncated_octahedron --box-edge-length 10.0
prepmd prepare --project-name demo --output-dir . --pdb-file /path/to/input.pdb --box-shape orthorhombic --box-dimensions 12 12 15
prepmd prepare --project-name demo --output-dir . --pdb-file /path/to/input.pdb --include-ions --neutralize-protein --ion-concentration 0.15 --ion-cation Na+ --ion-anion Cl-
```

Download directly from the Protein Data Bank (cached locally):

```bash
prepmd prepare --project-name demo --output-dir . --pdb-id 1ABC
prepmd prepare --project-name demo --output-dir . --apo-pdb-id 1ABC --holo-pdb-id 2XYZ
prepmd prepare --project-name demo --output-dir . --pdb-id 1ABC --pdb-cache-dir /path/to/cache
prepmd prepare --project-name demo --output-dir . --pdb-id 1ABC --offline --pdb-cache-dir /path/to/cache
```

`--pdb-file`/`--apo-pdb`/`--holo-pdb` and `--pdb-id`/`--apo-pdb-id`/`--holo-pdb-id` are mutually exclusive.
Exactly one input method must be provided.
Supported PDB IDs are 4 alphanumeric characters (for example `1ABC`).

Default cache location is `~/.cache/prepmd/pdb`. Cached files are plain `*.pdb` files and can be cleaned manually:

```bash
rm -f ~/.cache/prepmd/pdb/*.pdb
```

Use `--offline` (or config `protein.offline: true`) to force cache-only behavior for `pdb_id` inputs. If the PDB is not
already cached, prepmd exits with an actionable error and does not make network requests.

YAML config (local file):

```yaml
project_name: demo
protein:
  pdb_file: /path/to/input.pdb
```

TOML config (download by PDB ID):

```toml
project_name = "demo"
[protein]
pdb_id = "1ABC"
pdb_ids = { apo = "1ABC", holo = "2XYZ" }
pdb_cache_dir = "/path/to/cache"
offline = true

[water_box]
shape = "truncated_octahedron"
edge_length = 10.0
include_ions = true
neutralize_protein = true
ion_concentration_molar = 0.15
cation = "Na+"
anion = "Cl-"
```

## Development workflow

- Environment management: `pixi.toml` (profiles: `dev`, `test`, `lint`, `type`, `docs`)
- Task automation: `noxfile.py`
- Checks and formatting: `ruff`, `basedpyright`, `typeguard`, `pytest`, `hypothesis`
- Git hooks: `.pre-commit-config.yaml`
- Documentation: Sphinx docs in `docs/` with ReadTheDocs config in `.readthedocs.yml`

## Docker

Containerized CLI/dev/CI/gui (best-effort) workflows are documented in
[`docker/README.md`](docker/README.md).

## Desktop app builds (macOS + Windows)

This repository includes a GitHub Actions workflow at
`.github/workflows/desktop-apps.yml` that builds the GUI app for:

- macOS (`prepmd-gui.app` zipped as `prepmd-gui-macos.zip`)
- Windows (`prepmd-gui.exe` bundle zipped as `prepmd-gui-windows.zip`)

Run it from **Actions → Build Desktop Apps → Run workflow** and download the
artifacts from the workflow run summary.
