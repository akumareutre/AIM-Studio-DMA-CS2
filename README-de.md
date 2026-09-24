<div align="center">

# AIM Studio DMA
### By Akumaprog

**Eine Linux-Oberfläche für dein CS2 · DMA · KMBox-Setup**

[🇫🇷 Français](README.md) · [🇬🇧 English](README-en.md) · [🇪🇸 Español](README-es.md) · [🇩🇪 Deutsch](README-de.md) · [🇮🇹 Italiano](README-it.md) · [🇵🇹 Português](README-pt.md)

[Installation](#installation) · [Verkabelung](#verkabelung) · [Nutzung](#nutzung) · [Fehlerbehebung](#fehlerbehebung)

</div>
<img src="soft.png" alt="Logo" width="500">
---

## Überblick

AIM Studio DMA bündelt Profilwahl, Einstellungen, Motorsteuerung und
Offset-Updates in einer nativen Oberfläche. Das Öffnen des Menüs startet den
Motor nicht: Du behältst die Kontrolle mit **Start**, **Pausieren** und **Stopp**.

- Drei Profile: **Soft**, **Magnetisch**, **Rage**.
- Fünf Zonen: Kopf, Hals, Brust, Bauch, Becken.
- Einstellbarer Radius, Glättung, Frequenz und maximale Schrittweite.
- Optionen für Rückstoßkompensation und geometrische Sichtbarkeit.
- Automatische Auslesung der Spielempfindlichkeit standardmäßig.
- Automatische Erkennung des KMBox-Ports bei nur einem kompatiblen Gerät.
- Sechs Sprachen, gespeicherte Einstellungen und integriertes Protokoll.
- Automatische Installation der Abhängigkeiten, isoliert im Anwendungsordner.

## Hardware und Systemanforderungen

| Komponente | Anforderung |
| --- | --- |
| Steuerungsrechner | Raspberry Pi mit Raspberry Pi OS **64-Bit** oder Linux-PC **x86-64** mit Debian/Ubuntu und grafischer Oberfläche |
| Spiel-PC | PC mit CS2, ausgestattet mit der zu deinem Setup passenden DMA-Karte |
| DMA-Karte | FPGA-Karte, unterstützt von LeechCore/MemProcFS; die mitgelieferte USB-Inbetriebnahme zielt auf die **FT601-Brücke, VID 0403 / PID 601f** |
| KMBox | Modell B/VerB oder B Pro mit serieller Konsole, kompatibel mit den hier verwendeten `km.*`-Befehlen |
| Verbindungen | **Daten-**USB-Kabel, passende Anschlüsse und Stromversorgung |
| Erster Start | Internet, Zugriff auf System-/PyPI-/GitHub-Quellen, `sudo`-Rechte |

Die ausgelieferte Software ist eine **Linux**-Anwendung. Sie lässt sich nicht direkt
unter Windows oder macOS installieren. Ein 32-Bit-ARM-Betriebssystem wird nicht unterstützt.
Die in diesem Projekt getestete Referenz ist eine **KMBox VerB, Firmware 10.3.0, mit 115200 Baud**.
Die Kompatibilität einer B Pro hängt von ihrer Firmware ab: Allein der Produktname
garantiert nicht, dass ihre Konsole dasselbe Protokoll bietet. Eine KMBox Net ist
kein direkter Ersatz für diese serielle Verbindung.

## Verkabelung

### 1. DMA-Karte

1. Schalte den Spiel-PC aus und ziehe den Netzstecker, bevor du die PCIe-Karte installierst — gemäß Handbuch des Herstellers.
2. Setze die Karte in einen kompatiblen Steckplatz ein, schließe das Gehäuse und schalte den PC wieder ein.
3. Verbinde den **USB-Transferport des DMA** mit einem geeigneten Datenkabel mit dem Linux-Steuerungsrechner.
4. Hat die Karte einen separaten Programmierport, findest du ihn im Handbuch: Er ersetzt den Transferport nicht.
5. Die Karte benötigt eine funktionierende Firmware und muss von LeechCore/MemProcFS erkannt werden.

Die Software installiert und flasht die FPGA-Firmware nicht. Programmierung,
Stromversorgung und Konfiguration des Host-Rechners sind modellspezifisch: Nutze
die Dokumentation des Herstellers. Der auf Linux installierte USB-Treiber allein
macht nicht jede Karte kompatibel.

### 2. KMBox B Pro / VerB

Die Portnamen variieren je nach Revision; erkenne ihre **Funktion** im Handbuch.

1. Schließe die Maus an den Geräteeingang der KMBox an.
2. Um die Tasten F6 bis F9 im Spiel zu nutzen, schließe auch die Tastatur an den dafür vorgesehenen Eingang an, falls dein Modell das erlaubt.
3. Verbinde den USB-HID-Ausgang der KMBox mit dem **Spiel-PC**.
4. Verbinde ihren seriellen Steuerport mit der **Linux-Maschine**.
5. Prüfe, dass die Maus auf dem Spiel-PC normal funktioniert, bevor du den Motor startest.

```text
Spiel-PC ← PCIe → DMA-Karte ← USB-Transfer → Steuerungsrechner
Spiel-PC ← USB HID → KMBox  ← USB-Seriell → AIM Studio DMA
                       ↑
                Maus / Tastatur
```

Der Motor erwartet eine Konsole mit unter anderem `km.move`, `km.left` und den
Befehlen zum Auslesen der Tasten. Das Öffnen des Ports kann die KMBox neu starten:
Die Software wartet bis zu **25 Sekunden** auf ihre Konsole. Lasse keinen
seriellen Monitor oder ein anderes KMBox-Tool auf demselben Port offen.

### 3. Treiber und Abhängigkeiten

**Diese Komponenten musst du nicht manuell herunterladen: Der Launcher installiert sie.**

| Komponente | Automatische Installation |
| --- | --- |
| Oberfläche und Python-Umgebung | `python3`, `python3-venv`, `python3-tk` |
| Build-Unterstützung, falls kein Binärpaket verfügbar ist | `build-essential`, `python3-dev`, `libusb-1.0-0-dev` |
| USB- und Systemunterstützung | `libusb-1.0-0`, `libudev1`, `util-linux`, `ca-certificates` |
| Python-Module | `memprocfs==5.18.10`, `leechcorepyc==2.23.3`, `pyserial==3.5` |
| Native DMA-Bibliotheken | Offizielles MemProcFS-5.18.11-Archiv für ARM64/x86-64, per SHA-256 verifiziert |
| FT601-Transport | `leechcore_ft601_driver_linux.so`, zusammen mit den nativen Bibliotheken extrahiert |
| USB-/Seriell-Rechte | udev-Regeln für FT601 `0403:601f` und WCH-`1a86`-Schnittstellen |

Unter Linux werden kompatible USB-Serielle-Schnittstellen meist vom Kernel
übernommen (`ch341`, `cdc_acm`, je nach Gerät). Auf der Linux-Maschine ist kein
Windows-Treiberinstaller für CH340/CH341 oder FTDI nötig.
Ein Gerät mit anderer USB-ID kann passende Berechtigungen erfordern.

## Installation

### Erster Start

1. Wähle auf GitHub **Code → Download ZIP** und entpacke das Archiv vollständig auf der Linux-Maschine.
2. Lege den Ordner an einen beschreibbaren Ort, zum Beispiel in dein Home-Verzeichnis oder auf den Schreibtisch.
3. Öffne **AIM Studio DMA.desktop**. Je nach Linux-Desktop erlaubst du zuerst die Ausführung unter **Eigenschaften → Berechtigungen** und dann **Ausführen erlauben**, falls gefragt.
4. Ein Terminal zeigt die Vorbereitung. Gib das Systempasswort ein, falls `sudo` danach fragt, und lass die Installation beenden.
5. Das Menü öffnet sich und ein **AIM Studio DMA**-Verknüpfung wird zu den Anwendungen und, falls vorhanden, zum Schreibtisch hinzugefügt.
6. Nach der ersten Installation der USB-Regeln: Ziehe die USB-Verbindungen ab und wieder an, falls die Geräte noch nicht erreichbar sind.

Falls dein Dateimanager keine `.desktop`-Dateien ausführt, öffne ein Terminal
**im entpackten Ordner** und führe aus:

```bash
bash START.sh
```

**Ein einziger Start bereitet die Software vor; kein weiterer manueller Download
ist vorgesehen. Für diese erste Installation ist eine Internetverbindung nötig.**
Dieses Repository ist kein universelles Offline-Paket: Die Abhängigkeiten werden
für dein System ausgewählt und heruntergeladen. Spätere Starts nutzen die Installation erneut.
Wird die Installation unterbrochen, starte denselben Launcher erneut, um fortzufahren.
Auf manchen ARM64-Systemen werden MemProcFS und LeechCore automatisch kompiliert:
Diese erste Installation kann mehrere Minuten dauern.

### Spätere Starts

Nutze **AIM Studio DMA.desktop** im Ordner oder die installierte Verknüpfung.
Der im Ordner enthaltene Launcher findet `START.sh` automatisch: Du kannst den
gesamten Ordner verschieben oder umbenennen, auch in einen Pfad mit Leerzeichen.
Bewahre Launcher, `START.sh` und `release/` zusammen auf.
Externe Verknüpfungen auf dem Schreibtisch und in den Anwendungen zeigen auf den
Installationsort; nach dem Verschieben nutze den Launcher im Ordner.

## Nutzung

1. Verbinde die Geräte und öffne CS2 auf dem Spiel-PC.
2. Schließe andere Software, die dieselbe DMA-Karte oder den KMBox-Seriellport nutzt.
3. Öffne AIM Studio DMA und wähle oben rechts deine Sprache.
4. Wähle ein Profil, eine Körperzone und deine Einstellungen.
5. Begib dich in ein Match mit einem lebenden Spieler und klicke auf **Start**.
6. Prüfe im Protokoll die DMA-Verbindung, die KMBox und das Laden der Karte.

| Befehl | Aktion |
| --- | --- |
| Start | Startet den Motor mit den Menüeinstellungen |
| Physische linke Maustaste gedrückt | Erlaubt Korrekturen; die Software sendet keinen Schussklick |
| Pausieren / Fortsetzen | Schaltet die Hilfestellung über das Menü um |
| F6 standardmäßig | Schaltet die Hilfestellung um; F7/F8/F9/Maus 4/Maus 5 sind ebenfalls verfügbar |
| Stopp | Stoppt den Motor und gibt die Geräte frei |
| Esc im Menü | Fordert den Stopp an |
| Fenster schließen | Stoppt die vom Menü gestarteten Prozesse |

Stoppe den Motor, bevor du seine Einstellungen änderst. Um während des Spiels eine
physische Verknüpfung zu empfangen, muss das betreffende Gerät durch die KMBox laufen.
Einstellungen und Sprache werden lokal gespeichert.

### Profile und Geometrie

- **Soft**: Erfassung innerhalb eines Radius um das Fadenkreuz, mit einstellbarer Glättung.
- **Magnetisch**: Erfassung über den gesamten Bildschirm und Zielbeibehaltung beim Schießen.
- **Rage**: Erfassung über den gesamten Bildschirm mit direkteren Korrektureinstellungen.

Zehn Geometrien sind enthalten: Ancient, Anubis, Cache, Dust2, Inferno, Mills,
Mirage, Nuke, Train und Vertigo. Die `.bvh`-Beschleunigungs-Caches werden lokal
erzeugt; der erste Ladevorgang kann länger dauern.
Die Geometrieprüfung hängt davon ab, wie gut die Dateien zum aktuellen Spielstand passen.
Thera ist nicht enthalten: Die verfügbare Datei war ungültig.

### Empfindlichkeit, Auflösung und serieller Port

Beim ersten Start wird `release/aim-settings.conf` aus der Vorlage erstellt.

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

- **SENSITIVITY=0**: nutzt die im Spiel ausgelesene Empfindlichkeit. Es wird keine persönliche Kalibrierung des Entwicklers verteilt.
- Eine explizite Empfindlichkeit erzwingt diesen Wert. Ist die automatische Auslesung ungültig, ignoriert der Motor Bewegungen und meldet dies.
- Passe **WIDTH / HEIGHT** an die Spielauflösung an.
- **PORT=auto** passt, wenn nur ein kompatibler Port vorhanden ist. Andernfalls trage den stabilen Pfad `/dev/serial/by-id/...` ein.
- `M_YAW` und `M_PITCH` sind von der Empfindlichkeit getrennte Koeffizienten; Zoom oder besondere Eingabeeinstellungen können die effektive Umrechnung verändern.

### Nach einem CS2-Update

Stoppe den Motor, schließe die anderen DMA-Clients und begib dich in ein Match
mit einem lebenden Spieler. Klicke auf **Offsets aktualisieren**. Das Werkzeug
sucht die Adressen, prüft die Lesevorgänge und ersetzt `offsets.json` nach der Validierung.
Eine frühere Kopie bleibt als `.bak` erhalten. Schlägt die Validierung fehl,
bleiben die alten Werte: Manche Updates erfordern eine Anpassung der Software,
nicht nur der Offsets.

## Fehlerbehebung

| Symptom | Zu prüfen |
| --- | --- |
| Der Launcher öffnet sich in einem Editor | Ausführung erlauben oder `bash START.sh` aus dem Ordner ausführen |
| Download-Fehler | Internet, Zugriff auf PyPI/GitHub/APT-Quellen; erneut starten zum Fortsetzen |
| OS oder Prozessor abgelehnt | Debian/Ubuntu/Raspberry Pi OS 64-Bit, ARM64 oder x86-64 |
| KMBox fehlt / mehrere Ports | Datenkabel, richtiger Steuerport, dann `PORT` in der Konfiguration |
| KMBox reagiert nicht | `km.*`-kompatible Firmware, Baudrate, kein anderer serieller Monitor; bis zu 25 s warten |
| USB-Berechtigung verweigert | Gerät nach der Installation neu anschließen; ID und udev-Regeln prüfen |
| DMA nicht verfügbar | Richtiger USB-Port, kompatible Firmware, erkannte Karte, kein anderer DMA-Client |
| Warte auf `cs2.exe/client.dll` | CS2 muss auf der mit der DMA-Karte verbundenen Maschine laufen |
| Keine Korrektur | Physischer Klick, Pausenzustand, gültige Empfindlichkeit, Offsets und Geometrie; Protokoll lesen |
| Exit-Code 75 | Eine andere Instanz hält bereits die DMA-Sperre |

Hardware-Diagnose ohne Bewegung, aus dem Software-Ordner:

```bash
bash release/start-aim.sh --check --duration 10
```

Prüfung der installierten Umgebung:

```bash
bash release/setup-aim.sh --check
```

Die Hardware-Diagnose erfordert angeschlossene Geräte. Sie ersetzt keine Validierung
deiner Firmware oder deiner Verkabelung.

## Repository-Inhalt

```text
AIM Studio DMA/
├── AIM Studio DMA.desktop   # Grafischer Launcher für die Erstinstallation
├── START.sh                 # Einstiegspunkt
├── README.md
├── .gitignore               # Schließt Installation und persönliche Daten aus
└── release/
    ├── aim_*.py             # Oberfläche, Übersetzungen und Module
    ├── dma_aim.py           # Motor
    ├── update_aim_offsets.py
    ├── *.sh                # Installation und Launcher
    ├── install_aim_runtime.py
    ├── requirements-aim.txt
    ├── aim-settings.example.conf
    ├── offsets.json
    └── maps/               # Für die Sichtbarkeit benötigte Geometrien
```

Du kannst **diesen Ordner** als Wurzel des GitHub-Repositories veröffentlichen.
Installierte Abhängigkeiten, Caches und Einstellungen werden durch `.gitignore` ausgeschlossen.
Für Nutzer bevorzuge das Repository-ZIP oder ein Archiv in GitHub Releases: Die
Geometrien machen das Repository groß und eignen sich nicht für einzelne Web-Uploads.

## Komponenten und Danksagungen

- Oberfläche und Integration: **Akumaprog**.
- DMA-Zugriff: [MemProcFS](https://github.com/ufrisk/MemProcFS) und [LeechCore](https://github.com/ufrisk/LeechCore), von Ulf Frisk.
- Serielle Verbindung: [pySerial](https://github.com/pyserial/pyserial).
- Offset- und Signaturquellen: [a2x/cs2-dumper](https://github.com/a2x/cs2-dumper).
- ProCS2-Geometrien aus dem Projekt [chao-shushu/CS2-DMA](https://github.com/chao-shushu/CS2-DMA), gemäß der im Quellprojekt dokumentierten Herkunft.

Die Lizenzen der nativen Bibliotheken werden mit ihrer Installation in
`release/.runtime/vmm/` aufbewahrt. Drittkomponenten behalten ihre jeweiligen Lizenzen.
