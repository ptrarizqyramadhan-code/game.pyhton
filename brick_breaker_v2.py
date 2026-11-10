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
