#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! bash setup-aim.sh --check; then bash setup-aim.sh; fi
source ./aim-environment.sh

if [[ ${1:-} == --desktop ]]; then
    shift
    pick_lang "$@"
    set +e
    bash ./start-aim.sh "$@"
    status=$?
    printf '%b\n' "$(tr_msg done code=$status)"
    read -r _
    exit "$status"
fi
pick_lang "$@"

if [[ ! -x .venv-aim/bin/python ]]; then bash setup-aim.sh; fi
if pgrep -f '(^|/)java .*CS2DMA-[^ ]*\.jar' >/dev/null; then
    echo "$(tr_msg close_radar)" >&2
    exit 1
fi
if systemctl is-active --quiet memprocfs.service; then
    echo "$(tr_msg stop_memprocfs)"
    sudo systemctl stop memprocfs.service
fi

if [[ ${PORT:-auto} == auto || ! -e ${PORT:-/absent} ]]; then
    shopt -s nullglob
    ports=(/dev/serial/by-id/usb-1a86* /dev/serial/by-id/*KMBox*)
    if (( ${#ports[@]} == 0 )); then ports=(/dev/ttyUSB* /dev/ttyACM*); fi
    if (( ${#ports[@]} != 1 )); then
        echo "$(tr_msg port_error)" >&2
        exit 1
    fi
    PORT=${ports[0]}
fi
options=(--offsets "$PWD/offsets.json" --device "$DEVICE")
if [[ ${SENSITIVITY:-0} != 0 ]]; then options+=(--sensitivity "$SENSITIVITY"); fi
if [[ -n ${MEMMAP:-} ]]; then options+=(--memmap "$MEMMAP"); fi
echo "$(tr_msg header w=$WIDTH h=$HEIGHT port=$PORT)"
echo "$(tr_msg ctrl_c)"
exec flock --no-fork --nonblock --conflict-exit-code 75 \
    "$LOCK_DIR/cs2-dma-aim-$(id -u).lock" \
    .venv-aim/bin/python dma_aim.py \
    --port "$PORT" --baud "$BAUD" --width "$WIDTH" --height "$HEIGHT" \
    --mode "${MODE:-magnetic}" --body "${BODY:-head}" \
    --m-yaw "${M_YAW:-0.022}" --m-pitch "${M_PITCH:-0.022}" "${options[@]}" "$@"
