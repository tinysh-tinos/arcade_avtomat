import pygame
import random
import sys
import os
import json
import math


def save_score(score):
    path = os.environ.get("ARCADE_SCORE_FILE")
    if path:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"score": score}, f)
        except OSError:
            pass


pygame.init()
pygame.mixer.init()
pygame.joystick.init()

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Battle City")
clock = pygame.time.Clock()

BG_TOP = (12, 16, 28)
BG_BOTTOM = (22, 18, 40)
FIELD_BG = (18, 20, 32)
FIELD_BORDER = (60, 80, 140)

GRID_COLOR = (30, 36, 56)
BRICK_A = (170, 70, 30)
BRICK_B = (210, 110, 50)
BRICK_DARK = (110, 40, 15)
STEEL_A = (200, 210, 230)
STEEL_B = (140, 150, 180)
STEEL_DARK = (80, 90, 110)
TREE_A = (40, 160, 60)
TREE_B = (20, 100, 40)
WATER_A = (30, 90, 220)
WATER_B = (80, 140, 255)
ICE_A = (210, 230, 250)
ICE_B = (150, 180, 220)
EAGLE_GOLD = (255, 210, 60)
EAGLE_DARK = (180, 120, 20)
EAGLE_BG = (60, 40, 20)

PLAYER1_COLOR = (250, 220, 70)
PLAYER1_DARK = (180, 140, 20)
PLAYER2_COLOR = (90, 220, 120)
PLAYER2_DARK = (40, 150, 70)
ENEMY_BASIC = (220, 220, 230)
ENEMY_BASIC_DARK = (140, 140, 160)
ENEMY_FAST = (140, 200, 250)
ENEMY_FAST_DARK = (60, 120, 190)
ENEMY_POWER = (240, 160, 110)
ENEMY_POWER_DARK = (180, 90, 40)
ENEMY_ARMOR = (200, 140, 240)
ENEMY_ARMOR_DARK = (120, 70, 170)

BULLET_CORE = (255, 255, 255)
BULLET_GLOW = (255, 220, 100)
EXPLOSION_COLORS = [(255, 240, 180), (255, 180, 60), (240, 90, 30), (140, 30, 10)]
SHIELD_COLOR = (100, 220, 255)
FROZEN_COLOR = (150, 220, 255)
SPAWN_GLOW = (255, 255, 255)

TEXT_COLOR = (230, 240, 255)
TEXT_DIM = (150, 170, 200)
ACCENT = (100, 180, 255)

font_small = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.02), bold=True)
font_med = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.026), bold=True)
font_big = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.06), bold=True)
font_huge = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.09), bold=True)

GRID = 13
CELL = min((HEIGHT - int(HEIGHT * 0.22)) // GRID, (WIDTH - int(WIDTH * 0.42)) // GRID)
FIELD_W = CELL * GRID
FIELD_H = CELL * GRID
FIELD_X = (WIDTH - FIELD_W) // 2 - int(WIDTH * 0.06)
FIELD_Y = (HEIGHT - FIELD_H) // 2

TANK_SIZE = CELL - 2
BULLET_SIZE = max(5, CELL // 5)

TANK_SPEED = CELL * 2.2
BULLET_SPEED = CELL * 7.5
FAST_BULLET_SPEED = CELL * 10.5

T_EMPTY = 0
T_BRICK = 1
T_STEEL = 2
T_TREE = 3
T_WATER = 4
T_ICE = 5
T_BASE = 6
T_BASE_DEAD = 7

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIRS = [UP, DOWN, LEFT, RIGHT]

# ---------- Настройки джойстиков ----------
DEADZONE = 0.4
BTN_JUMP_LIKE = 0   # A / Cross
BTN_FIRE_LIKE = 2   # X / Square
BTN_START     = 7   # Start / Options
BTN_BACK      = 6   # Back / Select

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
    print(f"Найдено джойстиков: {len(joysticks)}")


LEVEL_MAPS = [
    [
        "             ",
        "  BB  BB  BB ",
        "  BB  BB  BB ",
        "  BB  BB  BB ",
        "  BB  BB  BB ",
        "  BB  BB  BB ",
        "             ",
        "  BB  BB  BB ",
        "  BB  BB  BB ",
        "  BB  BB  BB ",
        "  BB  BB  BB ",
        "  BB  BB  BB ",
        "      EE     ",
    ],
]


def _bg_cache():
    surf = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (WIDTH, y))
    return surf


BACKGROUND = _bg_cache()


def tile_from_char(ch):
    return {"B": T_BRICK, "S": T_STEEL, "T": T_TREE,
            "W": T_WATER, "I": T_ICE, "E": T_BASE, " ": T_EMPTY}.get(ch, T_EMPTY)


def make_field(level_idx):
    raw = LEVEL_MAPS[level_idx % len(LEVEL_MAPS)]
    field = [[T_EMPTY] * GRID for _ in range(GRID)]
    for r, row in enumerate(raw):
        for c, ch in enumerate(row):
            if r < GRID and c < GRID:
                field[r][c] = tile_from_char(ch)
    return field


def cell_rect(col, row):
    return pygame.Rect(FIELD_X + col * CELL, FIELD_Y + row * CELL, CELL, CELL)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)), int(lerp(c1[2], c2[2], t)))


def draw_glow(surface, x, y, radius, color, alpha=120):
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for i in range(6, 0, -1):
        r = int(radius * i / 6)
        a = int(alpha * (i / 6) * 0.4)
        pygame.draw.circle(s, (*color, a), (radius, radius), r)
    surface.blit(s, (x - radius, y - radius))


class Bullet:
    def __init__(self, x, y, direction, owner, strong=False):
        self.x = x
        self.y = y
        self.dir = direction
        self.owner = owner
        self.strong = strong
        self.alive = True
        self.speed = FAST_BULLET_SPEED if strong else BULLET_SPEED

    def rect(self):
        return pygame.Rect(int(self.x - BULLET_SIZE // 2),
                           int(self.y - BULLET_SIZE // 2),
                           BULLET_SIZE, BULLET_SIZE)

    def update(self, dt, field, tanks, on_hit):
        if not self.alive:
            return
        self.x += self.dir[0] * self.speed * dt
        self.y += self.dir[1] * self.speed * dt
        r = self.rect()

        if (r.right < FIELD_X or r.left > FIELD_X + FIELD_W or
                r.bottom < FIELD_Y or r.top > FIELD_Y + FIELD_H):
            self.alive = False
            on_hit(self.x, self.y, 0.6)
            return

        col = (r.centerx - FIELD_X) // CELL
        row = (r.centery - FIELD_Y) // CELL
        if 0 <= row < GRID and 0 <= col < GRID:
            t = field[row][col]
            if t == T_BRICK:
                self.alive = False
                field[row][col] = T_EMPTY
                on_hit(self.x, self.y, 0.6)
                return
            elif t == T_STEEL:
                if self.strong:
                    field[row][col] = T_EMPTY
                self.alive = False
                on_hit(self.x, self.y, 0.5)
                return
            elif t == T_BASE:
                self.alive = False
                on_hit(self.x, self.y, 2.8)
                return

        for tank in tanks:
            if tank is self.owner or not tank.alive:
                continue
            if self.rect().colliderect(tank.rect()):
                self.alive = False
                tank.hit()
                on_hit(self.x, self.y, 1.0)
                return

    def draw(self, surface):
        if not self.alive:
            return
        draw_glow(surface, self.x, self.y, BULLET_SIZE * 3, BULLET_GLOW, 100)
        pygame.draw.circle(surface, BULLET_GLOW, (int(self.x), int(self.y)), BULLET_SIZE)
        pygame.draw.circle(surface, BULLET_CORE, (int(self.x), int(self.y)), max(2, BULLET_SIZE // 2))


class Explosion:
    def __init__(self, x, y, size=1.0):
        self.x = x
        self.y = y
        self.size = size
        self.timer = 0.0
        self.duration = 0.45 * size
        self.alive = True

    def update(self, dt):
        self.timer += dt
        if self.timer >= self.duration:
            self.alive = False

    def draw(self, surface):
        if not self.alive:
            return
        t = self.timer / self.duration

        for i, color in enumerate(EXPLOSION_COLORS):
            layer_t = min(1.0, t * 1.5 + i * 0.1)
            r = int(CELL * (1.0 + layer_t * 2.2) * self.size)
            alpha = int(220 * (1 - layer_t))
            if alpha <= 0:
                continue
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, alpha), (r, r), r)
            surface.blit(s, (self.x - r, self.y - r))


class Tank:
    def __init__(self, col, row, kind="player", player_idx=0):
        self.col = col
        self.row = row
        self.x = FIELD_X + col * CELL + CELL // 2
        self.y = FIELD_Y + row * CELL + CELL // 2
        self.dir = UP
        self.kind = kind
        self.player_idx = player_idx
        self.alive = True
        self.level = 0
        self.shoot_cd = 0.0
        self.speed = TANK_SPEED
        self.hp = 1
        self.max_hp = 1
        self.score_val = 0
        self.frozen = 0.0
        self.shield = 0.0
        self.spawn_timer = 0.0
        self.blink_timer = 0.0
        self.tread_phase = 0.0

        if kind == "player":
            self.color = PLAYER1_COLOR if player_idx == 0 else PLAYER2_COLOR
            self.dark = PLAYER1_DARK if player_idx == 0 else PLAYER2_DARK
            self.max_hp = 1
        elif kind == "basic":
            self.speed = TANK_SPEED * 0.7
            self.color = ENEMY_BASIC
            self.dark = ENEMY_BASIC_DARK
            self.max_hp = 1
            self.score_val = 100
        elif kind == "fast":
            self.speed = TANK_SPEED * 1.6
            self.color = ENEMY_FAST
            self.dark = ENEMY_FAST_DARK
            self.max_hp = 1
            self.score_val = 200
        elif kind == "power":
            self.speed = TANK_SPEED * 0.85
            self.color = ENEMY_POWER
            self.dark = ENEMY_POWER_DARK
            self.max_hp = 1
            self.score_val = 300
        elif kind == "armor":
            self.speed = TANK_SPEED * 0.7
            self.color = ENEMY_ARMOR
            self.dark = ENEMY_ARMOR_DARK
            self.max_hp = 4
            self.score_val = 400

        self.hp = self.max_hp

    def rect(self):
        return pygame.Rect(int(self.x - TANK_SIZE // 2),
                           int(self.y - TANK_SIZE // 2),
                           TANK_SIZE, TANK_SIZE)

    def hit(self, damage=1):
        if self.shield > 0:
            return False
        self.hp -= damage
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def can_move(self, x, y, field, tanks, can_water=False):
        test = pygame.Rect(int(x - TANK_SIZE // 2),
                           int(y - TANK_SIZE // 2),
                           TANK_SIZE, TANK_SIZE)

        if (test.left < FIELD_X or test.right > FIELD_X + FIELD_W or
                test.top < FIELD_Y or test.bottom > FIELD_Y + FIELD_H):
            return False

        c0 = max(0, (test.left - FIELD_X) // CELL)
        c1 = min(GRID - 1, (test.right - FIELD_X - 1) // CELL)
        r0 = max(0, (test.top - FIELD_Y) // CELL)
        r1 = min(GRID - 1, (test.bottom - FIELD_Y - 1) // CELL)

        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                t = field[r][c]
                if t in (T_BRICK, T_STEEL, T_BASE):
                    return False
                if t == T_WATER and not can_water:
                    return False

        for tank in tanks:
            if not isinstance(tank, Tank):
                continue
            if tank is self or not tank.alive:
                continue
            if test.colliderect(tank.rect()):
                return False

        return True

    def try_move(self, direction, dt, field, tanks, can_water=False, on_ice=False):
        if self.frozen > 0:
            return False
        self.dir = direction
        mult = 1.5 if on_ice else 1.0
        dx = direction[0] * self.speed * dt * mult
        dy = direction[1] * self.speed * dt * mult

        moved = False
        if direction[0] != 0:
            if self.can_move(self.x + dx, self.y, field, tanks, can_water):
                self.x += dx
                moved = True
        else:
            if self.can_move(self.x, self.y + dy, field, tanks, can_water):
                self.y += dy
                moved = True

        if moved:
            self.tread_phase += dt * 8

        self.col = max(0, min(GRID - 1, int((self.x - FIELD_X) // CELL)))
        self.row = max(0, min(GRID - 1, int((self.y - FIELD_Y) // CELL)))
        return moved

    def update(self, dt):
        if self.shoot_cd > 0:
            self.shoot_cd -= dt
        if self.frozen > 0:
            self.frozen -= dt
        if self.shield > 0:
            self.shield -= dt
        if self.spawn_timer > 0:
            self.spawn_timer -= dt
        self.blink_timer += dt

    def shoot(self, bullets):
        if not self.alive or self.frozen > 0 or self.spawn_timer > 0:
            return
        if self.shoot_cd > 0:
            return

        own = sum(1 for b in bullets if b.owner is self and b.alive)
        max_out = 1
        if self.kind == "player" and self.level >= 2:
            max_out = 2
        if own >= max_out:
            return

        bx = self.x + self.dir[0] * TANK_SIZE // 2
        by = self.y + self.dir[1] * TANK_SIZE // 2
        strong = self.kind == "player" and self.level >= 3
        bullets.append(Bullet(bx, by, self.dir, self, strong=strong))
        self.shoot_cd = 0.25

    def draw(self, surface):
        if not self.alive:
            return

        r = self.rect()

        if self.spawn_timer > 0:
            pulse = 0.5 + 0.5 * math.sin(self.blink_timer * 20)
            draw_glow(surface, self.x, self.y, TANK_SIZE, SPAWN_GLOW, int(200 * pulse))
            s = pygame.Surface((TANK_SIZE, TANK_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(s, (*SPAWN_GLOW, int(180 * pulse)), s.get_rect(), border_radius=4)
            surface.blit(s, r)
            return

        body = self.color
        if self.frozen > 0:
            body = FROZEN_COLOR
        elif self.hp < self.max_hp and self.kind == "armor":
            if int(self.blink_timer * 8) % 2 == 0:
                body = self.dark

        draw_glow(surface, self.x, self.y, TANK_SIZE // 2 + 6, body, 60)

        pygame.draw.rect(surface, body, r, border_radius=max(3, CELL // 6))
        pygame.draw.rect(surface, self.dark, r, 2, border_radius=max(3, CELL // 6))

        cx, cy = r.centerx, r.centery
        bx = cx + self.dir[0] * TANK_SIZE * 0.48
        by = cy + self.dir[1] * TANK_SIZE * 0.48
        barrel_w = max(4, CELL // 4)
        pygame.draw.line(surface, self.dark, (cx, cy), (bx, by), barrel_w + 2)
        pygame.draw.line(surface, body, (cx, cy), (bx, by), barrel_w)

        turret_r = max(3, CELL // 5)
        pygame.draw.circle(surface, self.dark, (cx, cy), turret_r + 2)
        pygame.draw.circle(surface, body, (cx, cy), turret_r)

        tread_w = max(3, CELL // 5)
        tread_color = self.dark
        if self.dir in (UP, DOWN):
            treads = [
                (r.left, r.top, tread_w, r.height),
                (r.right - tread_w, r.top, tread_w, r.height),
            ]
        else:
            treads = [
                (r.left, r.top, r.width, tread_w),
                (r.left, r.bottom - tread_w, r.width, tread_w),
            ]
        for tr in treads:
            pygame.draw.rect(surface, tread_color, tr, border_radius=2)
            stripe_count = 4
            if self.dir in (UP, DOWN):
                for i in range(stripe_count):
                    sy = tr[1] + int(tr[3] * (i + 0.5) / stripe_count)
                    sy += int(math.sin(self.tread_phase + i) * 2)
                    pygame.draw.line(surface, self.color,
                                     (tr[0] + 2, sy), (tr[0] + tr[2] - 2, sy), 2)
            else:
                for i in range(stripe_count):
                    sx = tr[0] + int(tr[2] * (i + 0.5) / stripe_count)
                    sx += int(math.sin(self.tread_phase + i) * 2)
                    pygame.draw.line(surface, self.color,
                                     (sx, tr[1] + 2), (sx, tr[1] + tr[3] - 2), 2)

        if self.shield > 0:
            pulse = 0.5 + 0.5 * math.sin(self.blink_timer * 12)
            s = pygame.Surface((r.width + 14, r.height + 14), pygame.SRCALPHA)
            pygame.draw.rect(s, (*SHIELD_COLOR, int(120 + 100 * pulse)),
                             s.get_rect(), border_radius=8, width=3)
            surface.blit(s, (r.x - 7, r.y - 7))


class EnemyAI:
    def __init__(self, tank, get_tanks, base_pos):
        self.tank = tank
        self.get_tanks = get_tanks
        self.base = base_pos
        self.dir_timer = random.uniform(0.3, 1.0)
        self.shoot_timer = random.uniform(0.8, 2.0)

    def update(self, dt, field, bullets):
        t = self.tank
        if not t.alive:
            return
        self.dir_timer -= dt
        self.shoot_timer -= dt

        if self.dir_timer <= 0:
            self._choose_dir()
            self.dir_timer = random.uniform(0.4, 1.2)

        tanks = self.get_tanks()
        moved = t.try_move(t.dir, dt, field, tanks)
        if not moved:
            self._choose_dir()
            self.dir_timer = random.uniform(0.3, 0.8)

        if self.shoot_timer <= 0:
            t.shoot(bullets)
            self.shoot_timer = random.uniform(0.8, 2.0)

    def _choose_dir(self):
        t = self.tank
        r = random.random()

        if r < 0.5:
            bx = FIELD_X + self.base[0] * CELL + CELL // 2
            by = FIELD_Y + self.base[1] * CELL + CELL // 2
            target = (bx, by)
        elif r < 0.75 and t.kind in ("fast", "power"):
            target = (t.x, t.y)
        else:
            t.dir = random.choice(DIRS)
            return

        dx = target[0] - t.x
        dy = target[1] - t.y
        if abs(dx) > abs(dy):
            candidates = [RIGHT if dx > 0 else LEFT, DOWN if dy > 0 else UP]
        else:
            candidates = [DOWN if dy > 0 else UP, RIGHT if dx > 0 else LEFT]

        for d in candidates:
            if d != (-t.dir[0], -t.dir[1]):
                t.dir = d
                return
        t.dir = random.choice(DIRS)


def draw_tile_brick(surface, rect):
    pygame.draw.rect(surface, BRICK_A, rect)
    for i in range(4):
        for j in range(2):
            bx = rect.x + j * CELL // 2 + (i % 2) * CELL // 4
            by = rect.y + i * CELL // 4
            brick = pygame.Rect(bx + 1, by + 1, CELL // 2 - 2, CELL // 4 - 2)
            pygame.draw.rect(surface, BRICK_B, brick, border_radius=2)
            pygame.draw.rect(surface, BRICK_DARK, brick, 1, border_radius=2)


def draw_tile_steel(surface, rect):
    pygame.draw.rect(surface, STEEL_A, rect, border_radius=3)
    pygame.draw.rect(surface, STEEL_B, rect, 2, border_radius=3)
    pygame.draw.line(surface, (255, 255, 255),
                     (rect.x + 4, rect.y + 4),
                     (rect.right - 4, rect.y + 4), 2)
    pygame.draw.line(surface, (255, 255, 255),
                     (rect.x + 4, rect.y + 4),
                     (rect.x + 4, rect.bottom - 4), 2)
    pygame.draw.line(surface, STEEL_DARK,
                     (rect.right - 3, rect.y + 3),
                     (rect.right - 3, rect.bottom - 3), 2)
    pygame.draw.line(surface, STEEL_DARK,
                     (rect.x + 3, rect.bottom - 3),
                     (rect.right - 3, rect.bottom - 3), 2)


def draw_tile_water(surface, rect, time_ms, col):
    pygame.draw.rect(surface, WATER_A, rect)
    for i in range(3):
        y = rect.y + 4 + i * (rect.height - 8) // 3
        wave = math.sin(time_ms / 400 + col * 0.7 + i) * 3
        pygame.draw.line(surface, WATER_B,
                         (rect.x + 2, y + wave),
                         (rect.right - 2, y + wave), 2)
        highlight = math.cos(time_ms / 400 + col * 0.7 + i) * 3
        pygame.draw.line(surface, (150, 200, 255),
                         (rect.x + 6, y + wave + highlight),
                         (rect.right - 6, y + wave + highlight), 1)


def draw_tile_ice(surface, rect):
    pygame.draw.rect(surface, ICE_A, rect)
    pygame.draw.rect(surface, ICE_B, rect, 1, border_radius=2)
    pygame.draw.line(surface, (255, 255, 255),
                     (rect.x + 3, rect.y + 3),
                     (rect.centerx, rect.centery), 1)
    pygame.draw.line(surface, (255, 255, 255),
                     (rect.centerx, rect.centery),
                     (rect.right - 3, rect.bottom - 3), 1)


def draw_tile_tree(surface, rect, time_ms, col):
    pygame.draw.rect(surface, TREE_B, rect)
    random.seed(col * 7 + int(time_ms / 100))
    for i in range(8):
        for j in range(8):
            if random.random() < 0.7:
                px = rect.x + 2 + i * rect.width // 8
                py = rect.y + 2 + j * rect.height // 8
                r = max(2, CELL // 10)
                pygame.draw.circle(surface, TREE_A, (px, py), r)


def draw_tile_base(surface, rect, alive):
    cx, cy = rect.center
    size = CELL

    if alive:
        draw_glow(surface, cx, cy, CELL, EAGLE_GOLD, 80)
        bg_rect = pygame.Rect(cx - size, cy - size, size * 2, size * 2)
        pygame.draw.rect(surface, EAGLE_BG, bg_rect, border_radius=4)
        pygame.draw.rect(surface, EAGLE_DARK, bg_rect, 2, border_radius=4)

        wing = size * 0.65
        head = size * 0.45
        body_points = [
            (cx, cy - head),
            (cx + wing * 0.5, cy - head * 0.3),
            (cx + wing, cy),
            (cx + wing * 0.5, cy + head * 0.7),
            (cx, cy + head * 0.4),
            (cx - wing * 0.5, cy + head * 0.7),
            (cx - wing, cy),
            (cx - wing * 0.5, cy - head * 0.3),
        ]
        pygame.draw.polygon(surface, EAGLE_GOLD, body_points)
        pygame.draw.polygon(surface, EAGLE_DARK, body_points, 2)

        pygame.draw.circle(surface, EAGLE_BG, (cx - size * 0.2, cy - size * 0.15), max(2, CELL // 12))
        pygame.draw.circle(surface, EAGLE_BG, (cx + size * 0.2, cy - size * 0.15), max(2, CELL // 12))
        pygame.draw.polygon(surface, EAGLE_BG, [
            (cx - size * 0.15, cy + size * 0.15),
            (cx + size * 0.15, cy + size * 0.15),
            (cx, cy + size * 0.4),
        ])
    else:
        bg_rect = pygame.Rect(cx - size, cy - size, size * 2, size * 2)
        pygame.draw.rect(surface, (50, 25, 15), bg_rect, border_radius=4)
        pygame.draw.rect(surface, (30, 15, 8), bg_rect, 2, border_radius=4)
        pygame.draw.line(surface, (30, 15, 8),
                         (cx - size * 0.7, cy - size * 0.7),
                         (cx + size * 0.7, cy + size * 0.7), 5)
        pygame.draw.line(surface, (30, 15, 8),
                         (cx + size * 0.7, cy - size * 0.7),
                         (cx - size * 0.7, cy + size * 0.7), 5)


def draw_field(surface, field, time_ms):
    shadow = pygame.Surface((FIELD_W + 20, FIELD_H + 20), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 120), shadow.get_rect(), border_radius=12)
    surface.blit(shadow, (FIELD_X - 10, FIELD_Y - 10))

    pygame.draw.rect(surface, FIELD_BG, (FIELD_X, FIELD_Y, FIELD_W, FIELD_H), border_radius=8)

    for r in range(GRID):
        for c in range(GRID):
            rect = cell_rect(c, r)
            pygame.draw.rect(surface, GRID_COLOR, rect, 1)

    for r in range(GRID):
        for c in range(GRID):
            t = field[r][c]
            if t == T_EMPTY or t == T_TREE:
                continue
            rect = cell_rect(c, r)
            if t == T_BRICK:
                draw_tile_brick(surface, rect)
            elif t == T_STEEL:
                draw_tile_steel(surface, rect)
            elif t == T_WATER:
                draw_tile_water(surface, rect, time_ms, c)
            elif t == T_ICE:
                draw_tile_ice(surface, rect)
            elif t == T_BASE:
                draw_tile_base(surface, rect, True)
            elif t == T_BASE_DEAD:
                draw_tile_base(surface, rect, False)

    for r in range(GRID):
        for c in range(GRID):
            if field[r][c] == T_TREE:
                draw_tile_tree(surface, cell_rect(c, r), time_ms, c)

    pygame.draw.rect(surface, FIELD_BORDER, (FIELD_X, FIELD_Y, FIELD_W, FIELD_H),
                     3, border_radius=8)


def draw_hud(surface, score, lives_p1, lives_p2, level,
             enemies_left, enemies_total, show_p2=False):
    px = FIELD_X - int(WIDTH * 0.14)
    py = FIELD_Y

    def panel(x, y, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 130), s.get_rect(), border_radius=12)
        pygame.draw.rect(s, (*ACCENT, 180), s.get_rect(), 2, border_radius=12)
        surface.blit(s, (x, y))

    pw = int(WIDTH * 0.11)
    ph = int(HEIGHT * 0.09)

    panel(px, py, pw, ph)
    lbl = font_small.render("СЧЁТ", True, TEXT_DIM)
    surface.blit(lbl, (px + 12, py + 8))
    val = font_med.render(str(score), True, PLAYER1_COLOR)
    surface.blit(val, (px + 12, py + ph - 32))

    py += ph + 12
    panel(px, py, pw, ph)
    lbl = font_small.render("УРОВЕНЬ", True, TEXT_DIM)
    surface.blit(lbl, (px + 12, py + 8))
    val = font_med.render(str(level), True, ACCENT)
    surface.blit(val, (px + 12, py + ph - 32))

    py += ph + 12
    panel(px, py, pw, ph + 30)
    lbl = font_small.render("ЖИЗНИ P1", True, PLAYER1_COLOR)
    surface.blit(lbl, (px + 12, py + 8))
    for i in range(lives_p1):
        lx = px + 18 + i * 30
        ly = py + ph - 4
        tank_icon(surface, lx, ly, PLAYER1_COLOR, PLAYER1_DARK)

    if show_p2:
        py += ph + 42
        panel(px, py, pw, ph + 30)
        lbl = font_small.render("ЖИЗНИ P2", True, PLAYER2_COLOR)
        surface.blit(lbl, (px + 12, py + 8))
        for i in range(lives_p2):
            lx = px + 18 + i * 30
            ly = py + ph - 4
            tank_icon(surface, lx, ly, PLAYER2_COLOR, PLAYER2_DARK)

    rx = FIELD_X + FIELD_W + int(WIDTH * 0.025)
    ry = FIELD_Y
    panel(rx, ry, int(WIDTH * 0.10), int(HEIGHT * 0.55))

    lbl = font_med.render("ВРАГИ", True, TEXT_COLOR)
    surface.blit(lbl, (rx + 14, ry + 12))

    start_y = ry + 54
    cols = 4
    step = 26
    for i in range(enemies_total):
        c = i % cols
        r = i // cols
        ex = rx + 16 + c * step
        ey = start_y + r * step
        if i < enemies_left:
            pygame.draw.rect(surface, ENEMY_BASIC, (ex, ey, 20, 20), border_radius=3)
            pygame.draw.rect(surface, ENEMY_BASIC_DARK, (ex, ey, 20, 20), 2, border_radius=3)
        else:
            pygame.draw.rect(surface, (40, 45, 60), (ex, ey, 20, 20), border_radius=3)
            pygame.draw.rect(surface, (60, 70, 90), (ex, ey, 20, 20), 2, border_radius=3)


def tank_icon(surface, x, y, color, dark):
    size = 22
    r = pygame.Rect(x - size // 2, y - size // 2, size, size)
    pygame.draw.rect(surface, color, r, border_radius=3)
    pygame.draw.rect(surface, dark, r, 2, border_radius=3)
    pygame.draw.line(surface, dark, (r.centerx, r.centery),
                     (r.centerx, r.top + 2), 3)


class Game:
    def __init__(self, level_idx=0, num_players=1):
        self.level_idx = level_idx
        self.num_players = num_players
        self.field = make_field(level_idx)
        self.base_pos = (6, 12)
        self.base_alive = True

        self.player1 = Tank(4, 12, kind="player", player_idx=0)
        self.player1.dir = UP
        self.player1.spawn_timer = 1.0

        self.player2 = None
        if num_players == 2:
            self.player2 = Tank(8, 12, kind="player", player_idx=1)
            self.player2.dir = UP
            self.player2.spawn_timer = 1.0

        self.enemies = []
        self.ai_list = []
        self.bullets = []
        self.explosions = []

        self.score = 0
        self.lives_p1 = 3
        self.lives_p2 = 3
        self.total_enemies = 20
        self.spawned_enemies = 0
        self.max_on_field = 4
        self.spawn_timer = 0.5
        self.running = True

    def _all_tanks(self):
        result = []
        if self.player1 and self.player1.alive:
            result.append(self.player1)
        if self.player2 and self.player2.alive:
            result.append(self.player2)
        result.extend(e for e in self.enemies if e.alive)
        return result

    def spawn_enemy(self):
        if self.spawned_enemies >= self.total_enemies:
            return
        if sum(1 for e in self.enemies if e.alive) >= self.max_on_field:
            return

        spawn_cols = [0, 6, 12]
        random.shuffle(spawn_cols)
        for col in spawn_cols:
            x = FIELD_X + col * CELL + CELL // 2
            y = FIELD_Y + CELL // 2
            test = pygame.Rect(int(x - TANK_SIZE // 2), int(y - TANK_SIZE // 2),
                               TANK_SIZE, TANK_SIZE)
            if any(test.colliderect(t.rect()) for t in self._all_tanks()):
                continue

            idx = self.spawned_enemies
            if idx < 3:
                kind = "basic"
            else:
                roll = random.random()
                if roll < 0.45:
                    kind = "basic"
                elif roll < 0.7:
                    kind = "fast"
                elif roll < 0.9:
                    kind = "power"
                else:
                    kind = "armor"

            t = Tank(col, 0, kind=kind)
            t.dir = DOWN
            t.spawn_timer = 0.5
            self.enemies.append(t)
            self.ai_list.append(EnemyAI(t, self._all_tanks, self.base_pos))
            self.spawned_enemies += 1
            return

    def update(self, dt, inputs):
        """
        inputs: dict { "p1": {"dir": UP/DOWN/LEFT/RIGHT/None, "shoot": bool},
                       "p2": {...} }
        """
        if not self.running:
            return

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_enemy()
            self.spawn_timer = 2.0

        self._update_player(self.player1, dt, inputs["p1"])
        if self.player2:
            self._update_player(self.player2, dt, inputs["p2"])

        for ai in self.ai_list:
            if ai.tank.alive:
                ai.tank.update(dt)
                ai.update(dt, self.field, self.bullets)

        for b in self.bullets:
            b.update(dt, self.field, self._all_tanks(), self._on_hit)

        for ex in self.explosions:
            ex.update(dt)
        self.explosions = [e for e in self.explosions if e.alive]
        self.bullets = [b for b in self.bullets if b.alive]

        for e in self.enemies:
            if not e.alive and not getattr(e, "_scored", False):
                e._scored = True
                self.score += e.score_val
                self.explosions.append(Explosion(e.x, e.y, 1.3))
        self.enemies = [e for e in self.enemies if e.alive]
        self.ai_list = [a for a in self.ai_list if a.tank.alive]

        if self.field[self.base_pos[1]][self.base_pos[0]] != T_BASE:
            self.base_alive = False
            self.field[self.base_pos[1]][self.base_pos[0]] = T_BASE_DEAD
            self.explosions.append(Explosion(
                FIELD_X + self.base_pos[0] * CELL + CELL // 2,
                FIELD_Y + self.base_pos[1] * CELL + CELL // 2, 3.2))
            self.running = False

        if not self.player1.alive:
            self.lives_p1 -= 1
            if self.lives_p1 <= 0:
                self.running = False
            else:
                self.player1 = Tank(4, 12, kind="player", player_idx=0)
                self.player1.dir = UP
                self.player1.spawn_timer = 1.0

        if self.player2 and not self.player2.alive:
            self.lives_p2 -= 1
            if self.lives_p2 <= 0:
                self.player2 = None
            else:
                self.player2 = Tank(8, 12, kind="player", player_idx=1)
                self.player2.dir = UP
                self.player2.spawn_timer = 1.0

        if self.spawned_enemies >= self.total_enemies and not self.enemies:
            self.running = False

    def _update_player(self, p, dt, inp):
        p.update(dt)
        if not p.alive or p.spawn_timer > 0:
            return

        on_ice = False
        if 0 <= p.row < GRID and 0 <= p.col < GRID:
            on_ice = self.field[p.row][p.col] == T_ICE

        if inp["dir"]:
            p.try_move(inp["dir"], dt, self.field, self._all_tanks(), on_ice=on_ice)

        if inp["shoot"]:
            p.shoot(self.bullets)

    def _on_hit(self, x, y, size):
        self.explosions.append(Explosion(x, y, size))


# ============================================================
#         ВВОД: клавиатура + джойстики (раздельно)
# ============================================================
def _axis_dir(joy, axis_id):
    if joy is None or axis_id >= joy.get_numaxes():
        return None
    v = joy.get_axis(axis_id)
    if abs(v) < DEADZONE:
        return None
    return v


def _hat_dir(joy, hat_id=0):
    if joy is None or hat_id >= joy.get_numhats():
        return None
    hx, hy = joy.get_hat(hat_id)
    return (hx, hy)


def _button(joy, idx):
    if joy is None or idx >= joy.get_numbuttons():
        return False
    return joy.get_button(idx)


def read_player_input(tag, keys, joy, prev_shoot):
    """
    Возвращает (input_dict, new_prev_shoot).
    input_dict = {"dir": UP/DOWN/LEFT/RIGHT/None, "shoot": bool}
    Стрельба — по фронту нажатия (чтобы не строчило).
    """
    direction = None

    # --- Клавиатура ---
    if tag == "p1":
        if keys[pygame.K_w]:
            direction = UP
        elif keys[pygame.K_s]:
            direction = DOWN
        elif keys[pygame.K_a]:
            direction = LEFT
        elif keys[pygame.K_d]:
            direction = RIGHT
        shoot_key = keys[pygame.K_SPACE]
    else:
        if keys[pygame.K_UP]:
            direction = UP
        elif keys[pygame.K_DOWN]:
            direction = DOWN
        elif keys[pygame.K_LEFT]:
            direction = LEFT
        elif keys[pygame.K_RIGHT]:
            direction = RIGHT
        shoot_key = keys[pygame.K_RCTRL] or keys[pygame.K_RETURN]

    # --- Джойстик ---
    shoot_joy = False
    if joy is not None:
        ax = _axis_dir(joy, 0)
        ay = _axis_dir(joy, 1)
        hx, hy = _hat_dir(joy, 0) or (0, 0)

        # Приоритет — крестовина, потом стик
        if hx != 0 or hy != 0:
            if abs(hx) > abs(hy):
                direction = RIGHT if hx > 0 else LEFT
            else:
                direction = DOWN if hy > 0 else UP
        elif ax is not None or ay is not None:
            if ax is not None and (ay is None or abs(ax) >= abs(ay)):
                direction = RIGHT if ax > 0 else LEFT
            elif ay is not None:
                direction = DOWN if ay > 0 else UP

        shoot_joy = _button(joy, BTN_FIRE_LIKE) or _button(joy, BTN_JUMP_LIKE)

    shoot_now = shoot_key or shoot_joy
    shoot_pressed = shoot_now and not prev_shoot

    return {"dir": direction, "shoot": shoot_pressed}, shoot_now

def mem():
  mem_answer = random.randint(1,3)
  mem_spisok = ["67", "52", "42"]

  if mem_answer == 1:
    for i in range(67):
      print(mem_spisok[0])
  elif mem_answer == 2:
    for i in range(52):
      print(mem_spisok[1])
  elif mem_answer == 3:
    for i in range(42):
      print(mem_answer[2])

  return i


# ============================================================
#                       ЭКРАНЫ
# ============================================================
def game_over_screen(score, win, level):
    save_score(score)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    if win:
        title = font_huge.render("УРОВЕНЬ ПРОЙДЕН", True, (120, 255, 140))
    else:
        title = font_huge.render("GAME OVER", True, (255, 80, 80))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 180))

    s = font_big.render(f"Счёт: {score}", True, TEXT_COLOR)
    screen.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2 - 40))

    l = font_big.render(f"Уровень: {level}", True, ACCENT)
    screen.blit(l, (WIDTH // 2 - l.get_width() // 2, HEIGHT // 2 + 40))

    hint = font_med.render("A / R — заново    START / ESC — выход", True, TEXT_DIM)
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 130))

    pygame.display.flip()

    while True:
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
                if event.button == BTN_START or event.button == BTN_BACK:
                    pygame.quit()
                    sys.exit()
                if event.button in (BTN_JUMP_LIKE, BTN_FIRE_LIKE):
                    return True


def select_players():
    while True:
        screen.blit(BACKGROUND, (0, 0))

        title = font_huge.render("BATTLE CITY", True, PLAYER1_COLOR)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 220))

        sub = font_big.render("Выбор режима", True, TEXT_COLOR)
        screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 - 90))

        b1 = font_big.render("1 / A — один игрок", True, PLAYER1_COLOR)
        b2 = font_big.render("2 / X — два игрока", True, PLAYER2_COLOR)
        screen.blit(b1, (WIDTH // 2 - b1.get_width() // 2, HEIGHT // 2 - 10))
        screen.blit(b2, (WIDTH // 2 - b2.get_width() // 2, HEIGHT // 2 + 50))

        hint = font_med.render("START / ESC — выход", True, TEXT_DIM)
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 100))

        # Индикатор джойстиков
        jinfo = font_small.render(f"Джойстиков: {len(joysticks)}", True, TEXT_DIM)
        screen.blit(jinfo, (WIDTH // 2 - jinfo.get_width() // 2, HEIGHT - 60))

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_1:
                    return 1
                if event.key == pygame.K_2:
                    return 2
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == BTN_START or event.button == BTN_BACK:
                    pygame.quit()
                    sys.exit()
                if event.button == BTN_JUMP_LIKE:
                    return 1
                if event.button == BTN_FIRE_LIKE:
                    return 2
            if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                init_joysticks()


def main():
    init_joysticks()
    num_players = select_players()
    level = 0

    while True:
        game = Game(level_idx=level, num_players=num_players)

        # Предыдущее состояние огня для фронта нажатия
        prev_shoot = {"p1": False, "p2": False}

        mem()

        while game.running:
            dt = clock.tick(60) / 1000
            dt = min(dt, 0.05)
            time_ms = pygame.time.get_ticks()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    save_score(game.score)
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        save_score(game.score)
                        pygame.quit()
                        sys.exit()
                if event.type in (pygame.JOYDEVICEADDED,
                                  pygame.JOYDEVICEREMOVED):
                    init_joysticks()

            keys = pygame.key.get_pressed()

            # Джойстик #0 — Игрок 1, #1 — Игрок 2
            j1 = joysticks[0] if len(joysticks) >= 1 else None
            j2 = joysticks[1] if len(joysticks) >= 2 else None

            in1, prev_shoot["p1"] = read_player_input(
                "p1", keys, j1, prev_shoot["p1"])
            in2, prev_shoot["p2"] = read_player_input(
                "p2", keys, j2, prev_shoot["p2"])

            inputs = {"p1": in1, "p2": in2}
            game.update(dt, inputs)

            screen.blit(BACKGROUND, (0, 0))
            draw_field(screen, game.field, time_ms)

            for t in game._all_tanks():
                t.draw(screen)

            for b in game.bullets:
                b.draw(screen)

            for ex in game.explosions:
                ex.draw(screen)

            draw_hud(screen, game.score, game.lives_p1, game.lives_p2,
                     level + 1,
                     game.total_enemies - game.spawned_enemies + len(game.enemies),
                     game.total_enemies,
                     show_p2=(num_players == 2))

            pygame.display.flip()

        win = game.base_alive and game.spawned_enemies >= game.total_enemies
        score = game.score

        if win:
            level += 1
            if not game_over_screen(score, True, level):
                break
        else:
            if not game_over_screen(score, False, level + 1):
                break
            break


if __name__ == "__main__":
  main()
