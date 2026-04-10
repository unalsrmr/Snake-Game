"""
╔══════════════════════════════════════════════════════╗
║           RETRO SNAKE GAME                           ║
║  CSE444 Take-Home Exam — Vibe Coding Project         ║
║  Developed with Python & PyGame                      ║
╚══════════════════════════════════════════════════════╝

Controls:
  Arrow Keys / WASD  — Move snake
  P                  — Pause / Resume
  R                  — Restart (on Game Over screen)
  ESC                — Quit
"""

import pygame
import random
import sys
import json
import os
import math

# ─────────────────────────────────────────────────────────────────
#  CONFIGURATION CONSTANTS
# ─────────────────────────────────────────────────────────────────

WIN_W, WIN_H = 800, 640      # Total window size (pixels)
HUD_H        = 60            # Top HUD bar height
GRID         = 20            # Pixel size of one grid cell
COLS         = WIN_W // GRID                  # 40 columns
ROWS         = (WIN_H - HUD_H) // GRID        # 29 rows
FPS          = 60

# ── Retro colour palette ─────────────────────────────────────────
C_BG        = (  6,  10,   6)   # Almost-black background
C_GRID      = ( 15,  24,  15)   # Subtle grid lines
C_BORDER    = (  0, 160,  45)   # Play-area border
C_HUD_BG    = (  4,   8,   4)   # HUD background
C_SNAKE_H   = ( 90, 255, 130)   # Snake head (bright green)
C_SNAKE_B   = (  0, 200,  55)   # Snake body
C_SNAKE_T   = (  0, 120,  30)   # Snake tail (darker)
C_FOOD      = (220,  40,  40)   # Normal food (red)
C_BONUS     = (255, 210,   0)   # Bonus food (gold)
C_TEXT      = (180, 255, 180)   # General text
C_DIM       = ( 80, 130,  80)   # Dimmed / hint text
C_WHITE     = (255, 255, 255)
C_RED       = (220,  40,  40)
C_YELLOW    = (255, 220,   0)

# ── Directions ───────────────────────────────────────────────────
UP    = ( 0, -1)
DOWN  = ( 0,  1)
LEFT  = (-1,  0)
RIGHT = ( 1,  0)
OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}

# ── Game states ──────────────────────────────────────────────────
MENU      = "menu"
PLAYING   = "playing"
PAUSED    = "paused"
GAME_OVER = "game_over"

# ── Gameplay balance ─────────────────────────────────────────────
BASE_SPEED      = 7       # Grid moves per second at score 0
SPEED_PER_10PTS = 0.7     # Extra moves/s gained per 10 points
MAX_SPEED       = 22.0    # Hard cap on moves/s
NORMAL_PTS      = 10      # Points for eating normal food
BONUS_PTS       = 30      # Points for eating bonus food
BONUS_TTL       = 8.0     # Seconds bonus food stays on screen
BONUS_CHANCE    = 0.25    # Probability bonus food spawns after normal food

HS_FILE = "highscore.json"

# ─────────────────────────────────────────────────────────────────
#  UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────

def load_high_score() -> int:
    """Load persisted high score from disk; return 0 if unavailable."""
    if os.path.exists(HS_FILE):
        try:
            with open(HS_FILE, "r") as f:
                data = json.load(f)
                return int(data.get("high_score", 0))
        except (json.JSONDecodeError, ValueError):
            pass
    return 0


def save_high_score(score: int) -> None:
    """Persist high score to disk."""
    with open(HS_FILE, "w") as f:
        json.dump({"high_score": score}, f)


def cell_rect(col: int, row: int, shrink: int = 1) -> pygame.Rect:
    """Return the pygame.Rect for a grid cell, with optional shrink margin."""
    x = col * GRID + shrink
    y = HUD_H + row * GRID + shrink
    size = GRID - 2 * shrink
    return pygame.Rect(x, y, size, size)


def lerp_color(c1, c2, t: float):
    """Linearly interpolate between two RGB colours."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


# ─────────────────────────────────────────────────────────────────
#  PARTICLE  (visual effect on food eaten)
# ─────────────────────────────────────────────────────────────────

class Particle:
    """A small fading square that flies outward when food is eaten."""

    def __init__(self, col: int, row: int, color):
        cx = col * GRID + GRID // 2
        cy = HUD_H + row * GRID + GRID // 2
        angle = random.uniform(0, math.tau)
        speed = random.uniform(2, 6)
        self.x  = float(cx)
        self.y  = float(cy)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.life  = 1.0           # 1.0 → 0.0
        self.decay = random.uniform(0.04, 0.08)
        self.size  = random.randint(2, 5)

    def update(self) -> bool:
        """Move and fade. Return False when particle is dead."""
        self.x    += self.vx
        self.y    += self.vy
        self.vx   *= 0.90
        self.vy   *= 0.90
        self.life -= self.decay
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha = max(0, int(self.life * 255))
        color = (*self.color, alpha)
        surf  = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        surf.fill(color)
        surface.blit(surf, (int(self.x - self.size // 2),
                             int(self.y - self.size // 2)))


# ─────────────────────────────────────────────────────────────────
#  SNAKE
# ─────────────────────────────────────────────────────────────────

class Snake:
    """
    Represents the player-controlled snake.

    Attributes
    ----------
    body       : list of (col, row) tuples, head first
    direction  : current movement direction tuple
    _queued_dir: next direction to apply on the next move tick
    alive      : False after a fatal collision
    """

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        """Place snake in the centre of the grid, facing right."""
        mid_col = COLS // 2
        mid_row = ROWS // 2
        # Start with length 3
        self.body       = [(mid_col, mid_row),
                           (mid_col - 1, mid_row),
                           (mid_col - 2, mid_row)]
        self.direction  = RIGHT
        self._queued_dir = RIGHT
        self.alive      = True

    def change_direction(self, new_dir) -> None:
        """
        Queue a direction change. Prevents 180° reversal and
        double-key buffering issues.
        """
        if new_dir != OPPOSITE.get(self.direction):
            self._queued_dir = new_dir

    def move(self) -> tuple | None:
        """
        Advance the snake by one cell.

        Returns
        -------
        The cell that was vacated (tail tip), or None on wall collision.
        Dead snakes don't move.
        """
        if not self.alive:
            return None

        # Commit queued direction
        self.direction = self._queued_dir

        head_col, head_row = self.body[0]
        dc, dr = self.direction
        new_head = (head_col + dc, head_row + dr)

        # ── Wall collision ────────────────────────────────────────
        nc, nr = new_head
        if not (0 <= nc < COLS and 0 <= nr < ROWS):
            self.alive = False
            return None

        # ── Self collision ────────────────────────────────────────
        if new_head in self.body[:-1]:   # exclude tail (it will move)
            self.alive = False
            return None

        # ── Move body ─────────────────────────────────────────────
        vacated = self.body[-1]
        self.body.insert(0, new_head)
        self.body.pop()
        return vacated

    def grow(self) -> None:
        """Extend the snake by one cell (duplicate tail)."""
        self.body.append(self.body[-1])

    @property
    def head(self) -> tuple:
        return self.body[0]

    def occupies(self, col: int, row: int) -> bool:
        return (col, row) in self.body

    def draw(self, surface: pygame.Surface) -> None:
        """Render the snake with a head-to-tail colour gradient."""
        length = len(self.body)
        for i, (col, row) in enumerate(self.body):
            t = i / max(length - 1, 1)    # 0 at head → 1 at tail
            if i == 0:
                color = C_SNAKE_H
            else:
                color = lerp_color(C_SNAKE_B, C_SNAKE_T, t)
            rect = cell_rect(col, row, shrink=1)
            pygame.draw.rect(surface, color, rect, border_radius=4)

            # Draw direction indicator on head
            if i == 0:
                eye_offset = {
                    RIGHT: (rect.right - 5, rect.centery),
                    LEFT:  (rect.left  + 5, rect.centery),
                    UP:    (rect.centerx, rect.top    + 5),
                    DOWN:  (rect.centerx, rect.bottom - 5),
                }
                ex, ey = eye_offset[self.direction]
                pygame.draw.circle(surface, C_BG, (ex, ey), 3)


# ─────────────────────────────────────────────────────────────────
#  FOOD
# ─────────────────────────────────────────────────────────────────

class Food:
    """Normal food pellet. Respawns when eaten."""

    def __init__(self, snake: Snake):
        self.col, self.row = self._spawn(snake)
        self._pulse = 0.0    # animation phase

    def _spawn(self, snake: Snake):
        """Pick a random cell not occupied by the snake."""
        all_cells = [(c, r) for c in range(COLS) for r in range(ROWS)]
        free = [cell for cell in all_cells if cell not in snake.body]
        return random.choice(free)

    def respawn(self, snake: Snake) -> None:
        self.col, self.row = self._spawn(snake)

    def update(self, dt: float) -> None:
        self._pulse = (self._pulse + dt * 4) % math.tau

    def draw(self, surface: pygame.Surface) -> None:
        scale = 0.85 + 0.15 * math.sin(self._pulse)
        shrink = int(GRID * (1 - scale) / 2) + 1
        rect = cell_rect(self.col, self.row, shrink=shrink)
        pygame.draw.rect(surface, C_FOOD, rect, border_radius=5)
        # Highlight
        hi = pygame.Rect(rect.x + 2, rect.y + 2, 4, 4)
        pygame.draw.rect(surface, (255, 140, 140), hi, border_radius=2)


class BonusFood:
    """
    Rare golden bonus food. Appears for a limited time,
    worth 3× the normal food points.
    """

    def __init__(self, snake: Snake):
        self.col, self.row = self._spawn(snake)
        self.remaining = BONUS_TTL   # seconds left
        self._pulse    = 0.0

    def _spawn(self, snake: Snake):
        all_cells = [(c, r) for c in range(COLS) for r in range(ROWS)]
        free = [cell for cell in all_cells if cell not in snake.body]
        return random.choice(free)

    def update(self, dt: float) -> bool:
        """Update timer. Return False when expired."""
        self.remaining -= dt
        self._pulse     = (self._pulse + dt * 6) % math.tau
        return self.remaining > 0

    def draw(self, surface: pygame.Surface, font_small) -> None:
        # Blink when < 3 s remain
        if self.remaining < 3.0 and int(self.remaining * 4) % 2 == 0:
            return
        scale  = 0.80 + 0.20 * abs(math.sin(self._pulse))
        shrink = int(GRID * (1 - scale) / 2) + 1
        rect   = cell_rect(self.col, self.row, shrink=max(shrink, 1))
        pygame.draw.rect(surface, C_BONUS, rect, border_radius=5)
        hi = pygame.Rect(rect.x + 2, rect.y + 2, 4, 4)
        pygame.draw.rect(surface, (255, 255, 180), hi, border_radius=2)

        # Timer label above food
        secs  = math.ceil(self.remaining)
        label = font_small.render(str(secs), True, C_BONUS)
        lx    = self.col * GRID + GRID // 2 - label.get_width() // 2
        ly    = HUD_H + self.row * GRID - 14
        surface.blit(label, (lx, ly))


# ─────────────────────────────────────────────────────────────────
#  GAME
# ─────────────────────────────────────────────────────────────────

class Game:
    """
    Central game controller. Owns the game loop, state machine,
    rendering, and event handling.

    States:
      MENU      → player not yet started
      PLAYING   → active gameplay
      PAUSED    → suspended; overlay shown
      GAME_OVER → snake has died; score displayed
    """

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("🐍  Retro Snake")
        self.screen  = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock   = pygame.time.Clock()

        # Fonts
        self.font_big   = pygame.font.SysFont("consolas",  42, bold=True)
        self.font_med   = pygame.font.SysFont("consolas",  24, bold=True)
        self.font_small = pygame.font.SysFont("consolas",  16)

        # Game objects
        self.snake      = Snake()
        self.food       = Food(self.snake)
        self.bonus_food = None        # BonusFood | None

        # State
        self.state       = MENU
        self.score       = 0
        self.high_score  = load_high_score()
        self.particles   : list[Particle] = []

        # Timing
        self._move_timer  = 0.0      # accumulated time since last move
        self._speed       = BASE_SPEED

        # Background grid surface (pre-rendered once)
        self._bg = self._make_bg()

    # ── Background ────────────────────────────────────────────────

    def _make_bg(self) -> pygame.Surface:
        """Pre-render the grid lines and border once."""
        surf = pygame.Surface((WIN_W, WIN_H))
        surf.fill(C_BG)

        # HUD area
        pygame.draw.rect(surf, C_HUD_BG, (0, 0, WIN_W, HUD_H))
        pygame.draw.line(surf, C_BORDER, (0, HUD_H), (WIN_W, HUD_H), 2)

        # Grid lines
        for c in range(COLS + 1):
            x = c * GRID
            pygame.draw.line(surf, C_GRID, (x, HUD_H), (x, WIN_H))
        for r in range(ROWS + 1):
            y = HUD_H + r * GRID
            pygame.draw.line(surf, C_GRID, (0, y), (WIN_W, y))

        # Border
        play_rect = pygame.Rect(0, HUD_H, WIN_W, WIN_H - HUD_H)
        pygame.draw.rect(surf, C_BORDER, play_rect, 2)
        return surf

    # ── Reset / New game ──────────────────────────────────────────

    def _reset(self) -> None:
        """Re-initialise all game objects for a fresh run."""
        self.snake      = Snake()
        self.food       = Food(self.snake)
        self.bonus_food = None
        self.score      = 0
        self.particles  = []
        self._move_timer = 0.0
        self._speed      = BASE_SPEED
        self.state       = PLAYING

    # ── Speed calculation ─────────────────────────────────────────

    def _calc_speed(self) -> float:
        """Return current move speed (cells/second) based on score."""
        speed = BASE_SPEED + (self.score // 10) * SPEED_PER_10PTS
        return min(speed, MAX_SPEED)

    # ── Event handling ────────────────────────────────────────────

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()

            elif event.type == pygame.KEYDOWN:
                key = event.key

                # Quit shortcut
                if key == pygame.K_ESCAPE:
                    self._quit()

                # Menu → start
                if self.state == MENU:
                    if key == pygame.K_RETURN or key == pygame.K_SPACE:
                        self._reset()

                # Playing → direction / pause
                elif self.state == PLAYING:
                    if key in (pygame.K_UP,    pygame.K_w): self.snake.change_direction(UP)
                    if key in (pygame.K_DOWN,  pygame.K_s): self.snake.change_direction(DOWN)
                    if key in (pygame.K_LEFT,  pygame.K_a): self.snake.change_direction(LEFT)
                    if key in (pygame.K_RIGHT, pygame.K_d): self.snake.change_direction(RIGHT)
                    if key == pygame.K_p: self.state = PAUSED

                # Paused → resume
                elif self.state == PAUSED:
                    if key == pygame.K_p or key == pygame.K_RETURN:
                        self.state = PLAYING

                # Game over → restart
                elif self.state == GAME_OVER:
                    if key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                        self._reset()

    # ── Update ────────────────────────────────────────────────────

    def _update(self, dt: float) -> None:
        """Advance game logic by dt seconds."""
        if self.state != PLAYING:
            return

        self._speed = self._calc_speed()

        # ── Move tick ──────────────────────────────────────────
        self._move_timer += dt
        interval = 1.0 / self._speed

        if self._move_timer >= interval:
            self._move_timer -= interval
            self._do_move()

        # ── Animate food ──────────────────────────────────────
        self.food.update(dt)

        # ── Bonus food timer ──────────────────────────────────
        if self.bonus_food is not None:
            alive = self.bonus_food.update(dt)
            if not alive:
                self.bonus_food = None

        # ── Particles ─────────────────────────────────────────
        self.particles = [p for p in self.particles if p.update()]

    def _do_move(self) -> None:
        """Execute one grid move and check collisions."""
        self.snake.move()

        if not self.snake.alive:
            # Snake died — update high score and transition
            if self.score > self.high_score:
                self.high_score = self.score
                save_high_score(self.high_score)
            self.state = GAME_OVER
            return

        head = self.snake.head

        # ── Normal food collision ──────────────────────────
        if head == (self.food.col, self.food.row):
            self.snake.grow()
            self.score += NORMAL_PTS
            self._spawn_particles(self.food.col, self.food.row, C_FOOD)
            self.food.respawn(self.snake)
            # Possibly spawn bonus food
            if self.bonus_food is None and random.random() < BONUS_CHANCE:
                self.bonus_food = BonusFood(self.snake)

        # ── Bonus food collision ───────────────────────────
        if (self.bonus_food is not None and
                head == (self.bonus_food.col, self.bonus_food.row)):
            self.snake.grow()
            self.score += BONUS_PTS
            self._spawn_particles(self.bonus_food.col,
                                  self.bonus_food.row, C_BONUS)
            self.bonus_food = None

    def _spawn_particles(self, col: int, row: int, color) -> None:
        """Create a burst of particles at a grid cell."""
        for _ in range(12):
            self.particles.append(Particle(col, row, color))

    # ── Draw ──────────────────────────────────────────────────────

    def _draw(self) -> None:
        # Background
        self.screen.blit(self._bg, (0, 0))

        # Game objects
        self.food.draw(self.screen)
        if self.bonus_food is not None:
            self.bonus_food.draw(self.screen, self.font_small)
        self.snake.draw(self.screen)

        # Particles
        for p in self.particles:
            p.draw(self.screen)

        # HUD
        self._draw_hud()

        # Overlays
        if self.state == MENU:
            self._draw_menu()
        elif self.state == PAUSED:
            self._draw_pause()
        elif self.state == GAME_OVER:
            self._draw_game_over()

        pygame.display.flip()

    def _draw_hud(self) -> None:
        """Render the top HUD bar: score, high score, speed indicator."""
        # Score
        score_surf = self.font_med.render(f"SCORE  {self.score:>6}", True, C_TEXT)
        self.screen.blit(score_surf, (16, 16))

        # High score
        hs_surf = self.font_med.render(f"BEST  {self.high_score:>6}", True, C_DIM)
        self.screen.blit(hs_surf, (WIN_W // 2 - hs_surf.get_width() // 2, 16))

        # Speed / level label
        level = int((self._speed - BASE_SPEED) / SPEED_PER_10PTS) + 1 if self.state == PLAYING else 1
        lvl_surf = self.font_med.render(f"LVL  {level:>3}", True, C_TEXT)
        self.screen.blit(lvl_surf, (WIN_W - lvl_surf.get_width() - 16, 16))

    def _draw_overlay(self, title: str, lines: list[tuple]) -> None:
        """
        Draw a semi-transparent centred overlay box.
        lines = [(text, color, font), ...]
        """
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        # Box
        box_w, box_h = 480, 60 + 38 * len(lines)
        bx = (WIN_W - box_w) // 2
        by = (WIN_H - box_h) // 2
        pygame.draw.rect(self.screen, (10, 24, 10),
                         (bx, by, box_w, box_h), border_radius=12)
        pygame.draw.rect(self.screen, C_BORDER,
                         (bx, by, box_w, box_h), 2, border_radius=12)

        # Title
        t_surf = self.font_big.render(title, True, C_SNAKE_H)
        self.screen.blit(t_surf, (WIN_W // 2 - t_surf.get_width() // 2, by + 14))

        # Lines
        for i, (text, color, font) in enumerate(lines):
            s = font.render(text, True, color)
            self.screen.blit(s, (WIN_W // 2 - s.get_width() // 2,
                                 by + 60 + i * 38))

    def _draw_menu(self) -> None:
        self._draw_overlay("RETRO SNAKE", [
            ("Use ARROW KEYS or WASD to move",   C_TEXT, self.font_small),
            ("Eat red food  (+10 pts)",           C_FOOD, self.font_small),
            ("Eat gold food (+30 pts, limited!)", C_BONUS, self.font_small),
            ("P = Pause      ESC = Quit",         C_DIM,  self.font_small),
            ("Press ENTER or SPACE to start",     C_SNAKE_H, self.font_med),
        ])

    def _draw_pause(self) -> None:
        self._draw_overlay("PAUSED", [
            ("Game is paused",            C_DIM,    self.font_small),
            ("Press P or ENTER to resume",C_SNAKE_H,self.font_med),
        ])

    def _draw_game_over(self) -> None:
        is_new_hs = self.score >= self.high_score and self.score > 0
        hs_label  = "NEW HIGH SCORE!" if is_new_hs else f"Best: {self.high_score}"
        hs_color  = C_YELLOW if is_new_hs else C_DIM
        self._draw_overlay("GAME OVER", [
            (f"Score:  {self.score}",       C_WHITE,  self.font_med),
            (hs_label,                      hs_color, self.font_med),
            ("Press R / ENTER to restart",  C_SNAKE_H,self.font_med),
            ("Press ESC to quit",           C_DIM,    self.font_small),
        ])

    # ── Main loop ─────────────────────────────────────────────────

    def run(self) -> None:
        """Start and run the game loop until the window is closed."""
        while True:
            dt = self.clock.tick(FPS) / 1000.0   # delta time in seconds
            self._handle_events()
            self._update(dt)
            self._draw()

    # ── Helpers ───────────────────────────────────────────────────

    def _quit(self) -> None:
        """Save state and exit cleanly."""
        if self.score > self.high_score:
            save_high_score(self.score)
        pygame.quit()
        sys.exit()


# ─────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    game = Game()
    game.run()
