#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DISPLAY:-}" ]]; then
  echo "Error: DISPLAY is not set. For Linux X11 use: -e DISPLAY=\$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix" >&2
  exit 1
fi

if [[ $# -eq 0 ]]; then
  set -- --help
fi

if pixi run prepmd-gui --help >/dev/null 2>&1; then
  exec pixi run prepmd-gui "$@"
fi

echo "Error: 'prepmd-gui' entrypoint is not available in this revision. GUI image is best-effort and currently supports dependency/X11 setup only." >&2
echo "Try running CLI instead: docker run --rm prepmd:latest --help" >&2
exit 1
