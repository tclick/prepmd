#!/usr/bin/env bash
set -euo pipefail

if ! command -v pixi >/dev/null 2>&1; then
  echo "Error: pixi is not installed in this container." >&2
  exit 1
fi

if [[ $# -eq 0 ]]; then
  exec pixi run prepmd --help
fi

if ! pixi run prepmd --help >/dev/null 2>&1; then
  echo "Error: prepmd environment is not ready. Rebuild the image with docker build -f docker/Dockerfile -t prepmd:latest ." >&2
  exit 1
fi

exec pixi run prepmd "$@"
