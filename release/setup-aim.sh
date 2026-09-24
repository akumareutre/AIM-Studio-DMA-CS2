#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

ready() {
    [[ -f .runtime/setup-v1 && -x .venv-aim/bin/python && -f .runtime/vmm/vmm.so ]] &&
        .venv-aim/bin/python -c 'import tkinter, serial, memprocfs' >/dev/null 2>&1
}
if [[ ${1:-} == --check ]]; then ready; exit $?; fi
if [[ ${1:-} == --help ]]; then
    echo 'Installation automatique AIM Studio DMA pour Debian/Ubuntu/Raspberry Pi OS 64 bits.'
    echo 'Usage : bash setup-aim.sh [--check]'
    exit 0
fi
if ready; then exit 0; fi
trap 'echo "Installation interrompue. Relancer START.sh pour reprendre." >&2' ERR
[[ $(uname -s) == Linux ]] || { echo 'Linux requis.' >&2; exit 1; }
case $(uname -m) in aarch64|x86_64) ;; *) echo 'OS ARM64 ou x86-64 requis.' >&2; exit 1 ;; esac
command -v apt-get >/dev/null || { echo 'Installateur prévu pour Debian, Ubuntu et Raspberry Pi OS.' >&2; exit 1; }
echo 'AIM Studio DMA — préparation du premier lancement'
echo 'Le mot de passe système peut être demandé pour les paquets et les accès USB.'
admin=()
if [[ $EUID != 0 ]]; then admin=(sudo); fi
missing=()
for package in python3 python3-venv python3-tk python3-dev build-essential libusb-1.0-0-dev ca-certificates libusb-1.0-0 libudev1 util-linux; do
    if [[ $(dpkg-query -W -f='${Status}' "$package" 2>/dev/null || true) != 'install ok installed' ]]; then
        missing+=("$package")
    fi
done
if (( ${#missing[@]} )); then
    "${admin[@]}" apt-get update
    "${admin[@]}" apt-get install -y "${missing[@]}"
fi
echo '[1/4] Environnement Python isolé…'
if [[ ! -x .venv-aim/bin/python ]]; then python3 -m venv .venv-aim; fi
.venv-aim/bin/python -m pip install --disable-pip-version-check --prefer-binary -r requirements-aim.txt
echo '[2/4] Bibliothèques DMA adaptées au processeur…'
.venv-aim/bin/python install_aim_runtime.py
echo '[3/4] Accès USB et série…'
rules=$(mktemp)
trap 'rm -f "$rules"' EXIT
cat > "$rules" <<'RULES'
SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{idVendor}=="0403", ATTR{idProduct}=="601f", MODE="0660", TAG+="uaccess"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", MODE="0660", TAG+="uaccess"
RULES
if ! cmp -s "$rules" /etc/udev/rules.d/70-aim-studio.rules; then
    "${admin[@]}" install -m 0644 "$rules" /etc/udev/rules.d/70-aim-studio.rules
    "${admin[@]}" udevadm control --reload-rules
    "${admin[@]}" udevadm trigger --subsystem-match=usb --action=change
    "${admin[@]}" udevadm trigger --subsystem-match=tty --action=change
    "${admin[@]}" udevadm settle
fi
echo '[4/4] Configuration et raccourci…'
if [[ ! -f aim-settings.conf ]]; then cp aim-settings.example.conf aim-settings.conf; fi
.venv-aim/bin/python - <<'PY'
from pathlib import Path
import os
import subprocess
root = Path.cwd()
launcher = str(root/'start-aim-menu.sh')
# Échappement Desktop Entry (espaces, guillemets, %, $, backslash, backtick).
escaped = launcher.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
entry = ('#!/usr/bin/env -S gio launch\n[Desktop Entry]\nType=Application\nName=AIM Studio DMA\n'
         'Comment=Contrôle CS2 DMA / KMBox\n'
         f'Exec=bash "{escaped}"\nIcon=input-gaming\nTerminal=false\nCategories=Utility;\n')
applications = Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share')))/'applications'
applications.mkdir(parents=True, exist_ok=True)
(applications/'aim-studio.desktop').write_text(entry)
try:
    desktop = subprocess.check_output(['xdg-user-dir', 'DESKTOP'], text=True).strip()
    if desktop and Path(desktop).is_dir() and Path(desktop) != Path.home():
        shortcut = Path(desktop)/'Aim Studio.desktop'
        shortcut.write_text(entry)
        shortcut.chmod(0o755)
except (OSError, subprocess.CalledProcessError):
    pass
PY
LD_LIBRARY_PATH="$PWD/.runtime/vmm${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
    .venv-aim/bin/python -c 'import tkinter, serial, memprocfs; import ctypes; ctypes.CDLL("leechcore_ft601_driver_linux.so")'
touch .runtime/setup-v1
echo 'Installation terminée. Ouverture du menu ; aucun moteur lancé automatiquement.'
