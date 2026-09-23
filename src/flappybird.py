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
pygame.display.set_caption("Flappy Bird")
clock = pygame.time.Clock()

SKY_TOP = (80, 170, 230)
SKY_BOTTOM = (170, 220, 250)
GROUND_COLOR = (222, 216, 149)
GROUND_DARK = (200, 190, 110)
PIPE_COLOR = (90, 200, 90)
PIPE_DARK = (50, 150, 50)
PIPE_LIGHT = (140, 230, 140)
BIRD_BODY = (255, 220, 60)
BIRD_DARK = (230, 170, 30)
BIRD_WING = (250, 250, 250)
BEAK = (255, 140, 30)
EYE_WHITE = (255, 255, 255)
EYE_BLACK = (20, 20, 20)
TEXT_COLOR = (255, 255, 255)
TEXT_SHADOW = (40, 40, 40)
TEXT_DIM = (230, 235, 245)
GOLD = (255, 220, 60)
ACCENT = (120, 200, 255)

font_big = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.1), bold=True)
font_med = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.055), bold=True)
font_small = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.035))
font_tiny = pygame.font.SysFont("Segoe UI", int(HEIGHT * 0.028))

GROUND_H = int(HEIGHT * 0.17)
GRAVITY = HEIGHT * 2.4
FLAP_POWER = -HEIGHT * 0.9
PIPE_WIDTH = int(WIDTH * 0.1)
PIPE_GAP = int(HEIGHT * 0.36)
PIPE_SPEED = WIDTH * 0.32
PIPE_SPAWN = 1.6

score = 0
best = 0

# ---------- Настройки джойстиков ----------
DEADZONE = 0.5
BTN_A = 0
BTN_B = 1
BTN_X = 2
BTN_Y = 3
BTN_START = 7
BTN_BACK = 6

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
        r = int(SKY_TOP[0] * (1 - t) + SKY_BOTTOM[0] * t)
        g = int(SKY_TOP[1] * (1 - t) + SKY_BOTTOM[1] * t)
        b = int(SKY_TOP[2] * (1 - t) + SKY_BOTTOM[2] * t)
        pygame.draw.line(bg, (r, g, b), (0, y), (WIDTH, y))
    random.seed(11)
    for i in range(40):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT - GROUND_H - 200)
        r = random.randint(2, 5)
        pygame.draw.circle(bg, (255, 255, 255), (x, y), r)
    random.seed()
    return bg


BACKGROUND = make_background()


# ---------- Частицы ----------
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


particles = []


def spawn_burst(x, y, color, count=20):
    for _ in range(count):
        a = random.uniform(0, math.tau)
        spd = random.uniform(WIDTH * 0.05, WIDTH * 0.25)
        particles.append(Particle(
            x, y,
            math.cos(a) * spd, math.sin(a) * spd - HEIGHT * 0.1,
            color,
            random.uniform(0.3, 0.7),
            random.randint(2, 5),
        ))


class Bird:
    def __init__(self):
        self.x = WIDTH // 4
        self.y = HEIGHT // 2
        self.vy = 0
        self.radius = int(HEIGHT * 0.045)
        self.angle = 0
        self.wing_phase = 0
        self.flap_anim = 0.0

    def flap(self):
        self.vy = FLAP_POWER
        self.wing_phase = 0
        self.flap_anim = 1.0

    def update(self, dt):
        self.vy += GRAVITY * dt
        self.y += self.vy * dt

        target = max(-30, min(90, self.vy / 10))
        self.angle += (target - self.angle) * min(1, dt * 10)
        self.wing_phase += dt * 20
        self.flap_anim = max(0.0, self.flap_anim - dt * 3)

        if self.y < self.radius:
            self.y = self.radius
            self.vy = 0

    def rect(self):
        return pygame.Rect(
            self.x - self.radius, self.y - self.radius,
            self.radius * 2, self.radius * 2
        )

    def draw(self, surface, time_ms):
        size = self.radius * 3
        bird_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        r = self.radius

        # Свечение
        pulse = 0.7 + 0.3 * math.sin(time_ms / 200)
        glow_r = int(r * 1.7)
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*BIRD_BODY, int(50 * pulse)),
                           (glow_r, glow_r), glow_r)
        surface.blit(glow, (self.x - glow_r, self.y - glow_r))

        pygame.draw.circle(bird_surf, BIRD_DARK, (cx + 2, cy + 2), r)
        pygame.draw.circle(bird_surf, BIRD_BODY, (cx, cy), r)

        beak_points = [
            (cx + r - 4, cy - 4),
            (cx + r + 18, cy),
            (cx + r - 4, cy + 6),
        ]
        pygame.draw.polygon(bird_surf, BEAK, beak_points)
        pygame.draw.polygon(bird_surf, (200, 90, 10), beak_points, 2)

        pygame.draw.circle(bird_surf, EYE_WHITE, (cx + 10, cy - 10), 10)
        pygame.draw.circle(bird_surf, EYE_BLACK, (cx + 13, cy - 10), 5)
        pygame.draw.circle(bird_surf, (255, 255, 255), (cx + 15, cy - 12), 2)

        rotated = pygame.transform.rotate(bird_surf, -self.angle)
        rect = rotated.get_rect(center=(self.x, self.y))
        surface.blit(rotated, rect)


class Pipe:
    def __init__(self, x, gap_y):
        self.x = x
        self.gap_y = gap_y
        self.scored = False

    def update(self, dt):
        self.x -= PIPE_SPEED * dt

    def rects(self):
        top = pygame.Rect(self.x, 0, PIPE_WIDTH, self.gap_y - PIPE_GAP // 2)
        bottom = pygame.Rect(
            self.x, self.gap_y + PIPE_GAP // 2,
            PIPE_WIDTH, HEIGHT - GROUND_H - (self.gap_y + PIPE_GAP // 2)
        )
        return top, bottom

    def draw(self, surface):
        top, bottom = self.rects()
        for rect in (top, bottom):
            pygame.draw.rect(surface, PIPE_DARK,
                             rect.inflate(8, 0), border_radius=6)
            pygame.draw.rect(surface, PIPE_COLOR, rect, border_radius=6)
            highlight = pygame.Rect(rect.x + 12, rect.y, 20, rect.height)
            pygame.draw.rect(surface, PIPE_LIGHT, highlight, border_radius=6)

            cap_h = 40
            if rect.y == 0:
                cap = pygame.Rect(rect.x - 8, rect.bottom - cap_h,
                                  PIPE_WIDTH + 16, cap_h)
            else:
                cap = pygame.Rect(rect.x - 8, rect.y,
                                  PIPE_WIDTH + 16, cap_h)
            pygame.draw.rect(surface, PIPE_DARK, cap, border_radius=8)
            pygame.draw.rect(surface, PIPE_COLOR,
                             cap.inflate(-6, -6), border_radius=6)


class Cloud:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(50, HEIGHT // 2)
        self.speed = random.uniform(20, 50)
        self.scale = random.uniform(0.6, 1.4)

    def update(self, dt):
        self.x -= self.speed * dt
        if self.x < -200:
            self.x = WIDTH + 200
            self.y = random.randint(50, HEIGHT // 2)

    def draw(self, surface):
        s = self.scale
        for dx, dy, r in [(-40, 0, 35), (0, -15, 45), (40, 0, 35), (0, 10, 40)]:
            pygame.draw.circle(
                surface, (255, 255, 255),
                (int(self.x + dx * s), int(self.y + dy * s)),
                int(r * s)
            )


def draw_ground(surface, offset):
    ground = pygame.Rect(0, HEIGHT - GROUND_H, WIDTH, GROUND_H)
    pygame.draw.rect(surface, GROUND_COLOR, ground)
    pygame.draw.rect(surface, GROUND_DARK, (0, HEIGHT - GROUND_H, WIDTH, 12))

    stripe_w = 40
    for i in range(-1, WIDTH // stripe_w + 2):
        x = i * stripe_w - (offset % stripe_w)
        color = GROUND_DARK if i % 2 == 0 else GROUND_COLOR
        pygame.draw.rect(
            surface, color,
            (x, HEIGHT - GROUND_H + 12, stripe_w, GROUND_H - 12)
        )


def draw_score(surface):
    txt = font_big.render(str(score), True, TEXT_COLOR)
    shadow = font_big.render(str(score), True, TEXT_SHADOW)
    cx = WIDTH // 2
    surface.blit(shadow, (cx - shadow.get_width() // 2 + 4, 84))
    surface.blit(txt, (cx - txt.get_width() // 2, 80))

    best_txt = font_small.render(f"Рекорд: {best}", True, GOLD)
    best_sh = font_small.render(f"Рекорд: {best}", True, TEXT_SHADOW)
    surface.blit(best_sh, (cx - best_txt.get_width() // 2 + 2, 182))
    surface.blit(best_txt, (cx - best_txt.get_width() // 2, 180))


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
                if event.key in (pygame.K_SPACE, pygame.K_RETURN,
                                 pygame.K_UP):
                    return
            if event.type == pygame.MOUSEBUTTONDOWN:
                return
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in (BTN_START, BTN_BACK):
                    pygame.quit()
                    sys.exit()
                if event.button in (BTN_A, BTN_B, BTN_X, BTN_Y):
                    return
            if event.type in (pygame.JOYDEVICEADDED,
                              pygame.JOYDEVICEREMOVED):
                init_joysticks()

        screen.blit(BACKGROUND, (0, 0))
        for i in range(4):
            c = Cloud()
            c.draw(screen)

        pulse = 0.5 + 0.5 * math.sin(t * 2)
        title = font_big.render("FLAPPY BIRD", True, BIRD_BODY)
        shadow = font_big.render("FLAPPY BIRD", True, TEXT_SHADOW)
        tx = WIDTH // 2 - title.get_width() // 2
        ty = HEIGHT // 2 - 200 + int(math.sin(t * 1.5) * 6)
        screen.blit(shadow, (tx + 4, ty + 4))
        screen.blit(title, (tx, ty))

        controls = [
            "SPACE / ↑ / клик — взмах",
            "A / любая кнопка — взмах",
            "P / START — пауза",
        ]
        y = HEIGHT // 2 - 30
        for line in controls:
            img = font_small.render(line, True, TEXT_COLOR)
            screen.blit(img, (WIDTH // 2 - img.get_width() // 2, y))
            y += int(HEIGHT * 0.05)

        hint = font_med.render("SPACE / A — начать", True, GOLD)
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2,
                           HEIGHT - 150))

        jinfo = font_tiny.render(f"Джойстиков: {len(joysticks)}",
                                 True, TEXT_DIM)
        screen.blit(jinfo, (WIDTH // 2 - jinfo.get_width() // 2, HEIGHT - 80))

        pygame.display.flip()


def pause_screen():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    title = font_big.render("ПАУЗА", True, GOLD)
    title_sh = font_big.render("ПАУЗА", True, TEXT_SHADOW)
    tx = WIDTH // 2 - title.get_width() // 2
    screen.blit(title_sh, (tx + 4, HEIGHT // 2 - 100 + 4))
    screen.blit(title, (tx, HEIGHT // 2 - 100))

    hint1 = font_med.render("START / P — продолжить", True, TEXT_COLOR)
    screen.blit(hint1, (WIDTH // 2 - hint1.get_width() // 2, HEIGHT // 2 + 20))

    hint2 = font_small.render("ESC — выход", True, TEXT_DIM)
    screen.blit(hint2, (WIDTH // 2 - hint2.get_width() // 2, HEIGHT // 2 + 90))

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
                if event.key in (pygame.K_p, pygame.K_RETURN,
                                 pygame.K_SPACE):
                    return
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in (BTN_START, BTN_BACK, BTN_A, BTN_X):
                    return
        clock.tick(30)


def game_over_screen():
    save_score(score)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))

    title = font_big.render("ИГРА ОКОНЧЕНА", True, (255, 100, 100))
    title_sh = font_big.render("ИГРА ОКОНЧЕНА", True, TEXT_SHADOW)
    screen.blit(title_sh, (WIDTH // 2 - title.get_width() // 2 + 5,
                           HEIGHT // 2 - 205))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2,
                        HEIGHT // 2 - 210))

    s = font_med.render(f"Счёт: {score}", True, TEXT_COLOR)
    screen.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2 - 60))

    b = font_med.render(f"Рекорд: {best}", True, GOLD)
    screen.blit(b, (WIDTH // 2 - b.get_width() // 2, HEIGHT // 2))

    hint = font_small.render("A / R / SPACE — заново    START / Q / ESC — выход",
                             True, TEXT_COLOR)
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 100))

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
                if event.key in (pygame.K_r, pygame.K_SPACE, pygame.K_RETURN):
                    return True
                if event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                return True
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in (BTN_START, BTN_BACK):
                    pygame.quit()
                    sys.exit()
                if event.button in (BTN_A, BTN_B, BTN_X, BTN_Y):
                    return True


def main():
    global score, best

    init_joysticks()
    joy = joysticks[0] if joysticks else None

    start_screen()

    while True:
        bird = Bird()
        pipes = []
        clouds = [Cloud() for _ in range(6)]
        score = 0
        spawn_timer = 0
        ground_offset = 0
        game_started = False
        died = False
        shake = 0.0

        particles.clear()

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
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        bird.flap()
                        game_started = True
                if event.type == pygame.MOUSEBUTTONDOWN:
                    bird.flap()
                    game_started = True
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button in (BTN_START, BTN_BACK):
                        pause_screen()
                        continue
                    if event.button in (BTN_A, BTN_B, BTN_X, BTN_Y):
                        bird.flap()
                        game_started = True
                if event.type in (pygame.JOYDEVICEADDED,
                                  pygame.JOYDEVICEREMOVED):
                    init_joysticks()
                    joy = joysticks[0] if joysticks else None

            # Джойстик: крестовина вверх или стик вверх — тоже flap
            if joy is not None and not died:
                flap_trigger = False
                if joy.get_numhats() > 0:
                    _, hy = joy.get_hat(0)
                    if hy > 0:
                        flap_trigger = True
                if not flap_trigger and joy.get_numaxes() >= 2:
                    ay = joy.get_axis(1)
                    if ay < -DEADZONE:
                        # Чтобы не флапать каждый кадр — кулдаун через
                        # game_started и скорость
                        if not game_started or bird.vy > -HEIGHT * 0.2:
                            flap_trigger = True
                if flap_trigger:
                    bird.flap()
                    game_started = True

            # ==================================================
            #                     ЛОГИКА
            # ==================================================
            if game_started and not died:
                bird.update(dt)
                ground_offset += PIPE_SPEED * dt

                spawn_timer += dt
                if spawn_timer >= PIPE_SPAWN:
                    spawn_timer = 0
                    gap_y = random.randint(
                        PIPE_GAP // 2 + 80,
                        HEIGHT - GROUND_H - PIPE_GAP // 2 - 80
                    )
                    pipes.append(Pipe(WIDTH + PIPE_WIDTH, gap_y))

                for pipe in pipes:
                    pipe.update(dt)

                    if not pipe.scored and pipe.x + PIPE_WIDTH < bird.x:
                        pipe.scored = True
                        score += 1
                        if score > best:
                            best = score

                    top, bottom = pipe.rects()
                    if bird.rect().colliderect(top) or \
                       bird.rect().colliderect(bottom):
                        died = True
                        shake = HEIGHT * 0.015
                        spawn_burst(bird.x, bird.y, BIRD_BODY, 30)

                pipes = [p for p in pipes if p.x + PIPE_WIDTH > -10]

                if bird.y + bird.radius >= HEIGHT - GROUND_H:
                    bird.y = HEIGHT - GROUND_H - bird.radius
                    died = True
                    shake = HEIGHT * 0.02
                    spawn_burst(bird.x, bird.y, BIRD_BODY, 40)

                if died:
                    if score > best:
                        best = score
                    save_score(score)
                    running = False

            for cloud in clouds:
                cloud.update(dt)

            # ==================================================
            #                     ОТРИСОВКА
            # ==================================================
            # Тряска
            sx = sy = 0
            if shake > 0:
                sx = random.randint(-int(shake), int(shake))
                sy = random.randint(-int(shake), int(shake))
                shake *= 0.88
                if shake < 0.5:
                    shake = 0

            screen.blit(BACKGROUND, (sx, sy))

            for cloud in clouds:
                cloud.draw(screen)

            for pipe in pipes:
                pipe.draw(screen)

            draw_ground(screen, ground_offset)
            bird.draw(screen, time_ms)

            # Частицы
            for p in particles:
                p.draw(screen)
            particles[:] = [p for p in particles if p.update(dt)]

            draw_score(screen)

            if not game_started:
                hint = font_med.render("SPACE / A — взлёт", True, TEXT_COLOR)
                hint_sh = font_med.render("SPACE / A — взлёт", True, TEXT_SHADOW)
                screen.blit(hint_sh, (WIDTH // 2 - hint.get_width() // 2 + 3,
                                      HEIGHT // 2 - 197))
                screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2,
                                   HEIGHT // 2 - 200))

                if int(time_ms / 400) % 2 == 0:
                    sub = font_small.render("↑ или стик вверх", True, TEXT_DIM)
                    screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2,
                                      HEIGHT // 2 - 130))

            pygame.display.flip()

        if not game_over_screen():
            break


if __name__ == "__main__":
    main()
