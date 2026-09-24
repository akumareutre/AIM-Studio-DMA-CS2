<div align="center">

# AIM Studio DMA
### By Akumaprog

**A Linux interface to control your CS2 · DMA · KMBox setup**

[🇫🇷 Français](README.md) · [🇬🇧 English](README-en.md) · [🇪🇸 Español](README-es.md) · [🇩🇪 Deutsch](README-de.md) · [🇮🇹 Italiano](README-it.md) · [🇵🇹 Português](README-pt.md)

[Installation](#installation) · [Wiring](#wiring) · [Usage](#usage) · [Troubleshooting](#troubleshooting)

</div>
<img src="soft.png" alt="Logo" width="500">
---

## Overview

AIM Studio DMA brings profile selection, settings, engine control and offset updates
into a native interface. Opening the menu does not start the engine: you stay in
control with **Start**, **Suspend** and **Stop**.

- Three profiles: **Soft**, **Magnetic**, **Rage**.
- Five zones: head, neck, chest, stomach, pelvis.
- Adjustable radius, smoothing, frequency and maximum step.
- Recoil compensation and geometric visibility options.
- Automatic game sensitivity reading by default.
- Automatic KMBox port detection when a single compatible device is present.
- Six languages, saved preferences and built-in log.
- Automatic dependency installation, kept inside the application folder.

## Hardware and system requirements

| Component | Requirement |
| --- | --- |
| Control machine | Raspberry Pi running Raspberry Pi OS **64-bit**, or a Linux **x86-64** PC running Debian/Ubuntu with a graphical desktop |
| Gaming PC | PC running CS2, equipped with the DMA card compatible with your setup |
| DMA card | FPGA card supported by LeechCore/MemProcFS; the provided USB bring-up targets the **FT601 bridge, VID 0403 / PID 601f** |
| KMBox | B/VerB or B Pro model exposing a serial console compatible with the `km.*` commands used here |
| Connections | **Data** USB cables, ports and power suited to the devices |
| First launch | Internet, access to system/PyPI/GitHub sources, `sudo` rights |

The delivered software is a **Linux** application. It does not install directly on
Windows or macOS. A 32-bit ARM OS is not supported.
The reference tested in this project is a **KMBox VerB, firmware 10.3.0, at 115200 baud**.
B Pro compatibility depends on its firmware: the product name alone does not
guarantee that its console provides the same protocol. A KMBox Net is not a direct
replacement for this serial link.

## Wiring

### 1. DMA card

1. Power off and unplug the gaming PC before installing the PCIe card, following the manufacturer's manual.
2. Install the card in a compatible slot, then close the case and power the PC back on.
3. Connect the **DMA transfer USB port** to the control Linux machine with a suitable data cable.
4. If the card has a separate programming port, identify it in its manual: it does not replace the transfer port.
5. The card must have a working firmware and be recognized by LeechCore/MemProcFS.

The software does not install or flash the FPGA firmware. Programming, power and
host-machine configuration procedures are specific to the card model: use the
manufacturer's documentation. The USB driver installed on Linux alone is not
enough to make any card compatible.

### 2. KMBox B Pro / VerB

Port names vary between revisions; identify their **function** in the manual.

1. Connect the mouse to the KMBox device input.
2. To use the F6-F9 keys while in game, also connect the keyboard to the dedicated input, if your model supports it.
3. Connect the KMBox USB HID output to the **gaming PC**.
4. Connect its serial control port to the **Linux machine**.
5. Check that the mouse works normally on the gaming PC before starting the engine.

```text
Gaming PC ← PCIe → DMA card ← USB transfer → Control machine
Gaming PC ← USB HID → KMBox  ← USB serial  → AIM Studio DMA
                       ↑
                Mouse / keyboard
```

The engine expects a console providing `km.move`, `km.left` and the key-reading
commands, among others. Opening the port may reboot the KMBox: the software waits
for its console up to **25 seconds**. Do not leave a serial monitor or another
KMBox tool open on the same port.

### 3. Drivers and dependencies

**You do not have to download these components manually: the launcher installs them.**

| Component | Automatic installation |
| --- | --- |
| GUI and Python environment | `python3`, `python3-venv`, `python3-tk` |
| Build support when no binary package is available | `build-essential`, `python3-dev`, `libusb-1.0-0-dev` |
| USB and system support | `libusb-1.0-0`, `libudev1`, `util-linux`, `ca-certificates` |
| Python modules | `memprocfs==5.18.10`, `leechcorepyc==2.23.3`, `pyserial==3.5` |
| Native DMA libraries | Official MemProcFS 5.18.11 archive adapted to ARM64/x86-64, SHA-256 verified |
| FT601 transport | `leechcore_ft601_driver_linux.so`, extracted with the native libraries |
| USB/serial permissions | udev rules for FT601 `0403:601f` and WCH `1a86` serial interfaces |

On Linux, compatible USB serial interfaces are usually handled by the kernel
(`ch341`, `cdc_acm`, depending on the device). No Windows CH340/CH341 or FTDI
driver installer is needed on the Linux machine. A device using another USB ID
may require appropriate permissions.

## Installation

### First launch

1. On GitHub, choose **Code → Download ZIP**, then extract the archive completely on the Linux machine.
2. Keep the folder in a writable location, for example your home folder or the Desktop.
3. Open **AIM Studio DMA.desktop**. Depending on the Linux desktop, first allow its execution via **Properties → Permissions**, then **Allow launching** if prompted.
4. A terminal shows the preparation. Enter the system password if `sudo` asks for it and let the installation finish.
5. The menu opens and an **AIM Studio DMA** shortcut is added to the applications and to the Desktop when available.
6. After the first installation of the USB rules, unplug/replug the USB connections if the devices are not accessible yet.

If your file manager does not launch `.desktop` files, open a terminal **inside the
extracted folder** and run:

```bash
bash START.sh
```

**A single launch prepares the software; no additional manual download is planned.
An Internet connection is still required for this first installation.**
This repository is not a universal offline package: dependencies are selected and
downloaded for your system. Subsequent launches reuse the installation.
If the installation is interrupted, run the same launcher again to resume.
On some ARM64 setups, MemProcFS and LeechCore are compiled automatically:
this first installation may take several minutes.

### Subsequent launches

Use **AIM Studio DMA.desktop** in the folder or the installed shortcut.
The launcher provided in the folder finds `START.sh` automatically: you can move or
rename the whole folder, including into a path with spaces.
Keep the launcher, `START.sh` and `release/` together.
External shortcuts created on the Desktop and in the applications point to the
installation location; after moving the folder, use the in-folder launcher.

## Usage

1. Connect the devices and open CS2 on the gaming PC.
2. Close other software using the same DMA card or the KMBox serial port.
3. Open AIM Studio DMA and select your language at the top right.
4. Choose a profile, a body zone and your settings.
5. Join a match with a living player, then click **Start**.
6. Check the log for the DMA connection, the KMBox and the map loading.

| Command | Action |
| --- | --- |
| Start | Runs the engine with the menu settings |
| Physical left click held | Allows corrections; the software does not send trigger clicks |
| Suspend / Resume | Toggles the assistance from the menu |
| F6 by default | Toggles assistance; F7/F8/F9/Mouse 4/Mouse 5 are also offered |
| Stop | Stops the engine and releases the devices |
| Esc in the menu | Requests the stop |
| Close the window | Stops the processes launched by the menu |

Stop the engine before changing its settings. To receive a physical shortcut while
in game, the corresponding device must go through the KMBox.
Preferences and language are saved locally.

### Profiles and geometry

- **Soft**: acquisition within a radius around the crosshair, with adjustable smoothing.
- **Magnetic**: full-screen acquisition and target retention while firing.
- **Rage**: full-screen acquisition with more direct correction settings.

Ten geometries are included: Ancient, Anubis, Cache, Dust2, Inferno, Mills,
Mirage, Nuke, Train and Vertigo. The `.bvh` acceleration caches are generated
locally; the first load may take longer.
Geometry checking depends on how well the files match the current game build.
Thera is not included: the available file was invalid.

### Sensitivity, resolution and serial port

At first launch, `release/aim-settings.conf` is created from the provided template.

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

- **SENSITIVITY=0**: uses the sensitivity read from the game. No personal developer calibration is distributed.
- An explicit sensitivity forces this value. If the automatic reading is invalid, the engine ignores movements and reports it.
- Adapt **WIDTH / HEIGHT** to the game resolution.
- **PORT=auto** fits when only one compatible port is present. Otherwise, set its stable path `/dev/serial/by-id/...`.
- `M_YAW` and `M_PITCH` are coefficients separate from sensitivity; zoom or specific input settings can alter the effective conversion.

### After a CS2 update

Stop the engine, close the other DMA clients and join a match with a living
player. Click **Update offsets**. The tool looks up the addresses, verifies the
reads and replaces `offsets.json` after validation.
A previous copy is kept as `.bak`. If validation fails, the old values stay in
place: some updates require a software adaptation, not only offsets.

## Troubleshooting

| Symptom | To check |
| --- | --- |
| The launcher opens in an editor | Allow execution or run `bash START.sh` from the folder |
| Download failure | Internet, access to PyPI/GitHub/APT sources; relaunch to resume |
| OS or CPU refused | Debian/Ubuntu/Raspberry Pi OS 64-bit, ARM64 or x86-64 |
| KMBox missing / multiple ports | Data cable, correct control port, then `PORT` in the configuration |
| KMBox not responding | `km.*`-compatible firmware, baudrate, no other serial monitor; wait up to 25 s |
| USB permission denied | Replug the device after installation; check its ID and the udev rules |
| DMA unavailable | Correct USB port, compatible firmware, recognized card, no other DMA client |
| Waiting for `cs2.exe/client.dll` | CS2 must be running on the machine connected to the DMA card |
| No correction | Physical click, suspend state, valid sensitivity, offsets and geometry; read the log |
| Exit code 75 | Another instance already holds the DMA lock |

Hardware diagnostic without movement, from the software folder:

```bash
bash release/start-aim.sh --check --duration 10
```

Checking the installed environment:

```bash
bash release/setup-aim.sh --check
```

The hardware diagnostic requires the devices to be connected. It does not replace
a validation of your firmware or your wiring.

## Repository contents

```text
AIM Studio DMA/
├── AIM Studio DMA.desktop   # First-install graphical launcher
├── START.sh                 # Entry point
├── README.md
├── .gitignore               # Excludes installation and personal data
└── release/
    ├── aim_*.py             # GUI, translations and modules
    ├── dma_aim.py           # Engine
    ├── update_aim_offsets.py
    ├── *.sh                # Installation and launchers
    ├── install_aim_runtime.py
    ├── requirements-aim.txt
    ├── aim-settings.example.conf
    ├── offsets.json
    └── maps/               # Geometries required for visibility
```

You can publish **this folder** as the root of the GitHub repository. Installed
dependencies, caches and preferences are excluded by `.gitignore`.
For users, prefer the repository ZIP or an archive in GitHub Releases: geometries
make the repository large and do not suit per-file web uploads.

## Components and credits

- UI and integration: **Akumaprog**.
- DMA access: [MemProcFS](https://github.com/ufrisk/MemProcFS) and [LeechCore](https://github.com/ufrisk/LeechCore), by Ulf Frisk.
- Serial link: [pySerial](https://github.com/pyserial/pyserial).
- Offset and signature sources: [a2x/cs2-dumper](https://github.com/a2x/cs2-dumper).
- ProCS2 geometries taken from the [chao-shushu/CS2-DMA](https://github.com/chao-shushu/CS2-DMA) project, as documented in the source project.

The native library licenses are kept with their installation in
`release/.runtime/vmm/`. Third-party components keep their respective licenses.
