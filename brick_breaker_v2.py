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

    # ----- State -----
    def reset(self):
        self.score = 0
        self.lives = 3
        self.level = 1
        self.paused = False
        self.paddle = pygame.Rect((WIDTH - PADDLE_W) // 2, HEIGHT - 40, PADDLE_W, PADDLE_H)
        self.setup_level()

    def setup_level(self):
        self.speed, self.base_w, p2, p3, self.gift_chance = level_params(self.level)
        self.level_name, self.bricks = build_bricks(self.level, p2, p3)
        self.gifts, self.particles, self.flashes = [], [], []
        self.wide_t = self.boom_t = 0.0
        self.shake = 0
        self.banner = 2.5
        self.paddle.width = self.base_w
        self.paddle.centerx = WIDTH // 2
        self.reset_ball()

    def reset_ball(self):
        self.balls = [Ball(self.paddle.centerx, self.paddle.top - BALL_R - 1, stuck=True)]
        self.state = "ready"

    def launch(self):
        if self.state == "ready":
            a = math.radians(random.choice([-20, 20]))
            b = self.balls[0]
            b.vx, b.vy, b.stuck = self.speed * math.sin(a), -self.speed * math.cos(a), False
            self.state = "playing"

    def next_level(self):
        self.level += 1
        self.audio.play("levelup")
        self.setup_level()

    def lose_life(self):
        self.lives -= 1
        self.gifts.clear()
        self.wide_t = self.boom_t = 0.0
        if self.lives <= 0:
            self.state = "gameover"
            self.audio.play("gameover")
        else:
            self.audio.play("lose")
            self.reset_ball()

    # ----- Efek -----
    def spawn_particles(self, pos, color, n):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(1, 4)
            self.particles.append([pos[0], pos[1], math.cos(a) * sp, math.sin(a) * sp - 1,
                                   random.randint(20, 40), color])

    def maybe_drop_gift(self, pos):
        if random.random() < self.gift_chance:
            self.gifts.append([float(pos[0]), float(pos[1]), random.choice(list(GIFT_TYPES))])

    def apply_gift(self, kind):
        self.audio.play("gift")
        if kind == "multi":
            for ang in (-25, 25):
                if len(self.balls) >= MAX_BALLS:
                    break
                a = math.radians(ang)
                self.balls.append(Ball(self.paddle.centerx + ang * 0.4, self.paddle.top - BALL_R - 1,
                                       self.speed * math.sin(a), -self.speed * math.cos(a)))
        elif kind == "wide":
            self.wide_t = WIDE_TIME
        elif kind == "boom":
            self.boom_t = BOOM_TIME

    def destroy_brick(self, brick, sound=True, chain=True):
        if brick not in self.bricks:
            return
        self.bricks.remove(brick)
        self.score += 10 * brick["max"]
        center = brick["rect"].center
        self.spawn_particles(center, brick["color"], 8)
        self.maybe_drop_gift(center)
        if sound:
            self.audio.play("break")
        if chain and self.boom_t > 0:
            self.explode(center)

    def explode(self, center):
        cx, cy = center
        victims = sorted(self.bricks, key=lambda o: (o["rect"].centerx - cx) ** 2
                         + (o["rect"].centery - cy) ** 2)[:3]
        if not victims:
            return
        for v in victims:
            self.spawn_particles(v["rect"].center, ORANGE, 6)
            self.destroy_brick(v, sound=False, chain=False)
        self.flashes.append([cx, cy, 18])
        self.shake = 10
        self.audio.play("boom")

    # ----- Input -----
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.quit()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.quit()
                elif e.key == pygame.K_SPACE and not self.paused:
                    self.launch()
                elif e.key == pygame.K_r:
                    self.reset()
                elif e.key == pygame.K_m:
                    self.audio.toggle_music()
                elif e.key == pygame.K_p and self.state in ("ready", "playing"):
                    self.paused = not self.paused
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not self.paused:
                self.launch()
            elif e.type == pygame.MOUSEMOTION and not self.paused:
                self.paddle.centerx = e.pos[0]
        if not self.paused:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.paddle.x -= PADDLE_SPEED
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.paddle.x += PADDLE_SPEED
        self.paddle.clamp_ip(self.canvas.get_rect())

    # ----- Update -----
    def normalize(self, b):
        sp = math.hypot(b.vx, b.vy)
        if sp == 0:
            return
        k = self.speed / sp
        b.vx *= k
        b.vy *= k
        min_vy = self.speed * 0.25  # cegah bola melaju hampir datar
        if abs(b.vy) < min_vy:
            b.vy = math.copysign(min_vy, b.vy if b.vy else -1)
            b.vx = math.copysign(math.sqrt(self.speed ** 2 - b.vy ** 2), b.vx if b.vx else 1)

    def update_ball(self, b):
        b.x += b.vx
        b.y += b.vy
        if b.x - BALL_R <= 0:
            b.x, b.vx = BALL_R, abs(b.vx)
        elif b.x + BALL_R >= WIDTH:
            b.x, b.vx = WIDTH - BALL_R, -abs(b.vx)
        if b.y - BALL_R <= 0:
            b.y, b.vy = BALL_R, abs(b.vy)
        if b.y - BALL_R > HEIGHT:
            return False

        rect = pygame.Rect(int(b.x - BALL_R), int(b.y - BALL_R), BALL_R * 2, BALL_R * 2)

        if rect.colliderect(self.paddle) and b.vy > 0:
            off = max(-1.0, min(1.0, (b.x - self.paddle.centerx) / (self.paddle.width / 2)))
            ang = math.radians(off * 60)
            b.vx, b.vy = self.speed * math.sin(ang), -self.speed * math.cos(ang)
            b.y = self.paddle.top - BALL_R - 1
            self.audio.play("paddle")

        for brick in self.bricks:
            r = brick["rect"]
            if rect.colliderect(r):
                ox = min(rect.right - r.left, r.right - rect.left)
                oy = min(rect.bottom - r.top, r.bottom - rect.top)
                if ox < oy:
                    b.vx = -abs(b.vx) if rect.centerx < r.centerx else abs(b.vx)
                else:
                    b.vy = -abs(b.vy) if rect.centery < r.centery else abs(b.vy)
                brick["hp"] -= 1
                if brick["hp"] <= 0:
                    self.destroy_brick(brick)
                else:
                    self.spawn_particles(rect.center, WHITE, 3)
                    self.audio.play("hit")
                break

        self.normalize(b)
        return True

    def update(self):
        dt = 1.0 / FPS
        self.banner = max(0.0, self.banner - dt)
        self.shake = max(0, self.shake - 1)

        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.15
            p[4] -= 1
        self.particles = [p for p in self.particles if p[4] > 0]
        for f in self.flashes:
            f[2] -= 1
        self.flashes = [f for f in self.flashes if f[2] > 0]

        # lebar paddle (berubah halus)
        target = int(self.base_w * (WIDE_FACTOR if self.wide_t > 0 else 1))
        w = self.paddle.width
        w = min(target, w + 6) if w < target else max(target, w - 6)
        cx = self.paddle.centerx
        self.paddle.width = w
        self.paddle.centerx = cx
        self.paddle.clamp_ip(self.canvas.get_rect())

        if self.state == "ready":
            b = self.balls[0]
            b.x, b.y = self.paddle.centerx, self.paddle.top - BALL_R - 1
            return
        if self.state != "playing":
            return

        self.wide_t = max(0.0, self.wide_t - dt)
        self.boom_t = max(0.0, self.boom_t - dt)

        self.balls = [b for b in self.balls if self.update_ball(b)]

        for g in self.gifts[:]:
            g[1] += GIFT_SPEED
            if pygame.Rect(g[0] - GIFT_R, g[1] - GIFT_R, GIFT_R * 2, GIFT_R * 2).colliderect(self.paddle):
                self.apply_gift(g[2])
                self.gifts.remove(g)
            elif g[1] > HEIGHT + GIFT_R:
                self.gifts.remove(g)

        if not self.bricks:
            self.next_level()
        elif not self.balls:
            self.lose_life()

    # ----- Gambar -----
    def text(self, txt, font, color, center):
        surf = font.render(txt, True, color)
        self.canvas.blit(surf, surf.get_rect(center=center))

    def draw(self):
        c = self.canvas
        c.fill(BG)

        for b in self.bricks:
            pygame.draw.rect(c, b["color"], b["rect"], border_radius=4)
            if b["hp"] > 1:
                pygame.draw.rect(c, WHITE, b["rect"], width=b["hp"] * 2 - 1, border_radius=4)

        for x, y, kind in self.gifts:
            label, col = GIFT_TYPES[kind]
            pygame.draw.circle(c, col, (int(x), int(y)), GIFT_R)
            pygame.draw.circle(c, WHITE, (int(x), int(y)), GIFT_R, 2)
            self.text(label, self.small, WHITE, (int(x), int(y)))

        pad_col = (130, 200, 255) if self.wide_t > 0 else WHITE
        pygame.draw.rect(c, pad_col, self.paddle, border_radius=7)
        ball_col = ORANGE if self.boom_t > 0 else WHITE
        for b in self.balls:
            pygame.draw.circle(c, ball_col, (int(b.x), int(b.y)), BALL_R)

        for x, y, _vx, _vy, life, col in self.particles:
            size = max(1, life // 10)
            pygame.draw.rect(c, col, (int(x), int(y), size, size))
        for x, y, life in self.flashes:
            pygame.draw.circle(c, ORANGE, (int(x), int(y)), 90 - life * 4, 3)

        # HUD
        c.blit(self.font.render(f"Skor: {self.score}", True, WHITE), (12, 10))
        self.text(f"Level {self.level}", self.font, WHITE, (WIDTH // 2, 22))
        lives = self.font.render(f"Nyawa: {self.lives}", True, WHITE)
        c.blit(lives, (WIDTH - lives.get_width() - 12, 10))
        x = 12
        for label, t, col in (("Paddle panjang", self.wide_t, (130, 200, 255)),
                              ("Bola ledak", self.boom_t, ORANGE)):
            if t > 0:
                s = self.small.render(f"{label} {t:.1f}s", True, col)
                c.blit(s, (x, 44))
                x += s.get_width() + 24
        hint = self.small.render("P jeda  |  M musik", True, (120, 125, 150))
        c.blit(hint, (WIDTH - hint.get_width() - 12, HEIGHT - 24))

        if self.banner > 0 and self.state != "gameover":
            self.text(f"LEVEL {self.level}", self.big, WHITE, (WIDTH // 2, 375))
            self.text(self.level_name, self.font, (190, 195, 220), (WIDTH // 2, 420))
        if self.state == "ready":
            if self.level == 1:
                for i, (txt, col) in enumerate([
                        ("3  = tambah bola jadi 3", GIFT_TYPES["multi"][1]),
                        ("W  = paddle panjang 3 detik", GIFT_TYPES["wide"][1]),
                        ("B  = bola ledak (3 brick terdekat)", GIFT_TYPES["boom"][1])]):
                    self.text(txt, self.small, col, (WIDTH // 2, 455 + i * 22))
            self.text("Tekan SPASI atau klik untuk meluncurkan bola", self.font, WHITE,
                      (WIDTH // 2, 525))

        if self.state == "gameover":
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 150))
            c.blit(shade, (0, 0))
            self.text("GAME OVER", self.big, (239, 83, 80), (WIDTH // 2, HEIGHT // 2 - 20))
            self.text(f"Skor akhir: {self.score}  |  Level: {self.level}", self.font, WHITE,
                      (WIDTH // 2, HEIGHT // 2 + 30))
            self.text("Tekan R untuk main lagi", self.font, WHITE, (WIDTH // 2, HEIGHT // 2 + 62))
        elif self.paused:
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 130))
            c.blit(shade, (0, 0))
            self.text("JEDA", self.big, WHITE, (WIDTH // 2, HEIGHT // 2))

        ox = random.randint(-4, 4) if self.shake else 0
        oy = random.randint(-4, 4) if self.shake else 0
        self.screen.fill(BG)
        self.screen.blit(c, (ox, oy))
        pygame.display.flip()

    # ----- Loop -----
    def quit(self):
        pygame.quit()
        sys.exit()

    def run(self):
        was_paused = False
        while True:
            self.handle_events()
            if self.paused != was_paused:
                (pygame.mixer.pause if self.paused else pygame.mixer.unpause)()
                was_paused = self.paused
            if not self.paused:
                self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()
