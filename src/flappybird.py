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
import math

pygame.init()

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

font_big = pygame.font.SysFont("Segoe UI", 80, bold=True)
font_med = pygame.font.SysFont("Segoe UI", 40, bold=True)
font_small = pygame.font.SysFont("Segoe UI", 26)

GROUND_H = 120
GRAVITY = 1800
FLAP_POWER = -650
PIPE_WIDTH = 120
PIPE_GAP = 260
PIPE_SPEED = 380
PIPE_SPAWN = 1.6


def make_background():
    bg = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(SKY_TOP[0] * (1 - t) + SKY_BOTTOM[0] * t)
        g = int(SKY_TOP[1] * (1 - t) + SKY_BOTTOM[1] * t)
        b = int(SKY_TOP[2] * (1 - t) + SKY_BOTTOM[2] * t)
        pygame.draw.line(bg, (r, g, b), (0, y), (WIDTH, y))

    for i in range(40):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT - GROUND_H - 200)
        r = random.randint(2, 5)
        pygame.draw.circle(bg, (255, 255, 255, 100), (x, y), r)

    return bg


BACKGROUND = make_background()


class Bird:
    def __init__(self):
        self.x = WIDTH // 4
        self.y = HEIGHT // 2
        self.vy = 0
        self.radius = 28
        self.angle = 0
        self.wing_phase = 0

    def flap(self):
        self.vy = FLAP_POWER
        self.wing_phase = 0

    def update(self, dt):
        self.vy += GRAVITY * dt
        self.y += self.vy * dt

        target = max(-30, min(90, self.vy / 10))
        self.angle += (target - self.angle) * min(1, dt * 10)
        self.wing_phase += dt * 20

        if self.y < self.radius:
            self.y = self.radius
            self.vy = 0

    def rect(self):
        return pygame.Rect(
            self.x - self.radius, self.y - self.radius,
            self.radius * 2, self.radius * 2
        )

    def draw(self, surface):
        size = self.radius * 3
        bird_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        r = self.radius

        pygame.draw.circle(bird_surf, BIRD_DARK, (cx + 2, cy + 2), r)
        pygame.draw.circle(bird_surf, BIRD_BODY, (cx, cy), r)

        # wing_offset = math.sin(self.wing_phase) * 6
        # wing_points = [
        #     (cx - r // 2, cy + int(wing_offset)),
        #     (cx - r // 2 - 18, cy + 12 + int(wing_offset)),
        #     (cx + r // 2, cy + 14 + int(wing_offset)),
        # ]
        # pygame.draw.polygon(bird_surf, BIRD_WING, wing_points)
        # pygame.draw.polygon(bird_surf, (200, 200, 200), wing_points, 2)

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
            pygame.draw.rect(surface, PIPE_DARK, rect.inflate(8, 0), border_radius=6)
            pygame.draw.rect(surface, PIPE_COLOR, rect, border_radius=6)
            highlight = pygame.Rect(rect.x + 12, rect.y, 20, rect.height)
            pygame.draw.rect(surface, PIPE_LIGHT, highlight, border_radius=6)

            cap_h = 40
            if rect.y == 0:
                cap = pygame.Rect(rect.x - 8, rect.bottom - cap_h, PIPE_WIDTH + 16, cap_h)
            else:
                cap = pygame.Rect(rect.x - 8, rect.y, PIPE_WIDTH + 16, cap_h)
            pygame.draw.rect(surface, PIPE_DARK, cap, border_radius=8)
            pygame.draw.rect(surface, PIPE_COLOR, cap.inflate(-6, -6), border_radius=6)


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


def draw_score(surface, score, best):
    txt = font_big.render(str(score), True, TEXT_COLOR)
    shadow = font_big.render(str(score), True, TEXT_SHADOW)
    cx = WIDTH // 2
    surface.blit(shadow, (cx - shadow.get_width() // 2 + 4, 84))
    surface.blit(txt, (cx - txt.get_width() // 2, 80))

    best_txt = font_small.render(f"Рекорд: {best}", True, TEXT_COLOR)
    best_sh = font_small.render(f"Рекорд: {best}", True, TEXT_SHADOW)
    surface.blit(best_sh, (cx - best_txt.get_width() // 2 + 2, 182))
    surface.blit(best_txt, (cx - best_txt.get_width() // 2, 180))


def start_screen(best):
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_SPACE or event.key == pygame.K_UP:
                    return
            if event.type == pygame.MOUSEBUTTONDOWN:
                return

        screen.blit(BACKGROUND, (0, 0))

        title = font_big.render("FLAPPY BIRD", True, TEXT_COLOR)
        title_sh = font_big.render("FLAPPY BIRD", True, TEXT_SHADOW)
        screen.blit(title_sh, (WIDTH // 2 - title.get_width() // 2 + 5, 205))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 200))

        hint = font_med.render("ПРОБЕЛ / КЛИК — начать", True, TEXT_COLOR)
        hint_sh = font_med.render("ПРОБЕЛ / КЛИК — начать", True, TEXT_SHADOW)
        screen.blit(hint_sh, (WIDTH // 2 - hint.get_width() // 2 + 3, HEIGHT // 2 + 103))
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 100))

        best_txt = font_small.render(f"Рекорд: {best}", True, TEXT_COLOR)
        screen.blit(best_txt, (WIDTH // 2 - best_txt.get_width() // 2, HEIGHT // 2 + 180))

        esc = font_small.render("ESC — выход", True, TEXT_COLOR)
        screen.blit(esc, (WIDTH // 2 - esc.get_width() // 2, HEIGHT - 60))

        pygame.display.flip()
        clock.tick(60)


def game_over_screen(score, best):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))

    title = font_big.render("ИГРА ОКОНЧЕНА", True, (255, 100, 100))
    title_sh = font_big.render("ИГРА ОКОНЧЕНА", True, TEXT_SHADOW)
    screen.blit(title_sh, (WIDTH // 2 - title.get_width() // 2 + 5, HEIGHT // 2 - 205))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 210))

    s = font_med.render(f"Счёт: {score}", True, TEXT_COLOR)
    screen.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2 - 60))

    b = font_med.render(f"Рекорд: {best}", True, (255, 220, 60))
    screen.blit(b, (WIDTH // 2 - b.get_width() // 2, HEIGHT // 2))

    hint = font_small.render("R — заново    ESC — выход", True, TEXT_COLOR)
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
                if event.key == pygame.K_r or event.key == pygame.K_SPACE:
                    return True
                if event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                return True


def main():
    best = 0

    while True:
        start_screen(best)

        bird = Bird()
        pipes = []
        clouds = [Cloud() for _ in range(6)]
        score = 0
        spawn_timer = 0
        ground_offset = 0
        game_started = False

        running = True
        while running:
            dt = clock.tick(60) / 1000
            dt = min(dt, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    if event.key == pygame.K_SPACE or event.key == pygame.K_UP:
                        bird.flap()
                        game_started = True
                if event.type == pygame.MOUSEBUTTONDOWN:
                    bird.flap()
                    game_started = True

            if game_started:
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
                    if bird.rect().colliderect(top) or bird.rect().colliderect(bottom):
                        running = False

                pipes = [p for p in pipes if p.x + PIPE_WIDTH > -10]

                if bird.y + bird.radius >= HEIGHT - GROUND_H:
                    bird.y = HEIGHT - GROUND_H - bird.radius
                    running = False

            for cloud in clouds:
                cloud.update(dt)

            screen.blit(BACKGROUND, (0, 0))

            for cloud in clouds:
                cloud.draw(screen)

            for pipe in pipes:
                pipe.draw(screen)

            draw_ground(screen, ground_offset)
            bird.draw(screen)
            draw_score(screen, score, best)

            if not game_started:
                hint = font_med.render("ПРОБЕЛ — взлёт", True, TEXT_COLOR)
                hint_sh = font_med.render("ПРОБЕЛ — взлёт", True, TEXT_SHADOW)
                screen.blit(hint_sh, (WIDTH // 2 - hint.get_width() // 2 + 3, HEIGHT // 2 - 197))
                screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 - 200))

            pygame.display.flip()

        if score > best:
            best = score

        if not game_over_screen(score, best):
            break


if __name__ == "__main__":
    main()
