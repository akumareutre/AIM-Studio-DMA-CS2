<div align="center">

# AIM Studio DMA
### By Akumaprog

**Un'interfaccia Linux per controllare la tua configurazione CS2 · DMA · KMBox**

[🇫🇷 Français](README.md) · [🇬🇧 English](README-en.md) · [🇪🇸 Español](README-es.md) · [🇩🇪 Deutsch](README-de.md) · [🇮🇹 Italiano](README-it.md) · [🇵🇹 Português](README-pt.md)

[Installazione](#installazione) · [Collegamenti](#collegamenti) · [Utilizzo](#utilizzo) · [Risoluzione dei problemi](#risoluzione-dei-problemi)

</div>
<img src="soft.png" alt="Logo" width="500">
---

## Presentazione

AIM Studio DMA riunisce la scelta del profilo, le impostazioni, il controllo del
motore e l'aggiornamento degli offset in un'interfaccia nativa. L'apertura del menu
non avvia il motore: il controllo resta a te con **Avvia**, **Sospendi** e **Ferma**.

- Tre profili: **Soft**, **Magnetico**, **Rage**.
- Cinque zone: testa, collo, petto, addome, bacino.
- Impostazioni di raggio, smussamento, frequenza e spostamento massimo.
- Opzioni di compensazione del rinculo e di visibilità geometrica.
- Lettura automatica della sensibilità di gioco per impostazione predefinita.
- Rilevamento automatico della porta KMBox quando è presente un solo dispositivo compatibile.
- Sei lingue, preferenze salvate e registro integrato.
- Installazione automatica delle dipendenze, isolate nella cartella dell'applicazione.

## Hardware e requisiti di sistema

| Elemento | Requisito |
| --- | --- |
| Macchina di controllo | Raspberry Pi con Raspberry Pi OS **64 bit**, o PC Linux **x86-64** con Debian/Ubuntu e desktop grafico |
| PC di gioco | PC che esegue CS2, dotato della scheda DMA compatibile con la tua configurazione |
| Scheda DMA | Scheda FPGA supportata da LeechCore/MemProcFS; l'installazione USB fornita punta alla **scheda ponte FT601, VID 0403 / PID 601f** |
| KMBox | Modello B/VerB o B Pro che esponga una console seriale compatibile con i comandi `km.*` usati qui |
| Collegamenti | Cavi USB **dati**, porte e alimentazione adatte ai dispositivi |
| Primo avvio | Internet, accesso ai sorgenti di sistema/PyPI/GitHub, diritti `sudo` |

Il software fornito è un'applicazione **Linux**. Non si installa direttamente su
Windows o macOS. Un sistema operativo ARM a 32 bit non è supportato.
Il riferimento testato in questo progetto è una **KMBox VerB, firmware 10.3.0, a 115200 baud**.
La compatibilità di una B Pro dipende dal firmware: il solo nome commerciale non
garantisce che la sua console offra lo stesso protocollo. Una KMBox Net non è un
sostituto diretto di questo collegamento seriale.

## Collegamenti

### 1. Scheda DMA

1. Spegni e scollega il PC di gioco prima di installare la scheda PCIe, seguendo il manuale del produttore.
2. Installa la scheda in uno slot compatibile, poi chiudi il case e riaccendi il PC.
3. Collega la **porta USB di trasferimento DMA** alla macchina Linux di controllo con un cavo dati adatto.
4. Se la scheda ha una porta di programmazione separata, individuala nel manuale: non sostituisce la porta di trasferimento.
5. La scheda deve avere un firmware funzionante ed essere riconosciuta da LeechCore/MemProcFS.

Il software non installa né flashat il firmware FPGA. Le procedure di
programmazione, alimentazione e configurazione del sistema host sono specifiche
del modello di scheda: usa la documentazione del produttore. Il driver USB
installato su Linux da solo non rende compatibile qualsiasi scheda.

### 2. KMBox B Pro / VerB

I nomi delle porte variano tra le revisioni; individua la loro **funzione** nel manuale.

1. Collega il mouse all'ingresso periferica della KMBox.
2. Per usare i tasti F6-F9 durante il gioco, collega anche la tastiera all'ingresso dedicato, se il tuo modello lo consente.
3. Collega l'uscita USB HID della KMBox al **PC di gioco**.
4. Collega la sua porta seriale di controllo alla **macchina Linux**.
5. Verifica che il mouse funzioni normalmente sul PC di gioco prima di avviare il motore.

```text
PC di gioco ← PCIe → Scheda DMA ← USB di trasferimento → Macchina di controllo
PC di gioco ← USB HID → KMBox  ← USB seriale         → AIM Studio DMA
                       ↑
                Mouse / tastiera
```

Il motore attende una console che includa `km.move`, `km.left` e i comandi di
lettura dei tasti, tra gli altri. L'apertura della porta può riavviare la KMBox:
il software attende la sua console fino a **25 secondi**. Non lasciare un monitor
seriale o un altro strumento KMBox aperto sulla stessa porta.

### 3. Driver e dipendenze

**Non devi scaricare questi componenti manualmente: il launcher li installa.**

| Componente | Installazione automatica |
| --- | --- |
| Interfaccia e ambiente Python | `python3`, `python3-venv`, `python3-tk` |
| Supporto di compilazione se non è disponibile un pacchetto binario | `build-essential`, `python3-dev`, `libusb-1.0-0-dev` |
| Supporto USB e di sistema | `libusb-1.0-0`, `libudev1`, `util-linux`, `ca-certificates` |
| Moduli Python | `memprocfs==5.18.10`, `leechcorepyc==2.23.3`, `pyserial==3.5` |
| Librerie native DMA | Archivio ufficiale MemProcFS 5.18.11 adattato ad ARM64/x86-64, verificato tramite SHA-256 |
| Trasporto FT601 | `leechcore_ft601_driver_linux.so`, estratto con le librerie native |
| Permessi USB/serie | Regole udev per FT601 `0403:601f` e interfacce seriali WCH `1a86` |

Su Linux, le interfacce seriali USB compatibili sono generalmente gestite dal
kernel (`ch341`, `cdc_acm`, a seconda del dispositivo). Sulla macchina Linux non è
necessario alcun installer di driver Windows CH340/CH341 o FTDI.
Un dispositivo con un altro ID USB può richiedere permessi adeguati.

## Installazione

### Primo avvio

1. Su GitHub, scegli **Code → Download ZIP**, poi estrai completamente l'archivio sulla macchina Linux.
2. Tieni la cartella in una posizione scrivibile, ad esempio la tua cartella home o il desktop.
3. Apri **AIM Studio DMA.desktop**. A seconda del desktop Linux, consenti prima l'esecuzione tramite **Proprietà → Permessi**, poi **Consenti l'avvio** se richiesto.
4. Un terminale mostra la preparazione. Inserisci la password di sistema se `sudo` la chiede e lascia terminare l'installazione.
5. Si apre il menu e viene aggiunto un collegamento **AIM Studio DMA** alle applicazioni e al desktop quando disponibile.
6. Dopo la prima installazione delle regole USB, scollega/ricallega le connessioni USB se i dispositivi non sono ancora accessibili.

Se il tuo file manager non avvia i file `.desktop`, apri un terminale **nella
cartella estratta** ed esegui:

```bash
bash START.sh
```

**Un solo avvio prepara il software; non è previsto alcun download manuale
aggiuntivo. Per questa prima installazione è necessaria una connessione Internet.**
Questo repository non è un pacchetto universale offline: le dipendenze vengono
scelte e scaricate per il tuo sistema. Gli avvii successivi riutilizzano l'installazione.
Se l'installazione viene interrotta, riesegui lo stesso launcher per continuare.
Su alcune configurazioni ARM64, MemProcFS e LeechCore vengono compilati automaticamente:
questa prima installazione può richiedere diversi minuti.

### Avvii successivi

Usa **AIM Studio DMA.desktop** nella cartella o il collegamento installato.
Il launcher fornito nella cartella trova `START.sh` automaticamente: puoi spostare o
rinominare l'intera cartella, anche in un percorso con spazi.
Tieni insieme il launcher, `START.sh` e `release/`.
I collegamenti esterni creati sul desktop e nelle applicazioni puntano alla
posizione di installazione; dopo uno spostamento, usa il launcher nella cartella.

## Utilizzo

1. Collega i dispositivi e apri CS2 sul PC di gioco.
2. Chiudi altri software che usano la stessa scheda DMA o la porta seriale KMBox.
3. Apri AIM Studio DMA e seleziona la tua lingua in alto a destra.
4. Scegli un profilo, una zona del corpo e le tue impostazioni.
5. Entra in una partita con un giocatore vivo, poi clicca su **Avvia**.
6. Consulta il registro per verificare la connessione DMA, la KMBox e il caricamento della mappa.

| Comando | Azione |
| --- | --- |
| Avvia | Esegue il motore con le impostazioni del menu |
| Clic sinistro fisico tenuto | Consente le correzioni; il software non invia il clic di sparo |
| Sospendi / Riprendi | Attiva/disattiva l'assistenza dal menu |
| F6 predefinito | Attiva/disattiva l'assistenza; F7/F8/F9/Mouse 4/Mouse 5 sono anche disponibili |
| Ferma | Ferma il motore e libera i dispositivi |
| Esc nel menu | Richiede l'arresto |
| Chiudere la finestra | Ferma i processi avviati dal menu |

Ferma il motore prima di modificarne le impostazioni. Per ricevere un collegamento
fisico durante il gioco, il dispositivo interessato deve passare attraverso la KMBox.
Preferenze e lingua vengono salvate localmente.

### Profili e geometria

- **Soft**: acquisizione entro un raggio attorno al mirino, con smussamento regolabile.
- **Magnetico**: acquisizione a tutto schermo e mantenimento del bersaglio durante il fuoco.
- **Rage**: acquisizione a tutto schermo con impostazioni di correzione più dirette.

Sono incluse dieci geometrie: Ancient, Anubis, Cache, Dust2, Inferno, Mills,
Mirage, Nuke, Train e Vertigo. Le cache di accelerazione `.bvh` vengono generate
localmente; il primo caricamento può richiedere più tempo.
Il controllo della geometria dipende dalla corrispondenza tra i file e la versione
attuale del gioco. Thera non è inclusa: il file disponibile era non valido.

### Sensibilità, risoluzione e porta seriale

Al primo avvio, `release/aim-settings.conf` viene creato dal modello fornito.

```ini
PORT=auto
BAUD=115200
WIDTH=1920
HEIGHT=1080
SENSITIVITY=0
M_YAW=0.022
M_PITCH=0.022
DEVICE=fpga
```

- **SENSITIVITY=0**: usa la sensibilità letta nel gioco. Non viene distribuita alcuna calibrazione personale dello sviluppatore.
- Una sensibilità esplicita forza questo valore. Se la lettura automatica non è valida, il motore ignora i movimenti e lo segnala.
- Adatta **WIDTH / HEIGHT** alla risoluzione di gioco.
- **PORT=auto** va bene quando è presente una sola porta compatibile. Altrimenti, indica il suo percorso stabile `/dev/serial/by-id/...`.
- `M_YAW` e `M_PITCH` sono coefficienti separati dalla sensibilità; lo zoom o particolari impostazioni di input possono modificare la conversione effettiva.

### Dopo un aggiornamento di CS2

Ferma il motore, chiudi gli altri client DMA ed entra in una partita con un
giocatore vivo. Clicca su **Aggiorna offsets**. Lo strumento cerca gli indirizzi,
verifica le letture e sostituisce `offsets.json` dopo la validazione.
Una copia precedente viene conservata in `.bak`. Se la validazione fallisce, i
vecchi valori restano: alcuni aggiornamenti richiedono un adattamento del software,
non solo degli offsets.

## Risoluzione dei problemi

| Sintomo | Verificare |
| --- | --- |
| Il launcher si apre in un editor | Consenti l'esecuzione o esegui `bash START.sh` dalla cartella |
| Errore di download | Internet, accesso a PyPI/GitHub/APT; riesegui per continuare |
| Sistema o processore rifiutato | Debian/Ubuntu/Raspberry Pi OS 64 bit, ARM64 o x86-64 |
| KMBox assente / più porte | Cavo dati, porta di controllo corretta, poi `PORT` nella configurazione |
| La KMBox non risponde | Firmware compatibile con `km.*`, baudrate, nessun altro monitor seriale; attendere fino a 25 s |
| Permesso USB negato | Ricollega il dispositivo dopo l'installazione; verifica il suo ID e le regole udev |
| DMA non disponibile | Porta USB corretta, firmware compatibile, scheda riconosciuta, nessun altro client DMA |
| In attesa di `cs2.exe/client.dll` | CS2 deve essere in esecuzione sulla macchina collegata alla scheda DMA |
| Nessuna correzione | Clic fisico, stato di sospensione, sensibilità valida, offsets e geometria; leggi il registro |
| Codice di uscita 75 | Un'altra istanza detiene già il blocco DMA |

Diagnostica hardware senza movimento, dalla cartella del software:

```bash
bash release/start-aim.sh --check --duration 10
```

Verifica dell'ambiente installato:

```bash
bash release/setup-aim.sh --check
```

La diagnostica hardware richiede i dispositivi collegati. Non sostituisce la
validazione del firmware o del cablaggio.

## Contenuto del repository

```text
AIM Studio DMA/
├── AIM Studio DMA.desktop   # Launcher grafico di prima installazione
├── START.sh                 # Punto di ingresso
├── README.md
├── .gitignore               # Esclude installazione e dati personali
└── release/
    ├── aim_*.py             # Interfaccia, traduzioni e moduli
    ├── dma_aim.py           # Motore
    ├── update_aim_offsets.py
    ├── *.sh                # Installazione e launcher
    ├── install_aim_runtime.py
    ├── requirements-aim.txt
    ├── aim-settings.example.conf
    ├── offsets.json
    └── maps/               # Geometrie necessarie per la visibilità
```

Puoi pubblicare **questa cartella** come radice del repository GitHub. Le
dipendenze installate, le cache e le preferenze sono escluse da `.gitignore`.
Per gli utenti, preferisci lo ZIP del repository o un archivio in GitHub Releases:
le geometrie rendono il repository voluminoso e non si prestano al caricamento web file per file.

## Componenti e crediti

- Interfaccia e integrazione: **Akumaprog**.
- Accesso DMA: [MemProcFS](https://github.com/ufrisk/MemProcFS) e [LeechCore](https://github.com/ufrisk/LeechCore), di Ulf Frisk.
- Collegamento seriale: [pySerial](https://github.com/pyserial/pyserial).
- Fonti di offsets e firme: [a2x/cs2-dumper](https://github.com/a2x/cs2-dumper).
- Geometrie ProCS2 tratte dal progetto [chao-shushu/CS2-DMA](https://github.com/chao-shushu/CS2-DMA), secondo la provenienza documentata nel progetto sorgente.

Le licenze delle librerie native sono conservate con la loro installazione in
`release/.runtime/vmm/`. I componenti di terze parti mantengono le rispettive licenze.
