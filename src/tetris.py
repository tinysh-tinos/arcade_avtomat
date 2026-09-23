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
pygame.display.set_caption("Tetris")
clock = pygame.time.Clock()

BG_TOP = (18, 20, 32)
BG_BOTTOM = (10, 12, 22)
GRID_COLOR = (40, 44, 60)
PANEL_COLOR = (24, 28, 44)
PANEL_BORDER = (80, 90, 130)
TEXT_COLOR = (230, 240, 255)
TEXT_DIM = (160, 180, 200)
ACCENT = (120, 200, 255)
GOLD = (255, 220, 60)

COLORS = {
    "I": (60, 200, 240),
    "O": (240, 200, 60),
    "T": (170, 90, 220),
    "S": (80, 220, 120),
    "Z": (240, 80, 90),
    "J": (70, 120, 240),
    "L": (240, 150, 60),
}

SHAPES = {
    "I": [[1, 1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "T": [[0, 1, 0], [1, 1, 1]],
    "S": [[0, 1, 1], [1, 1, 0]],
    "Z": [[1, 1, 0], [0, 1, 1]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "L": [[0, 0, 1], [1, 1, 1]],
}

COLS, ROWS = 10, 20
CELL = min(int((WIDTH - 500) / COLS), int((HEIGHT - 100) / ROWS))
BOARD_W = COLS * CELL
BOARD_H = ROWS * CELL
BOARD_X = (WIDTH - BOARD_W) // 2 - 150
BOARD_Y = (HEIGHT - BOARD_H) // 2

font_big = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.08), bold=True)
font_med = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.04), bold=True)
font_small = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.028))
font_tiny = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.022))

score = 0
best = 0

# ---------- Настройки джойстиков ----------
DEADZONE = 0.4
BTN_A = 0        # A / Cross   — rotate
BTN_B = 1        # B / Circle  — hard drop
BTN_X = 2        # X / Square  — hold
BTN_Y = 3        # Y / Triangle — rotate (альтернатива)
BTN_START = 7    # Start
BTN_BACK = 6     # Back

# DAS / ARR
DAS_DELAY = 0.17   # задержка до автоповтора
ARR_INTERVAL = 0.05  # интервал автоповтора

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


def make_background():
    bg = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        pygame.draw.line(bg, (r, g, b), (0, y), (WIDTH, y))
    # Звёзды
    random.seed(42)
    for _ in range(120):
        sx = random.randint(0, WIDTH)
        sy = random.randint(0, HEIGHT)
        b = random.randint(80, 200)
        pygame.draw.circle(bg, (b, b, b), (sx, sy), 1)
    random.seed()
    return bg


BACKGROUND = make_background()


class Piece:
    def __init__(self, kind):
        self.kind = kind
        self.shape = [row[:] for row in SHAPES[kind]]
        self.x = COLS // 2 - len(self.shape[0]) // 2
        self.y = 0

    def cells(self, shape=None, ox=None, oy=None):
        s = shape if shape is not None else self.shape
        x0 = ox if ox is not None else self.x
        y0 = oy if oy is not None else self.y
        result = []
        for r, row in enumerate(s):
            for c, val in enumerate(row):
                if val:
                    result.append((x0 + c, y0 + r))
        return result

    def rotated(self):
        s = self.shape
        return [list(row) for row in zip(*s[::-1])]


def new_board():
    return [[None for _ in range(COLS)] for _ in range(ROWS)]


def valid(board, cells):
    for x, y in cells:
        if x < 0 or x >= COLS or y >= ROWS:
            return False
        if y >= 0 and board[y][x] is not None:
            return False
    return True


def lock_piece(board, piece):
    for x, y in piece.cells():
        if 0 <= y < ROWS and 0 <= x < COLS:
            board[y][x] = piece.kind


def clear_lines(board):
    cleared = 0
    cleared_rows = []
    new_rows = []
    for r, row in enumerate(board):
        if all(cell is not None for cell in row):
            cleared += 1
            cleared_rows.append(r)
        else:
            new_rows.append(row)
    for _ in range(cleared):
        new_rows.insert(0, [None for _ in range(COLS)])
    return new_rows, cleared, cleared_rows


# ---------- Частицы для эффектов ----------
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
        self.vy += 400 * dt
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


def spawn_line_particles(row, kind_color):
    for c in range(COLS):
        for _ in range(3):
            x = BOARD_X + c * CELL + CELL // 2
            y = BOARD_Y + row * CELL + CELL // 2
            a = random.uniform(0, math.tau)
            spd = random.uniform(100, 400)
            particles.append(Particle(
                x, y,
                math.cos(a) * spd, math.sin(a) * spd - 100,
                kind_color,
                random.uniform(0.4, 0.8),
                random.randint(2, 5),
            ))


# ---------- Всплывающие очки ----------
class FloatText:
    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 1.0
        self.max_life = 1.0

    def update(self, dt):
        self.y -= 60 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        t = max(0, self.life / self.max_life)
        alpha = int(255 * t)
        img = font_med.render(self.text, True, self.color)
        img.set_alpha(alpha)
        surf.blit(img, (self.x - img.get_width() // 2, self.y))


floats = []


def draw_cell(surface, x, y, color, size, radius=6):
    rect = pygame.Rect(x, y, size, size)
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    lighter = tuple(min(255, c + 60) for c in color)
    darker = tuple(max(0, c - 60) for c in color)
    pygame.draw.rect(surface, lighter,
                     (rect.x + 3, rect.y + 3, size - 6, 6), border_radius=3)
    pygame.draw.rect(surface, darker,
                     (rect.x + 3, rect.bottom - 9, size - 6, 6), border_radius=3)


def draw_board(surface, board, piece, ghost_y, time_ms):
    panel_rect = pygame.Rect(BOARD_X - 12, BOARD_Y - 12,
                             BOARD_W + 24, BOARD_H + 24)
    pygame.draw.rect(surface, PANEL_COLOR, panel_rect, border_radius=16)
    pygame.draw.rect(surface, PANEL_BORDER, panel_rect, 3, border_radius=16)

    pygame.draw.rect(surface, (12, 14, 24),
                     (BOARD_X, BOARD_Y, BOARD_W, BOARD_H), border_radius=8)

    for x in range(COLS + 1):
        pygame.draw.line(surface, GRID_COLOR,
                         (BOARD_X + x * CELL, BOARD_Y),
                         (BOARD_X + x * CELL, BOARD_Y + BOARD_H))
    for y in range(ROWS + 1):
        pygame.draw.line(surface, GRID_COLOR,
                         (BOARD_X, BOARD_Y + y * CELL),
                         (BOARD_X + BOARD_W, BOARD_Y + y * CELL))

    for y, row in enumerate(board):
        for x, kind in enumerate(row):
            if kind:
                draw_cell(surface,
                          BOARD_X + x * CELL + 2,
                          BOARD_Y + y * CELL + 2,
                          COLORS[kind], CELL - 4)

    if piece and ghost_y is not None:
        ghost_color = COLORS[piece.kind]
        # Пульсирующий призрак
        pulse = int(2 * math.sin(time_ms / 150))
        for gx, gy in piece.cells(ox=piece.x, oy=ghost_y):
            if 0 <= gy < ROWS:
                rect = pygame.Rect(
                    BOARD_X + gx * CELL + 4 + pulse,
                    BOARD_Y + gy * CELL + 4 + pulse,
                    CELL - 8 - pulse * 2, CELL - 8 - pulse * 2
                )
                pygame.draw.rect(surface, ghost_color, rect, 3, border_radius=6)

    if piece:
        for px, py in piece.cells():
            if 0 <= py < ROWS:
                draw_cell(surface,
                          BOARD_X + px * CELL + 2,
                          BOARD_Y + py * CELL + 2,
                          COLORS[piece.kind], CELL - 4)


def draw_mini(surface, piece, x, y, cell_size):
    if piece is None:
        return
    shape = SHAPES[piece.kind]
    w = len(shape[0]) * cell_size
    h = len(shape) * cell_size
    ox = x - w // 2
    oy = y - h // 2
    for r, row in enumerate(shape):
        for c, val in enumerate(row):
            if val:
                draw_cell(surface,
                          ox + c * cell_size + 2,
                          oy + r * cell_size + 2,
                          COLORS[piece.kind], cell_size - 4, radius=5)


def draw_panel(surface, level, lines, next_piece, hold_piece, can_hold):
    panel_x = BOARD_X + BOARD_W + 60
    panel_y = BOARD_Y
    panel_w = 260
    panel_h = BOARD_H

    pygame.draw.rect(surface, PANEL_COLOR,
                     (panel_x, panel_y, panel_w, panel_h), border_radius=16)
    pygame.draw.rect(surface, PANEL_BORDER,
                     (panel_x, panel_y, panel_w, panel_h), 3, border_radius=16)

    y = panel_y + 30
    label = font_small.render("СЧЁТ", True, TEXT_DIM)
    surface.blit(label, (panel_x + 30, y))
    y += 30
    val = font_med.render(str(score), True, TEXT_COLOR)
    surface.blit(val, (panel_x + 30, y))

    y += 55
    label = font_small.render("РЕКОРД", True, TEXT_DIM)
    surface.blit(label, (panel_x + 30, y))
    y += 30
    val = font_med.render(str(best), True, GOLD)
    surface.blit(val, (panel_x + 30, y))

    y += 55
    label = font_small.render("УРОВЕНЬ", True, TEXT_DIM)
    surface.blit(label, (panel_x + 30, y))
    y += 30
    val = font_med.render(str(level), True, ACCENT)
    surface.blit(val, (panel_x + 30, y))

    y += 55
    label = font_small.render("ЛИНИИ", True, TEXT_DIM)
    surface.blit(label, (panel_x + 30, y))
    y += 30
    val = font_med.render(str(lines), True, TEXT_COLOR)
    surface.blit(val, (panel_x + 30, y))

    # HOLD
    y += 60
    label = font_small.render("HOLD (X)", True,
                              ACCENT if can_hold else (100, 100, 120))
    surface.blit(label, (panel_x + 30, y))

    hold_box_y = y + 30
    pygame.draw.rect(surface, (12, 14, 24),
                     (panel_x + 30, hold_box_y, panel_w - 60, 110),
                     border_radius=10)
    pygame.draw.rect(surface, PANEL_BORDER,
                     (panel_x + 30, hold_box_y, panel_w - 60, 110),
                     2, border_radius=10)
    if hold_piece:
        draw_mini(surface, hold_piece, panel_x + panel_w // 2,
                  hold_box_y + 55, CELL - 8)

    # NEXT
    y = hold_box_y + 130
    label = font_small.render("СЛЕДУЮЩАЯ", True, TEXT_DIM)
    surface.blit(label, (panel_x + 30, y))

    next_box_y = y + 30
    pygame.draw.rect(surface, (12, 14, 24),
                     (panel_x + 30, next_box_y, panel_w - 60, 110),
                     border_radius=10)
    pygame.draw.rect(surface, PANEL_BORDER,
                     (panel_x + 30, next_box_y, panel_w - 60, 110),
                     2, border_radius=10)
    if next_piece:
        draw_mini(surface, next_piece, panel_x + panel_w // 2,
                  next_box_y + 55, CELL - 8)


# ============================================================
#                       ЭКРАНЫ
# ============================================================
def start_screen():
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
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    return
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in (BTN_START, BTN_BACK):
                    pygame.quit()
                    sys.exit()
                if event.button in (BTN_A, BTN_B, BTN_X, BTN_Y):
                    return
            if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                init_joysticks()

        screen.blit(BACKGROUND, (0, 0))

        pulse = 0.5 + 0.5 * math.sin(t * 2)
        title = font_big.render("ТЕТРИС", True, ACCENT)
        shadow = font_big.render("ТЕТРИС", True, (0, 0, 0))
        tx = WIDTH // 2 - title.get_width() // 2
        ty = HEIGHT // 2 - 220 + int(math.sin(t * 1.5) * 6)
        screen.blit(shadow, (tx + 4, ty + 4))
        screen.blit(title, (tx, ty))

        controls = [
            "КЛАВИАТУРА:",
            "  ← →  — движение",
            "  ↑    — поворот",
            "  ↓    — ускорить",
            "  SPACE — сбросить",
            "  SHIFT / C — HOLD",
            "",
            "ДЖОЙСТИК:",
            "  ← → / стик — движение",
            "  ↑ / A / Y   — поворот",
            "  ↓ / стик вниз — ускорить",
            "  B  — сбросить",
            "  X  — HOLD",
        ]
        y = HEIGHT // 2 - 100
        for line in controls:
            col = ACCENT if line.endswith(":") else TEXT_COLOR
            img = font_tiny.render(line, True, col)
            screen.blit(img, (WIDTH // 2 - img.get_width() // 2, y))
            y += int(HEIGHT * 0.032)

        hint1 = font_med.render("SPACE / A — начать", True, GOLD)
        screen.blit(hint1, (WIDTH // 2 - hint1.get_width() // 2,
                            HEIGHT - 120))

        jinfo = font_small.render(f"Джойстиков: {len(joysticks)}",
                                  True, TEXT_DIM)
        screen.blit(jinfo, (WIDTH // 2 - jinfo.get_width() // 2, HEIGHT - 70))

        pygame.display.flip()


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
                if event.button in (BTN_START, BTN_BACK, BTN_A, BTN_X):
                    return
        clock.tick(30)


def game_over_screen(level, lines):
    save_score(score)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    title = font_big.render("ИГРА ОКОНЧЕНА", True, (255, 100, 100))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 200))

    s = font_med.render(f"Счёт: {score}", True, TEXT_COLOR)
    screen.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2 - 90))

    b = font_med.render(f"Рекорд: {best}", True, GOLD)
    screen.blit(b, (WIDTH // 2 - b.get_width() // 2, HEIGHT // 2 - 40))

    l = font_med.render(f"Линии: {lines}", True, TEXT_COLOR)
    screen.blit(l, (WIDTH // 2 - l.get_width() // 2, HEIGHT // 2 + 10))

    lv = font_med.render(f"Уровень: {level}", True, ACCENT)
    screen.blit(lv, (WIDTH // 2 - lv.get_width() // 2, HEIGHT // 2 + 60))

    hint = font_small.render("A / R — заново    START / Q / ESC — выход",
                             True, TEXT_DIM)
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 140))

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
                if event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in (BTN_START, BTN_BACK):
                    pygame.quit()
                    sys.exit()
                if event.button == BTN_A:
                    return True


def piece_fits_anywhere(board, piece):
    for rot in range(4):
        p = Piece(piece.kind)
        p.shape = piece.shape
        for _ in range(rot):
            p.shape = p.rotated()
        for y in range(-2, ROWS):
            for x in range(-2, COLS):
                p.x, p.y = x, y
                if valid(board, p.cells()):
                    return True
    return False


# ============================================================
#                    ГЛАВНАЯ ИГРА
# ============================================================
def main():
    global score, best

    init_joysticks()
    joy = joysticks[0] if joysticks else None

    start_screen()

    while True:
        board = new_board()
        bag = []
        score = 0
        lines_cleared = 0
        level = 1
        drop_timer = 0
        drop_interval = 0.6
        soft_drop = False

        # HOLD
        hold_piece = None
        can_hold = True

        # DAS для клавиатуры
        das_timer = 0
        das_dir = 0  # -1 / 0 / +1
        das_active = False

        # DAS для джойстика
        joy_das_timer = 0
        joy_das_dir = 0
        joy_das_active = False

        floats.clear()
        particles.clear()

        def next_from_bag():
            nonlocal bag
            if not bag:
                bag = list(SHAPES.keys())
                random.shuffle(bag)
            return Piece(bag.pop())

        next_piece = next_from_bag()
        current = next_from_bag()

        running = True
        while running:
            dt = clock.tick(60) / 1000
            dt = min(dt, 0.05)
            time_ms = pygame.time.get_ticks()

            # ==================================================
            #                     СОБЫТИЯ
            # ==================================================
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
                        continue

                    if current is None:
                        continue

                    if event.key == pygame.K_LEFT:
                        test = current.cells(ox=current.x - 1)
                        if valid(board, test):
                            current.x -= 1
                        das_dir = -1
                        das_timer = 0
                        das_active = False
                    elif event.key == pygame.K_RIGHT:
                        test = current.cells(ox=current.x + 1)
                        if valid(board, test):
                            current.x += 1
                        das_dir = 1
                        das_timer = 0
                        das_active = False
                    elif event.key == pygame.K_DOWN:
                        soft_drop = True
                    elif event.key == pygame.K_UP:
                        rotated = current.rotated()
                        for kick in [0, -1, 1, -2, 2]:
                            cells = current.cells(shape=rotated,
                                                  ox=current.x + kick)
                            if valid(board, cells):
                                current.shape = rotated
                                current.x += kick
                                break
                    elif event.key == pygame.K_SPACE:
                        # HARD DROP
                        cells_before = current.y
                        while valid(board, current.cells(oy=current.y + 1)):
                            current.y += 1
                            score += 2
                            if score > best:
                                best = score
                        lock_piece(board, current)
                        board, cleared, crows = clear_lines(board)
                        if cleared:
                            for r in crows:
                                spawn_line_particles(r, ACCENT)
                            lines_cleared += cleared
                            gain = [0, 100, 300, 500, 800][cleared] * level
                            score += gain
                            if score > best:
                                best = score
                            cx = BOARD_X + BOARD_W // 2
                            cy = BOARD_Y + (crows[0] if crows else 0) * CELL
                            floats.append(FloatText(cx, cy, f"+{gain}", GOLD))
                            level = lines_cleared // 10 + 1
                            drop_interval = max(0.08,
                                                0.6 - (level - 1) * 0.05)
                        current = next_piece
                        next_piece = next_from_bag()
                        can_hold = True
                        drop_timer = 0
                        if not piece_fits_anywhere(board, current):
                            running = False
                        continue
                    elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT,
                                       pygame.K_c):
                        # HOLD
                        if can_hold and current is not None:
                            if hold_piece is None:
                                hold_piece = Piece(current.kind)
                                current = next_piece
                                next_piece = next_from_bag()
                            else:
                                tmp = Piece(hold_piece.kind)
                                hold_piece = Piece(current.kind)
                                current = tmp
                            can_hold = False
                            drop_timer = 0

                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_DOWN:
                        soft_drop = False
                    if event.key == pygame.K_LEFT and das_dir == -1:
                        das_dir = 0
                        das_active = False
                    if event.key == pygame.K_RIGHT and das_dir == 1:
                        das_dir = 0
                        das_active = False

                # Джойстик
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button in (BTN_START, BTN_BACK):
                        pause_screen()
                        continue
                    if current is None:
                        continue
                    if event.button in (BTN_A, BTN_Y):
                        rotated = current.rotated()
                        for kick in [0, -1, 1, -2, 2]:
                            cells = current.cells(shape=rotated,
                                                  ox=current.x + kick)
                            if valid(board, cells):
                                current.shape = rotated
                                current.x += kick
                                break
                    elif event.button == BTN_B:
                        # HARD DROP
                        while valid(board, current.cells(oy=current.y + 1)):
                            current.y += 1
                            score += 2
                            if score > best:
                                best = score
                        lock_piece(board, current)
                        board, cleared, crows = clear_lines(board)
                        if cleared:
                            for r in crows:
                                spawn_line_particles(r, ACCENT)
                            lines_cleared += cleared
                            gain = [0, 100, 300, 500, 800][cleared] * level
                            score += gain
                            if score > best:
                                best = score
                            cx = BOARD_X + BOARD_W // 2
                            cy = BOARD_Y + (crows[0] if crows else 0) * CELL
                            floats.append(FloatText(cx, cy, f"+{gain}", GOLD))
                            level = lines_cleared // 10 + 1
                            drop_interval = max(0.08,
                                                0.6 - (level - 1) * 0.05)
                        current = next_piece
                        next_piece = next_from_bag()
                        can_hold = True
                        drop_timer = 0
                        if not piece_fits_anywhere(board, current):
                            running = False
                        continue
                    elif event.button == BTN_X:
                        if can_hold and current is not None:
                            if hold_piece is None:
                                hold_piece = Piece(current.kind)
                                current = next_piece
                                next_piece = next_from_bag()
                            else:
                                tmp = Piece(hold_piece.kind)
                                hold_piece = Piece(current.kind)
                                current = tmp
                            can_hold = False
                            drop_timer = 0

                if event.type in (pygame.JOYDEVICEADDED,
                                  pygame.JOYDEVICEREMOVED):
                    init_joysticks()
                    joy = joysticks[0] if joysticks else None

            # ==================================================
            #                     DAS клавиатура
            # ==================================================
            if current is not None and das_dir != 0:
                das_timer += dt
                if not das_active:
                    if das_timer >= DAS_DELAY:
                        das_active = True
                        das_timer = 0
                else:
                    while das_timer >= ARR_INTERVAL:
                        das_timer -= ARR_INTERVAL
                        test = current.cells(ox=current.x + das_dir)
                        if valid(board, test):
                            current.x += das_dir

            # ==================================================
            #                  Ввод джойстика (движение)
            # ==================================================
            if current is not None and joy is not None:
                ax = 0
                ay = 0
                hx, hy = (0, 0)
                if joy.get_numaxes() >= 2:
                    ax = joy.get_axis(0)
                    ay = joy.get_axis(1)
                    if abs(ax) < DEADZONE:
                        ax = 0
                    if abs(ay) < DEADZONE:
                        ay = 0
                if joy.get_numhats() > 0:
                    hx, hy = joy.get_hat(0)

                # Определяем направление по X
                dir_x = 0
                if hx != 0:
                    dir_x = hx
                elif ax != 0:
                    dir_x = 1 if ax > 0 else -1

                if dir_x != 0:
                    if joy_das_dir != dir_x:
                        # Первое нажатие
                        test = current.cells(ox=current.x + dir_x)
                        if valid(board, test):
                            current.x += dir_x
                        joy_das_dir = dir_x
                        joy_das_timer = 0
                        joy_das_active = False
                    else:
                        joy_das_timer += dt
                        if not joy_das_active:
                            if joy_das_timer >= DAS_DELAY:
                                joy_das_active = True
                                joy_das_timer = 0
                        else:
                            while joy_das_timer >= ARR_INTERVAL:
                                joy_das_timer -= ARR_INTERVAL
                                test = current.cells(ox=current.x + dir_x)
                                if valid(board, test):
                                    current.x += dir_x
                else:
                    joy_das_dir = 0
                    joy_das_active = False
                    joy_das_timer = 0

                # Soft drop со стика (вниз)
                if hy == -1 or ay > DEADZONE:
                    soft_drop = True
                elif soft_drop and not pygame.key.get_pressed()[pygame.K_DOWN]:
                    soft_drop = False

            # ==================================================
            #                  Гравитация
            # ==================================================
            if current is not None:
                ghost_y = current.y
                while valid(board, current.cells(oy=ghost_y + 1)):
                    ghost_y += 1

                interval = 0.05 if soft_drop else drop_interval
                drop_timer += dt

                if drop_timer >= interval:
                    drop_timer = 0
                    if valid(board, current.cells(oy=current.y + 1)):
                        current.y += 1
                        if soft_drop:
                            score += 1
                            if score > best:
                                best = score
                    else:
                        lock_piece(board, current)
                        board, cleared, crows = clear_lines(board)
                        if cleared:
                            for r in crows:
                                spawn_line_particles(r, ACCENT)
                            lines_cleared += cleared
                            gain = [0, 100, 300, 500, 800][cleared] * level
                            score += gain
                            if score > best:
                                best = score
                            cx = BOARD_X + BOARD_W // 2
                            cy = BOARD_Y + (crows[0] if crows else 0) * CELL
                            floats.append(FloatText(cx, cy, f"+{gain}", GOLD))
                            level = lines_cleared // 10 + 1
                            drop_interval = max(0.08,
                                                0.6 - (level - 1) * 0.05)
                        current = next_piece
                        next_piece = next_from_bag()
                        can_hold = True
                        if not piece_fits_anywhere(board, current):
                            running = False

            # ==================================================
            #                     Отрисовка
            # ==================================================
            screen.blit(BACKGROUND, (0, 0))

            ghost_y_draw = None
            if current is not None:
                ghost_y_draw = current.y
                while valid(board, current.cells(oy=ghost_y_draw + 1)):
                    ghost_y_draw += 1

            draw_board(screen, board, current, ghost_y_draw, time_ms)
            draw_panel(screen, level, lines_cleared,
                       next_piece, hold_piece, can_hold)

            # Частицы
            for p in particles:
                p.draw(screen)
            particles[:] = [p for p in particles if p.update(dt)]

            # Всплывающие очки
            for f in floats:
                f.draw(screen)
            floats[:] = [f for f in floats if f.update(dt)]

            pygame.display.flip()

        if not game_over_screen(level, lines_cleared):
            break


if __name__ == "__main__":
    main()
