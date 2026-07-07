"""
╔══════════════════════════════════════════════════════════════╗
║           RETRO SNAKE GAME  — v2.0 (Maintenance)            ║
║  CSE444 — Software Engineering II                           ║
║  Original: Take-Home Exam   |   Updated: Maintenance HW     ║
╚══════════════════════════════════════════════════════════════╝

Controls:
  Arrow Keys / WASD  — Move snake
  B                  — Add / Remove Robot Snake (toggle)
  P                  — Pause / Resume
  R / ENTER / SPACE  — Restart (on Game Over screen)
  ESC                — Quit

New in v2.0:
    - Multi-level difficulty with named levels (ROOKIE to GODLIKE)
    - Robot snake: wanders randomly; touch it and you die
    - Invincibility food [I] cyan   : shield from robot for 10 s
    - Poison food        [P] purple : drops up to 3 tail segments and deducts score
    - Slow-motion food   [S] orange : reduces speed to ~45% for 10 s
"""

import pygame
import random
import sys
import json
import os
import math

# =================================================================
#  CONFIGURATION CONSTANTS  (original - unchanged)
# =================================================================

WIN_W, WIN_H = 800, 640
HUD_H        = 60
GRID         = 20
COLS         = WIN_W // GRID        # 40 columns
ROWS         = (WIN_H - HUD_H) // GRID  # 29 rows
FPS          = 60

# Original retro colour palette
C_BG        = (  6,  10,   6)
C_GRID      = ( 15,  24,  15)
C_BORDER    = (  0, 160,  45)
C_HUD_BG    = (  4,   8,   4)
C_SNAKE_H   = ( 90, 255, 130)
C_SNAKE_B   = (  0, 200,  55)
C_SNAKE_T   = (  0, 120,  30)
C_FOOD      = (220,  40,  40)
C_BONUS     = (255, 210,   0)
C_TEXT      = (180, 255, 180)
C_DIM       = ( 80, 130,  80)
C_WHITE     = (255, 255, 255)
C_RED       = (220,  40,  40)
C_YELLOW    = (255, 220,   0)

# NEW v2.0 colours
C_ROBOT_H   = (220,  80,  80)
C_ROBOT_B   = (160,  40,  40)
C_ROBOT_T   = ( 90,  15,  15)
C_INVINC    = (  0, 220, 255)
C_POISON    = (180,   0, 220)
C_SLOWMO    = (255, 140,   0)

# Directions
UP    = ( 0, -1)
DOWN  = ( 0,  1)
LEFT  = (-1,  0)
RIGHT = ( 1,  0)
OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}

# Game states
MENU      = "menu"
PLAYING   = "playing"
PAUSED    = "paused"
GAME_OVER = "game_over"

# Original gameplay balance (unchanged)
BASE_SPEED      = 7
SPEED_PER_10PTS = 0.7
MAX_SPEED       = 22.0
NORMAL_PTS      = 10
BONUS_PTS       = 30
BONUS_TTL       = 8.0
BONUS_CHANCE    = 0.25

HS_FILE = "highscore.json"

# NEW v2.0 constants
ROBOT_LEN           = 5
ROBOT_SPEED_RATIO   = 0.75
ROBOT_RESPAWN_T     = 30.0
ROBOT_DIR_MIN       = 0.8
ROBOT_DIR_MAX       = 2.2

SPECIAL_CHANCE          = 0.5   # Chance to spawn a special food at each spawn check
SPECIAL_SPAWN_INTERVAL  = 5.0    # Seconds between independent special-food spawn checks
SPECIAL_TTL             = 12.0   # Special food stays visible for 12 seconds
MAX_SPECIAL_FOODS       = 3      # Maximum number of special foods active at the same time

INVINC_DURATION         = 10.0
SLOWMO_DURATION         = 10.0
SLOWMO_FACTOR           = 0.45
POISON_DROP             = 3
MIN_SNAKE_LEN           = 3

# Difficulty levels: (min_score, level_num, name, player_speed, robot_speed, colour)
# Speed increases gradually at score thresholds.
DIFFICULTY_LEVELS = [
    (   0,  1, "ROOKIE",      7.0,  3.5, (180, 255, 180)),
    (  40,  2, "TRAINEE",     7.5,  4.0, (160, 255, 160)),
    (  90,  3, "NOVICE",      8.0,  4.5, (140, 255, 140)),
    ( 150,  4, "APPRENTICE",  8.6,  5.0, (180, 255, 120)),
    ( 230,  5, "SKILLED",     9.2,  5.8, (255, 230, 100)),
    ( 330,  6, "ADVANCED",    9.9,  6.5, (255, 210,  80)),
    ( 450,  7, "EXPERT",     10.7,  7.3, (255, 180,  60)),
    ( 600,  8, "MASTER",     11.5,  8.0, (255, 140,  50)),
    ( 780,  9, "ELITE",      12.4,  8.8, (255, 100,  50)),
    (1000, 10, "LEGEND",     13.3,  9.6, (255,  70,  70)),
    (1250, 11, "MYTHIC",     14.2, 10.5, (220,  60, 220)),
    (1550, 12, "GODLIKE",    15.0, 11.5, (180,  40, 255)),
]

# How long (seconds) the level-up banner stays on screen
LEVELUP_DISPLAY = 2.2


# =================================================================
#  UTILITY FUNCTIONS  (original + one new helper)
# =================================================================

def load_high_score():
    if os.path.exists(HS_FILE):
        try:
            with open(HS_FILE, "r") as f:
                data = json.load(f)
                return int(data.get("high_score", 0))
        except (json.JSONDecodeError, ValueError):
            pass
    return 0


def save_high_score(score):
    with open(HS_FILE, "w") as f:
        json.dump({"high_score": score}, f)


def cell_rect(col, row, shrink=1):
    x    = col * GRID + shrink
    y    = HUD_H + row * GRID + shrink
    size = GRID - 2 * shrink
    return pygame.Rect(x, y, size, size)


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def free_cells(occupied):
    """All grid cells NOT in the occupied list/set."""
    occ = set(occupied)
    return [(c, r) for c in range(COLS) for r in range(ROWS) if (c, r) not in occ]


# =================================================================
#  PARTICLE  (original - unchanged)
# =================================================================

class Particle:
    def __init__(self, col, row, color):
        cx = col * GRID + GRID // 2
        cy = HUD_H + row * GRID + GRID // 2
        angle = random.uniform(0, math.tau)
        speed = random.uniform(2, 6)
        self.x     = float(cx)
        self.y     = float(cy)
        self.vx    = math.cos(angle) * speed
        self.vy    = math.sin(angle) * speed
        self.color = color
        self.life  = 1.0
        self.decay = random.uniform(0.04, 0.08)
        self.size  = random.randint(2, 5)

    def update(self):
        self.x    += self.vx
        self.y    += self.vy
        self.vx   *= 0.90
        self.vy   *= 0.90
        self.life -= self.decay
        return self.life > 0

    def draw(self, surface):
        alpha = max(0, int(self.life * 255))
        color = (*self.color, alpha)
        surf  = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        surf.fill(color)
        surface.blit(surf, (int(self.x - self.size // 2),
                             int(self.y - self.size // 2)))


# =================================================================
#  SNAKE  (original logic unchanged; draw() gains invincibility flash)
# =================================================================

class Snake:
    """
    Player-controlled snake.
    body[0] is the head; body[-1] is the tail tip.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        mid_col = COLS // 2
        mid_row = ROWS // 2
        self.body        = [(mid_col, mid_row),
                            (mid_col - 1, mid_row),
                            (mid_col - 2, mid_row)]
        self.direction   = RIGHT
        self._queued_dir = RIGHT
        self.alive       = True

    def change_direction(self, new_dir):
        if new_dir != OPPOSITE.get(self.direction):
            self._queued_dir = new_dir

    def move(self, invincible=False):
        """
        Advance one cell. Returns vacated tail cell, or None on death.
        When invincible=True:
          - Wall hit wraps to the opposite side instead of killing the snake.
          - Self-collision is ignored (snake passes through its own body).
        """
        if not self.alive:
            return None
        self.direction = self._queued_dir
        hc, hr   = self.body[0]
        dc, dr   = self.direction
        new_head = (hc + dc, hr + dr)
        nc, nr   = new_head

        # Wall collision
        if not (0 <= nc < COLS and 0 <= nr < ROWS):
            if invincible:
                nc, nr   = nc % COLS, nr % ROWS   # wrap through the wall
                new_head = (nc, nr)
            else:
                self.alive = False
                return None

        # Self collision (skipped when invincible)
        if not invincible and new_head in self.body[:-1]:
            self.alive = False
            return None

        vacated = self.body[-1]
        self.body.insert(0, new_head)
        self.body.pop()
        return vacated

    def grow(self):
        self.body.append(self.body[-1])

    @property
    def head(self):
        return self.body[0]

    def occupies(self, col, row):
        return (col, row) in self.body

    def draw(self, surface, invincible=False, flash_phase=0.0):
        """
        Render the snake with a green gradient.
        NEW v2.0: when invincible, the snake flashes cyan.
        """
        length = len(self.body)
        # Flash alternates every ~0.33 s
        use_cyan = invincible and (int(flash_phase * 3) % 2 == 0)

        for i, (col, row) in enumerate(self.body):
            t = i / max(length - 1, 1)
            if i == 0:
                color = C_INVINC if use_cyan else C_SNAKE_H
            else:
                b = C_INVINC if use_cyan else C_SNAKE_B
                color = lerp_color(b, C_SNAKE_T, t)

            rect = cell_rect(col, row, shrink=1)
            pygame.draw.rect(surface, color, rect, border_radius=4)

            if i == 0:
                eye = {
                    RIGHT: (rect.right - 5, rect.centery),
                    LEFT:  (rect.left  + 5, rect.centery),
                    UP:    (rect.centerx, rect.top    + 5),
                    DOWN:  (rect.centerx, rect.bottom - 5),
                }
                ex, ey = eye[self.direction]
                pygame.draw.circle(surface, C_BG, (ex, ey), 3)


# =================================================================
#  FOOD  (original - unchanged)
# =================================================================

class Food:
    def __init__(self, snake, extra_occupied=None):
        self._pulse = 0.0
        self.respawn(snake, extra_occupied)

    def respawn(self, snake, extra_occupied=None):
        occupied = list(snake.body)

        if extra_occupied:
            occupied.extend(extra_occupied)

        free = free_cells(occupied)

        if free:
            self.col, self.row = random.choice(free)
        else:
            self.col, self.row = 0, 0

    def update(self, dt):
        self._pulse = (self._pulse + dt * 4) % math.tau

    def draw(self, surface):
        scale  = 0.85 + 0.15 * math.sin(self._pulse)
        shrink = int(GRID * (1 - scale) / 2) + 1
        rect   = cell_rect(self.col, self.row, shrink=shrink)
        pygame.draw.rect(surface, C_FOOD, rect, border_radius=5)
        hi = pygame.Rect(rect.x + 2, rect.y + 2, 4, 4)
        pygame.draw.rect(surface, (255, 140, 140), hi, border_radius=2)


class BonusFood:
    """Timed bonus food."""

    def __init__(self, snake, extra_occupied=None):
        occupied = list(snake.body)

        if extra_occupied:
            occupied.extend(extra_occupied)

        free = free_cells(occupied)

        if free:
            self.col, self.row = random.choice(free)
        else:
            self.col, self.row = 0, 0

        self.remaining = BONUS_TTL
        self._pulse    = 0.0

    def update(self, dt):
        self.remaining -= dt
        self._pulse     = (self._pulse + dt * 6) % math.tau
        return self.remaining > 0

    def draw(self, surface, font_small):
        if self.remaining < 3.0 and int(self.remaining * 4) % 2 == 0:
            return
        scale  = 0.80 + 0.20 * abs(math.sin(self._pulse))
        shrink = max(int(GRID * (1 - scale) / 2) + 1, 1)
        rect   = cell_rect(self.col, self.row, shrink=shrink)
        pygame.draw.rect(surface, C_BONUS, rect, border_radius=5)
        hi = pygame.Rect(rect.x + 2, rect.y + 2, 4, 4)
        pygame.draw.rect(surface, (255, 255, 180), hi, border_radius=2)
        secs  = math.ceil(self.remaining)
        label = font_small.render(str(secs), True, C_BONUS)
        lx = self.col * GRID + GRID // 2 - label.get_width() // 2
        ly = HUD_H + self.row * GRID - 14
        surface.blit(label, (lx, ly))


# =================================================================
#  NEW: SPECIAL FOOD  (v2.0 maintenance feature)
# =================================================================

class SpecialFood:
    """
    Base class for the three new collectable food types added in v2.0.
    Subclasses set COLOR and SYMBOL; Game._apply_special_food() reads
    isinstance() to choose the correct effect.
    """
    COLOR  = (255, 255, 255)
    SYMBOL = "?"

    def __init__(self, snake, extra_occupied=None):
        occupied = list(snake.body)

        if extra_occupied:
            occupied.extend(extra_occupied)

        free = free_cells(occupied)

        if free:
            self.col, self.row = random.choice(free)
        else:
            self.col, self.row = 0, 0

        self.remaining = SPECIAL_TTL
        self._pulse    = 0.0

    def update(self, dt):
        """Tick timer. Returns False when expired."""
        self.remaining -= dt
        self._pulse     = (self._pulse + dt * 5) % math.tau
        return self.remaining > 0

    def draw(self, surface, font_small):
        if self.remaining < 3.0 and int(self.remaining * 4) % 2 == 0:
            return
        scale  = 0.80 + 0.20 * abs(math.sin(self._pulse))
        shrink = max(int(GRID * (1 - scale) / 2) + 1, 1)
        rect   = cell_rect(self.col, self.row, shrink=shrink)
        pygame.draw.rect(surface, self.COLOR, rect, border_radius=5)
        # Letter symbol centred in cell
        sym = font_small.render(self.SYMBOL, True, C_BG)
        sx  = self.col * GRID + GRID // 2 - sym.get_width() // 2
        sy  = HUD_H + self.row * GRID + GRID // 2 - sym.get_height() // 2
        surface.blit(sym, (sx, sy))
        # Countdown above cell
        secs  = math.ceil(self.remaining)
        timer = font_small.render(str(secs), True, self.COLOR)
        tx    = self.col * GRID + GRID // 2 - timer.get_width() // 2
        ty    = HUD_H + self.row * GRID - 14
        surface.blit(timer, (tx, ty))


class InvincibilityFood(SpecialFood):
    """Cyan [I] — grants INVINC_DURATION seconds of shield against robot."""
    COLOR  = C_INVINC
    SYMBOL = "I"


class PoisonFood(SpecialFood):
    """Purple [P] — drops POISON_DROP tail segments (never below MIN_SNAKE_LEN)."""
    COLOR  = C_POISON
    SYMBOL = "P"


class SlowMotionFood(SpecialFood):
    """Orange [S] — multiplies snake speed by SLOWMO_FACTOR for SLOWMO_DURATION s."""
    COLOR  = C_SLOWMO
    SYMBOL = "S"


# =================================================================
#  NEW: ROBOT SNAKE  (v2.0 maintenance feature)
# =================================================================

class RobotSnake:
    """
    AI snake that wanders randomly. Does NOT chase food or the player.

    Collision rules:
      Player head hits robot body  -> game over (unless player is invincible)
      Robot head hits player body  -> robot hides for ROBOT_RESPAWN_T s,
                                      then reappears in a safe spot
    """

    def __init__(self, player):
        self.hidden      = False
        self.hide_timer  = 0.0
        self._move_timer = 0.0
        self._dir_timer  = 0.0
        self.speed       = BASE_SPEED * ROBOT_SPEED_RATIO
        self._place(player)

    def _place(self, player):
        """Spawn robot diagonally opposite the player to avoid immediate contact."""
        phc, phr = player.head
        sc = (COLS - 6) if phc < COLS // 2 else 5
        sr = (ROWS - 6) if phr < ROWS // 2 else 5
        sc = max(ROBOT_LEN, min(sc, COLS - ROBOT_LEN - 1))
        sr = max(0, min(sr, ROWS - 1))
        self.body      = [(sc - i, sr) for i in range(ROBOT_LEN)]
        self.direction = RIGHT
        self._dir_timer = random.uniform(ROBOT_DIR_MIN, ROBOT_DIR_MAX)

    def _pick_safe_direction(self):
        """Choose a random wall-safe direction; no U-turns."""
        hc, hr  = self.body[0]
        options = []
        for d in [UP, DOWN, LEFT, RIGHT]:
            if d == OPPOSITE.get(self.direction):
                continue
            nc, nr = hc + d[0], hr + d[1]
            if 0 <= nc < COLS and 0 <= nr < ROWS:
                options.append(d)
        if options:
            self.direction = random.choice(options)

    def update(self, dt, player):
        """Full update: handle hiding countdown OR move the robot."""
        if self.hidden:
            self.hide_timer -= dt
            if self.hide_timer <= 0:
                self.hidden    = False
                self.hide_timer = 0.0
                self._place(player)
            return

        # Random direction change
        self._dir_timer -= dt
        if self._dir_timer <= 0:
            self._pick_safe_direction()
            self._dir_timer = random.uniform(ROBOT_DIR_MIN, ROBOT_DIR_MAX)

        # Move on robot's own tick
        self._move_timer += dt
        if self._move_timer >= 1.0 / self.speed:
            self._move_timer -= 1.0 / self.speed
            self._step(player)

    def _step(self, player):
        """Move robot one cell forward."""
        hc, hr   = self.body[0]
        dc, dr   = self.direction
        new_head = (hc + dc, hr + dr)
        nc, nr   = new_head

        # Hit a wall -> pick new direction, retry once
        if not (0 <= nc < COLS and 0 <= nr < ROWS):
            self._pick_safe_direction()
            dc, dr   = self.direction
            new_head = (hc + dc, hr + dr)
            nc, nr   = new_head
            if not (0 <= nc < COLS and 0 <= nr < ROWS):
                return   # completely cornered, skip tick

        # Robot head hits player body -> robot hides
        if new_head in player.body:
            self.hidden    = True
            self.hide_timer = ROBOT_RESPAWN_T
            return

        self.body.insert(0, new_head)
        self.body.pop()

    def player_collision(self, player):
        """True if the player head is inside the robot body."""
        if self.hidden:
            return False
        return player.head in self.body

    def draw(self, surface):
        if self.hidden:
            return
        length = len(self.body)
        for i, (col, row) in enumerate(self.body):
            t     = i / max(length - 1, 1)
            color = C_ROBOT_H if i == 0 else lerp_color(C_ROBOT_B, C_ROBOT_T, t)
            rect  = cell_rect(col, row, shrink=1)
            pygame.draw.rect(surface, color, rect, border_radius=4)
            if i == 0:
                eye = {
                    RIGHT: (rect.right - 5, rect.centery),
                    LEFT:  (rect.left  + 5, rect.centery),
                    UP:    (rect.centerx, rect.top    + 5),
                    DOWN:  (rect.centerx, rect.bottom - 5),
                }
                ex, ey = eye.get(self.direction, (rect.centerx, rect.centery))
                pygame.draw.circle(surface, C_BG, (ex, ey), 3)


# =================================================================
#  GAME  (original structure; new sections clearly labelled)
# =================================================================

class Game:
    """
    Central game controller. Owns the game loop, state machine,
    rendering, and all event handling.

    States: MENU -> PLAYING -> PAUSED -> GAME_OVER
    """

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Snake v2.0  |  CSE444 Maintenance")
        self.screen  = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock   = pygame.time.Clock()

        # Fonts (unchanged)
        self.font_big   = pygame.font.SysFont("consolas", 42, bold=True)
        self.font_med   = pygame.font.SysFont("consolas", 24, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 16)

        # Original game objects
        self.snake      = Snake()
        self.food       = Food(self.snake)
        self.bonus_food = None

        # State
        self.state      = MENU
        self.score      = 0
        self.high_score = load_high_score()
        self.particles  = []

        # Timing
        self._move_timer = 0.0
        self._speed      = BASE_SPEED

        # NEW v2.0: effect timers
        self.invincible_timer = 0.0
        self.slowmo_timer     = 0.0
        self._flash_phase     = 0.0   # drives cyan flash animation
        # NEW v2.0: new entities (set properly in _reset)
        self.robot          = None
        self.special_foods  = []   # Multiple special foods can exist at the same time

        # Independent special-food spawn timer.
        # Special foods are no longer dependent on eating normal red food.
        self._special_spawn_timer = SPECIAL_SPAWN_INTERVAL

        # Robot toggle: persists across restarts so the user's choice is kept
        self.robot_enabled = False   # off by default; B key toggles

        # Level-up banner state (persists only for display; reset each game)
        self._prev_level    = 1      # tracks last known level to detect changes
        self._levelup_timer = 0.0    # counts down after a level-up event
        self._levelup_name  = ""     # name of the new level to display

        # Pre-rendered static background
        self._bg = self._make_bg()

    def _relocate_foods_if_needed(self):
        """
        Reposition foods if they overlap with the robot, snake, or other foods.
        Useful after the robot is added during gameplay.
        """

        occupied_by_snakes = list(self.snake.body)

        if self.robot is not None and not self.robot.hidden:
            occupied_by_snakes.extend(self.robot.body)

        # Normal food must not be on a snake.
        if (self.food.col, self.food.row) in occupied_by_snakes:
            self.food.respawn(self.snake, self._food_blockers(include_normal=False))

        # Bonus food must not be on a snake or normal food.
        if self.bonus_food is not None:
            bonus_pos = (self.bonus_food.col, self.bonus_food.row)
            blockers = occupied_by_snakes + [(self.food.col, self.food.row)]

            if bonus_pos in blockers:
                self.bonus_food = BonusFood(self.snake, self._food_blockers(
                    include_bonus=False
                ))

        # Special foods must not be on snakes or other foods.
        for food in self.special_foods[:]:
            food_pos = (food.col, food.row)

            blockers = occupied_by_snakes + [
                (self.food.col, self.food.row)
            ]

            if self.bonus_food is not None:
                blockers.append((self.bonus_food.col, self.bonus_food.row))

            for other in self.special_foods:
                if other is not food:
                    blockers.append((other.col, other.row))

            if food_pos in blockers:
                self.special_foods.remove(food)
    # -- Background (unchanged) -----------------------------------

    def _make_bg(self):
        surf = pygame.Surface((WIN_W, WIN_H))
        surf.fill(C_BG)
        pygame.draw.rect(surf, C_HUD_BG, (0, 0, WIN_W, HUD_H))
        pygame.draw.line(surf, C_BORDER, (0, HUD_H), (WIN_W, HUD_H), 2)
        for c in range(COLS + 1):
            pygame.draw.line(surf, C_GRID, (c * GRID, HUD_H), (c * GRID, WIN_H))
        for r in range(ROWS + 1):
            y = HUD_H + r * GRID
            pygame.draw.line(surf, C_GRID, (0, y), (WIN_W, y))
        pygame.draw.rect(surf, C_BORDER,
                         pygame.Rect(0, HUD_H, WIN_W, WIN_H - HUD_H), 2)
        return surf

    # -- Reset (extended for v2.0) --------------------------------

    def _reset(self):
        self.snake        = Snake()
        self.bonus_food   = None
        self.special_foods = []
        self.score        = 0
        self.particles    = []
        self._move_timer  = 0.0
        self._speed       = BASE_SPEED
        self.state        = PLAYING

        # NEW v2.0
        self.invincible_timer = 0.0
        self.slowmo_timer     = 0.0
        self._flash_phase     = 0.0

        # Spawn robot first, then spawn food while avoiding robot body.
        self.robot = RobotSnake(self.snake) if self.robot_enabled else None
        self.food  = Food(self.snake, self._food_blockers(
            include_normal=False,
            include_bonus=True,
            include_specials=True
        ))

        self._special_spawn_timer = 2.0

        self._prev_level      = 1
        self._levelup_timer   = 0.0
        self._levelup_name    = ""

    # -- Difficulty / speed ------------------------------------------

    def _get_difficulty(self):
        """
        Scan DIFFICULTY_LEVELS and return a tuple for the highest threshold
        the current score has reached:
          (level_num, name, player_speed, robot_speed, colour)
        """
        current = DIFFICULTY_LEVELS[0]
        for entry in DIFFICULTY_LEVELS:
            if self.score >= entry[0]:
                current = entry
        _, level_num, name, player_speed, robot_speed, colour = current
        return level_num, name, player_speed, robot_speed, colour

    def _calc_speed(self):
        """
        Return player move speed (cells/second) for the current score.
        Speed steps up only at level thresholds — no per-food micro-jumps.
        Slow-motion food halves the level speed while active.
        """
        _, _, speed, _, _ = self._get_difficulty()
        if self.slowmo_timer > 0:
            speed *= SLOWMO_FACTOR
        return speed

    def _level_progress(self):
        """
        Return (fraction, next_score) for the HUD progress bar.
        fraction  : 0.0–1.0 progress toward the next level threshold.
        next_score: score needed for the next level (None if at max level).
        """

        current_index = 0

        for i, entry in enumerate(DIFFICULTY_LEVELS):
            if self.score >= entry[0]:
                current_index = i
            else:
                break

        current_min = DIFFICULTY_LEVELS[current_index][0]

        # If this is the last level, there is no next level.
        if current_index >= len(DIFFICULTY_LEVELS) - 1:
            return 1.0, None

        next_min = DIFFICULTY_LEVELS[current_index + 1][0]
        span = next_min - current_min

        # Safety guard: prevents ZeroDivisionError if thresholds are duplicated.
        if span <= 0:
            return 1.0, None

        fraction = (self.score - current_min) / span
        fraction = max(0.0, min(1.0, fraction))

        return fraction, next_min
    # -- Event handling (unchanged core logic) --------------------

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            elif event.type == pygame.KEYDOWN:
                key = event.key
                if key == pygame.K_ESCAPE:
                    self._quit()
                if self.state == MENU:
                    if key in (pygame.K_RETURN, pygame.K_SPACE):
                        self._reset()
                    if key == pygame.K_b:           # toggle before starting
                        self.robot_enabled = not self.robot_enabled
                elif self.state == PLAYING:
                    if key in (pygame.K_UP,    pygame.K_w): self.snake.change_direction(UP)
                    if key in (pygame.K_DOWN,  pygame.K_s): self.snake.change_direction(DOWN)
                    if key in (pygame.K_LEFT,  pygame.K_a): self.snake.change_direction(LEFT)
                    if key in (pygame.K_RIGHT, pygame.K_d): self.snake.change_direction(RIGHT)
                    if key == pygame.K_p: self.state = PAUSED
                    if key == pygame.K_b:           # toggle mid-game
                        self.robot_enabled = not self.robot_enabled
                        if self.robot_enabled:
                            self.robot = RobotSnake(self.snake)   # spawn immediately

                            # Reposition foods if the new robot spawned on top of them.
                            self._relocate_foods_if_needed()
                        else:
                            self.robot = None                     # remove immediately
                elif self.state == PAUSED:
                    if key in (pygame.K_p, pygame.K_RETURN):
                        self.state = PLAYING
                elif self.state == GAME_OVER:
                    if key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                        self._reset()

    # -- Update (extended for v2.0) -------------------------------

    def _update(self, dt):
        if self.state != PLAYING:
            return

        self._speed = self._calc_speed()

        # Move tick (unchanged)
        self._move_timer += dt
        if self._move_timer >= 1.0 / self._speed:
            self._move_timer -= 1.0 / self._speed
            self._do_move()

        # Animate food (unchanged)
        self.food.update(dt)

        # Bonus food timer (unchanged)
        if self.bonus_food is not None:
            if not self.bonus_food.update(dt):
                self.bonus_food = None

        # Particles (unchanged)
        self.particles = [p for p in self.particles if p.update()]

        # NEW v2.0: robot snake — update movement and sync speed to current level
        if self.robot is not None:
            _, _, _, robot_speed, _ = self._get_difficulty()
            self.robot.speed = robot_speed          # live speed sync per level
            self.robot.update(dt, self.snake)

            # Robot can eat foods if it randomly moves onto them.
            self._robot_eat_foods()

        # NEW v2.0: special food lifetime timers
        for food in self.special_foods[:]:
            if not food.update(dt):
                self.special_foods.remove(food)

        # NEW v2.0: independent special food spawning
        # Special foods can appear even if the player does not eat normal red food.
        self._special_spawn_timer -= dt
        if self._special_spawn_timer <= 0:
            self._special_spawn_timer = SPECIAL_SPAWN_INTERVAL
            self._try_spawn_special_food()

        # NEW v2.0: effect countdown timers
        if self.invincible_timer > 0:
            self.invincible_timer = max(0.0, self.invincible_timer - dt)
            self._flash_phase     = (self._flash_phase + dt) % 1.0
        if self.slowmo_timer > 0:
            self.slowmo_timer = max(0.0, self.slowmo_timer - dt)

        # NEW v2.0: level-up detection — trigger banner when level number changes
        lvl_num, lvl_name, _, _, _ = self._get_difficulty()
        if lvl_num > self._prev_level:
            self._prev_level    = lvl_num
            self._levelup_timer = LEVELUP_DISPLAY
            self._levelup_name  = lvl_name
        if self._levelup_timer > 0:
            self._levelup_timer = max(0.0, self._levelup_timer - dt)

    # -- Do-move (extended: robot + special food collisions) ------

    def _do_move(self):
        # Player snake moves; pass invincibility so walls wrap and self-hit is ignored
        self.snake.move(invincible=self.invincible_timer > 0)

        if not self.snake.alive:
            self._trigger_game_over()
            return

        head = self.snake.head

        # NEW v2.0: player walks into robot -> game over (skip if invincible)
        if (self.robot is not None
                and not self.robot.hidden
                and self.invincible_timer <= 0
                and self.robot.player_collision(self.snake)):
            self._trigger_game_over()
            return

        # Normal food: +1 segment, +10 points
        if head == (self.food.col, self.food.row):
            self.snake.grow()
            self.score += NORMAL_PTS
            self._spawn_particles(self.food.col, self.food.row, C_FOOD)

            self.food.respawn(self.snake, self._food_blockers(
                include_normal=False,
                include_bonus=True,
                include_specials=True
            ))

            if self.bonus_food is None and random.random() < BONUS_CHANCE:
                self.bonus_food = BonusFood(self.snake, self._food_blockers(
                    include_normal=True,
                    include_bonus=False,
                    include_specials=True
        ))

        # Bonus food: +3 segments, +30 points
        if (self.bonus_food is not None
                and head == (self.bonus_food.col, self.bonus_food.row)):
            for _ in range(3):
                self.snake.grow()

            self.score += BONUS_PTS
            self._spawn_particles(self.bonus_food.col, self.bonus_food.row, C_BONUS)
            self.bonus_food = None

        # NEW v2.0: special foods
        for food in self.special_foods[:]:
            if head == (food.col, food.row):
                self._apply_special_food(food)
                self._spawn_particles(food.col, food.row, food.COLOR)
                self.special_foods.remove(food)
                break

    def _apply_special_food(self, food):
        """Apply the consumed special food's effect to the game state."""
        if isinstance(food, InvincibilityFood):
            self.invincible_timer = INVINC_DURATION
            self._flash_phase     = 0.0

        elif isinstance(food, PoisonFood):
            # Poison removes up to POISON_DROP tail segments,
            # but never reduces the snake below MIN_SNAKE_LEN.
            drop = min(POISON_DROP, len(self.snake.body) - MIN_SNAKE_LEN)
            removed_segments = max(0, drop)

            for _ in range(removed_segments):
                self.snake.body.pop()

            # Each lost segment equals -10 points.
            # Example: 3 removed segments -> -30 points.
            score_loss = removed_segments * NORMAL_PTS
            self.score = max(0, self.score - score_loss)

            # Re-sync current level after score loss.
            self._prev_level = self._get_difficulty()[0]

        elif isinstance(food, SlowMotionFood):
            self.slowmo_timer = SLOWMO_DURATION

    def _trigger_game_over(self):
        """Shared transition to GAME_OVER; updates high score."""
        if self.score > self.high_score:
            self.high_score = self.score
            save_high_score(self.high_score)
        self.state = GAME_OVER
    def _food_blockers(self,
                    include_normal=True,
                    include_bonus=True,
                    include_specials=True):
        """
        Return all occupied cells that a newly spawned food must avoid.
        This includes the robot snake and all existing food objects.
        The player snake body is already handled inside Food/BonusFood/SpecialFood.
        """

        blockers = []

        # Avoid robot snake body.
        if self.robot is not None and not self.robot.hidden:
            blockers.extend(self.robot.body)

        # Avoid normal red food.
        if include_normal and self.food is not None:
            blockers.append((self.food.col, self.food.row))

        # Avoid bonus gold food.
        if include_bonus and self.bonus_food is not None:
            blockers.append((self.bonus_food.col, self.bonus_food.row))

        # Avoid all active special foods.
        if include_specials:
            for food in self.special_foods:
                blockers.append((food.col, food.row))

        return blockers
    def _try_spawn_special_food(self):
        """
        Try to spawn one special food independently of normal food consumption.
        Multiple special foods can be active at the same time, up to MAX_SPECIAL_FOODS.
        """

        if len(self.special_foods) >= MAX_SPECIAL_FOODS:
            return

        if random.random() >= SPECIAL_CHANCE:
            return

        cls = random.choice([InvincibilityFood, PoisonFood, SlowMotionFood])

        self.special_foods.append(cls(self.snake, self._food_blockers(
            include_normal=True,
            include_bonus=True,
            include_specials=True
        )))
        
    def _robot_eat_foods(self):
        """
        Let the robot snake consume food objects when its head moves onto them.
        The robot does not gain score and does not receive special effects.
        """

        if self.robot is None or self.robot.hidden:
            return

        robot_head = self.robot.body[0]

        # Robot eats normal red food:
        # food is consumed and respawned somewhere else.
        if robot_head == (self.food.col, self.food.row):
            self._spawn_particles(self.food.col, self.food.row, C_FOOD)

            self.food.respawn(self.snake, self._food_blockers(
                include_normal=False,
                include_bonus=True,
                include_specials=True
            ))

        # Robot eats bonus gold food:
        # bonus food disappears.
        if (self.bonus_food is not None
                and robot_head == (self.bonus_food.col, self.bonus_food.row)):
            self._spawn_particles(self.bonus_food.col, self.bonus_food.row, C_BONUS)
            self.bonus_food = None

        # Robot eats special foods:
        # special food disappears, but robot does not gain its effect.
        for food in self.special_foods[:]:
            if robot_head == (food.col, food.row):
                self._spawn_particles(food.col, food.row, food.COLOR)
                self.special_foods.remove(food)
                break
    def _spawn_particles(self, col, row, color):
        for _ in range(12):
            self.particles.append(Particle(col, row, color))

    # -- Draw (extended for new entities) -------------------------

    def _draw(self):
        self.screen.blit(self._bg, (0, 0))

        # Food (unchanged)
        self.food.draw(self.screen)
        if self.bonus_food is not None:
            self.bonus_food.draw(self.screen, self.font_small)

        # NEW v2.0: special foods
        for food in self.special_foods:
            food.draw(self.screen, self.font_small)

        # NEW v2.0: robot snake (drawn before player so player appears on top)
        if self.robot is not None:
            self.robot.draw(self.screen)

        # Player snake (now passes invincibility info for flash)
        self.snake.draw(self.screen,
                        invincible=self.invincible_timer > 0,
                        flash_phase=self._flash_phase)

        # Particles
        for p in self.particles:
            p.draw(self.screen)

        self._draw_hud()

        if self.state == MENU:        self._draw_menu()
        elif self.state == PAUSED:    self._draw_pause()
        elif self.state == GAME_OVER: self._draw_game_over()

        # Level-up banner drawn last so it appears on top of everything
        if self._levelup_timer > 0:
            self._draw_levelup_banner()

        pygame.display.flip()

    # -- HUD (extended: named levels + progress bar + effect badges) --

    def _draw_hud(self):
        """
        HUD layout (60 px tall):
          y= 6  Row 1 : SCORE  |  BEST  |  L# NAME  →nextscore
          y=30  Progress bar (4px) toward next level
          y=40  Row 2 : effect badges (left)  |  [B] ROBOT ON/OFF (right)
        """
        lvl_num, lvl_name, _, _, lvl_col = self._get_difficulty()
        frac, next_score = self._level_progress()

        # ── Row 1 ────────────────────────────────────────────────
        score_surf = self.font_med.render(f"SCORE {self.score:>5}", True, C_TEXT)
        self.screen.blit(score_surf, (16, 6))

        hs_surf = self.font_med.render(f"BEST {self.high_score:>5}", True, C_DIM)
        self.screen.blit(hs_surf, (WIN_W // 2 - hs_surf.get_width() // 2, 6))

        # Level name + "→next" on the same right-side slot
        if next_score is not None:
            lvl_text = f"L{lvl_num} {lvl_name}  \u2192{next_score}"
        else:
            lvl_text = f"L{lvl_num} {lvl_name}  MAX"
        lvl_surf = self.font_med.render(lvl_text, True, lvl_col)
        self.screen.blit(lvl_surf, (WIN_W - lvl_surf.get_width() - 14, 6))

        # ── Progress bar ─────────────────────────────────────────
        bar_x, bar_y, bar_h = 16, 30, 4
        bar_w = WIN_W - 32
        pygame.draw.rect(self.screen, (25, 45, 25), (bar_x, bar_y, bar_w, bar_h))
        fill_w = int(bar_w * min(frac, 1.0))
        pygame.draw.rect(self.screen, lvl_col,      (bar_x, bar_y, fill_w, bar_h))

        # ── Row 2: effect badges (left) ───────────────────────────
        x = 16
        if self.invincible_timer > 0:
            t = self.font_small.render(
                f"SHIELD {self.invincible_timer:.0f}s", True, C_INVINC)
            self.screen.blit(t, (x, 40))
            x += t.get_width() + 12
        if self.slowmo_timer > 0:
            t = self.font_small.render(
                f"SLOW {self.slowmo_timer:.0f}s", True, C_SLOWMO)
            self.screen.blit(t, (x, 40))
            x += t.get_width() + 12
        if self.robot is not None and self.robot.hidden:
            t = self.font_small.render(
                f"ROBOT {self.robot.hide_timer:.0f}s", True, C_ROBOT_H)
            self.screen.blit(t, (x, 40))

        # ── Row 2: robot toggle (right) ───────────────────────────
        if self.state == PLAYING:
            if self.robot_enabled:
                rb = self.font_small.render("[B] ROBOT ON",  True, C_ROBOT_H)
            else:
                rb = self.font_small.render("[B] ROBOT OFF", True, C_DIM)
            self.screen.blit(rb, (WIN_W - rb.get_width() - 14, 40))

    # -- Level-up banner -------------------------------------------

    def _draw_levelup_banner(self):
        """
        Fading centred banner that appears for LEVELUP_DISPLAY seconds
        whenever the player crosses a level threshold.
        Fade-out starts in the last 0.6 s of the timer.
        """
        fade_start = 0.6
        if self._levelup_timer <= fade_start:
            alpha = int(255 * (self._levelup_timer / fade_start))
        else:
            alpha = 255

        # Find the colour of the new level
        _, _, _, _, lvl_col = self._get_difficulty()

        banner = pygame.Surface((WIN_W, 54), pygame.SRCALPHA)
        banner.fill((0, 0, 0, min(alpha, 160)))
        self.screen.blit(banner, (0, WIN_H // 2 - 27))

        title = self.font_big.render("LEVEL UP!", True, (*C_SNAKE_H, alpha))
        sub   = self.font_med.render(
            f">>> {self._levelup_name} <<<", True, (*lvl_col, alpha))
        self.screen.blit(title,
            (WIN_W // 2 - title.get_width() // 2, WIN_H // 2 - 48))
        self.screen.blit(sub,
            (WIN_W // 2 - sub.get_width()  // 2, WIN_H // 2 +  4))

    # -- Overlays -------------------------------------------------

    def _draw_overlay(self, title, lines):
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        box_w = 520
        box_h = 60 + 38 * len(lines)
        bx = (WIN_W - box_w) // 2
        by = (WIN_H - box_h) // 2
        pygame.draw.rect(self.screen, (10, 24, 10),
                         (bx, by, box_w, box_h), border_radius=12)
        pygame.draw.rect(self.screen, C_BORDER,
                         (bx, by, box_w, box_h), 2, border_radius=12)
        t_surf = self.font_big.render(title, True, C_SNAKE_H)
        self.screen.blit(t_surf, (WIN_W // 2 - t_surf.get_width() // 2, by + 14))
        for i, (text, color, font) in enumerate(lines):
            s = font.render(text, True, color)
            self.screen.blit(s, (WIN_W // 2 - s.get_width() // 2,
                                 by + 60 + i * 38))

    def _draw_menu(self):
        robot_line = (
            "B = Remove Robot Snake" if self.robot_enabled else "B = Add Robot Snake",
            C_ROBOT_H if self.robot_enabled else C_DIM,
            self.font_small
        )
        self._draw_overlay("RETRO SNAKE v2", [
            ("Arrow Keys / WASD to move",           C_TEXT,    self.font_small),
            ("Red +10 pts / +1 seg ",             C_FOOD,    self.font_small),
            ("Gold +30 pts / +3 seg",C_BONUS,self.font_small),
            ("[I] Cyan   = Shield from robot (10s)", C_INVINC,  self.font_small),
            ("[P] Purple = Poison -30 pts / -3 seg", C_POISON,  self.font_small),
            ("[S] Orange = Slow-motion (10s)",       C_SLOWMO,  self.font_small),
            robot_line,
            ("P = Pause     ESC = Quit",             C_DIM,     self.font_small),
            ("Press ENTER or SPACE to start",        C_SNAKE_H, self.font_med),
        ])

    def _draw_pause(self):
        self._draw_overlay("PAUSED", [
            ("Game is paused",             C_DIM,    self.font_small),
            ("Press P or ENTER to resume", C_SNAKE_H,self.font_med),
        ])

    def _draw_game_over(self):
        is_new_hs = self.score >= self.high_score and self.score > 0
        hs_label  = "NEW HIGH SCORE!" if is_new_hs else f"Best: {self.high_score}"
        hs_color  = C_YELLOW if is_new_hs else C_DIM
        self._draw_overlay("GAME OVER", [
            (f"Score:  {self.score}",       C_WHITE,   self.font_med),
            (hs_label,                      hs_color,  self.font_med),
            ("Press R / ENTER to restart",  C_SNAKE_H, self.font_med),
            ("Press ESC to quit",           C_DIM,     self.font_small),
        ])

    # -- Main loop (unchanged) ------------------------------------

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()

    def _quit(self):
        if self.score > self.high_score:
            save_high_score(self.score)
        pygame.quit()
        sys.exit()


# =================================================================
#  ENTRY POINT
# =================================================================

if __name__ == "__main__":
    game = Game()
    game.run()