# Sokoban Game with AI Action Tree Solver (BFS & DFS) and Level Settings

A complete Python implementation of Sokoban featuring:
- Real-time visual action search trees (BFS & DFS)
- Animated solution replay for academic presentations
- Complete level management & game settings from `sokoban-rs`

---

## Level Packs Included

1. **Microban (155 levels)** – David W. Skinner
2. **Microban II (135 levels)** – David W. Skinner
3. **Box World (100 levels)** – Thinking Rabbit

Total: **390 levels** loaded from `assets/levels/`.

---

## Features & Settings (from `sokoban-rs`)

### 1. Levels & Settings Dialog (`[⚙ Levels & Settings]`)
- **Pack Selector Tabs**: Switch between Microban (155), Microban II (135), and Box World (100).
- **Interactive Level Grid**: Browse and click any level directly. Solved levels are marked with a green `[✓]`.
- **Quick Jump Unsolved**:
  - `<< Prev Unsolved`: Jumps to the previous unsolved level.
  - `Next Unsolved >>`: Jumps to the next unsolved level.
- **Configurable Settings**:
  - `auto_switch_to_next_unsolved_level`: Automatically advances to the next unsolved level after completing a puzzle.
  - `even_square_shades`: Alternating light/dark chessboard pattern on floor tiles.
  - `instant_move`: Skip character walk animations for immediate movement.
  - `player_move_speed`: Walk animation timing.
- **Persistent Progress**: Saved automatically to `config.json` (solved levels, best moves, best pushes, last played level).

---

### 2. Dual Search Algorithms (BFS & DFS)
- **BFS (Breadth-First Search)**: Explores states layer-by-layer (FIFO queue); guarantees the shortest path (optimal moves).
- **DFS (Depth-First Search)**: Explores branches deeply (LIFO stack); demonstrates depth-first exploration.
- **Deadlock Pruning**: Static corner deadlocks are pruned to keep searches fast.

---

### 3. Real-Time Action Search Tree Visualization
- Visual action tree drawn on the right screen panel:
  - 🟡 **Pulsing Yellow**: Active node being expanded.
  - 🔵 **Cyan**: Frontier nodes in queue/stack.
  - ⚪ **Slate**: Explored nodes.
  - 🟢 **Emerald Green**: Winning solution path.
  - 🟠 **Orange Ring**: Current step executing on the board during replay.
- **Interactive Tree Camera**:
  - Auto-follows current search branch.
  - Click & drag to pan the tree.
  - Mouse wheel to zoom in / out.
  - Right-click to reset view.

---

### 4. Step-by-Step Solution Replay
- When a level is solved, the winning path lights up in green on the tree, and the board automatically animates the player walking and pushing boxes step-by-step.
- Control replay anytime with `[Replay]`, `[< Step]`, and `[Step >]`.

---

## Controls & Buttons

| Control / Button | Action |
|---|---|
| **Arrow Keys (↑ ↓ ← →)** | Move / push boxes manually |
| **`⚙ Levels & Settings`** | Open level picker & settings dialog |
| **`Algo: BFS / DFS`** | Toggle between BFS and DFS |
| **`Solve / Stop`** | Start or pause the AI solver |
| **`Speed: Fast`** | Cycle search/replay speed: Normal, Fast, Ultra, Instant |
| **`Replay`** | Replay the discovered solution from step 1 |
| **`< Step` / `Step >`** | Step backward / forward through the solution |
| **`Reset`** | Reset current level |
| **`Prev Lvl` / `Next Lvl`** | Navigate levels |
| **`Exit`** | Quit game |

---

## How to Run

```bash
cd sokoban-py
pip install -r requirements.txt
python main.py
```
