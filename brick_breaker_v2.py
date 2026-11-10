"""
Brick Breaker v2 - Python + Pygame

Instalasi : pip install pygame-ce   (atau: uv run --with pygame-ce brick_breaker_v2.py)

Kontrol:
  Panah Kiri/Kanan, A/D, atau Mouse : gerakkan paddle
  SPASI / Klik kiri                 : luncurkan bola
  P : jeda     M : musik on/off     R : mulai ulang     ESC : keluar

Gift (jatuh dari brick yang hancur, tangkap dengan paddle):
  3 (hijau) : tambah 2 bola baru dari paddle (total jadi 3)
  W (biru)  : paddle memanjang selama 3 detik
  B (merah) : bola ledak, brick yang hancur meledakkan 3 brick terdekat

Semua suara dan musik dibuat otomatis lewat kode (tanpa file audio).
"""

import math
import random
import sys
from array import array

import pygame

# ---------- Konfigurasi ----------
WIDTH, HEIGHT = 800, 600
FPS = 60

PADDLE_W, PADDLE_H = 120, 14
PADDLE_SPEED = 9
BALL_R = 8
BASE_SPEED = 6.0
MAX_SPEED = 12.5
MAX_BALLS = 8

BRICK_COLS = 12
BRICK_W, BRICK_H, BRICK_GAP = 62, 22, 4
BRICK_TOP = 80
BRICK_LEFT = (WIDTH - (BRICK_COLS * BRICK_W + (BRICK_COLS - 1) * BRICK_GAP)) // 2

GIFT_SPEED = 3.2
GIFT_R = 13
WIDE_TIME = 3.0      # detik
BOOM_TIME = 8.0      # detik
WIDE_FACTOR = 1.7

BG = (15, 18, 30)
WHITE = (240, 240, 245)
ORANGE = (255, 150, 50)
ROW_COLORS = [
    (239, 83, 80), (255, 167, 38), (255, 238, 88),
    (102, 187, 106), (66, 165, 245), (171, 71, 188),
]
GIFT_TYPES = {
    "multi": ("3", (102, 187, 106)),
    "wide": ("W", (66, 165, 245)),
    "boom": ("B", (239, 83, 80)),
}


# ---------- Bentuk brick tiap level ----------
def pat_classic():
    return [[True] * BRICK_COLS for _ in range(6)]


def pat_pyramid():
    return [[abs(c - 5.5) <= r + 0.5 for c in range(BRICK_COLS)] for r in range(7)]


def pat_diamond():
    return [[abs(c - 5.5) + abs(r - 4) <= 5 for c in range(BRICK_COLS)] for r in range(9)]


def pat_checker():
    return [[(r + c) % 2 == 0 for c in range(BRICK_COLS)] for r in range(7)]


def pat_wave():
    return [[abs(r - (3.5 + 2.5 * math.sin(c * 0.65))) < 1.3 for c in range(BRICK_COLS)]
            for r in range(8)]


def pat_heart():
    rows = [
        ".####..####.",
        "############",
        "############",
        ".##########.",
        "..########..",
        "...######...",
        "....####....",
        ".....##.....",
    ]
    return [[ch == "#" for ch in row] for row in rows]


def pat_x():
    return [[abs(c - r * 11 / 7) < 1.3 or abs(c - (11 - r * 11 / 7)) < 1.3
             for c in range(BRICK_COLS)] for r in range(8)]


def pat_stairs():
    return [[c <= r * 2 + 1 for c in range(BRICK_COLS)] for r in range(7)]


def pat_ring():
    grid = []
    for r in range(9):
        row = []
        for c in range(BRICK_COLS):
            d = ((c - 5.5) / 5.8) ** 2 + ((r - 4) / 4.3) ** 2
            row.append(0.35 <= d <= 1.0)
        grid.append(row)
    return grid


PATTERNS = [
    ("Klasik", pat_classic), ("Piramida", pat_pyramid), ("Berlian", pat_diamond),
    ("Papan Catur", pat_checker), ("Gelombang", pat_wave), ("Hati", pat_heart),
    ("Huruf X", pat_x), ("Tangga", pat_stairs), ("Cincin", pat_ring),
]


def level_params(level):
    """Semakin tinggi level: bola lebih cepat, paddle lebih kecil, brick lebih kuat."""
    speed = min(BASE_SPEED + (level - 1) * 0.7, MAX_SPEED)
    paddle_w = max(70, PADDLE_W - (level - 1) * 6)
    p2 = min(0.12 * (level - 1), 0.6)                       # peluang brick 2x pukul
    p3 = min(0.08 * (level - 2), 0.35) if level >= 3 else 0  # peluang brick 3x pukul
    gift_chance = max(0.15, 0.28 - 0.01 * level)
    return speed, paddle_w, p2, p3, gift_chance


def build_bricks(level, p2, p3):
    name, fn = PATTERNS[(level - 1) % len(PATTERNS)]
    bricks = []
    for r, row in enumerate(fn()):
        for c, on in enumerate(row):
            if not on:
                continue
            x = BRICK_LEFT + c * (BRICK_W + BRICK_GAP)
            y = BRICK_TOP + r * (BRICK_H + BRICK_GAP)
            roll = random.random()
            hp = 3 if roll < p3 else (2 if roll < p3 + p2 else 1)
            bricks.append({
                "rect": pygame.Rect(x, y, BRICK_W, BRICK_H),
                "color": ROW_COLORS[r % len(ROW_COLORS)],
                "hp": hp, "max": hp,
            })
    return name, bricks


# ---------- Pembuat suara (sintesis) ----------
def midi_freq(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tone(sr, freq, dur, vol, wave="square", decay=3.0, slide=0.0):
    n = int(sr * dur)
    out = []
    phase = 0.0
    atk = max(1, int(sr * 0.004))
    rel = max(1, int(sr * 0.006))
    for i in range(n):
        phase += (freq + slide * i / sr) / sr
        p = phase % 1.0
        if wave == "square":
            s = 1.0 if p < 0.5 else -1.0
        elif wave == "tri":
            s = 4.0 * abs(p - 0.5) - 1.0
        else:
            s = math.sin(2 * math.pi * phase)
        env = math.exp(-decay * i / n) * min(1.0, i / atk, (n - i) / rel)
        out.append(s * vol * env)
    return out


def noise(sr, dur, vol, decay=4.0, hold=1):
    n = int(sr * dur)
    out = []
    v = 0.0
    for i in range(n):
        if i % hold == 0:
            v = random.uniform(-1, 1)
        out.append(v * vol * math.exp(-decay * i / n))
    return out


def mix(*tracks):
    out = [0.0] * max(len(t) for t in tracks)
    for t in tracks:
        for i, v in enumerate(t):
            out[i] += v
    return out


def seq(sr, notes, vol, wave):
    out = []
    for f, d in notes:
        out += tone(sr, f, d, vol, wave, decay=2.0)
    return out


def add_into(buf, start, samples):
    for i, v in enumerate(samples):
        j = start + i
        if j >= len(buf):
            break
        buf[j] += v


class Audio:
    MUSIC_VOL = 0.3

    def __init__(self):
        self.ok = False
        self.sounds = {}
        self.music = None
        self.music_on = True
        info = pygame.mixer.get_init()
        if not info:
            return
        self.sr, fmt, self.ch = info
        if fmt != -16 or self.ch not in (1, 2):
            return
        try:
            self._build()
            self.ok = True
        except Exception as exc:  # audio tidak boleh membuat game crash
            print("Audio dinonaktifkan:", exc)

    def _snd(self, samples):
        buf = array("h")
        for s in samples:
            v = int(max(-1.0, min(1.0, s)) * 32767)
            buf.append(v)
            if self.ch == 2:
                buf.append(v)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def _build(self):
        sr, s = self.sr, self.sounds
        s["paddle"] = self._snd(tone(sr, 300, 0.09, 0.5, "square", 4, 500))
        s["hit"] = self._snd(tone(sr, 700, 0.05, 0.4, "square", 5, -200))
        s["break"] = self._snd(tone(sr, 520, 0.10, 0.45, "square", 4, 500))
        s["gift"] = self._snd(seq(sr, [(523, .07), (659, .07), (784, .07), (1047, .12)], 0.4, "square"))
        s["boom"] = self._snd(mix(noise(sr, 0.5, 0.9, 5, 7),
                                  tone(sr, 140, 0.5, 0.8, "sine", 4, -200)))
        s["lose"] = self._snd(tone(sr, 420, 0.5, 0.5, "sine", 2, -350))
        s["levelup"] = self._snd(seq(sr, [(523, .1), (659, .1), (784, .1), (1047, .25)], 0.35, "square"))
        s["gameover"] = self._snd(seq(sr, [(392, .22), (330, .22), (262, .22), (196, .5)], 0.6, "tri"))
        self.music = self._snd(self._compose())

    def _compose(self):
        """Loop chiptune sederhana: Am - F - C - G, dua putaran."""
        sr = self.sr
        eighth = 0.2  # 150 BPM
        chords = [(45, [57, 60, 64]), (41, [53, 57, 60]), (48, [55, 60, 64]), (43, [55, 59, 62])]
        patterns = [[0, 1, 2, 1, 0, 1, 2, 1], [2, 1, 2, 3, 2, 1, 0, 1]]
        step_n = int(sr * eighth)
        buf = [0.0] * (step_n * 8 * len(chords) * len(patterns))
        step = 0
        for pat in patterns:
            for root, triad in chords:
                notes = triad + [triad[0] + 12]
                for i in range(8):
                    start = step * step_n
                    add_into(buf, start, tone(sr, midi_freq(notes[pat[i]] + 12), eighth, 0.11, "square", 3))
                    if i % 2 == 0:
                        add_into(buf, start, tone(sr, midi_freq(root), eighth * 2, 0.22, "tri", 1.5))
                    else:
                        add_into(buf, start, noise(sr, 0.05, 0.05, 6, 3))
                    if i % 4 == 0:
                        add_into(buf, start, tone(sr, 110, 0.12, 0.3, "sine", 4, -500))
                    step += 1
        return buf

    def play(self, name):
        if self.ok:
            self.sounds[name].play()

    def start_music(self):
        if self.ok:
            self.music.set_volume(self.MUSIC_VOL)
            self.music.play(loops=-1)

    def toggle_music(self):
        if self.ok:
            self.music_on = not self.music_on
            self.music.set_volume(self.MUSIC_VOL if self.music_on else 0.0)


class Ball:
    __slots__ = ("x", "y", "vx", "vy", "stuck")

    def __init__(self, x, y, vx=0.0, vy=0.0, stuck=False):
        self.x, self.y, self.vx, self.vy, self.stuck = float(x), float(y), vx, vy, stuck


# ---------- Game ----------
class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption("Brick Breaker v2")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22)
        self.small = pygame.font.SysFont("arial", 17)
        self.big = pygame.font.SysFont("arial", 52, bold=True)
        self.audio = Audio()
        self.audio.start_music()
        self.reset()
