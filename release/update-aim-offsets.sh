#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! bash setup-aim.sh --check; then bash setup-aim.sh; fi
source ./aim-environment.sh
pick_lang "$@"
if pgrep -f '(^|/)java .*CS2DMA-[^ ]*\.jar' >/dev/null || systemctl is-active --quiet memprocfs.service; then
    echo "$(tr_msg free_dma)" >&2
    exit 1
fi
options=(--device "$DEVICE")
if [[ -n ${MEMMAP:-} ]]; then options+=(--memmap "$MEMMAP"); fi
exec .venv-aim/bin/python update_aim_offsets.py "${options[@]}" "$@"
