# prepmd

`prepmd` is a Typer + Rich CLI for scaffolding molecular dynamics simulation projects with:

- apo/holo variant support and multiple replicas
- engine support for Amber, NAMD, Gromacs, CHARMM, and OpenMM
- configurable force fields and water models (defaults: `ff19sb` + `OPC3`)
- default protocol stages for tapered minimization, NVT heating, tapered NPT equilibration, and
  multiple 100-ns production runs

## Quick start

```bash
prepmd prepare --project-name demo --output-dir .
```

or use a YAML/TOML config:

```bash
prepmd setup /path/to/config.yaml
```

You can also merge config file values with CLI overrides:

```bash
prepmd prepare --config /path/to/config.toml --engine gromacs --replicas 3
```

## Development workflow

- Environment management: `pixi.toml` (profiles: `dev`, `test`, `lint`, `type`, `docs`)
- Task automation: `noxfile.py`
- Checks and formatting: `ruff`, `basedpyright`, `typeguard`, `pytest`, `hypothesis`
- Git hooks: `.pre-commit-config.yaml`
- Documentation: Sphinx docs in `docs/` with ReadTheDocs config in `.readthedocs.yml`
