# Commun aux lanceurs, à sourcer depuis release/.
if [[ -d .runtime/vmm ]]; then
    export LD_LIBRARY_PATH="$PWD/.runtime/vmm${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
else
    export LD_LIBRARY_PATH="$PWD/vmm${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
export PYTHONUNBUFFERED=1
source ./aim-settings.conf
DEVICE=${DEVICE:-fpga}
LOCK_DIR=${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}
mkdir -p -- "$LOCK_DIR"

# Langue des lanceurs : LANG_CODE de la config, sinon demandée par le menu
# via --lang, sinon français.
LANG_CODE=${LANG_CODE:-fr}

# Messages des lanceurs visibles dans le journal du menu (clé : code:message).
declare -A TR_MSG
TR_MSG[fr:close_radar]='Fermer le radar avec Ctrl+C avant de lancer la visée : même carte DMA.'
TR_MSG[en:close_radar]='Close the radar with Ctrl+C before starting aim: same DMA card.'
TR_MSG[es:close_radar]='Cierra el radar con Ctrl+C antes de lanzar la puntería: misma tarjeta DMA.'
TR_MSG[de:close_radar]='Schließe das Radar mit Ctrl+C, bevor du die Zielhilfe startest: gleiche DMA-Karte.'
TR_MSG[it:close_radar]='Chiudi il radar con Ctrl+C prima di avviare la mira: stessa scheda DMA.'
TR_MSG[pt:close_radar]='Feche o radar com Ctrl+C antes de iniciar a mira: mesma placa DMA.'
TR_MSG[fr:free_dma]='Fermer le radar / arrêter le service MemProcFS pour libérer le DMA.'
TR_MSG[en:free_dma]='Close the radar / stop the MemProcFS service to free the DMA.'
TR_MSG[es:free_dma]='Cierra el radar / detén el servicio MemProcFS para liberar el DMA.'
TR_MSG[de:free_dma]='Schließe das Radar / stoppe den MemProcFS-Dienst, um das DMA freizugeben.'
TR_MSG[it:free_dma]='Chiudi il radar / ferma il servizio MemProcFS per liberare il DMA.'
TR_MSG[pt:free_dma]='Feche o radar / pare o serviço MemProcFS para liberar o DMA.'
TR_MSG[fr:stop_memprocfs]='Arrêt du service MemProcFS pour libérer la carte DMA...'
TR_MSG[en:stop_memprocfs]='Stopping the MemProcFS service to free the DMA card...'
TR_MSG[es:stop_memprocfs]='Deteniendo el servicio MemProcFS para liberar la tarjeta DMA...'
TR_MSG[de:stop_memprocfs]='Stoppe den MemProcFS-Dienst, um die DMA-Karte freizugeben...'
TR_MSG[it:stop_memprocfs]='Fermo il servizio MemProcFS per liberare la scheda DMA...'
TR_MSG[pt:stop_memprocfs]='Parando o serviço MemProcFS para liberar a placa DMA...'
TR_MSG[fr:port_error]='KMBox absente ou plusieurs ports série : brancher le boîtier, ou renseigner PORT dans aim-settings.conf.'
TR_MSG[en:port_error]='KMBox missing or multiple serial ports: plug in the device, or set PORT in aim-settings.conf.'
TR_MSG[es:port_error]='KMBox ausente o varios puertos serie: conecta el dispositivo, o indica PORT en aim-settings.conf.'
TR_MSG[de:port_error]='KMBox fehlt oder mehrere serielle Ports: Gerät anschließen oder PORT in aim-settings.conf setzen.'
TR_MSG[it:port_error]='KMBox assente o più porte seriali: collega il dispositivo, oppure imposta PORT in aim-settings.conf.'
TR_MSG[pt:port_error]='KMBox ausente ou várias portas seriais: conecte o dispositivo ou defina PORT em aim-settings.conf.'
TR_MSG[fr:header]='CS2 DMA / KMBox — {w}x{h} — {port}'
TR_MSG[en:header]='CS2 DMA / KMBox — {w}x{h} — {port}'
TR_MSG[es:header]='CS2 DMA / KMBox — {w}x{h} — {port}'
TR_MSG[de:header]='CS2 DMA / KMBox — {w}x{h} — {port}'
TR_MSG[it:header]='CS2 DMA / KMBox — {w}x{h} — {port}'
TR_MSG[pt:header]='CS2 DMA / KMBox — {w}x{h} — {port}'
TR_MSG[fr:ctrl_c]='Arrêt : Ctrl+C. Corrections uniquement pendant le clic gauche physique.'
TR_MSG[en:ctrl_c]='Stop: Ctrl+C. Corrections only while the physical left button is held.'
TR_MSG[es:ctrl_c]='Detener: Ctrl+C. Correcciones solo mientras se mantiene el clic izquierdo físico.'
TR_MSG[de:ctrl_c]='Stopp: Ctrl+C. Korrekturen nur bei gehaltener physischer linker Maustaste.'
TR_MSG[it:ctrl_c]='Stop: Ctrl+C. Correzioni solo mentre il clic sinistro fisico è premuto.'
TR_MSG[pt:ctrl_c]='Parar: Ctrl+C. Correções apenas enquanto o clique esquerdo físico está pressionado.'
TR_MSG[fr:done]='\nProgramme terminé (code {code}). Entrée pour fermer.'
TR_MSG[en:done]='\nProgram finished (code {code}). Press Enter to close.'
TR_MSG[es:done]='\nPrograma finalizado (código {code}). Enter para cerrar.'
TR_MSG[de:done]='\nProgramm beendet (Code {code}). Enter zum Schließen.'
TR_MSG[it:done]='\nProgramma terminato (codice {code}). Invio per chiudere.'
TR_MSG[pt:done]='\nPrograma encerrado (código {code}). Enter para fechar.'

tr_msg() { # tr_msg CLÉ [nom=valeur …] — message traduit avec remplacements {nom}.
    local key=$1; shift
    local message=${TR_MSG[${LANG_CODE:-fr}:$key]}
    [[ -n $message ]] || message=${TR_MSG[fr:$key]}
    local pair name value
    for pair in "$@"; do
        name=${pair%%=*}
        value=${pair#*=}
        message=${message//\{$name\}/$value}
    done
    printf '%b\n' "$message"
}

pick_lang() { # lit --lang dans les arguments sans les modifier.
    local next_is_lang=0 arg
    for arg in "$@"; do
        if (( next_is_lang )); then
            LANG_CODE=$arg
            next_is_lang=0
            continue
        fi
        case "$arg" in
            --lang) next_is_lang=1 ;;
            --lang=*) LANG_CODE=${arg#--lang=} ;;
        esac
    done
    export LANG_CODE
}
