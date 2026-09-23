import sys
import subprocess

def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

install_and_import('pygame')

import pygame
import random
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
pygame.joystick.init()

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Pac-Man")
clock = pygame.time.Clock()

BG_COLOR = (8, 8, 20)
BG_GLOW_1 = (20, 15, 50)
BG_GLOW_2 = (10, 20, 45)
WALL_COLOR = (30, 60, 200)
WALL_GLOW = (60, 120, 255)
WALL_EDGE = (120, 180, 255)
PELLET_COLOR = (255, 220, 180)
POWER_COLOR = (255, 180, 60)
PAC_COLOR = (255, 220, 40)
PAC_GLOW = (255, 200, 100)
GHOST_RED = (255, 60, 60)
GHOST_PINK = (255, 150, 200)
GHOST_CYAN = (100, 220, 240)
GHOST_ORANGE = (255, 160, 60)
GHOST_FRIGHT = (60, 80, 255)
GHOST_FRIGHT_FLASH = (230, 230, 255)
EYE_WHITE = (255, 255, 255)
EYE_BLUE = (40, 80, 220)
TEXT_COLOR = (230, 240, 255)
TEXT_DIM = (150, 170, 200)
ACCENT = (100, 180, 255)
GOLD = (255, 215, 80)

MAZE = [
    "############################",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#o####.#####.##.#####.####o#",
    "#.####.#####.##.#####.####.#",
    "#..........................#",
    "#.####.##.########.##.####.#",
    "#.####.##.########.##.####.#",
    "#......##....##....##......#",
    "######.#####.##.#####.######",
    "     #.#####.##.#####.#     ",
    "     #.##          ##.#     ",
    "     #.## ###--### ##.#     ",
    "######.## #      # ##.######",
    "      .   #      #   .      ",
    "######.## #      # ##.######",
    "     #.## ######## ##.#     ",
    "     #.##          ##.#     ",
    "     #.## ######## ##.#     ",
    "######.## ######## ##.######",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#.####.#####.##.#####.####.#",
    "#o..##.......##.......##..o#",
    "###.##.##.########.##.##.###",
    "###.##.##.########.##.##.###",
    "#......##....##....##......#",
    "#.##########.##.##########.#",
    "#.##########.##.##########.#",
    "#..........................#",
    "############################",
]

ROWS = len(MAZE)
COLS = len(MAZE[0])
CELL = min((WIDTH - 100) // COLS, (HEIGHT - 160) // ROWS)
BOARD_W = COLS * CELL
BOARD_H = ROWS * CELL
BOARD_X = (WIDTH - BOARD_W) // 2
BOARD_Y = (HEIGHT - BOARD_H) // 2 + 30

PAC_RADIUS = CELL // 2 - 3
PAC_SPEED = 3.2 * CELL
GHOST_SPEED = 2.6 * CELL
GHOST_FRIGHT_SPEED = 1.6 * CELL

font_big = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.08), bold=True)
font_med = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.04), bold=True)
font_small = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.028))

score = 0
best = 0

# ---------- Настройки джойстиков ----------
DEADZONE = 0.4
BTN_A = 0        # A / Cross
BTN_X = 2        # X / Square
BTN_START = 7    # Start / Options
BTN_BACK = 6     # Back / Select

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


# ---------- Фон с мягким свечением ----------
def make_background():
    surf = pygame.Surface((WIDTH, HEIGHT))
    surf.fill(BG_COLOR)
    # Мягкие радиальные градиенты
    for cx, cy, color in [
        (WIDTH * 0.25, HEIGHT * 0.3, BG_GLOW_1),
        (WIDTH * 0.75, HEIGHT * 0.7, BG_GLOW_2),
    ]:
        for r in range(int(WIDTH * 0.4), 0, -int(WIDTH * 0.02)):
            t = r / (WIDTH * 0.4)
            a = int(40 * (1 - t))
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, a), (r, r), r)
            surf.blit(s, (cx - r, cy - r))
    return surf


BACKGROUND = make_background()


def cell_center(col, row):
    return (BOARD_X + col * CELL + CELL // 2,
            BOARD_Y + row * CELL + CELL // 2)


def is_wall(col, row):
    if row < 0 or row >= ROWS or col < 0 or col >= COLS:
        return True
    return MAZE[row][col] == "#"


def make_grid():
    pellets = set()
    powers = set()
    for r, row in enumerate(MAZE):
        for c, ch in enumerate(row):
            if ch == ".":
                pellets.add((c, r))
            elif ch == "o":
                powers.add((c, r))
    return pellets, powers


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
        self.vx *= 0.94
        self.vy *= 0.94
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        t = max(0, self.life / self.max_life)
        r = max(1, int(self.size * t))
        alpha = int(255 * t)
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
        surf.blit(s, (int(self.x - r), int(self.y - r)))


particles = []


def spawn_particles(x, y, color, count=8):
    for _ in range(count):
        a = random.uniform(0, math.tau)
        spd = random.uniform(CELL * 1.5, CELL * 4.5)
        particles.append(Particle(
            x, y,
            math.cos(a) * spd, math.sin(a) * spd,
            color,
            random.uniform(0.2, 0.5),
            random.randint(2, 4),
        ))


def draw_glow(surface, x, y, radius, color, alpha=120):
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for i in range(6, 0, -1):
        r = int(radius * i / 6)
        a = int(alpha * (i / 6) * 0.4)
        pygame.draw.circle(s, (*color, a), (radius, radius), r)
    surface.blit(s, (x - radius, y - radius))


class Actor:
    def __init__(self, col, row, speed):
        self.col = col
        self.row = row
        self.x = BOARD_X + col * CELL + CELL // 2
        self.y = BOARD_Y + row * CELL + CELL // 2
        self.dir = (0, 0)
        self.speed = speed

    def can_move(self, direction):
        return not is_wall(self.col + direction[0], self.row + direction[1])

    def step(self, dt):
        if self.dir == (0, 0):
            return

        dist = self.speed * dt

        if self.dir[0] > 0:
            target_x = BOARD_X + (self.col + 1) * CELL + CELL // 2
            target_y = BOARD_Y + self.row * CELL + CELL // 2
        elif self.dir[0] < 0:
            target_x = BOARD_X + (self.col - 1) * CELL + CELL // 2
            target_y = BOARD_Y + self.row * CELL + CELL // 2
        elif self.dir[1] > 0:
            target_x = BOARD_X + self.col * CELL + CELL // 2
            target_y = BOARD_Y + (self.row + 1) * CELL + CELL // 2
        else:
            target_x = BOARD_X + self.col * CELL + CELL // 2
            target_y = BOARD_Y + (self.row - 1) * CELL + CELL // 2

        dx = target_x - self.x
        dy = target_y - self.y
        length = math.hypot(dx, dy)

        if length <= dist:
            self.x = target_x
            self.y = target_y
            self.col += self.dir[0]
            self.row += self.dir[1]
            if not self.can_move(self.dir):
                self.dir = (0, 0)
        else:
            self.x += dx / length * dist
            self.y += dy / length * dist

    def at_center(self):
        cx, cy = cell_center(self.col, self.row)
        return abs(self.x - cx) < 1 and abs(self.y - cy) < 1


class Pac(Actor):
    def __init__(self):
        super().__init__(14, 23, PAC_SPEED)
        self.next_dir = (0, 0)
        self.mouth = 0
        self.mouth_dir = 1

    def update(self, dt):
        if self.next_dir == (-self.dir[0], -self.dir[1]) and self.dir != (0, 0):
            self.dir = self.next_dir
            self.next_dir = (0, 0)

        if self.at_center():
            if self.next_dir != (0, 0) and self.can_move(self.next_dir):
                self.dir = self.next_dir
                self.next_dir = (0, 0)

        self.step(dt)

        if self.dir != (0, 0):
            self.mouth += self.mouth_dir * dt * 8
            if self.mouth > 1:
                self.mouth = 1
                self.mouth_dir = -1
            elif self.mouth < 0:
                self.mouth = 0
                self.mouth_dir = 1

    def draw(self, surface, time_ms):
        if self.dir == (1, 0):
            angle = 0
        elif self.dir == (-1, 0):
            angle = 180
        elif self.dir == (0, -1):
            angle = 90
        elif self.dir == (0, 1):
            angle = 270
        else:
            angle = 0

        # Свечение под Pac-Man
        pulse = 0.7 + 0.3 * math.sin(time_ms / 150)
        draw_glow(surface, self.x, self.y, int(PAC_RADIUS * 1.6),
                  PAC_GLOW, int(80 * pulse))

        # Тень
        shadow = pygame.Surface((PAC_RADIUS * 2, PAC_RADIUS), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 120), shadow.get_rect())
        surface.blit(shadow, (self.x - PAC_RADIUS, self.y + PAC_RADIUS - 4))

        open_angle = self.mouth * 35

        points = [(self.x, self.y)]
        steps = 24
        start = math.radians(open_angle)
        end = math.radians(360 - open_angle)
        for i in range(steps + 1):
            a = start + (end - start) * i / steps
            points.append((
                self.x + math.cos(a) * PAC_RADIUS,
                self.y + math.sin(a) * PAC_RADIUS
            ))

        rad = math.radians(angle)
        rotated = []
        for px, py in points:
            dx = px - self.x
            dy = py - self.y
            rx = dx * math.cos(rad) - dy * math.sin(rad)
            ry = dx * math.sin(rad) + dy * math.cos(rad)
            rotated.append((self.x + rx, self.y + ry))

        pygame.draw.polygon(surface, PAC_COLOR, rotated)
        # Блик
        pygame.draw.circle(surface, (255, 255, 200),
                           (int(self.x - PAC_RADIUS * 0.3),
                            int(self.y - PAC_RADIUS * 0.4)),
                           max(2, PAC_RADIUS // 5))


class Ghost(Actor):
    def __init__(self, col, row, color):
        super().__init__(col, row, GHOST_SPEED)
        self.color = color
        self.frightened = False
        self.eaten = False
        self.start_dir_timer = random.uniform(0, 0.3)
        self.wobble = random.uniform(0, 10)

    def update(self, dt, pac, fright_timer):
        if self.eaten:
            self.speed = GHOST_SPEED * 1.6
            target = (14, 14)
        elif self.frightened:
            self.speed = GHOST_FRIGHT_SPEED
            target = None
        else:
            self.speed = GHOST_SPEED
            target = (pac.col, pac.row)

        if self.at_center():
            options = []
            for d in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                if not is_wall(self.col + d[0], self.row + d[1]):
                    options.append(d)

            opposite = (-self.dir[0], -self.dir[1])
            if opposite in options and len(options) > 1:
                options.remove(opposite)

            if self.start_dir_timer > 0:
                self.start_dir_timer -= dt
                if self.dir == (0, 0) and options:
                    self.dir = random.choice(options)
            elif options:
                if target is None:
                    self.dir = random.choice(options)
                else:
                    best = options[0]
                    best_dist = 10 ** 9
                    for d in options:
                        nc = self.col + d[0]
                        nr = self.row + d[1]
                        dist = (nc - target[0]) ** 2 + (nr - target[1]) ** 2
                        if dist < best_dist:
                            best_dist = dist
                            best = d
                    self.dir = best

        self.step(dt)
        self.wobble += dt * 6

    def draw(self, surface, time_ms):
        r = PAC_RADIUS
        body_color = self.color

        if self.eaten:
            body_color = None
        elif self.frightened:
            body_color = GHOST_FRIGHT_FLASH if time_ms % 400 < 200 else GHOST_FRIGHT

        # Свечение
        if body_color:
            draw_glow(surface, self.x, self.y, int(r * 1.4), body_color, 60)

        # Тень
        shadow = pygame.Surface((r * 2, r), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 120), shadow.get_rect())
        surface.blit(shadow, (self.x - r, self.y + r - 4))

        # Покачивание
        wob = math.sin(self.wobble) * 1.5

        if body_color:
            pygame.draw.circle(surface, body_color,
                               (int(self.x), int(self.y - 2 + wob)), r)
            rect = pygame.Rect(int(self.x - r), int(self.y - 2 + wob),
                               r * 2, r + 4)
            pygame.draw.rect(surface, body_color, rect)

            wave_y = self.y + r + wob
            wave_w = (r * 2) / 4
            points = [(int(self.x - r), int(wave_y))]
            for i in range(4):
                x1 = int(self.x - r + i * wave_w + wave_w / 2)
                x2 = int(self.x - r + (i + 1) * wave_w)
                points.append((x1, int(wave_y + 5)))
                points.append((x2, int(wave_y)))
            points.append((int(self.x + r), int(wave_y)))
            points.append((int(self.x + r), int(self.y - 2 + wob)))
            points.append((int(self.x - r), int(self.y - 2 + wob)))
            pygame.draw.polygon(surface, body_color, points)

        # Глаза
        eye_r = max(3, r // 3)
        for ex in (-r // 3, r // 3):
            pygame.draw.circle(surface, EYE_WHITE,
                               (int(self.x + ex), int(self.y - 4 + wob)), eye_r)
            pygame.draw.circle(surface, EYE_BLUE,
                               (int(self.x + ex + self.dir[0] * 2),
                                int(self.y - 4 + self.dir[1] * 2 + wob)),
                               max(2, eye_r // 2))


def draw_maze(surface, time_ms):
    pulse = 0.6 + 0.4 * math.sin(time_ms / 700)
    for r, row in enumerate(MAZE):
        for c, ch in enumerate(row):
            if ch == "#":
                x = BOARD_X + c * CELL
                y = BOARD_Y + r * CELL
                rect = pygame.Rect(x + 2, y + 2, CELL - 4, CELL - 4)
                # Свечение стены
                draw_glow(surface, rect.centerx, rect.centery,
                          int(CELL * 0.7), WALL_GLOW, int(30 * pulse))
                pygame.draw.rect(surface, WALL_COLOR, rect, border_radius=5)
                # Внутренняя обводка
                pygame.draw.rect(surface, WALL_EDGE, rect, 1, border_radius=5)


def draw_pellets(surface, pellets, powers, time_ms):
    pulse = 0.6 + 0.4 * math.sin(time_ms / 200)
    for c, r in pellets:
        cx, cy = cell_center(c, r)
        # Лёгкое свечение
        draw_glow(surface, cx, cy, 10, PELLET_COLOR, 60)
        pygame.draw.circle(surface, PELLET_COLOR, (int(cx), int(cy)), 4)
    for c, r in powers:
        cx, cy = cell_center(c, r)
        rr = int(7 + 3 * pulse)
        draw_glow(surface, cx, cy, rr * 3, POWER_COLOR, 120)
        pygame.draw.circle(surface, POWER_COLOR, (int(cx), int(cy)), rr)
        pygame.draw.circle(surface, (255, 255, 200),
                           (int(cx), int(cy)), max(2, rr // 2))


def draw_hud(surface, lives, fright_timer):
    s = font_med.render(f"СЧЁТ: {score}", True, TEXT_COLOR)
    surface.blit(s, (BOARD_X, BOARD_Y - 50))

    b = font_med.render(f"РЕКОРД: {best}", True, GOLD)
    surface.blit(b, (BOARD_X + BOARD_W - b.get_width(), BOARD_Y - 50))

    for i in range(lives):
        cx = BOARD_X + 20 + i * 40
        cy = BOARD_Y + BOARD_H + 30
        points = [(cx, cy)]
        for j in range(20):
            a = math.radians(35 + (360 - 70) * j / 19)
            points.append((cx + math.cos(a) * 12, cy + math.sin(a) * 12))
        pygame.draw.polygon(surface, PAC_COLOR, points)

    if fright_timer > 0:
        bar_w = 200
        ratio = max(0, fright_timer / 7.0)
        pygame.draw.rect(surface, (60, 60, 90),
                         (BOARD_X + BOARD_W // 2 - bar_w // 2, BOARD_Y - 40,
                          bar_w, 14), border_radius=7)
        pygame.draw.rect(surface, GHOST_FRIGHT,
                         (BOARD_X + BOARD_W // 2 - bar_w // 2, BOARD_Y - 40,
                          int(bar_w * ratio), 14), border_radius=7)


# ============================================================
#           ВВОД: клавиатура + джойстик
# ============================================================
def read_direction(keys, joy):
    """Возвращает направление от клавиатуры/джойстика или None."""
    # --- Клавиатура ---
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        return (-1, 0)
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        return (1, 0)
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        return (0, -1)
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        return (0, 1)

    # --- Джойстик ---
    if joy is None:
        return None

    # Крестовина
    if joy.get_numhats() > 0:
        hx, hy = joy.get_hat(0)
        if hx != 0 or hy != 0:
            if abs(hx) >= abs(hy):
                return (1, 0) if hx > 0 else (-1, 0)
            else:
                return (0, 1) if hy > 0 else (0, -1)

    # Левый стик
    if joy.get_numaxes() >= 2:
        ax = joy.get_axis(0)
        ay = joy.get_axis(1)
        if abs(ax) > DEADZONE or abs(ay) > DEADZONE:
            if abs(ax) >= abs(ay):
                return (1, 0) if ax > 0 else (-1, 0)
            else:
                return (0, 1) if ay > 0 else (0, -1)
    return None


def button_pressed(joy, idx):
    if joy is None or idx >= joy.get_numbuttons():
        return False
    return joy.get_button(idx)


# ============================================================
#                       ЭКРАНЫ
# ============================================================
def pause_screen():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    title = font_big.render("ПАУЗА", True, GOLD)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 100))

    hint1 = font_med.render("START / P — продолжить", True, TEXT_COLOR)
    screen.blit(hint1, (WIDTH // 2 - hint1.get_width() // 2, HEIGHT // 2))

    hint2 = font_small.render("ESC — выход", True, TEXT_DIM)
    screen.blit(hint2, (WIDTH // 2 - hint2.get_width() // 2, HEIGHT // 2 + 70))

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
                if event.key in (pygame.K_p, pygame.K_RETURN, pygame.K_SPACE):
                    return
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == BTN_START or event.button == BTN_BACK:
                    return
                if event.button in (BTN_A, BTN_X):
                    return
        clock.tick(30)


def game_over_screen(win):
    save_score(score)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    if win:
        title = font_big.render("ПОБЕДА!", True, (120, 255, 140))
    else:
        title = font_big.render("ИГРА ОКОНЧЕНА", True, (255, 100, 100))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 150))

    s = font_med.render(f"Счёт: {score}", True, TEXT_COLOR)
    screen.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2 - 40))

    b = font_med.render(f"Рекорд: {best}", True, GOLD)
    screen.blit(b, (WIDTH // 2 - b.get_width() // 2, HEIGHT // 2 + 10))

    hint = font_small.render("A / R — заново    START / ESC — выход",
                             True, TEXT_DIM)
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 80))

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
                if event.button == BTN_A:
                    return True


def main():
    global score, best

    init_joysticks()
    joy = joysticks[0] if joysticks else None

    while True:
        pellets, powers = make_grid()
        pac = Pac()
        ghosts = [
            Ghost(14, 14, GHOST_RED),
            Ghost(13, 14, GHOST_PINK),
            Ghost(15, 14, GHOST_CYAN),
            Ghost(16, 14, GHOST_ORANGE),
        ]
        score = 0
        lives = 3
        fright_timer = 0
        respawn_timer = 0
        running = True
        win = False

        particles.clear()

        while running:
            dt = clock.tick(60) / 1000
            dt = min(dt, 0.05)
            time_ms = pygame.time.get_ticks()

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
                    if event.key in (pygame.K_p, pygame.K_RETURN):
                        pause_screen()
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == BTN_START or event.button == BTN_BACK:
                        pause_screen()
                if event.type in (pygame.JOYDEVICEADDED,
                                  pygame.JOYDEVICEREMOVED):
                    init_joysticks()
                    joy = joysticks[0] if joysticks else None

            if respawn_timer > 0:
                respawn_timer -= dt
                screen.blit(BACKGROUND, (0, 0))
                draw_maze(screen, time_ms)
                draw_pellets(screen, pellets, powers, time_ms)
                draw_hud(screen, lives, fright_timer)
                msg = font_med.render("Готов?", True, TEXT_COLOR)
                screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2))
                pygame.display.flip()
                continue

            # --- Ввод ---
            keys = pygame.key.get_pressed()
            new_dir = read_direction(keys, joy)
            if new_dir is not None:
                pac.next_dir = new_dir

            if fright_timer > 0:
                fright_timer -= dt
                if fright_timer <= 0:
                    for g in ghosts:
                        g.frightened = False

            pac.update(dt)

            pc = (pac.col, pac.row)
            if pc in pellets:
                pellets.discard(pc)
                score += 10
                if score > best:
                    best = score
                cx, cy = cell_center(*pc)
                spawn_particles(cx, cy, PELLET_COLOR, 6)
            elif pc in powers:
                powers.discard(pc)
                score += 50
                if score > best:
                    best = score
                cx, cy = cell_center(*pc)
                spawn_particles(cx, cy, POWER_COLOR, 16)
                fright_timer = 7.0
                for g in ghosts:
                    if not g.eaten:
                        g.frightened = True

            for g in ghosts:
                g.update(dt, pac, fright_timer)

                if g.eaten:
                    gx, gy = cell_center(14, 14)
                    if abs(g.x - gx) < CELL / 2 and abs(g.y - gy) < CELL / 2:
                        g.eaten = False
                        g.frightened = False
                        g.col, g.row = 14, 14
                        g.dir = (0, 0)
                        g.start_dir_timer = 0.2
                    continue

                dist = math.hypot(g.x - pac.x, g.y - pac.y)
                if dist < CELL * 0.6:
                    if g.frightened:
                        g.eaten = True
                        g.frightened = False
                        score += 200
                        if score > best:
                            best = score
                        spawn_particles(g.x, g.y, (150, 220, 255), 14)
                    else:
                        lives -= 1
                        spawn_particles(pac.x, pac.y, PAC_COLOR, 20)
                        if lives <= 0:
                            running = False
                        else:
                            pac = Pac()
                            ghosts = [
                                Ghost(14, 14, GHOST_RED),
                                Ghost(13, 14, GHOST_PINK),
                                Ghost(15, 14, GHOST_CYAN),
                                Ghost(16, 14, GHOST_ORANGE),
                            ]
                            fright_timer = 0
                            respawn_timer = 1.2

            if not pellets and not powers:
                win = True
                running = False

            # --- Отрисовка ---
            screen.blit(BACKGROUND, (0, 0))
            draw_maze(screen, time_ms)
            draw_pellets(screen, pellets, powers, time_ms)

            for p in particles:
                p.draw(screen)

            for g in ghosts:
                g.draw(screen, time_ms)

            pac.draw(screen, time_ms)
            draw_hud(screen, lives, fright_timer)

            particles[:] = [p for p in particles if p.update(dt)]

            pygame.display.flip()

        if not game_over_screen(win):
            break


if __name__ == "__main__":
    main()
