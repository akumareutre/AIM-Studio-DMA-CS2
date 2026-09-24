"""État de bascule et compensation de recul indépendante du suivi de cible."""
import math

HOTKEYS = {'F6': 'km.isdown(63)', 'F7': 'km.isdown(64)', 'F8': 'km.isdown(65)',
           'F9': 'km.isdown(66)', 'Souris 4': 'km.side1()', 'Souris 5': 'km.side2()'}


class Toggle:
    def __init__(self):
        self.enabled = True
        self.held = False

    def update(self, held, request=False):
        changed = (held and not self.held) or request
        self.held = held
        if changed:
            self.enabled = not self.enabled
        return changed


class Recoil:
    def __init__(self):
        self.previous = None
        self.shots = 0

    def reset(self):
        self.previous = None
        self.shots = 0

    def update(self, punch, shots, strength):
        if punch is None or not 0 <= shots <= 200 or not all(math.isfinite(p) and abs(p) < 45 for p in punch):
            self.reset()
            return (0., 0.), (0., 0.)
        current = tuple(p*2*strength/100 for p in punch[:2]) if shots else (0., 0.)
        # Une nouvelle rafale ou une reprise après perte de données initialise
        # la référence ; ne pas compenser d'un coup un recul déjà accumulé.
        if shots <= 1 or shots < self.shots or self.previous is None:
            difference = (0., 0.)
        else:
            difference = tuple(current[i]-self.previous[i] for i in range(2))
        self.previous, self.shots = current, shots
        return current, difference
