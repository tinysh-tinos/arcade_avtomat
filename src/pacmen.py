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
pygame.display.set_caption("Mortal Kombat")
clock = pygame.time.Clock()

BG_TOP = (30, 10, 40)
BG_BOTTOM = (80, 20, 20)
GROUND_H = int(HEIGHT * 0.15)
GROUND_COLOR = (40, 30, 25)
GROUND_LINE = (70, 50, 40)

P1_COLOR = (60, 140, 255)
P2_COLOR = (255, 80, 80)
FIRE_P1 = (100, 200, 255)
FIRE_P2 = (255, 140, 60)
HEALTH_GREEN = (60, 220, 80)
HEALTH_RED = (230, 50, 50)
HEALTH_BG = (40, 20, 20)
TEXT_COLOR = (255, 255, 255)

font_big = pygame.font.SysFont("Impact", int(HEIGHT * 0.1))
font_med = pygame.font.SysFont("Impact", int(HEIGHT * 0.055))
font_small = pygame.font.SysFont("Arial", int(HEIGHT * 0.03))

GRAVITY = HEIGHT * 2.8
JUMP_POWER = -HEIGHT * 1.05
MOVE_SPEED = WIDTH * 0.26
FIREBALL_SPEED = WIDTH * 0.6
FIREBALL_DAMAGE = 10

GROUND_Y = HEIGHT - GROUND_H

FIGHTER_W = int(WIDTH * 0.05)
FIGHTER_H = int(HEIGHT * 0.17)
FIREBALL_RADIUS = int(HEIGHT * 0.02)
HEAD_RADIUS = int(HEIGHT * 0.038)

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

    moon_r = int(HEIGHT * 0.17)
    pygame.draw.circle(bg, (180, 100, 60), (WIDTH // 2, int(HEIGHT * 0.22)), moon_r)
    pygame.draw.circle(bg, (220, 140, 80), (WIDTH // 2, int(HEIGHT * 0.22)), int(moon_r * 0.75))

    pygame.draw.rect(bg, GROUND_COLOR, (0, GROUND_Y, WIDTH, GROUND_H))
    step = int(WIDTH * 0.05)
    for x in range(-step, WIDTH + step, step):
        pygame.draw.line(bg, GROUND_LINE, (x, GROUND_Y), (x - step, HEIGHT), 2)

    return bg


BACKGROUND = make_background()


class Fighter:
    def __init__(self, x, color, controls, facing):
        self.x = x
        self.y = GROUND_Y
        self.w = FIGHTER_W
        self.h = FIGHTER_H
        self.vy = 0
        self.on_ground = True
        self.color = color
        self.controls = controls
        self.facing = facing
        self.health = 100
        self.rect = pygame.Rect(0, 0, self.w, self.h)
        self.update_rect()

    def update_rect(self):
        self.rect = pygame.Rect(
            int(self.x - self.w // 2),
            int(self.y - self.h),
            self.w, self.h
        )

    def move(self, keys, dt):
        if keys[self.controls["left"]]:
            self.x -= MOVE_SPEED * dt
        if keys[self.controls["right"]]:
            self.x += MOVE_SPEED * dt

        self.x = max(self.w // 2, min(WIDTH - self.w // 2, self.x))

        if keys[self.controls["jump"]] and self.on_ground:
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

    def draw(self, surface):
        body_rect = pygame.Rect(
            int(self.x - self.w // 2),
            int(self.y - self.h),
            self.w, self.h
        )
        pygame.draw.rect(surface, self.color, body_rect, border_radius=12)
        pygame.draw.rect(surface, (255, 255, 255), body_rect, 3, border_radius=12)

        head_center = (int(self.x), int(self.y - self.h - HEAD_RADIUS))
        pygame.draw.circle(surface, (220, 180, 140), head_center, HEAD_RADIUS)
        pygame.draw.circle(surface, (255, 255, 255), head_center, HEAD_RADIUS, 3)

        eye_dx = int(HEAD_RADIUS * 0.4) * self.facing
        eye_off = int(HEAD_RADIUS * 0.25)
        eye_r = max(3, HEAD_RADIUS // 6)
        pygame.draw.circle(surface, (20, 20, 20),
                           (head_center[0] + eye_dx, head_center[1] - eye_off), eye_r)
        pygame.draw.circle(surface, (20, 20, 20),
                           (head_center[0] + eye_dx - int(HEAD_RADIUS * 0.5),
                            head_center[1] - eye_off), eye_r)

        arm_y = int(self.y - self.h + self.h * 0.35)
        arm_len = int(self.w * 0.9)
        pygame.draw.line(surface, self.color,
                         (int(self.x), arm_y),
                         (int(self.x + self.facing * arm_len), arm_y + int(self.h * 0.08)),
                         max(8, int(self.h * 0.11)))

    def draw_health_bar(self, surface, x, y, bar_w, bar_h, align_right=False):
        pygame.draw.rect(surface, HEALTH_BG, (x, y, bar_w, bar_h), border_radius=8)
        pygame.draw.rect(surface, (100, 100, 100), (x, y, bar_w, bar_h), 3, border_radius=8)

        ratio = max(0, self.health) / 100
        fill_w = int(bar_w * ratio)

        if align_right:
            fill_rect = (x + bar_w - fill_w, y, fill_w, bar_h)
        else:
            fill_rect = (x, y, fill_w, bar_h)

        color = HEALTH_GREEN if ratio > 0.3 else HEALTH_RED
        if fill_w > 0:
            pygame.draw.rect(surface, color, fill_rect, border_radius=8)


class Fireball:
    def __init__(self, x, y, direction, color, owner):
        self.x = x
        self.y = y
        self.dir = direction
        self.color = color
        self.owner = owner
        self.radius = FIREBALL_RADIUS
        self.alive = True

    def update(self, dt):
        self.x += self.dir * FIREBALL_SPEED * dt
        if self.x < -60 or self.x > WIDTH + 60:
            self.alive = False

    def rect(self):
        return pygame.Rect(
            int(self.x - self.radius),
            int(self.y - self.radius),
            self.radius * 2, self.radius * 2
        )

    def draw(self, surface):
        pygame.draw.circle(surface, (255, 200, 100),
                           (int(self.x), int(self.y)), int(self.radius * 1.4))
        pygame.draw.circle(surface, self.color,
                           (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (255, 255, 255),
                           (int(self.x), int(self.y)), max(2, self.radius // 2))


def draw_hud(surface, p1, p2):
    margin = int(WIDTH * 0.03)
    bar_w = int(WIDTH * 0.35)
    bar_h = int(HEIGHT * 0.045)
    bar_y = int(HEIGHT * 0.04)

    p1.draw_health_bar(surface, margin, bar_y, bar_w, bar_h)
    p2.draw_health_bar(surface, WIDTH - margin - bar_w, bar_y, bar_w, bar_h, align_right=True)

    name1 = font_med.render("ИГРОК 1", True, P1_COLOR)
    name2 = font_med.render("ИГРОК 2", True, P2_COLOR)
    surface.blit(name1, (margin, bar_y + bar_h + 10))
    surface.blit(name2, (WIDTH - margin - name2.get_width(), bar_y + bar_h + 10))

    best_txt = font_small.render(f"Рекорд: {best}", True, (255, 220, 60))
    surface.blit(best_txt, (WIDTH // 2 - best_txt.get_width() // 2, bar_y + bar_h + 10))


def game_over_screen(winner):
    save_score(score)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    text = font_big.render(f"{winner} ПОБЕДИЛ!", True, (255, 220, 60))
    screen.blit(text, (WIDTH // 2 - text.get_width() // 2,
                       HEIGHT // 2 - text.get_height()))

    s = font_med.render(f"Счёт: {score}", True, TEXT_COLOR)
    screen.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2 + 20))

    b = font_med.render(f"Рекорд: {best}", True, (255, 220, 60))
    screen.blit(b, (WIDTH // 2 - b.get_width() // 2, HEIGHT // 2 + 80))

    hint = font_med.render("R — заново    ESC — выход", True, (220, 220, 220))
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 160))

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


def main():
    global score, best

    while True:
        p1 = Fighter(WIDTH * 0.25, P1_COLOR, {
            "left": pygame.K_a, "right": pygame.K_d,
            "jump": pygame.K_w, "fire": pygame.K_f
        }, facing=1)

        p2 = Fighter(WIDTH * 0.75, P2_COLOR, {
            "left": pygame.K_LEFT, "right": pygame.K_RIGHT,
            "jump": pygame.K_UP, "fire": pygame.K_RCTRL
        }, facing=-1)

        fireballs = []
        running = True
        winner = None

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
                    if event.key == p1.controls["fire"]:
                        ox, oy = p1.fire_origin()
                        fireballs.append(Fireball(ox, oy, 1, FIRE_P1, p1))
                    if event.key == p2.controls["fire"]:
                        ox, oy = p2.fire_origin()
                        fireballs.append(Fireball(ox, oy, -1, FIRE_P2, p2))

            keys = pygame.key.get_pressed()
            p1.move(keys, dt)
            p2.move(keys, dt)
            p1.apply_gravity(dt)
            p2.apply_gravity(dt)
            p1.update_rect()
            p2.update_rect()

            for fb in fireballs:
                fb.update(dt)

            for fb in fireballs:
                if not fb.alive:
                    continue
                for fighter in (p1, p2):
                    if fighter is fb.owner:
                        continue
                    if fb.rect().colliderect(fighter.rect):
                        fighter.health -= FIREBALL_DAMAGE
                        score += 5
                        if score > best:
                            best = score
                        fb.alive = False
                        if fighter.health <= 0:
                            winner = "ИГРОК 1" if fighter is p2 else "ИГРОК 2"
                            running = False

            for i in range(len(fireballs)):
                for j in range(i + 1, len(fireballs)):
                    a, b = fireballs[i], fireballs[j]
                    if a.alive and b.alive and a.owner is not b.owner:
                        if a.rect().colliderect(b.rect()):
                            a.alive = False
                            b.alive = False

            fireballs = [fb for fb in fireballs if fb.alive]

            screen.blit(BACKGROUND, (0, 0))
            p1.draw(screen)
            p2.draw(screen)
            for fb in fireballs:
                fb.draw(screen)
            draw_hud(screen, p1, p2)

            pygame.display.flip()

        if not game_over_screen(winner):
            break


if __name__ == "__main__":
    main()
