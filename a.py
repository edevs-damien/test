#!/usr/bin/env python3
"""
  ~ BUBBLE HUNT ~
  A terminal ASCII game where you guide a dolphin to eat bubbles.
  Uses only Python standard library (curses). No dependencies needed.

  Controls: Arrow keys or WASD to move | Q to quit
  Run with: python3 dolphin_game.py
"""

import curses
import random
import math
import time
import sys

# ── Dolphin sprite (right-facing) ──────────────────────────────────────────
DOLPHIN_R = [
    "    ,--/\\_   ",
    "~~~~\\     `-.",
    "~~~~/ ,' _  `",
    "~~~| /\\/ /  |",
    "~~~~\\/\\  \\  |",
    "~~~~~\\ \\  \\ |",
    "~~~~~~\\/\\__/ ",
]
DOLPHIN_L = [
    "   _/\\--,    ",
    ".-`     /~~~~",
    "`  _ ,. \\~~~~",
    "|  \\ \\/\\ |~~~",
    "|  /  /\\/~~~~",
    "| /  / /~~~~~",
    " \\__/\\/~~~~~~",
]
DOL_W = 13
DOL_H = 7

# ── Color pair IDs ─────────────────────────────────────────────────────────
C_OCEAN_DEEP  = 1
C_OCEAN_MID   = 2
C_OCEAN_SURF  = 3
C_DOLPHIN     = 4
C_WAVE        = 5
C_BUBBLE_GOOD = 6
C_BUBBLE_BIG  = 7
C_BUBBLE_BAD  = 8
C_HUD         = 9
C_HUD_VAL     = 10
C_MSG_GOOD    = 11
C_MSG_BAD     = 12
C_TITLE       = 13
C_COMBO       = 14
C_PARTICLE    = 15

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    # (pair_id, fg, bg)
    curses.init_pair(C_OCEAN_DEEP,  curses.COLOR_BLUE,    curses.COLOR_BLACK)
    curses.init_pair(C_OCEAN_MID,   curses.COLOR_CYAN,    curses.COLOR_BLACK)
    curses.init_pair(C_OCEAN_SURF,  curses.COLOR_WHITE,   curses.COLOR_BLACK)
    curses.init_pair(C_DOLPHIN,     curses.COLOR_WHITE,   curses.COLOR_BLACK)
    curses.init_pair(C_WAVE,        curses.COLOR_CYAN,    curses.COLOR_BLACK)
    curses.init_pair(C_BUBBLE_GOOD, curses.COLOR_CYAN,    curses.COLOR_BLACK)
    curses.init_pair(C_BUBBLE_BIG,  curses.COLOR_YELLOW,  curses.COLOR_BLACK)
    curses.init_pair(C_BUBBLE_BAD,  curses.COLOR_RED,     curses.COLOR_BLACK)
    curses.init_pair(C_HUD,         curses.COLOR_CYAN,    curses.COLOR_BLACK)
    curses.init_pair(C_HUD_VAL,     curses.COLOR_WHITE,   curses.COLOR_BLACK)
    curses.init_pair(C_MSG_GOOD,    curses.COLOR_YELLOW,  curses.COLOR_BLACK)
    curses.init_pair(C_MSG_BAD,     curses.COLOR_RED,     curses.COLOR_BLACK)
    curses.init_pair(C_TITLE,       curses.COLOR_CYAN,    curses.COLOR_BLACK)
    curses.init_pair(C_COMBO,       curses.COLOR_YELLOW,  curses.COLOR_BLACK)
    curses.init_pair(C_PARTICLE,    curses.COLOR_CYAN,    curses.COLOR_BLACK)


class Bubble:
    def __init__(self, cols, rows, level):
        margin = 3
        self.x = float(random.randint(margin, cols - DOL_W - margin))
        self.y = float(random.randint(2, rows - 5))
        self.poisoned = level >= 2 and random.random() < min(0.05 + level * 0.04, 0.35)
        self.big = (not self.poisoned) and random.random() < 0.18
        self.phase = random.uniform(0, math.pi * 2)
        self.vx = random.uniform(-0.15, 0.15)
        self.vy = random.uniform(-0.05, 0.05)
        self.age = 0
        self.max_age = max(120, 280 - level * 12)

    def update(self, tick):
        self.x += self.vx + math.sin(tick * 0.05 + self.phase) * 0.12
        self.y += self.vy + math.cos(tick * 0.04 + self.phase) * 0.06
        self.age += 1

    def alive(self, cols, rows):
        return (self.age < self.max_age and
                0 < self.x < cols - 2 and
                1 < self.y < rows - 2)


class Particle:
    def __init__(self, x, y, good=True):
        angle = random.uniform(0, math.pi * 2)
        spd = random.uniform(0.3, 1.8)
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle) * spd
        self.vy = math.sin(angle) * spd * 0.5
        self.life = random.randint(8, 18)
        self.ch = random.choice(['*', '.', '+', 'o', '·'])
        self.good = good

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.05
        self.life -= 1


class Game:
    def __init__(self, stdscr):
        self.scr = stdscr
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.keypad(True)
        init_colors()

        self.rows, self.cols = stdscr.getmaxyx()
        self.score = 0
        self.hi    = 0
        self.level = 1
        self.lives = 3
        self.combo = 0
        self.tick  = 0

        self.dx = 1
        self.dy = 0
        self.fx = float(self.cols // 2 - DOL_W // 2)
        self.fy = float(self.rows // 2 - DOL_H // 2)

        self.bubbles   = []
        self.particles = []

        self.msg       = ""
        self.msg_color = C_MSG_GOOD
        self.msg_timer = 0

        self.flash     = 0
        self.shake     = 0

        # spawn initial bubbles
        for _ in range(3):
            self.bubbles.append(Bubble(self.cols, self.rows, self.level))

    # ── Input ───────────────────────────────────────────────────────────────
    def handle_input(self):
        ch = self.scr.getch()
        if ch in (ord('q'), ord('Q')):
            return False
        if ch in (curses.KEY_UP,    ord('w'), ord('W')): self.dy = -1; self.dx =  0
        if ch in (curses.KEY_DOWN,  ord('s'), ord('S')): self.dy =  1; self.dx =  0
        if ch in (curses.KEY_LEFT,  ord('a'), ord('A')): self.dx = -1; self.dy =  0
        if ch in (curses.KEY_RIGHT, ord('d'), ord('D')): self.dx =  1; self.dy =  0
        return True

    # ── Update ──────────────────────────────────────────────────────────────
    def update(self):
        self.tick += 1
        if self.flash > 0: self.flash -= 1
        if self.shake > 0: self.shake -= 1
        if self.msg_timer > 0:
            self.msg_timer -= 1
            if self.msg_timer == 0:
                self.msg = ""

        # Move dolphin every 3 ticks
        if self.tick % 3 == 0:
            spd = 1.0 + (self.level - 1) * 0.3
            self.fx = max(0, min(self.cols - DOL_W - 1, self.fx + self.dx * spd))
            self.fy = max(1, min(self.rows - DOL_H - 2, self.fy + self.dy * spd))

        # Update bubbles
        dead_good = 0
        alive = []
        for b in self.bubbles:
            b.update(self.tick)
            if b.alive(self.cols, self.rows):
                alive.append(b)
            elif not b.poisoned:
                dead_good += 1
        self.bubbles = alive

        if dead_good > 0:
            self.combo = 0
            self._show_msg("missed!", C_MSG_BAD)

        # Collision: dolphin head zone
        hx = int(self.fx) + (DOL_W - 2 if self.dx >= 0 else 1)
        hy = int(self.fy) + 3
        eaten = []
        for b in self.bubbles:
            bx, by = int(b.x), int(b.y)
            if abs(hx - bx) <= 2 and abs(hy - by) <= 1:
                eaten.append(b)
        for b in eaten:
            self.bubbles.remove(b)
            if b.poisoned:
                self.lives -= 1
                self.combo  = 0
                self.shake  = 12
                for _ in range(10):
                    self.particles.append(Particle(b.x, b.y, good=False))
                self._show_msg("POISON! -1 life", C_MSG_BAD)
                if self.lives <= 0:
                    return 'dead'
            else:
                self.combo += 1
                pts = 50 if b.big else 10
                if self.combo > 3:
                    pts *= 2
                self.score += pts
                if self.score > self.hi:
                    self.hi = self.score
                self.flash = 6
                n = 16 if b.big else 8
                for _ in range(n):
                    self.particles.append(Particle(b.x, b.y, good=True))
                if self.combo > 2:
                    self._show_msg(f"COMBO x{self.combo}!", C_MSG_GOOD)
                elif b.big:
                    self._show_msg("BIG BUBBLE! +50", C_MSG_GOOD)
                else:
                    self._show_msg(f"+{pts}", C_MSG_GOOD)
                # Level up
                needed = 5 + self.level * 3
                if self.score >= needed * self.level * 10:
                    self.level += 1
                    self._show_msg(f"LEVEL {self.level}!", C_TITLE)
                    for _ in range(2):
                        self.bubbles.append(Bubble(self.cols, self.rows, self.level))

        # Update particles
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.update()

        # Auto-spawn bubbles
        max_b = 3 + self.level * 2
        interval = max(15, 70 - self.level * 7)
        if len(self.bubbles) < max_b and self.tick % interval == 0:
            self.bubbles.append(Bubble(self.cols, self.rows, self.level))

        return 'alive'

    def _show_msg(self, text, color):
        self.msg = text
        self.msg_color = color
        self.msg_timer = 60

    # ── Draw ────────────────────────────────────────────────────────────────
    def draw(self):
        self.scr.erase()
        rows, cols = self.rows, self.cols

        # Ocean background
        for y in range(1, rows - 1):
            d = y / rows
            wave = "~" * cols if y == 1 else ("~-" * (cols // 2 + 1))[:cols]
            if y == 1:
                attr = curses.color_pair(C_OCEAN_SURF)
            elif d < 0.4:
                attr = curses.color_pair(C_OCEAN_MID)
            else:
                attr = curses.color_pair(C_OCEAN_DEEP)
            # Animate wave offset
            offset = int(self.tick * 0.3 + y * 1.5) % cols
            line = wave[offset:] + wave[:offset]
            try:
                self.scr.addstr(y, 0, line[:cols], attr)
            except curses.error:
                pass

        # Particles
        for p in self.particles:
            px, py = int(p.x), int(p.y)
            if 1 <= py < rows - 1 and 0 <= px < cols:
                col = C_BUBBLE_GOOD if p.good else C_BUBBLE_BAD
                try:
                    self.scr.addch(py, px, p.ch, curses.color_pair(col))
                except curses.error:
                    pass

        # Bubbles
        for b in self.bubbles:
            bx = int(b.x + math.sin(self.tick * 0.07 + b.phase) * 0.6)
            by = int(b.y)
            if not (1 <= by < rows - 1 and 0 <= bx < cols):
                continue
            if b.poisoned:
                col = C_BUBBLE_BAD | curses.A_BOLD
                ch = '@'
                try:
                    self.scr.addch(by, bx, ch, curses.color_pair(C_BUBBLE_BAD) | curses.A_BOLD)
                    if bx + 1 < cols:
                        self.scr.addch(by, bx + 1, 'x', curses.color_pair(C_BUBBLE_BAD))
                except curses.error:
                    pass
            elif b.big:
                attr = curses.color_pair(C_BUBBLE_BIG) | curses.A_BOLD
                pulse = int(self.tick * 0.2 + b.phase) % 2
                ch = 'O' if pulse else 'o'
                try:
                    self.scr.addch(by, bx, ch, attr)
                    if bx - 1 >= 0:
                        self.scr.addch(by, bx - 1, '(', curses.color_pair(C_BUBBLE_BIG))
                    if bx + 1 < cols:
                        self.scr.addch(by, bx + 1, ')', curses.color_pair(C_BUBBLE_BIG))
                except curses.error:
                    pass
            else:
                blink = int(self.tick * 0.15 + b.phase) % 3
                ch = ['o', 'O', '0'][blink]
                try:
                    self.scr.addch(by, bx, ch,
                        curses.color_pair(C_BUBBLE_GOOD) | (curses.A_BOLD if blink == 1 else 0))
                except curses.error:
                    pass

        # Dolphin
        sprite = DOLPHIN_R if self.dx >= 0 else DOLPHIN_L
        ox = int(self.fx) + (random.randint(-1, 1) if self.shake > 0 else 0)
        oy = int(self.fy)
        for row_i, line in enumerate(sprite):
            sy = oy + row_i
            if sy < 1 or sy >= rows - 1:
                continue
            for col_i, ch in enumerate(line):
                sx = ox + col_i
                if sx < 0 or sx >= cols:
                    continue
                if ch == ' ':
                    continue
                if ch in '~-':
                    attr = curses.color_pair(C_WAVE)
                else:
                    bright = self.flash > 0
                    attr = curses.color_pair(C_DOLPHIN) | (curses.A_BOLD if bright else 0)
                try:
                    self.scr.addch(sy, sx, ch, attr)
                except curses.error:
                    pass

        # HUD bar (top)
        hud = (f" SCORE:{self.score:>5}  LEVEL:{self.level}  "
               f"LIVES:{'♥ ' * self.lives if self.lives > 0 else '☠'}  HI:{self.hi:>5} ")
        try:
            self.scr.addstr(0, 0, hud[:cols].ljust(cols),
                            curses.color_pair(C_HUD) | curses.A_BOLD)
        except curses.error:
            pass

        # Status bar (bottom)
        status = " [WASD/Arrows] move  [Q] quit  |  o=bubble  O=big(+50)  @x=POISON "
        try:
            self.scr.addstr(rows - 1, 0, status[:cols].ljust(cols),
                            curses.color_pair(C_HUD))
        except curses.error:
            pass

        # Message
        if self.msg:
            mx = max(0, cols // 2 - len(self.msg) // 2)
            my = 2
            try:
                self.scr.addstr(my, mx, self.msg,
                    curses.color_pair(self.msg_color) | curses.A_BOLD)
            except curses.error:
                pass

        self.scr.refresh()


def splash_screen(stdscr):
    rows, cols = stdscr.getmaxyx()
    stdscr.erase()
    lines = [
        ("~ BUBBLE HUNT ~",          C_TITLE,    curses.A_BOLD),
        ("",                          C_HUD,      0),
        ("Guide the dolphin to eat glowing bubbles!", C_HUD, 0),
        ("Avoid the red poison bubbles!",  C_MSG_BAD, 0),
        ("",                          C_HUD,      0),
        ("  o   = regular bubble  (+10 pts)",  C_BUBBLE_GOOD, 0),
        (" (O)  = big bubble      (+50 pts)",  C_BUBBLE_BIG,  curses.A_BOLD),
        (" @x   = POISON bubble   (-1 life)",  C_BUBBLE_BAD,  curses.A_BOLD),
        ("",                          C_HUD,      0),
        ("Combos give double points after 3 in a row!", C_COMBO, 0),
        ("",                          C_HUD,      0),
        ("Controls: Arrow keys or WASD",  C_HUD,  0),
        ("",                          C_HUD,      0),
        ("Press any key to dive in...", C_TITLE,  curses.A_BOLD),
    ]
    sy = rows // 2 - len(lines) // 2
    for i, (text, col, attr) in enumerate(lines):
        x = max(0, cols // 2 - len(text) // 2)
        try:
            stdscr.addstr(sy + i, x, text[:cols], curses.color_pair(col) | attr)
        except curses.error:
            pass
    stdscr.refresh()
    stdscr.nodelay(False)
    stdscr.getch()
    stdscr.nodelay(True)


def game_over_screen(stdscr, score, hi):
    rows, cols = stdscr.getmaxyx()
    stdscr.erase()
    lines = [
        ("~ GAME OVER ~",           C_MSG_BAD,  curses.A_BOLD),
        ("",                         C_HUD,      0),
        (f"Your score:  {score}",    C_HUD_VAL,  curses.A_BOLD),
        (f"Hi-score:    {hi}",       C_COMBO,    curses.A_BOLD),
        ("",                         C_HUD,      0),
        ("The ocean claimed another dolphin...", C_HUD, 0),
        ("",                         C_HUD,      0),
        ("Press R to play again", C_TITLE,    curses.A_BOLD),
        ("Press Q to quit",       C_HUD,      0),
    ]
    sy = rows // 2 - len(lines) // 2
    for i, (text, col, attr) in enumerate(lines):
        x = max(0, cols // 2 - len(text) // 2)
        try:
            stdscr.addstr(sy + i, x, text[:cols], curses.color_pair(col) | attr)
        except curses.error:
            pass
    stdscr.refresh()
    stdscr.nodelay(False)
    while True:
        ch = stdscr.getch()
        if ch in (ord('r'), ord('R')):
            return True
        if ch in (ord('q'), ord('Q')):
            return False


def main(stdscr):
    init_colors()
    splash_screen(stdscr)

    hi = 0
    while True:
        game = Game(stdscr)
        game.hi = hi
        running = True

        while running:
            t0 = time.monotonic()

            if not game.handle_input():
                return

            result = game.update()
            game.rows, game.cols = stdscr.getmaxyx()
            game.draw()

            if result == 'dead':
                time.sleep(0.4)
                hi = max(hi, game.score)
                play_again = game_over_screen(stdscr, game.score, hi)
                if not play_again:
                    return
                running = False

            # ~25 FPS
            elapsed = time.monotonic() - t0
            sleep = max(0, 0.04 - elapsed)
            time.sleep(sleep)


if __name__ == "__main__":
    if not sys.stdout.isatty():
        print("Please run in a terminal!")
        sys.exit(1)
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    print("\nThanks for playing Bubble Hunt! 🐬\n")