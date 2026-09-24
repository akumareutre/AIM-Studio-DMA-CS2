"""Profils partagés entre le moteur DMA et le menu graphique."""

PROFILES = {
    "soft": {"label": "Soft aim", "subtitle": "Assistance douce · zone proche",
             "radius": 160, "smooth_ms": 180, "max_step": 12, "hz": 30},
    "magnetic": {"label": "Magnétique", "subtitle": "Tout l’écran · cible maintenue",
                 "radius": 160, "smooth_ms": 110, "max_step": 32, "hz": 30},
    "rage": {"label": "Rage aim", "subtitle": "Suivi continu · correction directe",
             "radius": 160, "smooth_ms": 0, "max_step": 1000, "hz": 60},
}

BODY_PARTS = {
    "head": ("Tête", 6),
    "neck": ("Cou", 5),
    "chest": ("Poitrine", 4),
    "stomach": ("Ventre", 2),
    "pelvis": ("Bassin", 0),
}


def select_target(points, matrix, width, height, mode, radius, locked=None):
    """Les modes plein écran conservent leur cible tant qu'elle reste admissible."""
    from dma_aim import world_to_screen
    candidates = {}
    for pawn, point in points.items():
        screen = world_to_screen(point, matrix, width, height)
        if screen is None:
            continue
        distance = (screen[0] - width / 2)**2 + (screen[1] - height / 2)**2
        if mode != "soft" or distance <= radius**2:
            candidates[pawn] = (distance, point)
    if mode in ("magnetic", "rage") and locked in candidates:
        return locked, candidates[locked][1]
    if not candidates:
        return None
    pawn = min(candidates, key=lambda p: (candidates[p][0], p))
    return pawn, candidates[pawn][1]
