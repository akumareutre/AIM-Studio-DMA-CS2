#!/usr/bin/env python3
"""Retrouve les adresses du client chargé, puis publie un JSON vérifié.

Signatures issues de a2x/cs2-dumper/src/analysis/offsets.rs.
Aucune écriture sur la machine cible ; pas de copie aveugle d'offsets distants.
"""
import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import re
import struct
import tempfile
from urllib.request import urlopen

from dma_aim import OFFSETS, Reader
import aim_i18n as i18n

ROOT = Path(__file__).resolve().parent
PATTERNS = {
    "dwGlobalVars": rb'\x48\x89\x15....\x48\x89\x42',
    "dwEntityList": rb'\x48\x89\x0d....\xe9....\xcc',
    "dwViewMatrix": rb'\x48\x8d\x0d....\x48\xc1\xe0\x06',
    "dwSensitivity": rb'\x48\x8d\x0d....\x0f\x57\xc9\x0f\x28\xf0',
    "dwPrediction": rb'\x48\x8d\x05....\xc3\xcc{8}\x40\x53\x56\x41\x54',
    "dwCSGOInput": rb'\x48\x89\x05....\x0f\x57\xc0\x0f\x11\x05',
}
FIELDS = {
    "C_BaseEntity": ("m_iHealth", "m_lifeState", "m_iTeamNum", "m_pGameSceneNode"),
    "C_BasePlayerPawn": ("m_vOldOrigin", "m_vecViewOffset"),
    "CCSPlayerController": ("m_hPlayerPawn", "m_iPawnArmor", "m_iCompTeammateColor"),
    "C_CSPlayerPawn": ("m_iShotsFired", "m_pAimPunchServices", "m_angEyeAngles"),
    "CCSPlayer_AimPunchServices": ("m_predictableBaseAngle", "m_unpredictableBaseAngle"),
    "CSkeletonInstance": ("m_modelState",),
}


def number(value):
    result = int(value, 0) if isinstance(value, str) else value
    if type(result) is not int or not 0 < result < 0x40000000:
        raise ValueError("Valeur d'offset invalide")
    return result


def scan_sections(sections):
    matches = {key: [] for key in PATTERNS}
    relative = {"pawn": [], "angles": []}
    for rva, data in sections:
        for key, pattern in PATTERNS.items():
            for match in re.finditer(pattern, data, re.S):
                value = rva + match.start() + 7 + struct.unpack_from('<i', data, match.start()+3)[0]
                matches[key].append(value + (8 if key == "dwSensitivity" else 0))
        for key, pattern, displacement in (
            ("pawn", rb'\x4c\x39\xb6....\x74.\x44\x88\xbe', 3),
            ("angles", rb'\xf2\x42\x0f\x10\x84\x28....', 6),
        ):
            relative[key].extend(struct.unpack_from('<I', data, m.start()+displacement)[0]
                                 for m in re.finditer(pattern, data, re.S))
    for key, values in {**matches, **relative}.items():
        if len(values) != 1:
            raise ValueError(f"Signature {key} absente ou ambiguë : aucun fichier modifié. "
                             "Ce build nécessite une mise à jour des signatures.")
    found = {key: number(values[0]) for key, values in matches.items()}
    found["dwLocalPlayerPawn"] = number(found.pop("dwPrediction") + relative["pawn"][0])
    found["dwViewAngles"] = number(found.pop("dwCSGOInput") + relative["angles"][0])
    return found


def executable_sections(process, flags):
    base = process.module("client.dll").base
    header = process.memory.read(base, 4096, flags)
    if header[:2] != b'MZ':
        raise ValueError("client.dll illisible : vérifier la connexion DMA")
    pe = struct.unpack_from('<I', header, 0x3c)[0]
    if header[pe:pe+4] != b'PE\0\0':
        raise ValueError("En-tête client.dll invalide")
    count = struct.unpack_from('<H', header, pe+6)[0]
    start = pe+24+struct.unpack_from('<H', header, pe+20)[0]
    if not 1 <= count <= 96 or start+40*count > len(header):
        raise ValueError("Table des sections client.dll invalide")
    for i in range(count):
        pos = start+40*i
        size, rva = struct.unpack_from('<II', header, pos+8)
        characteristics = struct.unpack_from('<I', header, pos+36)[0]
        if characteristics & 0x20000000:
            if not 0 < size <= 128*1024*1024:
                raise ValueError("Taille de section invalide")
            data = process.memory.read(base+rva, size, flags)
            if len(data) != size:
                raise ValueError("Lecture du client incomplète : réessayer")
            yield rva, data


def fetch_json(url):
    with urlopen(url, timeout=12) as response:
        data = response.read(8*1024*1024+1)
    if len(data) > 8*1024*1024:
        raise ValueError("Réponse distante trop volumineuse")
    return json.loads(data)


def matching_schema(found, fetch=fetch_json):
    """N'utilise les champs distants que si les adresses du build concordent."""
    api = 'https://api.github.com/repos/a2x/cs2-dumper/commits/main'
    revision = fetch(api)['sha']
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError("Révision distante invalide")
    base = f'https://raw.githubusercontent.com/a2x/cs2-dumper/{revision}/output/'
    remote = fetch(base+'offsets.json')['client.dll']
    if any(number(remote[key]) != value for key, value in found.items()):
        print(i18n.t("offsets.other_build"), flush=True)
        return {}
    classes = fetch(base+'client_dll.json')['client.dll']['classes']
    return {field: number(classes[cls]['fields'][field])
            for cls, fields in FIELDS.items() for field in fields}


def atomic_json(path, value):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def update(path, device='fpga', memmap=None, online=True):
    import memprocfs
    path = Path(path)
    current = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(current, dict):
        raise ValueError("offsets.json doit contenir un objet JSON")
    settings = OFFSETS.copy()
    for key in settings.keys() & current.keys():
        value = current[key]
        settings[key] = int(value, 0) if isinstance(value, str) else value
    options = ['-device', device]
    if memmap:
        options += ['-memmap', str(Path(memmap).resolve())]
    vmm = reader = None
    try:
        print(i18n.t("offsets.connect"), flush=True)
        vmm = memprocfs.Vmm(options)
        process = vmm.process('cs2.exe')
        print(i18n.t("offsets.scan"), flush=True)
        found = scan_sections(executable_sections(process, memprocfs.FLAG_NOCACHE))
        if online:
            try:
                fields = matching_schema(found)
            except (OSError, ValueError, KeyError, TypeError) as error:
                print(i18n.t("offsets.remote_fail", error=error), flush=True)
                fields = {}
        else:
            fields = {}
        settings.update(fields)
        settings.update(found)
        print(i18n.t("offsets.verify"), flush=True)
        reader = Reader(process, settings, memprocfs.FLAG_NOCACHE, recoil=True, visibility=True)
        for _ in range(3):
            frame = reader.snapshot()
            if frame is None or not reader.map_name:
                raise ValueError(i18n.t("offsets.validate_fail"))
            if (reader.punch is None or not all(math.isfinite(x) and abs(x) < 45 for x in reader.punch)
                    or not 0 <= reader.shots <= 200):
                raise ValueError(i18n.t("offsets.recoil_bad"))
        result = dict(current)
        result.update({key: hex(value) for key, value in {**fields, **found}.items()})
        if path.exists():
            atomic_json(path.with_suffix('.json.bak'), current)
        atomic_json(path, result)
        print(i18n.t("offsets.done", map=reader.map_name, count=len(found)), flush=True)
    finally:
        if reader is not None:
            reader.close()
        if vmm is not None:
            vmm.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'offsets.json')
    parser.add_argument('--device', default='fpga')
    parser.add_argument('--memmap', type=Path)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--lang', choices=tuple(i18n.LANGUAGES), default=None,
                        help='Langue des messages (défaut : locale système)')
    args = parser.parse_args()
    i18n.set_lang(args.lang or os.environ.get("LANG_CODE") or i18n.detect())
    lock_dir = Path(os.environ.get('XDG_RUNTIME_DIR', tempfile.gettempdir()))
    try:
        with (lock_dir/f'cs2-dma-aim-{os.getuid()}.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError(i18n.t("offsets.busy")) from None
            update(args.output, args.device, args.memmap, not args.offline)
        return 0
    except (Exception, KeyboardInterrupt) as error:
        print(i18n.t("offsets.abort", error=error or i18n.t("offsets.cancel")), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
