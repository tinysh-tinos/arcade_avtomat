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

def save_score(score):
    path = os.environ.get("ARCADE_SCORE_FILE")
    if path:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"score": score}, f)
        except OSError:
            pass


pygame.init()

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
ACCENT = (120, 200, 255)

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

score = 0
best = 0


def make_background():
    bg = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        pygame.draw.line(bg, (r, g, b), (0, y), (WIDTH, y))
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
    new_rows = []
    for row in board:
        if all(cell is not None for cell in row):
            cleared += 1
        else:
            new_rows.append(row)
    for _ in range(cleared):
        new_rows.insert(0, [None for _ in range(COLS)])
    return new_rows, cleared


def draw_cell(surface, x, y, color, size, radius=6):
    rect = pygame.Rect(x, y, size, size)
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    lighter = tuple(min(255, c + 60) for c in color)
    darker = tuple(max(0, c - 60) for c in color)
    pygame.draw.rect(surface, lighter, (rect.x + 3, rect.y + 3, size - 6, 6), border_radius=3)
    pygame.draw.rect(surface, darker, (rect.x + 3, rect.bottom - 9, size - 6, 6), border_radius=3)


def draw_board(surface, board, piece, ghost_y):
    panel_rect = pygame.Rect(BOARD_X - 12, BOARD_Y - 12, BOARD_W + 24, BOARD_H + 24)
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
        for gx, gy in piece.cells(ox=piece.x, oy=ghost_y):
            if 0 <= gy < ROWS:
                rect = pygame.Rect(
                    BOARD_X + gx * CELL + 4,
                    BOARD_Y + gy * CELL + 4,
                    CELL - 8, CELL - 8
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


def draw_panel(surface, level, lines, next_piece):
    panel_x = BOARD_X + BOARD_W + 60
    panel_y = BOARD_Y
    panel_w = 260
    panel_h = BOARD_H

    pygame.draw.rect(surface, PANEL_COLOR, (panel_x, panel_y, panel_w, panel_h), border_radius=16)
    pygame.draw.rect(surface, PANEL_BORDER, (panel_x, panel_y, panel_w, panel_h), 3, border_radius=16)

    y = panel_y + 40
    label = font_small.render("СЧЁТ", True, (160, 180, 200))
    surface.blit(label, (panel_x + 30, y))
    y += 34
    val = font_med.render(str(score), True, TEXT_COLOR)
    surface.blit(val, (panel_x + 30, y))

    y += 70
    label = font_small.render("РЕКОРД", True, (160, 180, 200))
    surface.blit(label, (panel_x + 30, y))
    y += 34
    val = font_med.render(str(best), True, (255, 220, 60))
    surface.blit(val, (panel_x + 30, y))

    y += 70
    label = font_small.render("УРОВЕНЬ", True, (160, 180, 200))
    surface.blit(label, (panel_x + 30, y))
    y += 34
    val = font_med.render(str(level), True, ACCENT)
    surface.blit(val, (panel_x + 30, y))

    y += 70
    label = font_small.render("ЛИНИИ", True, (160, 180, 200))
    surface.blit(label, (panel_x + 30, y))
    y += 34
    val = font_med.render(str(lines), True, TEXT_COLOR)
    surface.blit(val, (panel_x + 30, y))

    y += 80
    label = font_small.render("СЛЕДУЮЩАЯ", True, (160, 180, 200))
    surface.blit(label, (panel_x + 30, y))

    preview_y = y + 100
    pygame.draw.rect(surface, (12, 14, 24),
                     (panel_x + 30, preview_y - 50, panel_w - 60, 130), border_radius=10)
    pygame.draw.rect(surface, PANEL_BORDER,
                     (panel_x + 30, preview_y - 50, panel_w - 60, 130), 2, border_radius=10)

    if next_piece:
        draw_mini(surface, next_piece, panel_x + panel_w // 2, preview_y + 15, CELL - 6)


def game_over_screen(level, lines):
    save_score(score)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    title = font_big.render("ИГРА ОКОНЧЕНА", True, (255, 100, 100))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 200))

    s = font_med.render(f"Счёт: {score}", True, TEXT_COLOR)
    screen.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2 - 90))

    b = font_med.render(f"Рекорд: {best}", True, (255, 220, 60))
    screen.blit(b, (WIDTH // 2 - b.get_width() // 2, HEIGHT // 2 - 40))

    l = font_med.render(f"Линии: {lines}", True, TEXT_COLOR)
    screen.blit(l, (WIDTH // 2 - l.get_width() // 2, HEIGHT // 2 + 10))

    lv = font_med.render(f"Уровень: {level}", True, ACCENT)
    screen.blit(lv, (WIDTH // 2 - lv.get_width() // 2, HEIGHT // 2 + 60))

    hint = font_small.render("R — заново    ESC — выход", True, (180, 200, 220))
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


def main():
    global score, best

    while True:
        board = new_board()
        bag = []
        score = 0
        lines_cleared = 0
        level = 1
        drop_timer = 0
        drop_interval = 0.6
        soft_drop = False

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

                    if current is None:
                        continue

                    if event.key == pygame.K_LEFT:
                        test = current.cells(ox=current.x - 1)
                        if valid(board, test):
                            current.x -= 1

                    elif event.key == pygame.K_RIGHT:
                        test = current.cells(ox=current.x + 1)
                        if valid(board, test):
                            current.x += 1

                    elif event.key == pygame.K_DOWN:
                        soft_drop = True

                    elif event.key == pygame.K_UP:
                        rotated = current.rotated()
                        for kick in [0, -1, 1, -2, 2]:
                            cells = current.cells(shape=rotated, ox=current.x + kick)
                            if valid(board, cells):
                                current.shape = rotated
                                current.x += kick
                                break

                    elif event.key == pygame.K_SPACE:
                        while valid(board, current.cells(oy=current.y + 1)):
                            current.y += 1
                            score += 2
                            if score > best:
                                best = score
                        lock_piece(board, current)
                        board, cleared = clear_lines(board)
                        if cleared:
                            lines_cleared += cleared
                            score += [0, 100, 300, 500, 800][cleared] * level
                            if score > best:
                                best = score
                            level = lines_cleared // 10 + 1
                            drop_interval = max(0.08, 0.6 - (level - 1) * 0.05)
                        current = next_piece
                        next_piece = next_from_bag()
                        drop_timer = 0
                        if not piece_fits_anywhere(board, current):
                            running = False
                        continue

                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_DOWN:
                        soft_drop = False

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
                        board, cleared = clear_lines(board)
                        if cleared:
                            lines_cleared += cleared
                            score += [0, 100, 300, 500, 800][cleared] * level
                            if score > best:
                                best = score
                            level = lines_cleared // 10 + 1
                            drop_interval = max(0.08, 0.6 - (level - 1) * 0.05)
                        current = next_piece
                        next_piece = next_from_bag()
                        if not piece_fits_anywhere(board, current):
                            running = False

            screen.blit(BACKGROUND, (0, 0))

            ghost_y_draw = None
            if current is not None:
                ghost_y_draw = current.y
                while valid(board, current.cells(oy=ghost_y_draw + 1)):
                    ghost_y_draw += 1

            draw_board(screen, board, current, ghost_y_draw)
            draw_panel(screen, level, lines_cleared, next_piece)

            pygame.display.flip()

        if not game_over_screen(level, lines_cleared):
            break


if __name__ == "__main__":
    main()
