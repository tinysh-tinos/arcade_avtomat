import sys
import subprocess
import math
import random

def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

install_and_import('pygame')

import pygame
import os
import json

def save_score(score):
    path = os.environ.get("ARCADE_SCORE_FILE")
    if path:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"score": score}, f)
        except OSError:
            pass


pygame.init()
pygame.joystick.init()

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Mortal Kombat")
clock = pygame.time.Clock()

# ---------- Палитра ----------
SKY_TOP    = (12, 8, 28)
SKY_MID    = (48, 18, 62)
SKY_BOT    = (120, 40, 50)
SUN_COLOR  = (255, 180, 90)
SUN_GLOW   = (255, 120, 60)
MOUNTAIN_1 = (28, 16, 40)
MOUNTAIN_2 = (18, 10, 28)
TEMPLE_COL = (35, 22, 35)
TEMPLE_DARK= (22, 14, 24)
GROUND_COL = (58, 40, 34)
GROUND_LT  = (82, 58, 48)
GROUND_DK  = (34, 22, 20)

P1_COLOR   = (70, 150, 255)
P1_DARK    = (30, 80, 170)
P2_COLOR   = (255, 90, 90)
P2_DARK    = (160, 40, 50)
SKIN       = (230, 190, 150)
SKIN_DARK  = (190, 150, 115)
FIRE_P1    = (120, 210, 255)
FIRE_P2    = (255, 150, 60)

HEALTH_GREEN = (70, 230, 90)
HEALTH_YEL   = (240, 200, 60)
HEALTH_RED   = (230, 50, 50)
HEALTH_BG    = (30, 16, 20)
HEALTH_GHOST = (240, 200, 60)
TEXT_COLOR   = (255, 255, 255)
GOLD         = (255, 215, 80)

font_big   = pygame.font.SysFont("Impact", int(HEIGHT * 0.11))
font_med   = pygame.font.SysFont("Impact", int(HEIGHT * 0.055))
font_small = pygame.font.SysFont("Arial", int(HEIGHT * 0.028))
font_dmg   = pygame.font.SysFont("Impact", int(HEIGHT * 0.035))

GRAVITY         = HEIGHT * 2.8
JUMP_POWER      = -HEIGHT * 1.05
MOVE_SPEED      = WIDTH * 0.26
FIREBALL_SPEED  = WIDTH * 0.65
FIREBALL_DAMAGE = 10
ROUND_TIME      = 60

GROUND_H = int(HEIGHT * 0.16)
GROUND_Y = HEIGHT - GROUND_H

FIGHTER_W = int(WIDTH * 0.05)
FIGHTER_H = int(HEIGHT * 0.17)
FIREBALL_RADIUS = int(HEIGHT * 0.022)
HEAD_RADIUS     = int(HEIGHT * 0.038)

score = 0
best  = 0

DEADZONE = 0.4
BTN_JUMP  = 0
BTN_FIRE  = 2
BTN_START = 7

joysticks = []

def init_joysticks():
    global joysticks
    joysticks = []
    pygame.joystick.quit()
    pygame.joystick.init()
    for i in range(pygame.joystick.get_count()):
        j = pygame.joystick.Joystick(i)
        j.init()
        joysticks.append(j)


# ============================================================
#                       ФОН
# ============================================================
def make_background():
    bg = pygame.Surface((WIDTH, HEIGHT))

    # --- Небо: трёхцветный градиент ---
    for y in range(GROUND_Y):
        t = y / GROUND_Y
        if t < 0.5:
            k = t / 0.5
            r = int(SKY_TOP[0] * (1 - k) + SKY_MID[0] * k)
            g = int(SKY_TOP[1] * (1 - k) + SKY_MID[1] * k)
            b = int(SKY_TOP[2] * (1 - k) + SKY_MID[2] * k)
        else:
            k = (t - 0.5) / 0.5
            r = int(SKY_MID[0] * (1 - k) + SKY_BOT[0] * k)
            g = int(SKY_MID[1] * (1 - k) + SKY_BOT[1] * k)
            b = int(SKY_MID[2] * (1 - k) + SKY_BOT[2] * k)
        pygame.draw.line(bg, (r, g, b), (0, y), (WIDTH, y))

    # --- Звёзды в верхней части ---
    random.seed(42)
    for _ in range(160):
        sx = random.randint(0, WIDTH)
        sy = random.randint(0, int(GROUND_Y * 0.55))
        brightness = random.randint(120, 255)
        size = random.choice([1, 1, 1, 2])
        pygame.draw.circle(bg, (brightness, brightness, brightness), (sx, sy), size)
    random.seed()

    # --- Солнце с сиянием ---
    sun_x = int(WIDTH * 0.72)
    sun_y = int(GROUND_Y * 0.55)
    sun_r = int(HEIGHT * 0.13)
    for i in range(12, 0, -1):
        radius = sun_r + i * int(HEIGHT * 0.012)
        alpha = int(60 * (1 - i / 12))
        glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*SUN_GLOW, alpha), (radius, radius), radius)
        bg.blit(glow, (sun_x - radius, sun_y - radius))
    pygame.draw.circle(bg, SUN_COLOR, (sun_x, sun_y), sun_r)
    pygame.draw.circle(bg, (255, 220, 160), (sun_x, sun_y), int(sun_r * 0.75))

    # --- Дальние горы ---
    def draw_mountains(color, base_y, height_scale, seed, points_count=14):
        random.seed(seed)
        pts = [(0, GROUND_Y)]
        for i in range(points_count + 1):
            x = int(WIDTH * i / points_count)
            y = base_y - random.randint(0, int(HEIGHT * height_scale))
            pts.append((x, y))
        pts.append((WIDTH, GROUND_Y))
        pygame.draw.polygon(bg, color, pts)
        random.seed()

    draw_mountains(MOUNTAIN_2, int(GROUND_Y * 1.0), 0.20, 1, 12)
    draw_mountains(MOUNTAIN_1, int(GROUND_Y * 1.0), 0.14, 2, 16)

    # --- Пагода / храм вдалеке ---
    def draw_pagoda(cx, base_y, w, h):
        # основание
        pygame.draw.rect(bg, TEMPLE_COL, (cx - w, base_y - h, w * 2, h))
        # крыши (три уровня)
        for level in range(3):
            ly = base_y - h + int(h * level * 0.3)
            lw = int(w * (1.4 - level * 0.15))
            lh = int(h * 0.12)
            # трапеция крыши
            pygame.draw.polygon(bg, TEMPLE_DARK, [
                (cx - lw, ly + lh),
                (cx + lw, ly + lh),
                (cx + int(lw * 0.7), ly),
                (cx - int(lw * 0.7), ly),
            ])
        # шпиль
        pygame.draw.polygon(bg, TEMPLE_DARK, [
            (cx - 6, base_y - h - int(h * 0.05)),
            (cx + 6, base_y - h - int(h * 0.05)),
            (cx, base_y - h - int(h * 0.15)),
        ])

    draw_pagoda(int(WIDTH * 0.18), GROUND_Y + 10, int(WIDTH * 0.055), int(HEIGHT * 0.22))
    draw_pagoda(int(WIDTH * 0.82), GROUND_Y + 10, int(WIDTH * 0.045), int(HEIGHT * 0.18))

    # --- Земля (арена) ---
    pygame.draw.rect(bg, GROUND_COL, (0, GROUND_Y, WIDTH, GROUND_H))
    # Верхняя кромка
    pygame.draw.rect(bg, GROUND_LT, (0, GROUND_Y, WIDTH, int(HEIGHT * 0.008)))
    # Текстура — пятна песка
    random.seed(7)
    for _ in range(400):
        x = random.randint(0, WIDTH)
        y = random.randint(GROUND_Y + 10, HEIGHT - 2)
        r = random.randint(2, 7)
        shade = random.randint(-15, 15)
        col = (
            max(0, min(255, GROUND_COL[0] + shade)),
            max(0, min(255, GROUND_COL[1] + shade)),
            max(0, min(255, GROUND_COL[2] + shade)),
        )
        pygame.draw.circle(bg, col, (x, y), r)
    random.seed()
    # Линии перспективы
    for i in range(1, 14):
        y = GROUND_Y + int(GROUND_H * (i / 14) ** 1.6)
        pygame.draw.line(bg, GROUND_DK, (0, y), (WIDTH, y), 1)

    return bg


BACKGROUND = make_background()


# ============================================================
#                     ЭФФЕКТЫ
# ============================================================
class Particle:
    def __init__(self, x, y, vx, vy, color, life, size):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += HEIGHT * 1.2 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        t = max(0, self.life / self.max_life)
        r = max(1, int(self.size * t))
        alpha = int(255 * t)
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
        surf.blit(s, (int(self.x - r), int(self.y - r)))


class DamageText:
    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 0.9
        self.max_life = 0.9

    def update(self, dt):
        self.y -= HEIGHT * 0.12 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        t = max(0, self.life / self.max_life)
        alpha = int(255 * t)
        img = font_dmg.render(self.text, True, self.color)
        img.set_alpha(alpha)
        surf.blit(img, (self.x - img.get_width() // 2, self.y))


particles = []
damage_texts = []
screen_shake = 0.0


def spawn_hit_effects(x, y, color):
    global screen_shake
    for _ in range(24):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(WIDTH * 0.05, WIDTH * 0.25)
        particles.append(Particle(
            x, y,
            math.cos(ang) * spd,
            math.sin(ang) * spd - HEIGHT * 0.1,
            color,
            random.uniform(0.3, 0.7),
            random.randint(2, 5),
        ))
    screen_shake = max(screen_shake, HEIGHT * 0.012)


# ============================================================
#                      БОЕЦ
# ============================================================
class Fighter:
    def __init__(self, x, color, dark_color, facing, joy_index, keymap):
        self.x = x
        self.y = GROUND_Y
        self.w = FIGHTER_W
        self.h = FIGHTER_H
        self.vy = 0
        self.on_ground = True
        self.color = color
        self.dark = dark_color
        self.facing = facing
        self.health = 100.0
        self.display_health = 100.0   # для плавной анимации урона
        self.ghost_health = 100.0     # жёлтая подложка
        self.joy_index = joy_index
        self.keymap = keymap
        self.hit_flash = 0.0
        self.anim_t = random.uniform(0, 10)
        self.rect = pygame.Rect(0, 0, self.w, self.h)
        self.attack_anim = 0.0
        self.update_rect()

    def update_rect(self):
        self.rect = pygame.Rect(
            int(self.x - self.w // 2),
            int(self.y - self.h),
            self.w, self.h
        )

    def get_axis(self, axis_id):
        if self.joy_index is None or self.joy_index >= len(joysticks):
            return 0.0
        j = joysticks[self.joy_index]
        if axis_id >= j.get_numaxes():
            return 0.0
        val = j.get_axis(axis_id)
        return 0.0 if abs(val) < DEADZONE else val

    def get_hat(self, hat_id=0):
        if self.joy_index is None or self.joy_index >= len(joysticks):
            return (0, 0)
        j = joysticks[self.joy_index]
        if hat_id >= j.get_numhats():
            return (0, 0)
        return j.get_hat(hat_id)

    def get_button(self, btn_id):
        if self.joy_index is None or self.joy_index >= len(joysticks):
            return False
        j = joysticks[self.joy_index]
        if btn_id >= j.get_numbuttons():
            return False
        return j.get_button(btn_id)

    def move(self, keys, dt):
        move_dir = 0.0
        if keys[self.keymap["left"]]:
            move_dir -= 1.0
        if keys[self.keymap["right"]]:
            move_dir += 1.0

        axis_x = self.get_axis(0)
        if axis_x != 0.0:
            move_dir += axis_x
        hat_x, _ = self.get_hat(0)
        if hat_x != 0:
            move_dir += hat_x

        move_dir = max(-1.0, min(1.0, move_dir))
        self.x += move_dir * MOVE_SPEED * dt
        self.x = max(self.w // 2, min(WIDTH - self.w // 2, self.x))

        # Авторазворот к противнику (классика MK)
        # (оставляем фиксированный facing — каждый смотрит на центр)

        jump_pressed = keys[self.keymap["jump"]] or self.get_button(BTN_JUMP)
        if jump_pressed and self.on_ground:
            self.vy = JUMP_POWER
            self.on_ground = False

    def apply_gravity(self, dt):
        self.vy += GRAVITY * dt
        self.y += self.vy * dt
        if self.y >= GROUND_Y:
            self.y = GROUND_Y
            self.vy = 0
            self.on_ground = True

    def fire_origin(self):
        return (self.x + self.facing * self.w // 2, self.y - self.h // 2)

    def take_damage(self, amount):
        self.health -= amount
        if self.health < 0:
            self.health = 0
        self.hit_flash = 0.25
        self.attack_anim = 0.0
        spawn_hit_effects(
            self.x + self.facing * self.w * 0.2,
            self.y - self.h * 0.55,
            (255, 220, 120),
        )
        damage_texts.append(DamageText(
            self.x, self.y - self.h - HEAD_RADIUS - 10,
            f"-{amount}", (255, 200, 80)
        ))

    def update_visual(self, dt):
        # плавная анимация полос здоровья
        if self.display_health > self.health:
            self.display_health -= (100 - self.health) * dt * 2.5
            if self.display_health < self.health:
                self.display_health = self.health
        if self.ghost_health > self.health:
            self.ghost_health -= (self.ghost_health - self.health) * dt * 1.2
            if self.ghost_health < self.health:
                self.ghost_health = self.health
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.anim_t += dt

    def draw(self, surface):
        cx = int(self.x)
        # Тень
        shadow_w = int(self.w * 1.2)
        shadow_h = int(HEIGHT * 0.02)
        shadow = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 130), (0, 0, shadow_w, shadow_h))
        surface.blit(shadow, (cx - shadow_w // 2, GROUND_Y - shadow_h // 2))

        # Лёгкое «дыхание»
        bob = math.sin(self.anim_t * 3.2) * HEIGHT * 0.004
        base_y = self.y + bob

        # Ноги
        leg_w = int(self.w * 0.28)
        leg_h = int(self.h * 0.45)
        leg_y = base_y - leg_h
        pygame.draw.rect(surface, self.dark,
                         (cx - int(self.w * 0.42) - leg_w // 2,
                          leg_y, leg_w, leg_h), border_radius=6)
        pygame.draw.rect(surface, self.dark,
                         (cx + int(self.w * 0.42) - leg_w // 2,
                          leg_y, leg_w, leg_h), border_radius=6)

        # Торс
        body_rect = pygame.Rect(
            cx - self.w // 2,
            int(base_y - self.h),
            self.w,
            int(self.h * 0.62)
        )
        body_color = self.color
        if self.hit_flash > 0:
            k = self.hit_flash / 0.25
            body_color = (
                int(self.color[0] + (255 - self.color[0]) * k),
                int(self.color[1] + (255 - self.color[1]) * k),
                int(self.color[2] + (255 - self.color[2]) * k),
            )
        pygame.draw.rect(surface, body_color, body_rect, border_radius=10)
        pygame.draw.rect(surface, (255, 255, 255), body_rect, 2, border_radius=10)

        # Пояс
        belt_y = body_rect.bottom - int(self.h * 0.06)
        pygame.draw.rect(surface, (30, 30, 30),
                         (body_rect.left, belt_y, body_rect.width,
                          int(self.h * 0.05)))
        pygame.draw.rect(surface, GOLD,
                         (body_rect.left, belt_y, body_rect.width,
                          int(self.h * 0.05)), 2)

        # Руки
        arm_y = int(body_rect.top + self.h * 0.12)
        arm_len = int(self.w * 1.0)
        hand_r = max(6, int(self.h * 0.06))

        # Задняя рука
        pygame.draw.line(surface, self.dark,
                         (cx, arm_y),
                         (cx - self.facing * int(arm_len * 0.5),
                          arm_y + int(self.h * 0.12)),
                         max(6, int(self.h * 0.07)))
        # Передняя рука (вытянута в сторону противника)
        pygame.draw.line(surface, body_color,
                         (cx, arm_y),
                         (cx + self.facing * arm_len,
                          arm_y + int(self.h * 0.05)),
                         max(8, int(self.h * 0.09)))
        pygame.draw.circle(surface, SKIN,
                           (cx + self.facing * arm_len,
                            arm_y + int(self.h * 0.05)), hand_r)
        pygame.draw.circle(surface, (255, 255, 255),
                           (cx + self.facing * arm_len,
                            arm_y + int(self.h * 0.05)), hand_r, 2)

        # Голова
        head_center = (cx, int(base_y - self.h - HEAD_RADIUS + bob * 0.3))
        pygame.draw.circle(surface, SKIN, head_center, HEAD_RADIUS)
        pygame.draw.circle(surface, (255, 255, 255), head_center, HEAD_RADIUS, 2)

        # Повязка
        band_h = max(4, HEAD_RADIUS // 3)
        band_rect = pygame.Rect(
            head_center[0] - HEAD_RADIUS,
            head_center[1] - band_h // 2 - int(HEAD_RADIUS * 0.15),
            HEAD_RADIUS * 2, band_h
        )
        pygame.draw.rect(surface, self.dark, band_rect)
        # Хвостик повязки
        pygame.draw.polygon(surface, self.dark, [
            (head_center[0] - self.facing * HEAD_RADIUS,
             band_rect.centery),
            (head_center[0] - self.facing * int(HEAD_RADIUS * 1.6),
             band_rect.centery - int(HEAD_RADIUS * 0.3)),
            (head_center[0] - self.facing * int(HEAD_RADIUS * 1.6),
             band_rect.centery + int(HEAD_RADIUS * 0.6)),
        ])

        # Глаза
        eye_dx = int(HEAD_RADIUS * 0.35) * self.facing
        eye_off = int(HEAD_RADIUS * 0.15)
        eye_r = max(2, HEAD_RADIUS // 7)
        pygame.draw.circle(surface, (20, 20, 20),
                           (head_center[0] + eye_dx,
                            head_center[1] - eye_off), eye_r)
        pygame.draw.circle(surface, (20, 20, 20),
                           (head_center[0] + eye_dx - int(HEAD_RADIUS * 0.55),
                            head_center[1] - eye_off), eye_r)

    def draw_health_bar(self, surface, x, y, bar_w, bar_h, align_right=False):
        # Фон
        pygame.draw.rect(surface, HEALTH_BG, (x, y, bar_w, bar_h), border_radius=8)
        # Жёлтая «подложка» (показывает недавний урон)
        ghost_ratio = max(0, self.ghost_health) / 100
        ghost_w = int(bar_w * ghost_ratio)
        if ghost_w > 0:
            gx = x + bar_w - ghost_w if align_right else x
            pygame.draw.rect(surface, HEALTH_GHOST,
                             (gx, y, ghost_w, bar_h), border_radius=8)
        # Здоровье
        ratio = max(0, self.display_health) / 100
        fill_w = int(bar_w * ratio)
        if fill_w > 0:
            if ratio > 0.5:
                color = HEALTH_GREEN
            elif ratio > 0.25:
                color = HEALTH_YEL
            else:
                color = HEALTH_RED
            fx = x + bar_w - fill_w if align_right else x
            pygame.draw.rect(surface, color,
                             (fx, y, fill_w, bar_h), border_radius=8)
            # Блик
            shine = pygame.Surface((fill_w, bar_h // 3), pygame.SRCALPHA)
            shine.fill((255, 255, 255, 50))
            surface.blit(shine, (fx, y + 2))
        # Рамка
        pygame.draw.rect(surface, (200, 200, 200),
                         (x, y, bar_w, bar_h), 3, border_radius=8)


# ============================================================
#                    ОГНЕННЫЙ ШАР
# ============================================================
class Fireball:
    def __init__(self, x, y, direction, color, owner):
        self.x = x
        self.y = y
        self.dir = direction
        self.color = color
        self.owner = owner
        self.radius = FIREBALL_RADIUS
        self.alive = True
        self.trail_timer = 0.0
        self.anim_t = 0.0

    def update(self, dt):
        self.x += self.dir * FIREBALL_SPEED * dt
        self.anim_t += dt
        if self.x < -60 or self.x > WIDTH + 60:
            self.alive = False

        # Шлейф
        self.trail_timer += dt
        if self.trail_timer > 0.02:
            self.trail_timer = 0.0
            for _ in range(2):
                particles.append(Particle(
                    self.x + random.uniform(-self.radius, self.radius),
                    self.y + random.uniform(-self.radius, self.radius),
                    -self.dir * random.uniform(WIDTH * 0.02, WIDTH * 0.08),
                    random.uniform(-HEIGHT * 0.05, HEIGHT * 0.05),
                    self.color,
                    random.uniform(0.2, 0.45),
                    random.randint(2, 4),
                ))

    def rect(self):
        return pygame.Rect(
            int(self.x - self.radius), int(self.y - self.radius),
            self.radius * 2, self.radius * 2
        )

    def draw(self, surface):
        # Внешнее свечение
        glow_r = int(self.radius * 2.4)
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        for i in range(6, 0, -1):
            a = int(40 * (1 - i / 6))
            pygame.draw.circle(glow, (*self.color, a),
                               (glow_r, glow_r),
                               int(glow_r * i / 6))
        surface.blit(glow, (int(self.x - glow_r), int(self.y - glow_r)))

        # Ядро
        pygame.draw.circle(surface, (255, 230, 150),
                           (int(self.x), int(self.y)), int(self.radius * 1.3))
        pygame.draw.circle(surface, self.color,
                           (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (255, 255, 255),
                           (int(self.x), int(self.y)), max(2, self.radius // 2))


# ============================================================
#                    HUD
# ============================================================
def draw_hud(surface, p1, p2, time_left):
    margin = int(WIDTH * 0.03)
    bar_w = int(WIDTH * 0.36)
    bar_h = int(HEIGHT * 0.045)
    bar_y = int(HEIGHT * 0.04)

    p1.draw_health_bar(surface, margin, bar_y, bar_w, bar_h)
    p2.draw_health_bar(surface, WIDTH - margin - bar_w, bar_y,
                       bar_w, bar_h, align_right=True)

    # Тень под текстом имён
    name1 = font_med.render("ИГРОК 1", True, P1_COLOR)
    name2 = font_med.render("ИГРОК 2", True, P2_COLOR)
    sh1 = font_med.render("ИГРОК 1", True, (0, 0, 0))
    sh2 = font_med.render("ИГРОК 2", True, (0, 0, 0))
    surface.blit(sh1, (margin + 2, bar_y + bar_h + 12))
    surface.blit(sh2, (WIDTH - margin - name2.get_width() + 2, bar_y + bar_h + 12))
    surface.blit(name1, (margin, bar_y + bar_h + 10))
    surface.blit(name2, (WIDTH - margin - name2.get_width(), bar_y + bar_h + 10))

    # Таймер
    timer_col = GOLD if time_left > 10 else (255, 80, 80)
    t_txt = font_big.render(str(int(time_left) + 1), True, timer_col)
    t_sh = font_big.render(str(int(time_left) + 1), True, (0, 0, 0))
    tx = WIDTH // 2 - t_txt.get_width() // 2
    surface.blit(t_sh, (tx + 3, bar_y + 3))
    surface.blit(t_txt, (tx, bar_y))

    # Рекорд
    best_txt = font_small.render(f"РЕКОРД: {best}   СЧЁТ: {score}",
                                 True, GOLD)
    surface.blit(best_txt,
                 (WIDTH // 2 - best_txt.get_width() // 2, bar_y + bar_h + 18))


# ============================================================
#                  ЭКРАН ПОБЕДЫ
# ============================================================
def game_over_screen(winner):
    save_score(score)
    t = 0.0
    while True:
        dt = clock.tick(60) / 1000
        t += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_r:
                    return True
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == BTN_START:
                    pygame.quit()
                    sys.exit()
                if event.button == BTN_JUMP:
                    return True

        # Затемнение
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        screen.blit(overlay, (0, 0))

        # Пульсирующий заголовок
        pulse = 0.5 + 0.5 * math.sin(t * 3)
        glow_r = int(HEIGHT * 0.2 + pulse * HEIGHT * 0.05)
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*GOLD, 60), (glow_r, glow_r), glow_r)
        screen.blit(glow, (WIDTH // 2 - glow_r, HEIGHT // 2 - glow_r))

        text = font_big.render(f"{winner} ПОБЕДИЛ!", True, GOLD)
        sh = font_big.render(f"{winner} ПОБЕДИЛ!", True, (0, 0, 0))
        tx = WIDTH // 2 - text.get_width() // 2
        ty = HEIGHT // 2 - text.get_height() - 40
        screen.blit(sh, (tx + 4, ty + 4))
        screen.blit(text, (tx, ty))

        s = font_med.render(f"СЧЁТ: {score}", True, TEXT_COLOR)
        screen.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2 + 20))

        b = font_med.render(f"РЕКОРД: {best}", True, GOLD)
        screen.blit(b, (WIDTH // 2 - b.get_width() // 2, HEIGHT // 2 + 80))

        if int(t * 2) % 2 == 0:
            hint = font_med.render("A / R — заново    START / ESC — выход",
                                   True, (220, 220, 220))
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2,
                               HEIGHT // 2 + 170))

        pygame.display.flip()


# ============================================================
#                     ГЛАВНЫЙ ЦИКЛ
# ============================================================
def main():
    global score, best, screen_shake

    init_joysticks()

    # Наборы клавиш для каждого игрока (исправление бага!)
    P1_KEYS = {
        "left":  pygame.K_a,
        "right": pygame.K_d,
        "jump":  pygame.K_w,
        "fire":  pygame.K_f,
    }
    P2_KEYS = {
        "left":  pygame.K_LEFT,
        "right": pygame.K_RIGHT,
        "jump":  pygame.K_UP,
        "fire":  pygame.K_RCTRL,
    }

    while True:
        score = 0

        p1_joy = 0 if len(joysticks) >= 1 else None
        p2_joy = 1 if len(joysticks) >= 2 else None

        p1 = Fighter(WIDTH * 0.25, P1_COLOR, P1_DARK, facing=1,
                     joy_index=p1_joy, keymap=P1_KEYS)
        p2 = Fighter(WIDTH * 0.75, P2_COLOR, P2_DARK, facing=-1,
                     joy_index=p2_joy, keymap=P2_KEYS)

        fireballs = []
        running = True
        winner = None
        time_left = float(ROUND_TIME)

        p1_fire_prev = False
        p2_fire_prev = False

        while running:
            dt = clock.tick(60) / 1000
            dt = min(dt, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    save_score(score)
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        save_score(score)
                        pygame.quit()
                        sys.exit()
                if event.type in (pygame.JOYDEVICEADDED,
                                  pygame.JOYDEVICEREMOVED):
                    init_joysticks()

            keys = pygame.key.get_pressed()

            # --- Огонь ---
            p1_fire = keys[P1_KEYS["fire"]] or p1.get_button(BTN_FIRE)
            if p1_fire and not p1_fire_prev:
                ox, oy = p1.fire_origin()
                fireballs.append(Fireball(ox, oy, 1, FIRE_P1, p1))
            p1_fire_prev = p1_fire

            p2_fire = keys[P2_KEYS["fire"]] or p2.get_button(BTN_FIRE)
            if p2_fire and not p2_fire_prev:
                ox, oy = p2.fire_origin()
                fireballs.append(Fireball(ox, oy, -1, FIRE_P2, p2))
            p2_fire_prev = p2_fire

            # --- Движение ---
            p1.move(keys, dt)
            p2.move(keys, dt)
            p1.apply_gravity(dt)
            p2.apply_gravity(dt)
            p1.update_rect()
            p2.update_rect()
            p1.update_visual(dt)
            p2.update_visual(dt)

            for fb in fireballs:
                fb.update(dt)

            # --- Попадания ---
            for fb in fireballs:
                if not fb.alive:
                    continue
                for fighter in (p1, p2):
                    if fighter is fb.owner:
                        continue
                    if fb.rect().colliderect(fighter.rect):
                        fighter.take_damage(FIREBALL_DAMAGE)
                        score += 5
                        if score > best:
                            best = score
                        fb.alive = False
                        if fighter.health <= 0:
                            winner = "ИГРОК 1" if fighter is p2 else "ИГРОК 2"
                            running = False

            # --- Столкновения снарядов ---
            for i in range(len(fireballs)):
                for j in range(i + 1, len(fireballs)):
                    a, b = fireballs[i], fireballs[j]
                    if a.alive and b.alive and a.owner is not b.owner:
                        if a.rect().colliderect(b.rect()):
                            spawn_hit_effects(
                                (a.x + b.x) / 2, (a.y + b.y) / 2,
                                (255, 255, 200)
                            )
                            a.alive = False
                            b.alive = False

            fireballs = [fb for fb in fireballs if fb.alive]

            # --- Таймер ---
            time_left -= dt
            if time_left <= 0:
                # Побеждает тот, у кого больше здоровья
                if p1.health > p2.health:
                    winner = "ИГРОК 1"
                elif p2.health > p1.health:
                    winner = "ИГРОК 2"
                else:
                    winner = "НИЧЬЯ"
                running = False

            # --- Частицы ---
            particles[:] = [p for p in particles if p.update(dt)]
            damage_texts[:] = [d for d in damage_texts if d.update(dt)]

            # --- Тряска ---
            shake_x = shake_y = 0
            if screen_shake > 0:
                shake_x = random.randint(-int(screen_shake), int(screen_shake))
                shake_y = random.randint(-int(screen_shake), int(screen_shake))
                screen_shake *= 0.88
                if screen_shake < 0.5:
                    screen_shake = 0

            # --- Рисование ---
            screen.blit(BACKGROUND, (shake_x, shake_y))
            p1.draw(screen)
            p2.draw(screen)
            for fb in fireballs:
                fb.draw(screen)
            for p in particles:
                p.draw(screen)
            for d in damage_texts:
                d.draw(screen)
            draw_hud(screen, p1, p2, max(0, time_left))

            pygame.display.flip()

        if not game_over_screen(winner):
            break


if __name__ == "__main__":
    main()
