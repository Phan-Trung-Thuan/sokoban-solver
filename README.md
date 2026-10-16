# Sokoban Game with AI Action Tree Solver (BFS, DFS, Greedy, A* & IDS) and Level Settings

A complete Python implementation of Sokoban featuring:
- Real-time visual action search trees (BFS, DFS, Greedy, A* & IDS)
- Monodirectional and bidirectional modes for every algorithm
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
  - `auto_switch_to_next_unsolved_level`: Off by default, so the solved board and state tree stay visible until you choose another level. Can be enabled in settings.
  - `even_square_shades`: Alternating light/dark chessboard pattern on floor tiles.
  - `instant_move`: Skip character walk animations for immediate movement.
  - `player_move_speed`: Walk animation timing.
- **Persistent Progress**: Saved automatically to `config.json` (solved levels, best moves, best pushes, last played level).

---

### 2. Search Algorithms (BFS, DFS, Greedy, A* & IDS)
- **BFS (Breadth-First Search)**: Explores states layer-by-layer (FIFO queue); guarantees the shortest path (optimal moves).
- **DFS (Depth-First Search)**: Explores branches deeply (LIFO stack); demonstrates depth-first exploration.
- **Greedy (Greedy Best-First Search)**: Expands the state with the lowest heuristic `h(n)`; does not guarantee the shortest solution.
- **A* (A-Star Search)**: Expands the state with the lowest `g(n) + h(n)`, where `g(n)` counts player moves (including pushes); guarantees the shortest solution in moves by retaining cheaper routes to states.
- **IDS (Iterative Deepening Search)**: Repeats depth-limited DFS with limits 0, 1, 2, and so on; guarantees the shortest solution in moves without a heuristic. Each iteration resets duplicate records and accepts shorter routes to states. Search stops without a solution when no unexplored successors remain beyond the current limit.
- **IDS Visualization**: The tree shows the current iteration, with its depth limit in the status banners. The explored count includes all iterations. The visualizer retains the current tree and duplicate records, so this implementation uses more memory than textbook IDS that stores only the active DFS path.
- **Heuristic**: Sums the Manhattan distance from each goal to its nearest box. It ignores walls, player travel, and competition between goals for boxes, giving a lower bound on the remaining moves.
- **Deadlock Pruning**: Static corner deadlocks are pruned to keep searches fast.
- **Search Direction**: The button beside **Algo** toggles **Monodirectional** (from the initial state) and **Bidirectional** (from both the initial state and solved states). Both modes support all five algorithms. Changing direction stops the current search; click **Solve** to start with the new mode.
- **Backward Search**: Uses reverse walking and pulling to undo legal forward moves. It starts from every free player position with boxes on goals; levels with extra boxes also enumerate the remaining box placements. Goal roots are prepared incrementally so the controls remain responsive. The two searches join only when player and box positions match, and the result replays using ordinary forward moves.
- **Bidirectional Guarantees**: BFS waits for its frontier depth bound; A* waits for an admissible cost bound rather than stopping at the first meeting. IDS increases a total move limit, split between forward and backward DFS, resetting both searches each iteration. These three algorithms retain shortest-move solutions; DFS and Greedy find solutions without an optimality guarantee.
- **Bidirectional Tree**: Forward search grows right from the start; backward search grows left from `G` goal roots. Backward frontier nodes are purple, and a purple link marks the meeting states. The winning route is highlighted and supports the same replay controls in either mode. Bidirectional search can use more memory and is not always faster, especially when there are many goal states.

---

### 3. Real-Time Action Search Tree Visualization
- Visual action tree drawn on the right screen panel:
  - 🟡 **Pulsing Yellow**: Active node being expanded.
  - 🔵 **Cyan**: Frontier nodes in queue/stack.
  - ⚪ **Slate**: Explored nodes.
  - 🟢 **Emerald Green**: Winning solution path.
  - 🟠 **Orange Ring**: Current step executing on the board during replay.
- **Interactive Tree Camera**:
  - Free camera by default: your view stays in place during search and replay.
  - Click & drag to pan the tree; release to leave it at the chosen position.
  - Mouse wheel to zoom in / out, including before starting a solver.
  - Press **F** with the pointer over the tree to toggle following the active search/replay node. Dragging or zooming turns following off.
  - Right-click to reset the view in free camera mode.

---

### 4. Step-by-Step Solution Replay
- When a level is solved, the winning path lights up in green on the tree, and the board automatically animates the player walking and pushing boxes step-by-step.
- Control replay anytime with `[Replay]`, `[< Step]`, and `[Step >]`.
- **Search Results**: The HUD and tree panel show **States checked** during search, replay, and after completion, alongside the solution's total moves. Each processed search node counts once; duplicates rejected before processing and goal-root initialization do not count. Bidirectional search totals both directions. IDS includes repeated checks across all depth limits, and A* includes states processed again after finding a shorter route. Searches with no solution also retain their final count.

---

## Controls & Buttons

| Control / Button | Action |
|---|---|
| **Arrow Keys (↑ ↓ ← →)** | Move / push boxes manually |
| **`⚙ Levels & Settings`** | Open level picker & settings dialog |
| **`Algo: BFS / DFS / Greedy / A* / IDS`** | Cycle through the five search algorithms |
| **`Monodirectional / Bidirectional`** | Toggle the search direction for the selected algorithm |
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

Run solver regression tests with `python -m unittest -v`.
