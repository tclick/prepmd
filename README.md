# prepmd

`prepmd` is a Typer + Rich CLI for scaffolding molecular dynamics simulation projects with:

- apo/holo variant support and multiple replicas
- engine support for Amber, NAMD, Gromacs, CHARMM, and OpenMM
- configurable force fields and water models (defaults: `ff19sb` + `OPC3`)
- default protocol stages for tapered minimization, NVT heating, tapered NPT equilibration, and
  multiple 100-ns production runs

## Quick start

```bash
prepmd prepare --project-name demo --output-dir . --pdb-file /path/to/input.pdb
```

or use a YAML/TOML config:

```bash
prepmd setup /path/to/config.yaml
```

You can also merge config file values with CLI overrides:

```bash
prepmd prepare --config /path/to/config.toml --engine gromacs --replicas 3
```

Water-box geometry can be selected from the CLI:

```bash
prepmd prepare --project-name demo --output-dir . --pdb-file /path/to/input.pdb --box-shape cubic --box-side-length 12.0
prepmd prepare --project-name demo --output-dir . --pdb-file /path/to/input.pdb --box-shape truncated_octahedron --box-edge-length 10.0
prepmd prepare --project-name demo --output-dir . --pdb-file /path/to/input.pdb --box-shape orthorhombic --box-dimensions 12 12 15
```

Download directly from the Protein Data Bank (cached locally):

```bash
prepmd prepare --project-name demo --output-dir . --pdb-id 1ABC
prepmd prepare --project-name demo --output-dir . --pdb-id 1ABC --pdb-cache-dir /path/to/cache
```

`--pdb-file` and `--pdb-id` are mutually exclusive. Exactly one input method must be provided.
Supported PDB IDs are 4 alphanumeric characters (for example `1ABC`).

Default cache location is `~/.cache/prepmd/pdb`. Cached files are plain `*.pdb` files and can be cleaned manually:

```bash
rm -f ~/.cache/prepmd/pdb/*.pdb
```

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
pdb_cache_dir = "/path/to/cache"

[water_box]
shape = "truncated_octahedron"
edge_length = 10.0
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
