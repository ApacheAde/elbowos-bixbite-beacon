#!/usr/bin/env python3
"""Bixbite Beacon — neon lighthouse-sweep arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "BIXBITE BEACON"
HANDLE = "x.com/ElbowOS"

VOID = (6, 8, 28)
INK = (14, 16, 52)
NAVY = (22, 28, 72)
ROSE = (255, 72, 128)
BIX = (255, 36, 86)
GOLD = (255, 214, 96)
CREAM = (255, 244, 232)
CYAN = (72, 228, 255)
VIO = (168, 96, 255)
LIME = (150, 255, 120)
FOG = (40, 48, 90)


class Mote:
    __slots__ = ("x", "y", "vx", "vy", "kind", "r", "phase")

    def __init__(self, kind: str):
        self.kind = kind  # "moth" score, "bat" hazard, "buoy" bonus
        self.x = random.uniform(80, W - 80)
        self.y = random.uniform(180, 980)
        self.vx = random.uniform(-70, 70)
        self.vy = random.uniform(-36, 48)
        self.r = {"moth": 16, "bat": 18, "buoy": 20}[kind]
        self.phase = random.random() * math.tau


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, vx, vy, life, col, r=4):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.col, self.r = life, col, r


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 58)
        self.font_md = pygame.font.Font(None, 44)
        self.font_sm = pygame.font.Font(None, 30)
        self.lx, self.ly = W * 0.5, 1488
        self.reset()
        self.screen = None
        if not record:
            self.screen = pygame.display.set_mode((W, H))
            pygame.display.set_caption(TITLE)

    def reset(self) -> None:
        self.t = 0.0
        self.score = 0
        self.combo = 0
        self.ang = -math.pi / 2
        self.spin = 1.15
        self.pulse = 0.0
        self.reach = 980
        self.motes = [self._spawn(random.choice(("moth", "moth", "buoy", "bat"))) for _ in range(11)]
        self.sparks: list[Spark] = []
        self.pops: list[tuple] = []
        self.stars = [(random.randint(0, W), random.randint(0, 1400), random.random()) for _ in range(110)]
        self.running = True
        self.flash = 0.0

    def _spawn(self, kind: str) -> Mote:
        m = Mote(kind)
        m.y = random.uniform(160, 420) if random.random() < 0.55 else random.uniform(420, 1100)
        return m

    def burst(self, x, y, col, n=12) -> None:
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(80, 360)
            self.sparks.append(Spark(x, y, math.cos(a) * sp, math.sin(a) * sp,
                                     random.uniform(0.16, 0.48), col, random.randint(3, 7)))

    def in_beam(self, x, y) -> bool:
        dx, dy = x - self.lx, y - self.ly
        dist = math.hypot(dx, dy)
        if dist < 70 or dist > self.reach + self.pulse * 140:
            return False
        want = math.atan2(dy, dx)
        err = (want - self.ang + math.pi) % math.tau - math.pi
        half = 0.16 + 0.08 * self.pulse
        return abs(err) < half

    def update(self, dt: float) -> None:
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.pulse = max(0.0, self.pulse - dt * 1.6)
        self.ang += self.spin * dt
        wrap = (self.ang + math.pi) % math.tau - math.pi
        if wrap > -0.18:
            self.spin = -abs(self.spin)
        if wrap < -math.pi + 0.18:
            self.spin = abs(self.spin)
        if self.record:
            self.autoplay(dt)
        live = []
        for m in self.motes:
            m.phase += dt * 3.2
            m.x += m.vx * dt + math.sin(self.t * 1.4 + m.phase) * 18 * dt
            m.y += m.vy * dt
            if m.x < 50 or m.x > W - 50:
                m.vx *= -1
            if m.y < 140 or m.y > 1280:
                m.vy *= -1
            if self.in_beam(m.x, m.y):
                if m.kind == "bat":
                    self.combo = 0
                    self.score = max(0, self.score - 8)
                    self.burst(m.x, m.y, VIO, 10)
                    self.pops.append(("-8", m.x, m.y - 16, 0.5, VIO))
                    live.append(self._spawn("moth"))
                    continue
                self.combo += 1
                pts = (22 if m.kind == "buoy" else 10) + self.combo * 2
                self.score += pts
                self.flash = 0.12
                col = CYAN if m.kind == "buoy" else GOLD
                self.burst(m.x, m.y, col, 16)
                self.pops.append((f"+{pts}", m.x, m.y - 18, 0.55, col))
                live.append(self._spawn(random.choice(("moth", "moth", "buoy", "bat"))))
            else:
                live.append(m)
        self.motes = live
        sparks = []
        for sp in self.sparks:
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt + 30 * dt
            sp.life -= dt
            if sp.life > 0:
                sparks.append(sp)
        self.sparks = sparks[-240:]
        self.pops = [(a, x, y - 70 * dt, life - dt, c) for a, x, y, life, c in self.pops if life - dt > 0]

    def autoplay(self, dt: float) -> None:
        prey = [m for m in self.motes if m.kind != "bat"]
        if not prey:
            return
        target = min(prey, key=lambda m: abs(((math.atan2(m.y - self.ly, m.x - self.lx) - self.ang + math.pi) % math.tau) - math.pi))
        want = math.atan2(target.y - self.ly, target.x - self.lx)
        err = (want - self.ang + math.pi) % math.tau - math.pi
        self.spin += max(-2.8, min(2.8, err * 4.2)) * dt * 8
        self.spin = max(-2.2, min(2.2, self.spin))
        if abs(err) < 0.14 and self.pulse <= 0:
            self.pulse = 1.0

    def draw(self, s: pygame.Surface) -> None:
        s.fill(VOID)
        for sx, sy, tw in self.stars:
            yy = int((sy + self.t * (8 + tw * 22)) % 1400)
            c = 36 + int(tw * 90)
            pygame.draw.circle(s, (c // 2, c // 2, c), (sx, yy), 1 + int(tw * 2))
        pygame.draw.rect(s, INK, pygame.Rect(0, 1360, W, 560))
        pygame.draw.polygon(s, NAVY, [(0, 1420), (180, 1368), (420, 1410), (700, 1358), (W, 1424), (W, H), (0, H)])
        reach = self.reach + self.pulse * 160
        half = 0.17 + 0.09 * self.pulse
        pts = [(int(self.lx), int(self.ly))]
        for i in range(12):
            a = self.ang - half + (2 * half) * i / 11
            pts.append((int(self.lx + math.cos(a) * reach), int(self.ly + math.sin(a) * reach)))
        beam = pygame.Surface((W, H), pygame.SRCALPHA)
        alpha = 70 + int(70 * self.pulse)
        pygame.draw.polygon(beam, (*ROSE, alpha), pts)
        pygame.draw.polygon(beam, (*GOLD, 40 + int(50 * self.pulse)), pts, 0)
        s.blit(beam, (0, 0))
        pygame.draw.line(s, CREAM, (self.lx, self.ly),
                         (self.lx + math.cos(self.ang) * reach, self.ly + math.sin(self.ang) * reach), 3)
        for m in self.motes:
            rr = int(m.r + 2 * math.sin(m.phase))
            if m.kind == "moth":
                col = GOLD
                pygame.draw.circle(s, col, (int(m.x), int(m.y)), rr)
                pygame.draw.ellipse(s, CREAM, (int(m.x - rr - 6), int(m.y - 5), 10, 8), 1)
                pygame.draw.ellipse(s, CREAM, (int(m.x + rr - 4), int(m.y - 5), 10, 8), 1)
            elif m.kind == "buoy":
                pygame.draw.circle(s, CYAN, (int(m.x), int(m.y)), rr)
                pygame.draw.circle(s, CREAM, (int(m.x), int(m.y)), rr, 2)
                pygame.draw.circle(s, GOLD, (int(m.x), int(m.y - 4)), 4)
            else:
                pygame.draw.circle(s, VIO, (int(m.x), int(m.y)), rr)
                pygame.draw.circle(s, BIX, (int(m.x), int(m.y)), rr, 2)
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x), int(sp.y)), max(1, int(sp.r * sp.life / 0.4)))
        pygame.draw.rect(s, FOG, pygame.Rect(int(self.lx) - 28, int(self.ly) - 10, 56, 220), border_radius=8)
        pygame.draw.polygon(s, ROSE, [(self.lx - 46, self.ly + 8), (self.lx, self.ly - 58), (self.lx + 46, self.ly + 8)])
        pygame.draw.circle(s, GOLD, (int(self.lx), int(self.ly - 8)), 18)
        pygame.draw.circle(s, CREAM, (int(self.lx), int(self.ly - 8)), 8)
        pygame.draw.rect(s, BIX, pygame.Rect(int(self.lx) - 36, int(self.ly) + 200, 72, 18), border_radius=4)
        if self.flash > 0:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((255, 90, 130, int(50 * self.flash / 0.12)))
            s.blit(veil, (0, 0))
        title = self.font_lg.render(TITLE, True, ROSE)
        s.blit(title, title.get_rect(center=(W // 2, 54)))
        handle = self.font_sm.render(HANDLE, True, GOLD)
        s.blit(handle, handle.get_rect(center=(W // 2, 106)))
        s.blit(self.font_md.render(f"SCORE  {self.score}", True, GOLD), (70, 1688))
        s.blit(self.font_md.render(f"CHAIN  x{self.combo}", True, CYAN), (W - 340, 1688))
        hint = self.font_sm.render("sweep the bixbite lantern across moths & buoys", True, CREAM)
        s.blit(hint, hint.get_rect(center=(W // 2, 1760)))
        for tag, x, y, life, col in self.pops:
            img = self.font_md.render(tag, True, col)
            s.blit(img, img.get_rect(center=(int(x), int(y))))
        foot = self.font_sm.render("A/D aim  SPACE pulse  R reset  ESC quit", True, (200, 170, 190))
        s.blit(foot, foot.get_rect(center=(W // 2, H - 28)))

    def handle(self, ev) -> None:
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.running = False
            elif ev.key == pygame.K_r:
                self.reset()
            elif ev.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                self.pulse = 1.0

    def play(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                self.handle(ev)
            keys = pygame.key.get_pressed()
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                self.spin -= 3.4 * dt
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                self.spin += 3.4 * dt
            self.spin = max(-2.4, min(2.4, self.spin))
            self.update(dt)
            self.draw(self.surf)
            self.screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    play = "--play" in sys.argv
    if record or not play:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record or not play)
    if record or not play:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/BIXBITE_BEACON_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
