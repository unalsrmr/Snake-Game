# 🐍 Retro Snake Game

A feature-rich retro Snake game built with **Python** and **PyGame** for the CSE444 Take-Home Exam.

---

## Requirements

- Python 3.13 or newer
- PyGame 2.6.x

## Installation

```bash
py -3.13 -m pip install pygame
```

## How to Run

```bash
py -3.13 snake_game.py
```

---

## Controls

| Key | Action |
|-----|--------|
| `Arrow Keys` / `W A S D` | Move the snake |
| `P` | Pause / Resume |
| `R` / `Enter` / `Space` | Restart (on Game Over screen) |
| `ESC` | Quit |

---

## Features

- Grid-based gameplay with smooth animation
- Snake grows when eating food
- Two food types: normal (🔴 +10 pts) and bonus (🟡 +30 pts, time-limited)
- Progressive difficulty — speed increases every 10 points
- Particle burst effect when food is eaten
- Persistent high score saved to `highscore.json`
- Pause screen, menu screen, game over screen
- Retro green-on-black colour theme

---

## Project Structure

```
snake_project/
├── snake_game.py   ← Main game source code
├── README.md       ← This file
├── highscore.json  ← Auto-created on first run
└── report.pdf      ← Project report
```

---

## Notes

- High score is saved automatically to `highscore.json` in the same directory.
- The game window is 800×640 pixels (fixed size).
- Designed and tested on Windows/Linux/macOS with **Python 3.13** and **PyGame 2.6.1**.
- If you have multiple Python versions installed, always use `py -3.13` to ensure the correct interpreter is used.