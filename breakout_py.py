"""
Brick Breaker - Game sederhana dengan Python + Pygame

Instalasi : pip install pygame
Menjalankan: python brick_breaker.py

Kontrol:
  Panah Kiri/Kanan atau A/D atau Mouse : gerakkan paddle
  SPASI / Klik kiri                    : luncurkan bola
  R                                    : mulai ulang
  ESC                                  : keluar
"""
import tkinter as tk
import math
import sys

import pygame

# ---------- Konfigurasi ----------
WIDTH, HEIGHT = 800, 600
FPS = 60

PADDLE_W, PADDLE_H = 110, 14
PADDLE_SPEED = 9
BALL_R = 8
BASE_SPEED = 6.0

BRICK_ROWS, BRICK_COLS = 6, 10
BRICK_GAP = 4
BRICK_TOP = 70
BRICK_H = 24

BG = (15, 18, 30)
WHITE = (240, 240, 245)
ROW_COLORS = [
    (239, 83, 80),
    (255, 167, 38),
    (255, 238, 88),
    (102, 187, 106),
    (66, 165, 245),
    (171, 71, 188),
]


def build_bricks():
    """Membuat daftar brick (Rect, warna, poin)."""
    total_gap = BRICK_GAP * (BRICK_COLS + 1)
    bw = (WIDTH - total_gap) // BRICK_COLS
    bricks = []
    for r in range(BRICK_ROWS):
        for c in range(BRICK_COLS):
            x = BRICK_GAP + c * (bw + BRICK_GAP)
            y = BRICK_TOP + r * (BRICK_H + BRICK_GAP)
            points = (BRICK_ROWS - r) * 10
            bricks.append((pygame.Rect(x, y, bw, BRICK_H), ROW_COLORS[r % len(ROW_COLORS)], points))
    return bricks


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Brick Breaker")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22)
        self.big = pygame.font.SysFont("arial", 52, bold=True)
        self.reset()

    # ---------- State ----------
    def reset(self):
        self.score = 0
        self.lives = 3
        self.level = 1
        self.paddle = pygame.Rect((WIDTH - PADDLE_W) // 2, HEIGHT - 40, PADDLE_W, PADDLE_H)
        self.bricks = build_bricks()
        self.state = "ready"  # ready | playing | gameover
        self.reset_ball()

    def reset_ball(self):
        self.speed = BASE_SPEED + (self.level - 1) * 0.8
        self.bx = float(self.paddle.centerx)
        self.by = float(self.paddle.top - BALL_R - 1)
        self.vx = 0.0
        self.vy = 0.0
        self.state = "ready"

    def launch(self):
        if self.state == "ready":
            angle = math.radians(-20)
            self.vx = self.speed * math.sin(angle)
            self.vy = -self.speed * math.cos(angle)
            self.state = "playing"

    def next_level(self):
        self.level += 1
        self.bricks = build_bricks()
        self.reset_ball()

    # ---------- Input ----------
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.quit()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.quit()
                elif e.key == pygame.K_SPACE:
                    self.launch()
                elif e.key == pygame.K_r:
                    self.reset()
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.launch()
            elif e.type == pygame.MOUSEMOTION:
                self.paddle.centerx = e.pos[0]

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.paddle.x -= PADDLE_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.paddle.x += PADDLE_SPEED
        self.paddle.clamp_ip(self.screen.get_rect())

    # ---------- Update ----------
    def update(self):
        if self.state == "ready":
            self.bx = float(self.paddle.centerx)
            self.by = float(self.paddle.top - BALL_R - 1)
            return
        if self.state != "playing":
            return

        self.bx += self.vx
        self.by += self.vy

        # Dinding
        if self.bx - BALL_R <= 0:
            self.bx = BALL_R
            self.vx = abs(self.vx)
        elif self.bx + BALL_R >= WIDTH:
            self.bx = WIDTH - BALL_R
            self.vx = -abs(self.vx)
        if self.by - BALL_R <= 0:
            self.by = BALL_R
            self.vy = abs(self.vy)

        # Bola jatuh
        if self.by - BALL_R > HEIGHT:
            self.lives -= 1
            if self.lives <= 0:
                self.state = "gameover"
            else:
                self.reset_ball()
            return

        ball_rect = pygame.Rect(self.bx - BALL_R, self.by - BALL_R, BALL_R * 2, BALL_R * 2)

        # Paddle: sudut pantulan tergantung posisi benturan
        if ball_rect.colliderect(self.paddle) and self.vy > 0:
            offset = (self.bx - self.paddle.centerx) / (self.paddle.width / 2)
            offset = max(-1.0, min(1.0, offset))
            angle = math.radians(offset * 60)
            self.vx = self.speed * math.sin(angle)
            self.vy = -self.speed * math.cos(angle)
            self.by = self.paddle.top - BALL_R - 1

        # Brick
        for i, (rect, _color, points) in enumerate(self.bricks):
            if ball_rect.colliderect(rect):
                overlap_x = min(ball_rect.right - rect.left, rect.right - ball_rect.left)
                overlap_y = min(ball_rect.bottom - rect.top, rect.bottom - ball_rect.top)
                if overlap_x < overlap_y:
                    self.vx = -self.vx
                else:
                    self.vy = -self.vy
                self.score += points
                del self.bricks[i]
                break

        if not self.bricks:
            self.next_level()

    # ---------- Gambar ----------
    def draw_text(self, text, font, color, center):
        surf = font.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(center=center))

    def draw(self):
        self.screen.fill(BG)

        for rect, color, _ in self.bricks:
            pygame.draw.rect(self.screen, color, rect, border_radius=4)

        pygame.draw.rect(self.screen, WHITE, self.paddle, border_radius=7)
        pygame.draw.circle(self.screen, WHITE, (int(self.bx), int(self.by)), BALL_R)

        # HUD
        self.screen.blit(self.font.render(f"Skor: {self.score}", True, WHITE), (12, 12))
        self.draw_text(f"Level {self.level}", self.font, WHITE, (WIDTH // 2, 24))
        lives = self.font.render(f"Nyawa: {self.lives}", True, WHITE)
        self.screen.blit(lives, (WIDTH - lives.get_width() - 12, 12))

        if self.state == "ready":
            self.draw_text("Tekan SPASI atau klik untuk meluncurkan bola", self.font, WHITE,
                           (WIDTH // 2, HEIGHT // 2 + 120))
        elif self.state == "gameover":
            self.draw_text("GAME OVER", self.big, (239, 83, 80), (WIDTH // 2, HEIGHT // 2))
            self.draw_text(f"Skor akhir: {self.score}  -  Tekan R untuk main lagi",
                           self.font, WHITE, (WIDTH // 2, HEIGHT // 2 + 55))

        pygame.display.flip()

    # ---------- Loop ----------
    def quit(self):
        pygame.quit()
        sys.exit()

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()