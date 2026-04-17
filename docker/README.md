# Docker usage for `prepmd`

This directory provides Docker workflows for reproducible CLI usage, development, CI checks, and best-effort GUI support.

> License: images include `LICENSE.md` and this project is GPL-3.0-or-later.

## 1) Build images

From the repository root (`/home/runner/work/prepmd/prepmd`):

```bash
docker build -f docker/Dockerfile -t prepmd:latest .
docker build -f docker/Dockerfile.dev -t prepmd-dev:latest .
docker build -f docker/Dockerfile.gui -t prepmd-gui:latest .
```

## 2) CLI container usage

Run help:

```bash
docker run --rm -v "$(pwd)":/work prepmd:latest --help
```

Run setup/prepare (inputs and outputs under the mounted folder):

```bash
docker run --rm -v "$(pwd)":/work prepmd:latest prepare \
  --project-name demo --output-dir /work --pdb-id 1ABC
```

### Using compose (CLI)

```bash
docker compose -f docker/docker-compose.yml run --rm prepmd --help
```

Optional env vars in compose:

- `PREPMD_WORKDIR` host path mounted to `/work`
- `PREPMD_OUTPUT_DIR` output location inside container (`/work` by default)
- `PREPMD_PDB_CACHE_DIR` cache location inside container (`/work/.cache/prepmd/pdb` by default)

## 3) Development container

Open an interactive shell with repo mounted at `/work`:

```bash
docker compose -f docker/docker-compose.dev.yml run --rm prepmd-dev
```

Inside container, run nox sessions through pixi:

```bash
pixi run -e dev nox -s lint
pixi run -e dev nox -s type
pixi run -e dev nox -s test
pixi run -e dev nox -s docs
```

## 4) GUI image (best-effort)

The GUI image installs common Qt/X11 runtime libraries and forwards `DISPLAY`.

### Linux X11 forwarding

```bash
xhost +local:docker
docker compose -f docker/docker-compose.gui.yml run --rm prepmd-gui
```

Then revoke access if desired:

```bash
xhost -local:docker
```

### Headless/noVNC mode

Not bundled in this repository image. Use an external desktop/noVNC wrapper image if browser-based GUI access is required.

### Current limitation

This repository revision does not expose a stable `prepmd-gui` command yet; the GUI image is provided as a dependency/runtime foundation for future GUI entrypoints.

## 5) CI container checks

GitHub Actions workflow: `.github/workflows/docker-build-test.yml`

It builds `docker/Dockerfile` with layer caching and runs inside the built image:

- `nox -s lint`
- `nox -s type`
- `nox -s test`
- `nox -s docs`

(Executed via `pixi run -e dev nox -s ...`.)

## 6) Security notes

- Do not bake secrets into images (`ARG`/`ENV` credentials are intentionally avoided).
- Proprietary MD engines are not bundled; users should provide their own licensed tools when needed.
