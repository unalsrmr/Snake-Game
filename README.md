# 🐍 Retro Snake Game — v2.0 (Maintenance Release)

A feature-rich retro Snake game built with **Python 3** and **PyGame 2.x**.

> 🎨 **Built with vibe coding** — this project was developed through an iterative, AI-assisted coding process rather than a traditional spec-first workflow.

---

## Requirements

- Python 3.10 or newer
- PyGame 2.x

## Installation

```bash
pip install pygame
```

## How to Run

```bash
python snake_game.py
```

---

## Controls

| Key | Action |
|---|---|
| `Arrow Keys` / `W A S D` | Move the snake |
| `B` | Add / Remove Robot Snake (toggle, works in menu and during play) |
| `P` | Pause / Resume |
| `R` / `Enter` / `Space` | Restart (Game Over screen) |
| `ESC` | Quit |

---

## Original Features (v1.0)

- Grid-based Snake on a 40×29 cell board
- Normal red food: **+10 points**, +1 segment
- Timed bonus gold food: **+30 points**, time-limited
- Progressive speed increase in the original version
- Particle burst effects and colour-gradient snake body
- Pause screen, Game Over screen, Main Menu
- Persistent high score saved to `highscore.json`

---

## Maintenance Features (v2.0)

### 🎚️ Multi-Level Difficulty (12 Levels)

Bonus gold food was updated in v2.0 to give **+30 points** and +3 segments.
Both player speed and robot speed increase at score thresholds.
Level name and a progress bar toward the next level are shown in the HUD.
A **LEVEL UP!** banner flashes on screen when a new level is reached.

| Level | Name | Score | Player spd | Robot spd |
|---|---|---|---|---|
| L1  | ROOKIE      |    0 | 7.0  | 3.5  |
| L2  | TRAINEE     |   40 | 7.5  | 4.0  |
| L3  | NOVICE      |   90 | 8.0  | 4.5  |
| L4  | APPRENTICE  |  150 | 8.6  | 5.0  |
| L5  | SKILLED     |  230 | 9.2  | 5.8  |
| L6  | ADVANCED    |  330 | 9.9  | 6.5  |
| L7  | EXPERT      |  450 | 10.7 | 7.3  |
| L8  | MASTER      |  600 | 11.5 | 8.0  |
| L9  | ELITE       |  780 | 12.4 | 8.8  |
| L10 | LEGEND      | 1000 | 13.3 | 9.6  |
| L11 | MYTHIC      | 1250 | 14.2 | 10.5 |
| L12 | GODLIKE     | 1550 | 15.0 | 11.5 |

### 🤖 Robot Snake

Press **B** to toggle the robot snake on or off at any time (even mid-game).

| Event | Outcome |
|---|---|
| Your head hits robot body | **Game Over** (unless invincible) |
| Robot head hits your body | Robot disappears for **30 seconds**, then respawns |
| HUD shows | `ROBOT Xs` countdown while robot is hidden |
| Robot moves onto normal red food | Normal food is consumed and respawns; robot gains no score or effect |
| Robot moves onto bonus or special food | The food disappears; robot gains no score or effect |

### ✨ Special Food System

Special foods spawn **independently** on a timer (every ~5 seconds, 50% chance per check).
Up to **3 special foods** can be active simultaneously.
All food spawns avoid every snake body, robot body, and other food positions.

| Icon | Colour | Effect |
|---|---|---|
| **[I]** | Cyan | **Invincibility** 10 s — pass through walls, own body, and robot without dying. Refreshes if eaten again. |
| **[P]** | Purple | **Poison** — removes up to 3 tail segments and deducts 10 pts per segment (max −30 pts, min score 0). |
| **[S]** | Orange | **Slow-motion** 10 s — reduces speed to ~45%. Refreshes to 10 s if eaten again. |

All special foods blink and show a countdown timer. They disappear after 12 seconds if not eaten.

---

## HUD Layout

```
┌─ SCORE   150 ─────── BEST   200 ──────── L5 SKILLED →230 ─┐
│ ████████████████░░░░░░░░░░░░░░░░░░░░  (progress bar)       │
│ SHIELD 8s   SLOW 4s                         [B] ROBOT OFF  │
└────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
snake_project/
├── snake_game.py   ← Main game source (v2.0)
├── README.md       ← This file
├── highscore.json  ← Auto-created on first run
└── report.pdf      ← Maintenance report
```
