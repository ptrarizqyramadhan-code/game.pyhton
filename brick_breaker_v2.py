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

