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
TEXT_DIM = (160, 180, 200)
ACCENT = (120, 255, 140)
GOLD = (255, 215, 80)

font_big = pygame.font.SysFont("Segoe UI", 64, bold=True)
font_med = pygame.font.SysFont("Segoe UI", 32, bold=True)
font_small = pygame.font.SysFont("Segoe UI", 22)

snake = []
direction = (1, 0)
food = (0, 0)
score = 0
speed = 8
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


def spawn_particles(x, y, color, count=14):
    for _ in range(count):
        a = random.uniform(0, math.tau)
        spd = random.uniform(80, 320)
        particles.append(Particle(
            x, y,
            math.cos(a) * spd, math.sin(a) * spd,
            color,
            random.uniform(0.25, 0.6),
            random.randint(2, 5),
        ))


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
            glow = pygame.Surface((size + 16 + pulse * 2, size + 16 + pulse * 2),
                                  pygame.SRCALPHA)
            pygame.draw.rect(glow, (*SNAKE_HEAD, 60), glow.get_rect(),
                             border_radius=14)
            surface.blit(glow, (px - 8 - pulse, py - 8 - pulse))
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
    surface.blit(glow, (cx - CELL, cy - CELL))
    pygame.draw.circle(surface, FOOD_OUTER, (cx, cy), int(r_outer))
    pygame.draw.circle(surface, FOOD_INNER, (cx - 3, cy - 3), int(r_inner))


def draw_hud(surface):
    panel = pygame.Surface((280, 120), pygame.SRCALPHA)
    pygame.draw.rect(panel, (0, 0, 0, 120), panel.get_rect(), border_radius=18)
    pygame.draw.rect(panel, (*ACCENT, 180), panel.get_rect(), 2, border_radius=18)
    surface.blit(panel, (30, 30))
    s1 = font_small.render("СЧЁТ", True, TEXT_DIM)
    s2 = font_med.render(str(score), True, TEXT_COLOR)
    s3 = font_small.render(f"Рекорд: {best}", True, GOLD)
    surface.blit(s1, (55, 45))
    surface.blit(s2, (55, 68))
    surface.blit(s3, (55, 108))


# ============================================================
#           ВВОД: клавиатура + джойстик
# ============================================================
def read_direction(keys, joy):
    """Возвращает новое направление от клавиатуры/джойстика или None."""
    # --- Клавиатура ---
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        return (0, -1)
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        return (0, 1)
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        return (-1, 0)
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        return (1, 0)

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
                if event.button == BTN_START or event.button == BTN_BACK:
                    pygame.quit()
                    sys.exit()
                if event.button in (BTN_A, BTN_X):
                    return
            if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                init_joysticks()

        screen.blit(BACKGROUND, (0, 0))

        # Пульсирующий заголовок
        pulse = 0.5 + 0.5 * math.sin(t * 2)
        title = font_big.render("ЗМЕЙКА", True, ACCENT)
        shadow = font_big.render("ЗМЕЙКА", True, (0, 0, 0))
        tx = WIDTH // 2 - title.get_width() // 2
        ty = HEIGHT // 2 - 180 + int(math.sin(t * 1.5) * 6)
        screen.blit(shadow, (tx + 4, ty + 4))
        screen.blit(title, (tx, ty))

        sub = font_med.render("Стрелки / WASD / Джойстик", True, TEXT_COLOR)
        screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 - 40))

        hint1 = font_med.render("SPACE / A — начать", True, GOLD)
        screen.blit(hint1, (WIDTH // 2 - hint1.get_width() // 2, HEIGHT // 2 + 60))

        hint2 = font_small.render("P — пауза    Q / ESC — выход", True, TEXT_DIM)
        screen.blit(hint2, (WIDTH // 2 - hint2.get_width() // 2, HEIGHT // 2 + 130))

        jinfo = font_small.render(f"Джойстиков: {len(joysticks)}", True, TEXT_DIM)
        screen.blit(jinfo, (WIDTH // 2 - jinfo.get_width() // 2, HEIGHT - 80))

        if int(t * 2) % 2 == 0:
            blink = font_small.render("●", True, ACCENT)
            screen.blit(blink, (WIDTH // 2 - blink.get_width() // 2, HEIGHT // 2 + 105))

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


def game_over():
    save_score(score)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    title = font_big.render("ИГРА ОКОНЧЕНА", True, FOOD_OUTER)
    score_txt = font_med.render(f"Счёт: {score}", True, TEXT_COLOR)
    best_txt = font_med.render(f"Рекорд: {best}", True, GOLD)
    hint = font_small.render("A / R — заново    START / Q / ESC — выход",
                             True, TEXT_DIM)

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
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_r:
                    return True
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in (BTN_START, BTN_BACK):
                    pygame.quit()
                    sys.exit()
                if event.button == BTN_A:
                    return True


def reset_game():
    global snake, direction, food, score, speed
    snake = [(COLS // 4, ROWS // 2),
             (COLS // 4 - 1, ROWS // 2),
             (COLS // 4 - 2, ROWS // 2)]
    direction = (1, 0)
    food = spawn_food()
    score = 0
    speed = 8


def main():
    global direction, food, score, speed, best

    init_joysticks()
    joy = joysticks[0] if joysticks else None

    start_screen()

    reset_game()

    # Очередь поворотов (буфер до 2), чтобы быстрые нажатия не терялись
    turn_queue = []

    running = True
    timer = 0
    while running:
        dt = clock.tick(60)
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
                    timer = 0
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in (BTN_START, BTN_BACK):
                    pause_screen()
                    timer = 0
            if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                init_joysticks()
                joy = joysticks[0] if joysticks else None

        # --- Ввод направления ---
        keys = pygame.key.get_pressed()
        new_dir = read_direction(keys, joy)
        if new_dir is not None:
            # Не даём развернуться на 180°
            if (new_dir[0] != -direction[0] or new_dir[1] != -direction[1]):
                # Заменяем конец очереди на новое нажатие
                if not turn_queue or turn_queue[-1] != new_dir:
                    turn_queue.append(new_dir)
                    if len(turn_queue) > 2:
                        turn_queue.pop(0)

        timer += dt
        step_delay = 1000 / speed
        if timer >= step_delay:
            timer = 0

            # Применяем поворот из очереди
            while turn_queue:
                cand = turn_queue.pop(0)
                if cand[0] != -direction[0] or cand[1] != -direction[1]:
                    direction = cand
                    break

            head_x, head_y = snake[0]
            new_head = (head_x + direction[0], head_y + direction[1])

            # Столкновение со стеной или собой
            if not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS) or \
               new_head in snake:
                if score > best:
                    best = score
                # Частицы на месте смерти
                cx = head_x * CELL + CELL // 2
                cy = head_y * CELL + CELL // 2
                spawn_particles(cx, cy, FOOD_OUTER, 30)
                if game_over():
                    reset_game()
                    turn_queue.clear()
                    timer = 0
                    particles.clear()
                    continue
                else:
                    return

            snake.insert(0, new_head)

            if new_head == food:
                score += 1
                # Частицы на месте еды
                fx, fy = food
                spawn_particles(fx * CELL + CELL // 2,
                                fy * CELL + CELL // 2,
                                FOOD_OUTER, 16)
                food = spawn_food()
                if speed < 22:
                    speed += 0.4
            else:
                snake.pop()

        # --- Отрисовка ---
        screen.blit(BACKGROUND, (0, 0))
        draw_food(screen, time_ms)
        draw_snake(screen, time_ms)

        for p in particles:
            p.draw(screen)
        particles[:] = [p for p in particles if p.update(dt / 1000)]

        draw_hud(screen)
        pygame.display.flip()


if __name__ == "__main__":
    main()
