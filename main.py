"""
Sokoban – Complete game with:
- AI Action Search Tree Solver (BFS / DFS)
- Real-time visual tree growth & step-by-step solution replay
- Full Level Management & Settings (Packs: Microban, Microban II, Box World)
- Unsolved level tracking, chessboard floor shading, instant move, and settings modal dialog.
Run:  python main.py
"""

import os
import sys
import glob
import time
import pygame

from solver import SokobanSolver
from tree_view import TreeViewer
from settings import GameConfig, LevelsManager, LevelsSettingsDialog

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FPS = 60

TILE_SRC_SIZE = 128          # pixels in the spritesheet
TILE_PADDING = 1             # 1 px gap between tiles in the sheet
SHEET_COLS = 6

TILE_RENDER_SIZE = 64        # default tile size

HUD_HEIGHT = 45
BUTTON_BAR_HEIGHT = 55

BG_COLOR = (20, 24, 32)
HUD_BG = (14, 18, 25)
HUD_FG = (240, 240, 240)
BTN_BG = (45, 55, 70)
BTN_HOVER = (70, 85, 110)
BTN_ACTIVE = (40, 160, 220)
BTN_FG = (240, 240, 240)
POPUP_BG = (0, 0, 0, 190)
POPUP_FG = (255, 255, 100)

# Tile indices
TILE_FLOOR = 0
TILE_BOX = 1
TILE_GOAL = 2
TILE_WALL = 3

# Player animation tile indices per direction (3 frames each)
PLAYER_FRAMES = {
    "down":  [6, 7, 8],
    "up":    [9, 10, 11],
    "right": [12, 13, 14],
    "left":  [15, 16, 17],
}

# Directions mapping
DIR_OFFSETS = {
    pygame.K_UP:    (0, -1),
    pygame.K_DOWN:  (0,  1),
    pygame.K_LEFT:  (-1, 0),
    pygame.K_RIGHT: (1,  0),
}

DIR_NAMES = {
    pygame.K_UP:    "up",
    pygame.K_DOWN:  "down",
    pygame.K_LEFT:  "left",
    pygame.K_RIGHT: "right",
}

NAME_TO_DIR = {
    "up":    (0, -1),
    "down":  (0,  1),
    "left":  (-1, 0),
    "right": (1,  0),
}


# ---------------------------------------------------------------------------
# Spritesheet helpers
# ---------------------------------------------------------------------------

def load_tiles(sheet_path: str) -> list[pygame.Surface]:
    """Load the tilesheet and return a list of 18 tile surfaces (128x128)."""
    sheet = pygame.image.load(sheet_path).convert_alpha()
    tiles: list[pygame.Surface] = []
    for i in range(SHEET_COLS * 3):  # 18 tiles
        col = i % SHEET_COLS
        row = i // SHEET_COLS
        x = col * (TILE_SRC_SIZE + TILE_PADDING)
        y = row * (TILE_SRC_SIZE + TILE_PADDING)
        surf = sheet.subsurface(pygame.Rect(x, y, TILE_SRC_SIZE, TILE_SRC_SIZE))
        tiles.append(surf)
    return tiles


def scale_tile(tile: pygame.Surface, size: int) -> pygame.Surface:
    return pygame.transform.smoothscale(tile, (size, size))


def make_box_on_goal_sprite(box_tile: pygame.Surface, size: int) -> pygame.Surface:
    """Return a version of the box sprite with a green tint overlay."""
    base = scale_tile(box_tile, size).copy()
    overlay = pygame.Surface((size, size), pygame.SRCALPHA)
    overlay.fill((0, 180, 0, 70))
    base.blit(overlay, (0, 0))
    return base


def make_shaded_floor_sprite(floor_tile: pygame.Surface, size: int, shade_factor: float) -> pygame.Surface:
    """Return a darker version of the floor tile for alternating chessboard squares."""
    base = scale_tile(floor_tile, size).copy()
    if shade_factor > 0:
        dark_overlay = pygame.Surface((size, size), pygame.SRCALPHA)
        alpha = int(255 * shade_factor)
        dark_overlay.fill((0, 0, 0, min(255, alpha)))
        base.blit(dark_overlay, (0, 0))
    return base


# ---------------------------------------------------------------------------
# XSB level parser
# ---------------------------------------------------------------------------

class Level:
    """Represents a single Sokoban level."""

    def __init__(self, grid: list[list[str]], title: str = ""):
        self.title = title
        self.width = max(len(row) for row in grid) if grid else 0
        self.height = len(grid)

        self.walls: set[tuple[int, int]] = set()
        self.goals: set[tuple[int, int]] = set()
        self.floors: set[tuple[int, int]] = set()
        self.initial_boxes: set[tuple[int, int]] = set()
        self.initial_player: tuple[int, int] = (0, 0)

        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                if ch == "#":
                    self.walls.add((x, y))
                elif ch == "@":
                    self.initial_player = (x, y)
                    self.floors.add((x, y))
                elif ch == "+":
                    self.initial_player = (x, y)
                    self.goals.add((x, y))
                    self.floors.add((x, y))
                elif ch == "$":
                    self.initial_boxes.add((x, y))
                    self.floors.add((x, y))
                elif ch == "*":
                    self.initial_boxes.add((x, y))
                    self.goals.add((x, y))
                    self.floors.add((x, y))
                elif ch == ".":
                    self.goals.add((x, y))
                    self.floors.add((x, y))
                elif ch == " ":
                    self.floors.add((x, y))

        self._compute_interior()

    def _compute_interior(self):
        """Mark all floor/goal cells reachable from the player as interior."""
        visited: set[tuple[int, int]] = set()
        stack = [self.initial_player]
        while stack:
            pos = stack.pop()
            if pos in visited:
                continue
            visited.add(pos)
            x, y = pos
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nb = (x + dx, y + dy)
                if (nb not in visited and nb not in self.walls
                        and 0 <= nb[0] < self.width and 0 <= nb[1] < self.height):
                    stack.append(nb)
        self.floors = visited - self.walls


def parse_xsb_file(path: str) -> list[Level]:
    """Parse an XSB file and return a list of Level objects."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    levels: list[Level] = []
    current_title = ""
    current_grid: list[list[str]] = []

    def _flush():
        nonlocal current_grid, current_title
        if current_grid and any("#" in row for row in [list(r) for r in current_grid]):
            levels.append(Level(current_grid, current_title))
        current_grid = []
        current_title = ""

    for raw in lines:
        line = raw.rstrip("\n\r")
        if line.startswith(";"):
            if current_grid:
                _flush()
            current_title = line.lstrip("; ").strip()
            continue
        if not line or line.isspace():
            if current_grid:
                _flush()
            continue
        if any(ch in line for ch in "#@+$*."):
            current_grid.append(list(line))
        else:
            if current_grid:
                _flush()
            current_title = line.strip()

    _flush()
    return levels


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

class GameState:
    """Mutable state for the current level being played."""

    def __init__(self, level: Level):
        self.level = level
        self.reset()

    def reset(self):
        self.player = self.level.initial_player
        self.boxes: set[tuple[int, int]] = set(self.level.initial_boxes)
        self.moves = 0
        self.pushes = 0
        self.facing = "down"
        self.solved = False

        self.animating = False
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.anim_total_frames = 3
        self.anim_frames_shown = 0

    def try_move(self, dx: int, dy: int, direction: str, instant: bool = False) -> bool:
        """Attempt to move the player. Returns True if moved."""
        if self.solved:
            return False

        self.facing = direction
        nx, ny = self.player[0] + dx, self.player[1] + dy
        target = (nx, ny)

        if target in self.level.walls:
            return False

        if target in self.boxes:
            behind = (nx + dx, ny + dy)
            if behind in self.level.walls or behind in self.boxes:
                return False
            self.boxes.remove(target)
            self.boxes.add(behind)
            self.pushes += 1

        self.player = target
        self.moves += 1

        if self.level.goals and self.level.goals <= self.boxes:
            self.solved = True

        if not instant:
            self.animating = True
            self.anim_frame = 0
            self.anim_timer = 0.0
            self.anim_frames_shown = 0
        else:
            self.animating = False

        return True

    def get_player_tile_index(self) -> int:
        frames = PLAYER_FRAMES[self.facing]
        if self.animating:
            return frames[self.anim_frame % len(frames)]
        return frames[0]

    def update_animation(self, dt: float, frame_duration: float = 0.10):
        if not self.animating:
            return
        self.anim_timer += dt
        if self.anim_timer >= frame_duration:
            self.anim_timer -= frame_duration
            self.anim_frame += 1
            self.anim_frames_shown += 1
            if self.anim_frames_shown >= self.anim_total_frames:
                self.animating = False
                self.anim_frame = 0


# ---------------------------------------------------------------------------
# UI Button
# ---------------------------------------------------------------------------

class Button:
    def __init__(self, text: str, rect: pygame.Rect, callback, is_active: bool = False):
        self.text = text
        self.rect = rect
        self.callback = callback
        self.hovered = False
        self.is_active = is_active

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        if self.is_active:
            color = BTN_ACTIVE
        elif self.hovered:
            color = BTN_HOVER
        else:
            color = BTN_BG

        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        border_col = (140, 180, 220) if self.is_active else (80, 95, 115)
        pygame.draw.rect(surface, border_col, self.rect, width=1, border_radius=6)
        txt = font.render(self.text, True, BTN_FG)
        tx = self.rect.x + (self.rect.width - txt.get_width()) // 2
        ty = self.rect.y + (self.rect.height - txt.get_height()) // 2
        surface.blit(txt, (tx, ty))

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------

def main():
    pygame.init()

    # Start maximized and resizable
    info = pygame.display.Info()
    win_w, win_h = info.current_w, info.current_h
    screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
    pygame.display.set_caption("Sokoban with Action Tree Solver (BFS / DFS)")

    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(
            ctypes.windll.user32.GetForegroundWindow(), 3  # SW_MAXIMIZE
        )
    except Exception:
        pass

    clock = pygame.time.Clock()

    # Paths relative to this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_assets = os.path.join(base_dir, "assets")
    assets_dir = local_assets if os.path.exists(local_assets) else os.path.join(base_dir, "..", "assets")
    sheet_path = os.path.join(assets_dir, "textures", "tilesheet.png")
    levels_dir = os.path.join(assets_dir, "levels")
    config_file = os.path.join(base_dir, "config.json")

    # Load persistent game config and levels manager
    game_config = GameConfig(config_file)
    levels_manager = LevelsManager(levels_dir, game_config, parse_xsb_file)
    settings_dialog = LevelsSettingsDialog(levels_manager)

    # Sprites
    raw_tiles = load_tiles(sheet_path)
    scaled_tiles = [scale_tile(t, TILE_RENDER_SIZE) for t in raw_tiles]
    box_on_goal = make_box_on_goal_sprite(raw_tiles[TILE_BOX], TILE_RENDER_SIZE)

    # Fonts
    hud_font = pygame.font.SysFont("consolas", 15, bold=True)
    hud_status_font = pygame.font.SysFont("consolas", 14, bold=True)
    btn_font = pygame.font.SysFont("consolas", 13, bold=True)
    popup_font = pygame.font.SysFont("consolas", 36, bold=True)

    # State
    state = GameState(levels_manager.current_level)
    solved_time: float | None = None

    # Solver & Tree Visualization State
    current_algorithm = "BFS"
    solver: SokobanSolver | None = None
    tree_viewer = TreeViewer()

    solver_mode = "IDLE"  # "IDLE", "SOLVING", "REPLAYING"
    search_speed = "Fast"
    speed_steps = {"Normal": 2, "Fast": 25, "Ultra": 100, "Instant": 10000}

    replay_index = 0
    replay_timer = 0.0
    replay_step_delay = 0.16

    # Callbacks
    def reload_level():
        nonlocal state, solved_time, solver, solver_mode, replay_index
        state = GameState(levels_manager.current_level)
        solved_time = None
        solver = None
        solver_mode = "IDLE"
        replay_index = 0
        tree_viewer.reset_view()

    def reset_level():
        reload_level()

    def next_level():
        levels_manager.next_level()
        reload_level()

    def prev_level():
        levels_manager.prev_level()
        reload_level()

    def open_settings():
        settings_dialog.open()

    def toggle_algorithm():
        nonlocal current_algorithm, solver, solver_mode
        current_algorithm = "DFS" if current_algorithm == "BFS" else "BFS"
        solver = None
        solver_mode = "IDLE"
        _rebuild_buttons()

    def toggle_solve():
        nonlocal solver, solver_mode, replay_index, solved_time
        if solver_mode == "SOLVING":
            solver_mode = "IDLE"
        else:
            state.reset()
            solved_time = None
            solver = SokobanSolver(levels_manager.current_level, current_algorithm)
            solver_mode = "SOLVING"
            replay_index = 0
        _rebuild_buttons()

    def cycle_speed():
        nonlocal search_speed, replay_step_delay
        speeds = ["Normal", "Fast", "Ultra", "Instant"]
        idx = (speeds.index(search_speed) + 1) % len(speeds)
        search_speed = speeds[idx]
        if search_speed == "Normal":
            replay_step_delay = 0.25
        elif search_speed == "Fast":
            replay_step_delay = 0.15
        elif search_speed == "Ultra":
            replay_step_delay = 0.08
        else:
            replay_step_delay = 0.04
        _rebuild_buttons()

    def start_replay():
        nonlocal solver_mode, replay_index, state, solved_time
        if solver and solver.solved:
            state.reset()
            solved_time = None
            replay_index = 0
            solver_mode = "REPLAYING"
            _rebuild_buttons()

    def step_forward():
        nonlocal replay_index, state
        if solver and solver.solved and replay_index < len(solver.solution_actions):
            act = solver.solution_actions[replay_index]
            dx, dy = NAME_TO_DIR[act]
            state.try_move(dx, dy, act, instant=game_config.instant_move)
            replay_index += 1

    def step_backward():
        nonlocal replay_index, state
        if solver and solver.solved and replay_index > 0:
            target_idx = replay_index - 1
            state.reset()
            replay_index = 0
            for i in range(target_idx):
                act = solver.solution_actions[i]
                dx, dy = NAME_TO_DIR[act]
                state.try_move(dx, dy, act, instant=game_config.instant_move)
            replay_index = target_idx

    def exit_game():
        pygame.quit()
        sys.exit()

    # Rebuild bottom control buttons
    buttons: list[Button] = []

    def _rebuild_buttons():
        nonlocal buttons
        btn_y = win_h - BUTTON_BAR_HEIGHT + (BUTTON_BAR_HEIGHT - 36) // 2

        btn_specs = [
            ("Reset", 75, reset_level, False),
            (f"Algo: {current_algorithm}", 110, toggle_algorithm, True),
            ("Stop" if solver_mode == "SOLVING" else "Solve", 80, toggle_solve, solver_mode == "SOLVING"),
            (f"Speed: {search_speed}", 115, cycle_speed, False),
            ("Replay", 80, start_replay, solver_mode == "REPLAYING"),
            ("< Step", 70, step_backward, False),
            ("Step >", 70, step_forward, False),
            ("⚙ Levels & Settings", 155, open_settings, False),
            ("Prev Lvl", 85, prev_level, False),
            ("Next Lvl", 85, next_level, False),
            ("Exit", 60, exit_game, False),
        ]

        total_w = sum(w for _, w, _, _ in btn_specs)
        gap = max(4, min(10, (win_w - total_w) // (len(btn_specs) + 1)))
        total_w_with_gaps = total_w + gap * (len(btn_specs) - 1)
        start_x = max(6, (win_w - total_w_with_gaps) // 2)

        cur_x = start_x
        buttons = []
        for text, w, cb, is_act in btn_specs:
            buttons.append(Button(text, pygame.Rect(cur_x, btn_y, w, 36), cb, is_act))
            cur_x += w + gap

    _rebuild_buttons()

    # Track active level to detect changes made inside Settings modal
    last_known_pack_idx = game_config.current_pack_idx
    last_known_lvl_idx = game_config.current_level_idx

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        # Detect level changes from settings modal
        if (last_known_pack_idx != game_config.current_pack_idx or
                last_known_lvl_idx != game_config.current_level_idx):
            last_known_pack_idx = game_config.current_pack_idx
            last_known_lvl_idx = game_config.current_level_idx
            reload_level()

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if event.type == pygame.VIDEORESIZE:
                win_w, win_h = event.w, event.h
                screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
                _rebuild_buttons()

            # Route to settings dialog if open
            if settings_dialog.visible:
                if settings_dialog.handle_event(event):
                    continue

            # Route to bottom buttons
            for btn in buttons:
                btn.handle_event(event)

            # Route to tree viewer
            tree_viewer.handle_event(event)

            # Manual player movement with arrow keys (when not replaying/searching)
            if event.type == pygame.KEYDOWN and solver_mode == "IDLE":
                if event.key in DIR_OFFSETS:
                    dx, dy = DIR_OFFSETS[event.key]
                    direction = DIR_NAMES[event.key]
                    state.try_move(dx, dy, direction, instant=game_config.instant_move)
                    if state.solved and solved_time is None:
                        solved_time = time.time()
                        game_config.mark_solved(
                            game_config.current_pack_idx,
                            game_config.current_level_idx,
                            state.moves,
                            state.pushes
                        )

        # Update solver execution
        if solver_mode == "SOLVING" and solver:
            steps_this_frame = speed_steps[search_speed]
            for _ in range(steps_this_frame):
                res_type, data = solver.step()
                if res_type == 'SOLVED':
                    solver_mode = "REPLAYING"
                    state.reset()
                    replay_index = 0
                    replay_timer = 0.0
                    game_config.mark_solved(
                        game_config.current_pack_idx,
                        game_config.current_level_idx,
                        len(solver.solution_actions),
                        sum(1 for nid in solver.solution_path if solver.nodes[nid].is_push)
                    )
                    _rebuild_buttons()
                    break
                elif res_type == 'FINISHED':
                    solver_mode = "IDLE"
                    _rebuild_buttons()
                    break

        # Update solution replay animation
        current_replay_nid = None
        if solver and solver.solved:
            if replay_index < len(solver.solution_path):
                current_replay_nid = solver.solution_path[replay_index]

        if solver_mode == "REPLAYING" and solver and solver.solved:
            replay_timer += dt
            if replay_timer >= replay_step_delay:
                replay_timer = 0.0
                if replay_index < len(solver.solution_actions):
                    act = solver.solution_actions[replay_index]
                    dx, dy = NAME_TO_DIR[act]
                    state.try_move(dx, dy, act, instant=game_config.instant_move)
                    replay_index += 1
                else:
                    # Replay complete
                    solver_mode = "IDLE"
                    if state.solved and solved_time is None:
                        solved_time = time.time()
                    _rebuild_buttons()

        # Auto-switch to next unsolved level if enabled
        if (state.solved and solved_time is not None and
                game_config.auto_switch_to_next_unsolved_level and
                solver_mode == "IDLE"):
            if time.time() - solved_time > 2.0:
                if levels_manager.next_unsolved_level():
                    reload_level()
                else:
                    levels_manager.next_level()
                    reload_level()

        # Update player animation
        state.update_animation(dt, frame_duration=game_config.player_move_speed)

        # Update tree viewer camera
        tree_viewer.update(dt, solver, current_replay_nid)

        # -------------------------------------------------------------------
        # Rendering
        # -------------------------------------------------------------------
        screen.fill(BG_COLOR)

        # Split screen dimensions
        main_top = HUD_HEIGHT
        main_bottom = win_h - BUTTON_BAR_HEIGHT
        main_h = main_bottom - main_top

        board_panel_w = max(380, int(win_w * 0.46))
        tree_panel_w = win_w - board_panel_w - 12
        tree_panel_x = board_panel_w + 6

        # Update tree view rect
        tree_rect = pygame.Rect(tree_panel_x, main_top + 4, tree_panel_w, main_h - 8)
        tree_viewer.set_rect(tree_rect)

        # 1. Render Sokoban Board Area
        board_rect = pygame.Rect(6, main_top + 4, board_panel_w - 6, main_h - 8)
        pygame.draw.rect(screen, (24, 28, 38), board_rect, border_radius=6)
        pygame.draw.rect(screen, (50, 65, 85), board_rect, width=1, border_radius=6)

        lw = state.level.width
        lh = state.level.height
        board_pixel_w = lw * TILE_RENDER_SIZE
        board_pixel_h = lh * TILE_RENDER_SIZE

        avail_w = board_rect.width - 20
        avail_h = board_rect.height - 20
        scale = min(avail_w / max(1, board_pixel_w), avail_h / max(1, board_pixel_h))
        tile_size = max(16, int(TILE_RENDER_SIZE * scale))

        if tile_size != TILE_RENDER_SIZE:
            cur_scaled = [scale_tile(t, tile_size) for t in raw_tiles]
            cur_box_on_goal = make_box_on_goal_sprite(raw_tiles[TILE_BOX], tile_size)
            cur_shaded_floor = make_shaded_floor_sprite(raw_tiles[TILE_FLOOR], tile_size, game_config.even_square_shades)
        else:
            cur_scaled = scaled_tiles
            cur_box_on_goal = box_on_goal
            cur_shaded_floor = make_shaded_floor_sprite(raw_tiles[TILE_FLOOR], tile_size, game_config.even_square_shades)

        offset_x = board_rect.x + (board_rect.width - lw * tile_size) // 2
        offset_y = board_rect.y + (board_rect.height - lh * tile_size) // 2

        # Draw floors (with optional chessboard shading)
        for (fx, fy) in state.level.floors:
            if game_config.even_square_shades > 0.0 and (fx + fy) % 2 == 0:
                screen.blit(cur_shaded_floor, (offset_x + fx * tile_size, offset_y + fy * tile_size))
            else:
                screen.blit(cur_scaled[TILE_FLOOR], (offset_x + fx * tile_size, offset_y + fy * tile_size))

        # Draw walls
        for (wx, wy) in state.level.walls:
            screen.blit(cur_scaled[TILE_WALL], (offset_x + wx * tile_size, offset_y + wy * tile_size))

        # Draw goals
        for (gx, gy) in state.level.goals:
            screen.blit(cur_scaled[TILE_GOAL], (offset_x + gx * tile_size, offset_y + gy * tile_size))

        # Draw boxes
        for (bx, by) in state.boxes:
            if (bx, by) in state.level.goals:
                screen.blit(cur_box_on_goal, (offset_x + bx * tile_size, offset_y + by * tile_size))
            else:
                screen.blit(cur_scaled[TILE_BOX], (offset_x + bx * tile_size, offset_y + by * tile_size))

        # Draw player
        player_idx = state.get_player_tile_index()
        px, py = state.player
        screen.blit(cur_scaled[player_idx], (offset_x + px * tile_size, offset_y + py * tile_size))

        # Board label with pack and solved status
        is_cur_solved = game_config.is_solved(game_config.current_pack_idx, game_config.current_level_idx)
        board_status = " [SOLVED ✓]" if is_cur_solved else ""
        board_lbl = hud_status_font.render(
            f"{levels_manager.current_pack.name} – Level #{game_config.current_level_idx + 1}{board_status}",
            True,
            (80, 240, 140) if is_cur_solved else (160, 180, 205)
        )
        screen.blit(board_lbl, (board_rect.x + 12, board_rect.y + 10))

        # 2. Render Action Search Tree Canvas
        tree_viewer.draw(screen, solver, current_replay_nid)

        # 3. Top HUD Bar
        pygame.draw.rect(screen, HUD_BG, (0, 0, win_w, HUD_HEIGHT))
        pygame.draw.line(screen, (50, 65, 85), (0, HUD_HEIGHT), (win_w, HUD_HEIGHT), 1)

        cur_pack_name = levels_manager.current_pack.name
        cur_l_num = game_config.current_level_idx + 1
        pack_total = levels_manager.total_levels_in_current_pack()
        level_text = f"[{cur_pack_name}] Level {cur_l_num}/{pack_total}"
        lt = hud_font.render(level_text, True, HUD_FG)
        screen.blit(lt, (14, (HUD_HEIGHT - lt.get_height()) // 2))

        # Center Status Banner
        if solver_mode == "SOLVING":
            status_str = f"[{current_algorithm} SEARCHING...] Nodes Explored: {solver.steps_explored if solver else 0}"
            status_col = (255, 220, 60)
        elif solver_mode == "REPLAYING":
            status_str = f"[REPLAYING SOLUTION] Step {replay_index} / {len(solver.solution_actions) if solver else 0}"
            status_col = (50, 220, 255)
        elif solver and solver.solved:
            status_str = f"[{current_algorithm} SOLVED] Solution Length: {len(solver.solution_actions)} moves"
            status_col = (80, 255, 140)
        elif state.solved:
            status_str = "LEVEL SOLVED!"
            status_col = (80, 255, 140)
        else:
            status_str = "Play with Arrow Keys, click [Solve], or open [⚙ Levels & Settings]"
            status_col = (180, 195, 215)

        st_surf = hud_status_font.render(status_str, True, status_col)
        screen.blit(st_surf, ((win_w - st_surf.get_width()) // 2, (HUD_HEIGHT - st_surf.get_height()) // 2))

        # Right stats (moves, pushes, and best record)
        best_k = f"pack_{game_config.current_pack_idx}_lvl_{game_config.current_level_idx}"
        best_m = game_config.best_moves.get(best_k, None)
        best_str = f" (Best: {best_m})" if best_m is not None else ""
        stats_text = f"Moves: {state.moves}{best_str}   Pushes: {state.pushes}"
        st = hud_font.render(stats_text, True, HUD_FG)
        screen.blit(st, (win_w - st.get_width() - 14, (HUD_HEIGHT - st.get_height()) // 2))

        # 4. Bottom Control Bar
        pygame.draw.rect(screen, HUD_BG, (0, win_h - BUTTON_BAR_HEIGHT, win_w, BUTTON_BAR_HEIGHT))
        pygame.draw.line(screen, (50, 65, 85), (0, win_h - BUTTON_BAR_HEIGHT), (win_w, win_h - BUTTON_BAR_HEIGHT), 1)

        for btn in buttons:
            btn.draw(screen, btn_font)

        # 5. Solved Overlay Popup (displayed after human solve or replay completion)
        if state.solved and solver_mode == "IDLE":
            overlay = pygame.Surface((board_rect.width, board_rect.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (board_rect.x, board_rect.y))

            msg1 = popup_font.render("LEVEL SOLVED!", True, (80, 255, 120))
            msg2 = hud_font.render(f"Moves: {state.moves}  |  Pushes: {state.pushes}", True, (240, 240, 240))
            cx = board_rect.x + (board_rect.width - msg1.get_width()) // 2
            cy = board_rect.y + (board_rect.height - msg1.get_height()) // 2 - 16
            screen.blit(msg1, (cx, cy))
            screen.blit(msg2, (board_rect.x + (board_rect.width - msg2.get_width()) // 2, cy + 48))

        # 6. Modal Settings Dialog
        if settings_dialog.visible:
            settings_dialog.draw(screen, win_w, win_h)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
