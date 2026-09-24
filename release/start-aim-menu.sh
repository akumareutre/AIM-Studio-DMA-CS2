#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! bash setup-aim.sh --check; then bash setup-aim.sh; fi
source ./aim-environment.sh
exec .venv-aim/bin/python aim_menu.py "$@"
