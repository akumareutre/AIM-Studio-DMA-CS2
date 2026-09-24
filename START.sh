#!/usr/bin/env bash
# Point d'entrée pour un téléchargement ZIP ou un clone neuf.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ${1:-} == --installer-terminal ]]; then
    shift
elif [[ ! -t 0 ]] && ! bash release/setup-aim.sh --check; then
    # Passer une commande unique au terminal : LXTerminal réinterprète -e.
    # La fenêtre principale, une fois installée, n'a pas besoin de terminal.
    printf -v command '%q ' bash "$PWD/START.sh" --installer-terminal "$@"
    exec x-terminal-emulator -e "$command"
fi
if ! bash release/setup-aim.sh --check; then
    if bash release/setup-aim.sh; then
        :
    else
        status=$?
        printf '\nInstallation échouée (code %s). Entrée pour fermer.\n' "$status" >&2
        if [[ -t 0 ]]; then read -r _ || true; fi
        exit "$status"
    fi
fi
exec bash release/start-aim-menu.sh "$@"
