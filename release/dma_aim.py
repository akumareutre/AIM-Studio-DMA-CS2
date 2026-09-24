#!/usr/bin/env python3
"""CS2 -> DMA en lecture seule -> KMBox USB-série (Linux ARM64).

Requiert le wrapper officiel MemProcFS 5.x ARM64 et pyserial.
Le wrapper actuel s'importe sous le nom memprocfs, l'ancien sous vmmpy.
L'API officielle moderne est process.memory, et non vmm.mem_read.

Exemple : python3 dma_aim.py --width 1920 --height 1080 --port /dev/ttyUSB0
Arrêt : Ctrl+C ou SIGTERM. Ne pas partager la carte avec le radar/MemProcFS.
Le mouvement n'est actif que pendant le maintien du bouton gauche physique.
Les offsets et le layout des bones doivent correspondre au build du jeu.
La conversion souris suppose l'absence d'accélération et des coefficients
m_yaw/m_pitch effectifs corrects ; le zoom peut modifier ces coefficients.
"""

import argparse
import importlib
import json
import logging
import math
import os
import queue
import re
import signal
import struct
import sys
import threading
import time
from pathlib import Path
from aim_profiles import PROFILES, BODY_PARTS, select_target
from aim_control import HOTKEYS, Toggle, Recoil
from aim_visibility import CollisionMesh
import aim_i18n as i18n

WIDTH, HEIGHT = 1920, 1080
# Adresses vérifiées par signatures sur client.dll le 24/09/2026 (PID 59972).
# Les mises à jour du jeu peuvent les déplacer ; surcharge via --offsets JSON.
OFFSETS = {
    "dwLocalPlayerPawn": 0x255C5A8,
    "dwEntityList": 0x2711048,
    "dwViewMatrix": 0x25618F0,
    "dwViewAngles": 0x2572118,
    "dwSensitivity": 0x25592E8,
    "dwSensitivity_sensitivity": 0x58,
    "m_hPlayerPawn": 0x92C,
    "m_iHealth": 0x34C,
    "m_lifeState": 0x354,  # uint8 : LIFE_ALIVE = 0 (pas un DWORD).
    "m_iTeamNum": 0x3E7,
    "m_vOldOrigin": 0x14A4,
    "m_vecViewOffset": 0xF60,
    "m_pGameSceneNode": 0x330,
    "m_modelState": 0x140,
    # Layout non décrit par les offsets Schema : à revérifier après mise à jour.
    "m_pBoneArray": 0x80,  # Relatif à sceneNode + m_modelState.
    "bone_stride": 0x20,
    "head_bone": 6,
    "entity_stride": 0x70,
    "entity_chunks": 0x10,
    "dwGlobalVars": 0x2227F08,
    "global_map_name": 0x188,
    "m_iShotsFired": 0x1EB4,
    "m_pAimPunchServices": 0x1598,
    "m_predictableBaseAngle": 0x50,
    "m_unpredictableBaseAngle": 0xA4,
    # Techniques du référentiel Mzzzj (offsets absents = désactivées).
    # À renseigner pour ce build via --offsets, ex. cs2-dumper :
    #   m_vecLastClipCameraPos (position caméra clipée, origine de visée)
    #   m_aimPunchCache + aim_punch_cache_stride (RCS par cache QAngle)
    "m_vecLastClipCameraPos": 0,
    "m_aimPunchCache": 0,
    "aim_punch_cache_stride": 12,
}
U64, U32, I32 = struct.Struct("<Q"), struct.Struct("<I"), struct.Struct("<i")
U8, F32, VEC3, MAT4 = (struct.Struct(f) for f in ("<B", "<f", "<3f", "<16f"))
LOG = logging.getLogger("dma-aim")


def unpack(layout, data):
    if not isinstance(data, (bytes, bytearray)) or len(data) != layout.size:
        raise ValueError(f"Lecture incomplète : {layout.size} octets attendus")
    return layout.unpack(data)


def pointer(value):
    return isinstance(value, int) and 0x10000 <= value < 0x0000800000000000


def finite(values):
    return all(math.isfinite(x) for x in values)


def world_to_screen(position, matrix, width, height):
    """Matrice row-major : clip = M * (x,y,z,1), puis division par W."""
    if not finite(position) or not finite(matrix):
        return None
    x, y, z = position
    w = matrix[12]*x + matrix[13]*y + matrix[14]*z + matrix[15]
    if w <= 0.001:
        return None
    nx = (matrix[0]*x + matrix[1]*y + matrix[2]*z + matrix[3]) / w
    ny = (matrix[4]*x + matrix[5]*y + matrix[6]*z + matrix[7]) / w
    if not finite((nx, ny)) or abs(nx) > 1 or abs(ny) > 1:
        return None
    return (nx + 1)*width/2, (1 - ny)*height/2


def angle_delta(eye, head, view):
    x, y, z = (head[i] - eye[i] for i in range(3))
    if math.hypot(x, y, z) < 0.01:
        raise ValueError("Distance de visée nulle")
    pitch = -math.degrees(math.atan2(z, math.hypot(x, y)))
    yaw = math.degrees(math.atan2(y, x))
    return pitch - view[0], (yaw - view[1] + 180) % 360 - 180


# Vitesse maximale de cible acceptée (u/s) et avance maximale en unités monde :
# gardes inspirées de la prédiction du projet chao-shushu CS2-DMA (predictionTimeMs).
MAX_TARGET_SPEED, MAX_LEAD = 5000.0, 120.0


def predict(now, pawn, head, history, prediction_ms, max_lead=MAX_LEAD):
    """Extrapoler la tête vers l'avant (viser où la cible SERA, style predictionTimeMs).

    La vélocité est dérivée des positions des snapshots successifs (aucun offset
    requis) puis lissée par une moyenne exponentielle ; le point visé est décalé
    de velocity * prediction_ms, borné pour ne jamais viser au-delà d'une
    distance raisonnable ni suivre une vélocité aberrante. Retourne head tel quel
    si la prédiction est désactivée ou la vélocité inconnue/nulle.
    """
    entry = history.get(pawn)
    previous_time = entry[0] if entry else None
    previous_head = entry[1] if entry else None
    velocity = entry[2] if entry else None
    if previous_time is not None and previous_head is not None:
        elapsed = now - previous_time
        if 0 < elapsed <= 0.5:
            speed = tuple((head[i] - previous_head[i]) / elapsed for i in range(3))
            if math.hypot(*speed) <= MAX_TARGET_SPEED:
                velocity = speed if velocity is None else tuple(
                    0.75*speed[i] + 0.25*velocity[i] for i in range(3))
    history[pawn] = (now, head, velocity)
    if not prediction_ms or velocity is None:
        return head
    lead = tuple(velocity[i]*prediction_ms/1000 for i in range(3))
    magnitude = math.hypot(*lead)
    if magnitude > max_lead:
        lead = tuple(v*max_lead/magnitude for v in lead)
    return tuple(head[i] + lead[i] for i in range(3))


def normalize_map_name(raw):
    """Normalise un nom de carte lu depuis le jeu pour le comparer au nom de
    fichier de géométrie (miroir de NormalizeMapName du projet chao-shushu).
    "maps/de_dust2.vpk" -> "de_dust2" ; "de_mirage" -> "de_mirage"."""
    name = raw
    for prefix in ("maps/", "maps\\"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    for ext in (".vpk", ".bsp"):
        pos = name.find(ext)
        if pos != -1:
            name = name[:pos]
    return name.strip("/\\")


def decode_map_name(data):
    """Valide une chaîne mémoire avant toute recherche de fichier de carte."""
    raw, terminator, _ = data.partition(b'\0')
    if not terminator:
        raise ValueError("Nom de carte non terminé : vérifier les offsets du build CS2")
    if raw in (b'', b'<empty>'):
        return None
    if not re.fullmatch(rb'[A-Za-z0-9_./\\-]+', raw):
        raise ValueError("Nom de carte illisible : vérifier dwGlobalVars et global_map_name pour ce build CS2")
    name = normalize_map_name(raw.decode('ascii'))
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_-]*', name):
        raise ValueError("Nom de carte invalide : vérifier les offsets du build CS2")
    return name


def find_map_geometry(maps_dir, map_name):
    """Retourne le chemin du fichier de géométrie correspondant à une carte
    (comparaison normalisée), ou None. Permet la détection automatique."""
    maps_dir = Path(maps_dir)
    if not maps_dir.is_dir():
        return None
    current = normalize_map_name(map_name)
    if not current:
        return None
    for path in sorted(maps_dir.iterdir()):
        # Les caches BVH (<carte>.bvh) ne sont jamais des géométries : exclus
        # pour ne pas charger un cache comme fichier de triangles (crash).
        if not path.is_file() or path.name.endswith('.bvh'):
            continue
        if normalize_map_name(path.stem or path.name) == current:
            return path
    return None


def load_map_geometry(path):
    """Charge une géométrie en réutilisant le cache BVH précalculé
    (<fichier>.bvh, créé au premier chargement) : de_cache passe de ~55 s de
    build à ~1,2 s. Le fichier de géométrie reste la source des triangles."""
    path = Path(path)
    cache = path.with_suffix('.bvh')
    if cache.is_file():
        try:
            return CollisionMesh.from_cache(cache, path)
        except (OSError, ValueError, struct.error):
            LOG.warning(i18n.t("engine.cache_bad", name=cache.name))
            try:
                cache.unlink()
            except OSError:
                pass
    mesh = CollisionMesh(path)
    try:
        mesh.save_cache(cache)
    except (OSError, ValueError):
        pass  # cache non critique : le build direct reste valide
    return mesh


def load_geometry_to(path, result_queue):
    """Thread de chargement : met le CollisionMesh ou l'erreur dans la file."""
    try:
        result_queue.put(load_map_geometry(path))
    except BaseException as error:  # noqa: BLE001 - transmis à la boucle principale
        result_queue.put(error)


class Collector:
    """Collecte DMA asynchrone (thread daemon). Les lectures scatter peuvent
    staller sporadiquement 0,7-8 s (bus FPGA/cible, pics observés en jeu) :
    avec ce thread, la boucle principale ne bloque jamais et consomme toujours
    le snapshot le plus récent. Une erreur de collecte est exposée dans
    `error` pour reconnecter proprement."""

    def __init__(self, reader, hz, stop):
        self.reader = reader
        self.hz = hz
        self.stop = stop
        self.done = threading.Event()
        self.frame = None
        self.t = 0.0
        self.sample = None
        self.error = None
        self.thread = threading.Thread(target=self._run, name="collector-dma", daemon=True)

    def start(self):
        self.thread.start()

    def shutdown(self, timeout=1.5):
        self.done.set()
        self.thread.join(timeout)

    def _run(self):
        fails = 0
        while not self.done.is_set() and not self.stop.is_set():
            t0 = time.monotonic()
            try:
                frame = self.reader.snapshot()
            except BaseException as error:  # noqa: BLE001 - reconnecté par la boucle
                # Une lecture partielle transitoire (p. ex. « Lecture incomplète »)
                # ne doit pas jeter le reader : on retente dessus avant d'abandonner.
                fails += 1
                if fails >= 3:
                    self.error = error
                    self.frame = None
                    self.sample = None
                    return
                self.stop.wait(0.25)
                continue
            fails = 0
            self.frame = frame
            self.t = time.monotonic()
            # Publication atomique : position, angles et recul de la même lecture.
            # L'âge part du début de la collecte, pas de la fin d'un éventuel stall.
            self.sample = (frame, t0, self.reader.punch, self.reader.shots, self.reader.map_name)
            self.error = None
            self.stop.wait(max(0.001, 1 / self.hz - (time.monotonic() - t0)))


class Reader:
    """Un handle scatter réutilisé ; aucune écriture mémoire ni thread par entité."""

    def __init__(self, process, offsets, flags, bone=None, recoil=False, visibility=False):
        self.base = process.module("client.dll").base
        if not pointer(self.base):
            raise RuntimeError("client.dll indisponible")
        self.o = offsets
        self.bone = offsets["head_bone"] if bone is None else bone
        self.read_recoil, self.read_visibility = recoil, visibility
        self.punch, self.shots, self.map_name = None, 0, None
        self.scatter = process.memory.scatter_initialize(flags)

    def close(self):
        self.scatter.close()

    def batch(self, requests):
        requests = list(dict.fromkeys(requests))
        if not requests:
            return {}
        sc = self.scatter
        sc.clear()
        for address, size in requests:
            if not pointer(address) or not pointer(address + size - 1):
                raise ValueError("Adresse virtuelle invalide")
            sc.prepare(address, size)
        sc.execute()
        result = {}
        for address, size in requests:
            try:
                data = sc.read(address, size)
                if len(data) == size:
                    result[address] = data
            except RuntimeError:
                continue  # Une entité peut disparaître pendant la collecte.
        return result

    def snapshot(self):
        self.punch, self.shots = None, 0
        o, base = self.o, self.base
        root_va = base + o["dwEntityList"]
        local_va = base + o["dwLocalPlayerPawn"]
        matrix_va = base + o["dwViewMatrix"]
        view_va = base + o["dwViewAngles"]
        sens_va = base + o["dwSensitivity"]
        roots = [(root_va, 8), (local_va, 8), (matrix_va, 64), (view_va, 12), (sens_va, 8)]
        if self.read_visibility:
            roots.append((base + o["dwGlobalVars"], 8))
        data = self.batch(roots)
        globals_ptr = unpack(U64, data[base + o["dwGlobalVars"]])[0] if self.read_visibility and base + o["dwGlobalVars"] in data else 0
        # Le nom de carte ne dépend ni de la santé ni de l'existence du pawn.
        if self.read_visibility:
            detected_map = None
            if pointer(globals_ptr):
                address = globals_ptr + o["global_map_name"]
                names = self.batch([(address, 8)])
                name_ptr = unpack(U64, names[address])[0] if address in names else 0
                if pointer(name_ptr):
                    names = self.batch([(name_ptr, 64)])
                    if name_ptr in names:
                        self.map_name = None
                        detected_map = decode_map_name(names[name_ptr])
            self.map_name = detected_map
        root, = unpack(U64, data.get(root_va))
        local, = unpack(U64, data.get(local_va))
        matrix = unpack(MAT4, data.get(matrix_va))
        view = unpack(VEC3, data.get(view_va))
        sens_ptr, = unpack(U64, data.get(sens_va))
        if not pointer(root) or not pointer(local) or not finite(matrix + view):
            return None

        chunk_va = root + o["entity_chunks"]
        requests = [(chunk_va, 8), (local + o["m_iHealth"], 4),
                    (local + o["m_lifeState"], 1), (local + o["m_iTeamNum"], 1),
                    (local + o["m_vOldOrigin"], 12), (local + o["m_vecViewOffset"], 12)]
        sens_value_va = sens_ptr + o["dwSensitivity_sensitivity"] if pointer(sens_ptr) else 0
        if sens_value_va:
            requests.append((sens_value_va, 4))
        if o.get("m_vecLastClipCameraPos"):
            requests.append((local + o["m_vecLastClipCameraPos"], 12))
        if self.read_recoil:
            requests.append((local + o["m_iShotsFired"], 4))
            if o.get("m_aimPunchCache"):
                requests.append((local + o["m_aimPunchCache"], 16))
            else:
                requests.append((local + o["m_pAimPunchServices"], 8))
        data = self.batch(requests)
        camera = unpack(VEC3, data[local + o["m_vecLastClipCameraPos"]]) if o.get("m_vecLastClipCameraPos") and local + o["m_vecLastClipCameraPos"] in data else None
        cache = unpack("QQ", data[local + o["m_aimPunchCache"]]) if self.read_recoil and o.get("m_aimPunchCache") and local + o["m_aimPunchCache"] in data else None
        service = unpack(U64, data[local + o["m_pAimPunchServices"]])[0] if self.read_recoil and local + o["m_pAimPunchServices"] in data else 0
        if self.read_recoil and local + o["m_iShotsFired"] in data:
            self.shots = unpack(I32, data[local + o["m_iShotsFired"]])[0]
        health, = unpack(I32, data.get(local + o["m_iHealth"]))
        life, = unpack(U8, data.get(local + o["m_lifeState"]))
        team, = unpack(U8, data.get(local + o["m_iTeamNum"]))
        if not 0 < health <= 100 or life != 0 or team not in (2, 3):
            return None
        origin = unpack(VEC3, data.get(local + o["m_vOldOrigin"]))
        offset = unpack(VEC3, data.get(local + o["m_vecViewOffset"]))
        eye = tuple(a + b for a, b in zip(origin, offset))
        if camera and finite(camera) and abs(camera[0]-eye[0]) < 3000 and abs(camera[1]-eye[1]) < 3000 and abs(camera[2]-eye[2]) < 3000:
            eye = camera  # Mzzzj : visée depuis la caméra clipée plutôt que origin+viewOffset.
        if not finite(eye):
            raise ValueError("Position locale invalide")
        sensitivity = unpack(F32, data[sens_value_va])[0] if sens_value_va in data else None
        chunk, = unpack(U64, data.get(chunk_va))
        if not pointer(chunk):
            return None

        # Contrôleurs dans les slots 1..64 ; résolution des handles vers les pawns.
        stride = o["entity_stride"]
        slots_va = chunk + stride
        requests = [(slots_va, 64*stride)]
        if pointer(service):
            requests.extend(((service + o["m_predictableBaseAngle"], 12),
                             (service + o["m_unpredictableBaseAngle"], 12)))
        if cache and pointer(cache[1]) and 1 <= cache[0] < 0xFFFF:
            # Mzzzj : dernier QAngle du cache (pitch, yaw), depuis CUtlVector<QAngle>.
            requests.append((cache[1] + (cache[0]-1)*o["aim_punch_cache_stride"], 12))
        data = self.batch(requests)
        if cache and pointer(cache[1]) and 1 <= cache[0] < 0xFFFF:
            try:
                punch = unpack(VEC3, data.get(cache[1] + (cache[0]-1)*o["aim_punch_cache_stride"]))
                self.punch = punch[:2]  # pitch, yaw (roll ignoré)
            except ValueError:
                self.punch = None
        if self.punch is None and pointer(service):
            try:
                predictable = unpack(VEC3, data.get(service + o["m_predictableBaseAngle"]))
                unpredictable = unpack(VEC3, data.get(service + o["m_unpredictableBaseAngle"]))
                self.punch = tuple(a+b for a, b in zip(predictable, unpredictable))
            except ValueError:
                self.punch = None
        slots = data.get(slots_va)
        if slots is None:
            raise ValueError("Liste des entités illisible")
        controllers = {U64.unpack_from(slots, i*stride)[0] for i in range(64)}
        data = self.batch([(p + o["m_hPlayerPawn"], 4) for p in controllers if pointer(p)])
        handles = {unpack(U32, b)[0] for b in data.values()}
        handles.difference_update((0, 0xFFFFFFFF))
        chunk_addrs = {h: root + o["entity_chunks"] + 8*((h & 0x7FFF) >> 9) for h in handles}
        data = self.batch([(a, 8) for a in chunk_addrs.values()])
        pawn_addrs = []
        for h, address in chunk_addrs.items():
            if address in data:
                c, = unpack(U64, data[address])
                if pointer(c):
                    pawn_addrs.append(c + stride*(h & 0x1FF))
        data = self.batch([(a, 8) for a in pawn_addrs])
        pawns = {unpack(U64, b)[0] for b in data.values()}
        pawns = {p for p in pawns if pointer(p) and p != local}
        fields = (("m_iHealth", 4), ("m_lifeState", 1), ("m_iTeamNum", 1), ("m_pGameSceneNode", 8))
        data = self.batch([(p + o[name], size) for p in pawns for name, size in fields])
        enemies = {}
        for p in pawns:
            try:
                hp, = unpack(I32, data.get(p + o["m_iHealth"]))
                life, = unpack(U8, data.get(p + o["m_lifeState"]))
                t, = unpack(U8, data.get(p + o["m_iTeamNum"]))
                scene, = unpack(U64, data.get(p + o["m_pGameSceneNode"]))
                if 0 < hp <= 100 and life == 0 and t in (2, 3) and t != team and pointer(scene):
                    enemies[p] = scene + o["m_modelState"] + o["m_pBoneArray"]
            except ValueError:
                continue
        data = self.batch([(a, 8) for a in enemies.values()])
        head_addrs = {}
        for p, a in enemies.items():
            if a in data:
                bones, = unpack(U64, data[a])
                if pointer(bones):
                    head_addrs[p] = bones + self.bone*o["bone_stride"]
        data = self.batch([(a, 12) for a in head_addrs.values()])
        heads = {p: unpack(VEC3, data[a]) for p, a in head_addrs.items() if a in data}
        return eye, view, matrix, sensitivity, heads


class Mouse:
    def __init__(self, serial_module, args, stop=None):
        self.stop = stop if stop is not None else threading.Event()
        self.port = serial_module.Serial(port=None, baudrate=args.baud, timeout=0,
                                         write_timeout=0.1, exclusive=True)
        self.port.dtr = False
        self.port.rts = False
        self.port.port = args.port
        try:
            self.port.open()
            LOG.info(i18n.t("engine.kmbox.init"))
            self.wait_reply(b">>>", 25)
            self.port.write(b'DMA_AIM_ENABLED=1\r\nkm.move(0,0)\r\nprint("DMA_KM_READY")\r\n')
            self.wait_reply(b"\r\nDMA_KM_READY\r\n", 3)
            LOG.info(i18n.t("engine.kmbox.ready"))
        except BaseException:
            self.port.close()
            raise
        self.remainder = [0.0, 0.0]
        self.target = None

    def wait_reply(self, expected, timeout):
        deadline = time.monotonic() + timeout
        response = bytearray()
        while time.monotonic() < deadline:
            response.extend(self.port.read(min(self.port.in_waiting, 4096)))
            if b"Traceback" in response:
                raise RuntimeError("KMBox : " + response[-1000:].decode(errors="replace"))
            if expected in response:
                return bytes(response)
            if len(response) > 8192:
                del response[:-4096]
            if self.stop.wait(0.02):
                raise KeyboardInterrupt
        raise RuntimeError("KMBox sans réponse attendue : vérifier le câblage, le baud et le firmware")

    def reset(self):
        self.remainder[:] = [0.0, 0.0]
        self.target = None

    def left_pressed(self):
        """km.left() lit les boutons ; bit 0 = physique, bit 1 = logiciel."""
        self.port.reset_input_buffer()
        command = b'print("DMA_BUTTON",km.left())\r\n'
        if self.port.write(command) != len(command):
            raise OSError("Lecture bouton : commande série tronquée")
        deadline = time.monotonic() + 0.5
        response = bytearray()
        while time.monotonic() < deadline:
            response.extend(self.port.read(min(self.port.in_waiting, 4096)))
            match = re.search(rb"(?:^|\r?\n)DMA_BUTTON ([0-3])\r?\n", response)
            if match:
                return bool(int(match.group(1)) & 1)
            if b"Traceback" in response or len(response) > 8192:
                raise RuntimeError("État du bouton KMBox illisible")
            if self.stop.wait(0.002):
                return False
        # Ne jamais réutiliser un ancien état « pressé » en cas de perte série.
        raise RuntimeError("Délai dépassé lors de la lecture du bouton KMBox")

    def input_state(self, key):
        self.port.reset_input_buffer()
        command = f'print("DMA_INPUT",km.left(),{HOTKEYS[key]})\r\n'.encode()
        if self.port.write(command) != len(command):
            raise OSError("Lecture des touches : commande tronquée")
        deadline, response = time.monotonic() + 0.5, bytearray()
        while time.monotonic() < deadline:
            response.extend(self.port.read(min(self.port.in_waiting, 4096)))
            match = re.search(rb"(?:^|\r?\n)DMA_INPUT ([0-3]) ([0-3])\r?\n", response)
            if match:
                return bool(int(match.group(1)) & 1), bool(int(match.group(2)) & 1)
            if b"Traceback" in response or len(response) > 8192:
                raise RuntimeError("État des touches KMBox illisible")
            if self.stop.wait(0.002):
                return False, False
        raise RuntimeError("Délai dépassé lors de la lecture des touches KMBox")

    def set_enabled(self, enabled):
        command = f'DMA_AIM_ENABLED={int(enabled)}\r\n'.encode()
        if self.port.write(command) != len(command):
            raise OSError("Bascule KMBox : commande tronquée")

    def movement_counts(self, target, pitch, yaw, sensitivity, dt, args, smooth=True):
        """Quantifier la correction sans entretenir une oscillation sous un count."""
        if target != self.target:
            self.reset()
            self.target = target
        # Lissage exponentiel indépendant de la fréquence effective des lectures.
        alpha = 1 if not smooth or args.smooth_ms == 0 else 1 - math.exp(-min(dt, 0.1)/(args.smooth_ms/1000))
        values = (-yaw/(sensitivity*args.m_yaw), pitch/(sensitivity*args.m_pitch))
        steps = []
        for axis, value in enumerate(values):
            # Sous un demi-count, tout déplacement entier éloignerait la visée.
            # Le RCS différentiel conserve son accumulation de fractions.
            if smooth and abs(value) < 0.5:
                self.remainder[axis] = 0.0
                steps.append(0)
                continue
            if smooth and value*self.remainder[axis] < 0:
                self.remainder[axis] = 0.0
            value = max(-args.max_step, min(args.max_step, value*alpha))
            total = value + self.remainder[axis]
            step = math.trunc(total)
            self.remainder[axis] = total - step
            steps.append(step)
        return tuple(steps)

    def move(self, target, pitch, yaw, sensitivity, dt, args, smooth=True):
        steps = self.movement_counts(target, pitch, yaw, sensitivity, dt, args, smooth)
        # Évacuer les réponses/échos du firmware, avec une limite par itération.
        waiting = self.port.in_waiting
        if waiting:
            self.port.read(min(waiting, 4096))
        if steps[0] or steps[1]:
            # Recontrôle sur le boîtier au moment exact d'exécuter le mouvement :
            # un relâchement pendant une lecture DMA lente bloque la correction.
            command = (f"km.move({steps[0]},{steps[1]}) if DMA_AIM_ENABLED and km.left() & 1 else None\r\n").encode("ascii")
            if self.port.write(command) != len(command):
                raise OSError("Écriture série partielle ; arrêt pour éviter une commande tronquée")

    def close(self):
        self.port.close()


def positive(text):
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("Valeur positive et finie attendue")
    return value

def nonnegative(text):
    value = float(text)
    if not math.isfinite(value) or value < 0:
        raise argparse.ArgumentTypeError("Valeur positive ou nulle attendue")
    return value


class Status:
    def __init__(self, enabled):
        self.output_enabled = enabled
        self.last = 0
        self.enabled = True

    def send(self, phase, force=False, **values):
        now = time.monotonic()
        if self.output_enabled and (force or now - self.last >= 0.25):
            print("@status " + json.dumps({"phase": phase, "enabled": self.enabled, **values}), flush=True)
            self.last = now


def arguments():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", default="/dev/ttyUSB0")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--width", type=int, default=WIDTH)
    p.add_argument("--height", type=int, default=HEIGHT)
    p.add_argument("--device", default="fpga")
    p.add_argument("--memmap", type=Path)
    p.add_argument("--offsets", type=Path, default=Path(__file__).with_name("offsets.json"))
    p.add_argument("--mode", choices=PROFILES, default="magnetic")
    p.add_argument("--body", choices=BODY_PARTS, default="head")
    p.add_argument("--hz", type=positive)
    p.add_argument("--radius", type=positive, help="Rayon du mode Soft uniquement, pixels")
    p.add_argument("--smooth-ms", type=nonnegative)
    p.add_argument("--max-step", type=int)
    p.add_argument("--sensitivity", type=positive, help="Sinon lecture de la sensibilité du jeu")
    p.add_argument("--m-yaw", type=positive, default=0.022)
    p.add_argument("--m-pitch", type=positive, default=0.022)
    p.add_argument("--max-frame-ms", type=positive, default=150.0)
    p.add_argument("--check", action="store_true", help="Diagnostic DMA/KMBox, sans déplacement")
    p.add_argument("--duration", type=positive, help="Durée du test en secondes après initialisation")
    p.add_argument("--status-json", action="store_true", help="Télémétrie du menu graphique")
    p.add_argument("--lang", choices=tuple(i18n.LANGUAGES), default=None,
                   help="Langue du journal (défaut : locale système, français sinon)")
    p.add_argument("--toggle-key", choices=HOTKEYS, default="F6")
    p.add_argument("--recoil", type=nonnegative, default=0, help="Compensation RCS, de 0 à 100 %%")
    p.add_argument("--visibility", choices=("strict", "off"), default="strict")
    p.add_argument("--collision", type=Path, help="Géométrie .aimcoll correspondant à la carte (sinon détection automatique dans --maps-dir)")
    p.add_argument("--maps-dir", type=Path, default=Path(__file__).resolve().parent / "maps",
                   help="Dossier des géométries ProCS2 pour la détection automatique (défaut : maps/ à côté du script)")
    p.add_argument("--fov", type=nonnegative, default=5, help="FOV angulaire en degrés (référence Mzzzj : 5 ; 0 = illimité)")
    p.add_argument("--head-z-offset", type=float, default=-1.0, help="Correction Z de la tête en unités monde (référence Mzzzj : -1)")
    p.add_argument("--prediction-ms", type=nonnegative, default=0,
                   help="Prédiction de mouvement : viser où la cible sera, en ms (0 = désactivé, style predictionTimeMs)")
    p.add_argument("--max-lead", type=positive, default=MAX_LEAD,
                   help="Avance maximale de la prédiction, en unités monde (défaut : 120)")
    args = p.parse_args()
    for key in ("hz", "radius", "smooth_ms", "max_step"):
        if getattr(args, key) is None:
            setattr(args, key, PROFILES[args.mode][key])
    if not (1 <= args.width <= 32768 and 1 <= args.height <= 32768):
        p.error("Résolution invalide")
    if not 1 <= args.max_step <= 32767 or args.baud <= 0 or args.hz > 1000:
        p.error("max-step doit être entre 1 et 32767, baud > 0 et hz <= 1000")
    if args.memmap and not args.memmap.is_file():
        p.error("Fichier memmap introuvable")
    if args.recoil > 100:
        p.error("Compensation du recul : 0 à 100 %%")
    return args


def close(resource):
    if resource is not None:
        try:
            resource.close()
        except Exception as error:
            LOG.warning(i18n.t("engine.warn.close", error=error))


def main():
    args = arguments()
    i18n.set_lang(args.lang or os.environ.get("LANG_CODE") or i18n.detect())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stop = threading.Event()
    toggle_request = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    signal.signal(signal.SIGUSR1, lambda *_: toggle_request.set())
    vmm = reader = mouse = mesh = None
    collector = None
    status = Status(args.status_json)
    locked = None
    toggle, recoil = Toggle(), Recoil()
    history = {}
    geometry_queue = queue.Queue(maxsize=8)   # résultats des chargements auto (thread)
    geometry_pending = None                   # carte en cours de chargement
    geometry_warning = ""                     # dernière carte sans fichier (évite les répétitions)
    geometry_failed = set()                   # cartes dont le chargement a échoué (ex. de_thera corrompu)
    try:
        if args.visibility == "strict":
            if args.collision:
                status.send("geometry", force=True)
                mesh = load_map_geometry(args.collision)
            else:
                maps_dir = args.maps_dir
                if maps_dir is None or not Path(maps_dir).is_dir():
                    LOG.warning(i18n.t("engine.warn.strict"))
                else:
                    LOG.info(i18n.t("engine.strict.auto", dir=maps_dir))
        offsets = OFFSETS.copy()
        if args.offsets:
            overrides = json.loads(args.offsets.read_text())
            for key in offsets.keys() & overrides.keys():
                value = overrides[key]
                offsets[key] = int(value, 0) if isinstance(value, str) else value
        if any(type(v) is not int or not 0 <= v < 0x40000000 for v in offsets.values()):
            raise ValueError("Offsets invalides : entiers positifs requis")
        if offsets["bone_stride"] < 12 or offsets["entity_stride"] < 8:
            raise ValueError("Stride trop petit")
        try:
            vmmpy = importlib.import_module("memprocfs")
        except ModuleNotFoundError as error:
            if error.name != "memprocfs":
                raise
            vmmpy = importlib.import_module("vmmpy")
        if not hasattr(vmmpy, "Vmm"):
            raise RuntimeError("Wrapper obsolète : installer le wrapper officiel MemProcFS 5.x ARM64")
        serial = importlib.import_module("serial")
        status.send("kmbox", force=True)
        mouse = Mouse(serial, args, stop)
        options = ["-device", args.device]
        if args.memmap:
            options += ["-memmap", str(args.memmap.resolve())]
        status.send("dma", force=True)
        vmm = vmmpy.Vmm(options)
        LOG.info(i18n.t("engine.dma.wait"))
        last_warning = last_step = 0.0
        last_sample = None
        reconnect_delay = 1.0
        deadline = time.monotonic() + args.duration if args.duration else math.inf
        frames = moves = 0
        last_status = 0.0
        while not stop.is_set() and time.monotonic() < deadline:
            start = time.monotonic()
            try:
                if reader is None:
                    try:
                        process = vmm.process("cs2.exe")
                    except RuntimeError:
                        process = vmm.process("cs2")
                    reader = Reader(process, offsets, vmmpy.FLAG_NOCACHE, BODY_PARTS[args.body][1],
                                    recoil=args.recoil > 0, visibility=args.visibility == "strict")
                    LOG.info(i18n.t("engine.proc", pid=process.pid))
                    collector = Collector(reader, args.hz, stop)
                    collector.start()
                pressed, key_held = mouse.input_state(args.toggle_key)
                if collector is not None and collector.error is not None:
                    raise collector.error
                requested = toggle_request.is_set()
                toggle_request.clear()
                if toggle.update(key_held, requested):
                    mouse.set_enabled(toggle.enabled)
                    mouse.reset()
                    recoil.reset()
                    locked = None
                    status.enabled = toggle.enabled
                    LOG.info(i18n.t("engine.assist", state=i18n.t("assist.on" if toggle.enabled else "assist.off"),
                                    hotkey=args.toggle_key))
                    status.send("idle" if toggle.enabled else "paused", force=True)
                if (not pressed or not toggle.enabled) and not args.check:
                    mouse.reset()
                    recoil.reset()
                    locked = None
                    history.clear()
                    last_step = 0.0
                sample = collector.sample if collector is not None else None
                frame, t_frame, punch, shots, map_name = sample or (None, 0.0, None, 0, None)
            except (RuntimeError, ValueError, OSError) as error:
                mouse.reset()
                recoil.reset()
                locked = None
                if collector is not None:
                    collector.shutdown()
                    collector = None
                close(reader)
                reader = None
                if start - last_warning >= 5:
                    LOG.warning(i18n.t("engine.warn.data", error=error))
                    last_warning = start
                status.send("waiting", force=True, detail=str(error))
                # Backoff : ne pas marteler le processus PID à chaque itération
                # quand le jeu n'est pas (encore) lisible (ex. retour au menu).
                stop.wait(reconnect_delay)
                reconnect_delay = min(10.0, reconnect_delay * 2)
                continue
            now = time.monotonic()
            dt = now - last_step if last_step else 1/args.hz
            last_step = now
            age_ms = (now - t_frame) * 1000 if frame is not None else None
            selected = None
            new_sample = sample is not None and sample is not last_sample
            if frame is not None and new_sample:
                frames += 1
                reconnect_delay = 1.0
            fresh = frame is not None and age_ms is not None and age_ms <= args.max_frame_ms
            if (pressed and toggle.enabled or args.check) and fresh and new_sample:
                last_sample = sample
                eye, view, matrix, sensitivity, heads = frame
                sensitivity = args.sensitivity or sensitivity
                if sensitivity is None or not math.isfinite(sensitivity) or not 0.001 <= sensitivity <= 100:
                    mouse.reset()
                    if now - last_warning >= 5:
                        LOG.warning(i18n.t("engine.warn.sens"))
                        last_warning = now
                    stop.wait(0.1)
                    continue
                compensation, change = recoil.update(punch, shots, args.recoil) if args.recoil else ((0., 0.), (0., 0.))
                recoil_view = (view[0] + compensation[0], view[1] + compensation[1], view[2])
                def candidates(points):
                    if not points or args.fov <= 0:
                        return points
                    result = {}
                    for pawn, point in points.items():
                        try:
                            dp, dy = angle_delta(eye, point, recoil_view)
                        except ValueError:
                            continue
                        if math.hypot(dp, dy) <= args.fov:
                            result[pawn] = point
                    return result
                selected = select_target(candidates(heads), matrix, args.width, args.height,
                                         args.mode, args.radius, locked) if args.visibility == "off" else None
                if args.visibility == "strict" and mesh is not None:
                    clear_points = {p: h for p, h in heads.items() if mesh.visible(eye, h, map_name)}
                    selected = select_target(candidates(clear_points), matrix, args.width, args.height,
                                             args.mode, args.radius, locked)
                locked = selected[0] if selected and pressed else None
                if selected:
                    pawn, head = selected
                    if args.prediction_ms:
                        head = predict(time.monotonic(), pawn, head, history,
                                       args.prediction_ms, args.max_lead)
                    if args.body == "head" and args.head_z_offset:
                        head = (head[0], head[1], head[2] + args.head_z_offset)  # Mzzzj : AimPos.z -= 1.f
                    pitch, yaw = angle_delta(eye, head, view)
                    pitch, yaw = pitch-compensation[0], yaw-compensation[1]
                    if finite((pitch, yaw)) and pressed and toggle.enabled and not stop.is_set() and not args.check:
                        mouse.move(pawn, pitch, yaw, sensitivity, dt, args)
                        moves += 1
                    else:
                        mouse.reset()
                else:
                    if args.recoil and any(change) and pressed and toggle.enabled and not stop.is_set() and not args.check:
                        mouse.move("recoil", -change[0], -change[1], sensitivity, dt, args, smooth=False)
                        moves += 1
                    else:
                        mouse.reset()
            elif not fresh or not (pressed and toggle.enabled or args.check):
                mouse.reset()
                recoil.reset()
                locked = None
                if frame is not None and age_ms > args.max_frame_ms and now - last_warning >= 5:
                    LOG.warning(i18n.t("engine.warn.stale", age=age_ms, max=args.max_frame_ms))
                    last_warning = now
            if args.check and frame is not None and now - last_status >= 2:
                LOG.info(i18n.t("engine.diag", ms=age_ms, enemies=len(frame[4]), target=bool(selected),
                            sens=args.sensitivity or frame[3]))
                if args.recoil:
                    LOG.info(i18n.t("engine.diag.rcs", shots=shots, punch=punch))
                last_status = now
            current_map = ""
            if args.visibility == "strict" and isinstance(map_name, str):
                current_map = normalize_map_name(map_name)
            if args.visibility == "strict" and mesh is not None and current_map and current_map != mesh.map_name:
                # Carte changée en cours de partie : l'ancienne géométrie ne
                # s'applique plus, on la libère (fail-closed jusqu'au rechrgmt).
                close(mesh)
                mesh = None
            if args.visibility == "strict":
                # Résultats des chargements automatiques (threads daemon).
                while not geometry_queue.empty():
                    try:
                        loaded = geometry_queue.get_nowait()
                    except queue.Empty:
                        break
                    if loaded is None or isinstance(loaded, BaseException):
                        _msg = loaded if isinstance(loaded, BaseException) else i18n.t("engine.result.none")
                        LOG.warning(i18n.t("engine.geo.failed", error=_msg))
                        if current_map:
                            geometry_failed.add(current_map)
                        geometry_pending = None
                    elif current_map and loaded.map_name == current_map:
                        LOG.info(i18n.t("engine.geo.loaded", map=loaded.map_name, triangles=len(loaded.memory)//36))
                        mesh = loaded
                        geometry_pending = None
                    else:
                        close(loaded)  # la carte a changé pendant le chargement
                # Détection : dès que la carte est connue et non couverte, on charge.
                if (current_map and (mesh is None or mesh.map_name != current_map)
                        and geometry_pending != current_map and current_map not in geometry_failed):
                    candidate = find_map_geometry(args.maps_dir, current_map)
                    if candidate is None:
                        if current_map != geometry_warning:
                            LOG.warning(i18n.t("engine.warn.nogeo", map=current_map, dir=args.maps_dir))
                            geometry_warning = current_map
                    else:
                        geometry_pending = current_map
                        LOG.info(i18n.t("engine.geo.detect", map=current_map, file=candidate.name))
                        threading.Thread(target=load_geometry_to,
                                         args=(candidate, geometry_queue), daemon=True).start()
            geometry_ok = args.visibility == "off" or (mesh is not None and current_map == mesh.map_name)
            phase = "paused" if not toggle.enabled else (
                "geometry" if args.visibility == "strict" and geometry_pending else
                "geometry_missing" if not geometry_ok else
                ("tracking" if selected and pressed and not args.check else "ready"))
            status.send(phase,
                        map_name=current_map, geometry_map=mesh.map_name if mesh is not None else None,
                        geometry_pending=geometry_pending,
                        pressed=pressed, target=bool(selected), enemies=len(frame[4]) if frame is not None else 0,
                        ms=age_ms if age_ms is not None else round((now - start) * 1000, 1), frames=frames, moves=moves,
                        recoil_valid=punch is not None if args.recoil else False,
                        shots=shots if args.recoil else 0)
            # Pas de rattrapage en rafale ; toujours céder au moins 1 ms au système.
            stop.wait(max(0.001, 1/args.hz - (time.monotonic() - start)))
        LOG.info(i18n.t("engine.end", frames=frames, corrections=moves))
        return 0 if frames or not args.duration or not args.check else 2
    except KeyboardInterrupt:
        return 0
    except Exception as error:
        LOG.error(i18n.t("engine.err.stop", error=error))
        status.send("error", force=True, detail=str(error))
        return 1
    finally:
        if collector is not None:
            collector.shutdown()
        close(reader)
        close(vmm)
        close(mouse)
        close(mesh)


if __name__ == "__main__":
    sys.exit(main())
