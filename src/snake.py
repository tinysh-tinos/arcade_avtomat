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

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Змейка")
clock = pygame.time.Clock()

CELL = 32
COLS, ROWS = WIDTH // CELL, HEIGHT // CELL

BG_TOP = (18, 22, 34)
BG_BOTTOM = (28, 34, 52)
GRID_COLOR = (38, 44, 64)
SNAKE_HEAD = (120, 255, 140)
SNAKE_TAIL = (30, 130, 70)
FOOD_OUTER = (255, 90, 110)
FOOD_INNER = (255, 200, 210)
TEXT_COLOR = (230, 240, 255)
ACCENT = (120, 255, 140)

font_big = pygame.font.SysFont("Segoe UI", 64, bold=True)
font_med = pygame.font.SysFont("Segoe UI", 32, bold=True)
font_small = pygame.font.SysFont("Segoe UI", 22)

snake = []
direction = (1, 0)
food = (0, 0)
score = 0
speed = 8
best = 0


def make_background():
    bg = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(BG_TOP[0] * (1 - t) + BG_BOTTOM[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOTTOM[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOTTOM[2] * t)
        pygame.draw.line(bg, (r, g, b), (0, y), (WIDTH, y))
    for x in range(0, WIDTH, CELL):
        pygame.draw.line(bg, GRID_COLOR, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, CELL):
        pygame.draw.line(bg, GRID_COLOR, (0, y), (WIDTH, y), 1)
    return bg


BACKGROUND = make_background()


def lerp_color(c1, c2, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def draw_rounded_cell(surface, color, x, y, size, radius=8):
    rect = pygame.Rect(x, y, size, size)
    pygame.draw.rect(surface, color, rect, border_radius=radius)


def draw_eye(surface, cx, cy, direction):
    dx, dy = direction
    offset = 6
    r = 4
    if dx != 0:
        ex = cx + dx * offset
        ey1 = cy - offset
        ey2 = cy + offset
        pygame.draw.circle(surface, (20, 30, 20), (ex, ey1), r)
        pygame.draw.circle(surface, (20, 30, 20), (ex, ey2), r)
        pygame.draw.circle(surface, (255, 255, 255), (ex + dx, ey1 - 1), 2)
        pygame.draw.circle(surface, (255, 255, 255), (ex + dx, ey2 - 1), 2)
    else:
        ey = cy + dy * offset
        ex1 = cx - offset
        ex2 = cx + offset
        pygame.draw.circle(surface, (20, 30, 20), (ex1, ey), r)
        pygame.draw.circle(surface, (20, 30, 20), (ex2, ey), r)
        pygame.draw.circle(surface, (255, 255, 255), (ex1 - 1, ey + dy), 2)
        pygame.draw.circle(surface, (255, 255, 255), (ex2 - 1, ey + dy), 2)


def spawn_food():
    while True:
        pos = (random.randint(0, COLS - 1), random.randint(0, ROWS - 1))
        if pos not in snake:
            return pos


def draw_snake(surface, time_ms):
    n = len(snake)
    for i, (x, y) in enumerate(snake):
        t = i / max(n - 1, 1)
        color = lerp_color(SNAKE_HEAD, SNAKE_TAIL, t)
        px = x * CELL + 2
        py = y * CELL + 2
        size = CELL - 4
        if i == 0:
            pulse = int(2 * math.sin(time_ms / 200))
            glow = pygame.Surface((size + 16 + pulse * 2, size + 16 + pulse * 2), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*SNAKE_HEAD, 60), glow.get_rect(), border_radius=14)
            screen.blit(glow, (px - 8 - pulse, py - 8 - pulse))
        draw_rounded_cell(surface, color, px, py, size, radius=8)
    hx, hy = snake[0]
    cx = hx * CELL + CELL // 2
    cy = hy * CELL + CELL // 2
    draw_eye(surface, cx, cy, direction)


def draw_food(surface, time_ms):
    fx, fy = food
    cx = fx * CELL + CELL // 2
    cy = fy * CELL + CELL // 2
    pulse = 2 * math.sin(time_ms / 150)
    r_outer = CELL // 2 - 4 + pulse
    r_inner = r_outer // 2
    glow = pygame.Surface((CELL * 2, CELL * 2), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*FOOD_OUTER, 60), (CELL, CELL), int(r_outer + 8))
    screen.blit(glow, (cx - CELL, cy - CELL))
    pygame.draw.circle(screen, FOOD_OUTER, (cx, cy), int(r_outer))
    pygame.draw.circle(screen, FOOD_INNER, (cx - 3, cy - 3), int(r_inner))


def draw_hud(surface):
    panel = pygame.Surface((280, 120), pygame.SRCALPHA)
    pygame.draw.rect(panel, (0, 0, 0, 120), panel.get_rect(), border_radius=18)
    pygame.draw.rect(panel, (*ACCENT, 180), panel.get_rect(), 2, border_radius=18)
    surface.blit(panel, (30, 30))
    s1 = font_small.render("СЧЁТ", True, (160, 180, 200))
    s2 = font_med.render(str(score), True, TEXT_COLOR)
    s3 = font_small.render(f"Рекорд: {best}", True, (160, 180, 200))
    surface.blit(s1, (55, 45))
    surface.blit(s2, (55, 68))
    surface.blit(s3, (55, 108))


def game_over():
    save_score(score)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    title = font_big.render("ИГРА ОКОНЧЕНА", True, FOOD_OUTER)
    score_txt = font_med.render(f"Счёт: {score}", True, TEXT_COLOR)
    best_txt = font_med.render(f"Рекорд: {best}", True, ACCENT)
    hint = font_small.render("R — заново    Q — выход", True, (160, 180, 200))

    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 180))
    screen.blit(score_txt, (WIDTH // 2 - score_txt.get_width() // 2, HEIGHT // 2 - 60))
    screen.blit(best_txt, (WIDTH // 2 - best_txt.get_width() // 2, HEIGHT // 2))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 100))
    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_r:
                    return True


def reset_game():
    global snake, direction, food, score, speed
    snake = [(COLS // 4, ROWS // 2), (COLS // 4 - 1, ROWS // 2), (COLS // 4 - 2, ROWS // 2)]
    direction = (1, 0)
    food = spawn_food()
    score = 0
    speed = 8


def main():
    global direction, food, score, speed, best

    reset_game()

    running = True
    timer = 0
    while running:
        dt = clock.tick(60)
        time_ms = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    save_score(score)
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_UP and direction != (0, 1):
                    direction = (0, -1)
                elif event.key == pygame.K_DOWN and direction != (0, -1):
                    direction = (0, 1)
                elif event.key == pygame.K_LEFT and direction != (1, 0):
                    direction = (-1, 0)
                elif event.key == pygame.K_RIGHT and direction != (-1, 0):
                    direction = (1, 0)

        timer += dt
        step_delay = 1000 / speed
        if timer >= step_delay:
            timer = 0
            head_x, head_y = snake[0]
            new_head = (head_x + direction[0], head_y + direction[1])

            if not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS):
                if score > best:
                    best = score
                if game_over():
                    reset_game()
                    timer = 0
                    continue
                else:
                    return

            if new_head in snake:
                if score > best:
                    best = score
                if game_over():
                    reset_game()
                    timer = 0
                    continue
                else:
                    return

            snake.insert(0, new_head)

            if new_head == food:
                score += 1
                food = spawn_food()
                if speed < 22:
                    speed += 0.4
            else:
                snake.pop()

        screen.blit(BACKGROUND, (0, 0))
        draw_food(screen, time_ms)
        draw_snake(screen, time_ms)
        draw_hud(screen)
        pygame.display.flip()


if __name__ == "__main__":
    main()
