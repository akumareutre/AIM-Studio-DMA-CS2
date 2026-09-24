"""Intersection segment/triangles avec BVH, en coordonnées monde CS2.

Deux formats acceptés :
  - AIMCOLL1 (natif) : magic (8), nom de carte UTF-8 terminé par zéro (64),
    nombre de triangles uint32 LE (4), puis 9 float32 LE par triangle.
  - ProCS2 (chao-shushu) : liste de triangles float32 brut, 36 octets par
    triangle (3 sommets × 3 coordonnées), sans en-tête ; le nom de carte est
    dérivé du nom de fichier. Détecté par la taille multiple de 36 et l'absence
    de magic.

La géométrie doit représenter les obstacles de la scène ; aucune approximation
par « spotted ».
"""
import array
import math
import mmap
import struct
from pathlib import Path

HEADER = struct.Struct('<8s64sI')
TRIANGLE = struct.Struct('<9f')
MAGIC = b'AIMCOLL1'


def normalize_map_name_static(raw):
    """Normalise un nom de carte pour la comparaison (maps/de_dust2.vpk →
    de_dust2). Version locale pour ne pas dépendre de dma_aim."""
    name = raw or ""
    for prefix in ("maps/", "maps\\"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    for ext in (".vpk", ".bsp"):
        pos = name.find(ext)
        if pos != -1:
            name = name[:pos]
    return name.strip("/\\")


class CollisionMesh:
    def __init__(self, path):
        self.file = open(path, 'rb')
        self.memory = None
        self.cache = None          # mmap du cache BVH précalculé, s'il est utilisé
        self.cache_map = None
        self.header_size = 0
        try:
            self.memory = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
            size = len(self.memory)
            magic = self.memory[:8] if size >= 8 else b''
            if magic != MAGIC:
                if size == 0 or size % TRIANGLE.size:
                    raise ValueError('Format/volume de géométrie invalide')
                count = size // TRIANGLE.size
                # Limite volontaire : de_cache (~1,62 M) et de_train (~1,54 M)
                # sont les plus grandes cartes ProCS2 connues ; au-delà, le BVH
                # Python dépasse des ressources raisonnables sur le Pi.
                if not 0 < count <= 2_000_000:
                    raise ValueError('Format/volume de géométrie invalide')
                self.header_size, self.map_name = 0, normalize_map_name_static(Path(path).stem)
            else:
                _, name, count = HEADER.unpack_from(self.memory)
                if not 0 < count <= 2_000_000:
                    raise ValueError('Format/volume de géométrie invalide')
                if size != HEADER.size + count*TRIANGLE.size:
                    raise ValueError('Géométrie tronquée')
                self.header_size = HEADER.size
                self.map_name = normalize_map_name_static(name.split(b'\0')[0].decode('utf-8', errors='replace'))
                if not self.map_name:
                    raise ValueError('Nom de carte absent')
            bounds = array.array('f')
            for i in range(count):
                t = self.triangle(i)
                if not all(math.isfinite(v) for v in t):
                    raise ValueError('Coordonnées de géométrie non finies')
                bounds.extend(min(t[a::3]) for a in range(3))
                bounds.extend(max(t[a::3]) for a in range(3))

            def build(indices):
                box = tuple(min(bounds[6*i+a] for i in indices) for a in range(3)) + tuple(
                    max(bounds[6*i+a+3] for i in indices) for a in range(3))
                if len(indices) <= 8:
                    return box, tuple(indices), None, None
                axis = max(range(3), key=lambda a: box[a+3]-box[a])
                indices.sort(key=lambda i: bounds[6*i+axis]+bounds[6*i+axis+3])
                mid = len(indices)//2
                return box, None, build(indices[:mid]), build(indices[mid:])

            self.root = build(list(range(count)))
        except BaseException:
            self.close()
            raise

    def triangle(self, index):
        return TRIANGLE.unpack_from(self.memory, self.header_size + index*TRIANGLE.size)

    @staticmethod
    def box_hit(box, origin, delta):
        low, high = 0., 1.
        for a in range(3):
            if abs(delta[a]) < 1e-12:
                if not box[a] <= origin[a] <= box[a+3]:
                    return False
            else:
                t1, t2 = (box[a]-origin[a])/delta[a], (box[a+3]-origin[a])/delta[a]
                low, high = max(low, min(t1, t2)), min(high, max(t1, t2))
                if low > high:
                    return False
        return True

    @staticmethod
    def triangle_hit(t, origin, d):
        e1 = tuple(t[3+a]-t[a] for a in range(3))
        e2 = tuple(t[6+a]-t[a] for a in range(3))
        h = (d[1]*e2[2]-d[2]*e2[1], d[2]*e2[0]-d[0]*e2[2], d[0]*e2[1]-d[1]*e2[0])
        det = sum(e1[a]*h[a] for a in range(3))
        if abs(det) < 1e-9:
            return False
        s = tuple(origin[a]-t[a] for a in range(3))
        u = sum(s[a]*h[a] for a in range(3))/det
        if not 0 <= u <= 1:
            return False
        q = (s[1]*e1[2]-s[2]*e1[1], s[2]*e1[0]-s[0]*e1[2], s[0]*e1[1]-s[1]*e1[0])
        v = sum(d[a]*q[a] for a in range(3))/det
        if v < 0 or u+v > 1:
            return False
        distance = sum(e2[a]*q[a] for a in range(3))/det
        return 0.00001 < distance < 0.99999

    def visible(self, origin, target, map_name):
        map_name = normalize_map_name_static(map_name)
        if map_name != self.map_name or not all(math.isfinite(v) for v in (*origin, *target)):
            return False
        delta = tuple(target[a]-origin[a] for a in range(3))
        stack = [self.root]
        while stack:
            box, indices, left, right = stack.pop()
            if not self.box_hit(box, origin, delta):
                continue
            if indices is not None:
                if any(self.triangle_hit(self.triangle(i), origin, delta) for i in indices):
                    return False
            else:
                stack.extend((left, right))
        return True

    # -- Cache BVH précalculé ------------------------------------------------
    # Le build du BVH Python est coûteux (de_cache ≈ 1,6 M triangles : ~55 s et
    # ~390 Mo de RAM pic). Le cache sérialise l'arbre fini : chargement en jeu
    # en ~2-5 s, sans CPU de tri ni GC massif pendant la partie.
    CACHE_MAGIC = b'AIMBVH1\x00'
    CACHE_HEADER = struct.Struct('<8sI')
    CACHE_NODE = struct.Struct('<6fI')   # bounds (6×f32) + nombre d'indices (I)

    def save_cache(self, path):
        """Sérialise le BVH en ordre préfixe : 6 float32 de boîte, compteur
        d'indices, indices. Feuille : compteur > 0 ; interne : compteur = 0."""
        parts = [self.CACHE_MAGIC]
        count = [0]

        def emit(node):
            box, indices, left, right = node
            count[0] += 1
            if indices is None:
                encode = self.CACHE_NODE.pack(*box, 0)
            else:
                encode = self.CACHE_NODE.pack(*box, len(indices)) + array.array('I', indices).tobytes()
            parts.append(encode)
            if left is not None:
                emit(left)
            if right is not None:
                emit(right)

        emit(self.root)
        header = self.CACHE_HEADER.pack(self.CACHE_MAGIC, count[0])
        with open(path, 'wb') as cache:
            cache.write(header)
            for part in parts[1:]:
                cache.write(part)

    @classmethod
    def from_cache(cls, path, geometry_path):
        """Reconstruit un BVH depuis un cache précalculé. Le fichier de géométrie
        d'origine reste ouvert pour lire les triangles à la volée."""
        self = cls.__new__(cls)
        self.cache = None
        self.cache_map = None
        self.file = open(geometry_path, 'rb')
        self.memory = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
        size = len(self.memory)
        magic = self.memory[:8] if size >= 8 else b''
        if magic == MAGIC:
            _, name, count = HEADER.unpack_from(self.memory)
            self.header_size = HEADER.size
            self.map_name = normalize_map_name_static(name.split(b'\0')[0].decode('utf-8', errors='replace'))
        else:
            self.header_size = 0
            self.map_name = normalize_map_name_static(Path(geometry_path).stem)
        self.cache = open(path, 'rb')
        self.cache_map = mmap.mmap(self.cache.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            cache_magic, nodes = self.CACHE_HEADER.unpack_from(self.cache_map)
            if cache_magic != self.CACHE_MAGIC or not 0 < nodes <= 4_000_000:
                raise ValueError('Cache BVH invalide')
            self._cache_off = self.CACHE_HEADER.size
            self.root = self._build_from_cache()
        except BaseException:
            self.close()
            raise
        return self

    def _build_from_cache(self):
        node_size = self.CACHE_NODE.size
        data = self.cache_map
        offset = [self._cache_off]

        def read_child():
            box = self.CACHE_NODE.unpack_from(data, offset[0])
            offset[0] += node_size
            index_count = box[6]
            if index_count:
                arr = array.array('I')
                arr.frombytes(data[offset[0]:offset[0]+index_count*4])
                indices = tuple(arr)
                offset[0] += index_count*4
                return box[:6], indices, None, None
            return box[:6], None, read_child(), read_child()

        return read_child()

    def close(self):
        if getattr(self, 'cache_map', None) is not None:
            self.cache_map.close()
            self.cache_map = None
        if getattr(self, 'cache', None) is not None:
            self.cache.close()
            self.cache = None
        if getattr(self, 'memory', None) is not None:
            self.memory.close()
            self.memory = None
        if getattr(self, 'file', None) is not None:
            self.file.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Convertir un OBJ de collision, en coordonnées monde CS2, en géométrie de visibilité')
    parser.add_argument('obj')
    parser.add_argument('output')
    parser.add_argument('--map', required=True)
    parser.add_argument('--raw', action='store_true',
                        help='Format ProCS2 (chao-shushu) : triangles float32 bruts, sans en-tête ; nom de carte = nom du fichier')
    args = parser.parse_args()
    name = args.map.encode()
    if not args.raw and not 1 <= len(name) <= 63:
        parser.error('Nom de carte : 1 à 63 octets UTF-8')
    vertices, triangles = [], []
    with open(args.obj) as source:
        for line in source:
            parts = line.split('#', 1)[0].split()
            if not parts:
                continue
            if parts[0] == 'v':
                point = tuple(map(float, parts[1:4]))
                if len(point) != 3 or not all(math.isfinite(v) for v in point):
                    raise ValueError('Sommet OBJ invalide')
                vertices.append(point)
            elif parts[0] == 'f':
                face = [int(p.split('/')[0]) for p in parts[1:]]
                if len(face) != 3:
                    raise ValueError('Exporter un OBJ triangulé : faces non triangulaires refusées')
                indices = [i-1 if i > 0 else len(vertices)+i for i in face]
                if 0 in face or any(i < 0 or i >= len(vertices) for i in indices):
                    raise ValueError('Indice de face invalide')
                triangles.append(tuple(v for i in indices for v in vertices[i]))
    if not 0 < len(triangles) <= 1000000:
        raise ValueError('Nombre de triangles invalide')
    with open(args.output, 'xb') as output:
        if args.raw:
            for triangle in triangles:
                output.write(TRIANGLE.pack(*triangle))
        else:
            output.write(HEADER.pack(b'AIMCOLL1', name, len(triangles)))
            for triangle in triangles:
                output.write(TRIANGLE.pack(*triangle))
    print(f'{len(triangles)} triangles enregistrés pour {args.map}')
