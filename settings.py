"""
Levels and Configuration Settings module for Sokoban.
Handles:
- Level packs management (Microban 155, Microban II 135, Box World 100).
- Level progression and solved status tracking.
- Next / Previous unsolved level navigation.
- Persistent game settings (auto-switch unsolved, chessboard shading, instant move, animation speed).
- Interactive Levels & Settings Modal Dialog.
"""

import os
import json
import pygame
from typing import Optional, Any


class GameConfig:
    """Stores persistent game configurations and progress."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.player_move_speed: float = 0.12        # seconds per step
        self.even_square_shades: float = 0.15       # chessboard floor shading
        self.instant_move: bool = False             # skip animation
        self.auto_switch_to_next_unsolved_level: bool = True
        self.current_pack_idx: int = 0
        self.current_level_idx: int = 0
        self.solved_levels: set[str] = set()        # e.g. "pack_0_lvl_0"
        self.best_moves: dict[str, int] = {}
        self.best_pushes: dict[str, int] = {}
        self.load()

    def load(self):
        if not os.path.exists(self.config_path):
            self.save()
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.player_move_speed = data.get("player_move_speed", self.player_move_speed)
            self.even_square_shades = data.get("even_square_shades", self.even_square_shades)
            self.instant_move = data.get("instant_move", self.instant_move)
            self.auto_switch_to_next_unsolved_level = data.get(
                "auto_switch_to_next_unsolved_level", self.auto_switch_to_next_unsolved_level
            )
            self.current_pack_idx = data.get("current_pack_idx", 0)
            self.current_level_idx = data.get("current_level_idx", 0)
            self.solved_levels = set(data.get("solved_levels", []))
            self.best_moves = data.get("best_moves", {})
            self.best_pushes = data.get("best_pushes", {})
        except Exception:
            pass

    def save(self):
        try:
            data = {
                "player_move_speed": self.player_move_speed,
                "even_square_shades": self.even_square_shades,
                "instant_move": self.instant_move,
                "auto_switch_to_next_unsolved_level": self.auto_switch_to_next_unsolved_level,
                "current_pack_idx": self.current_pack_idx,
                "current_level_idx": self.current_level_idx,
                "solved_levels": list(self.solved_levels),
                "best_moves": self.best_moves,
                "best_pushes": self.best_pushes,
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def mark_solved(self, pack_idx: int, lvl_idx: int, moves: int, pushes: int):
        key = f"pack_{pack_idx}_lvl_{lvl_idx}"
        self.solved_levels.add(key)
        if key not in self.best_moves or moves < self.best_moves[key]:
            self.best_moves[key] = moves
        if key not in self.best_pushes or pushes < self.best_pushes[key]:
            self.best_pushes[key] = pushes
        self.save()

    def is_solved(self, pack_idx: int, lvl_idx: int) -> bool:
        return f"pack_{pack_idx}_lvl_{lvl_idx}" in self.solved_levels


class LevelPack:
    """Represents a pack of levels loaded from a single file."""

    def __init__(self, name: str, filename: str, levels: list):
        self.name = name
        self.filename = filename
        self.levels = levels


class LevelsManager:
    """Manages all level packs and navigation."""

    PACK_DEFINITIONS = [
        ("Microban", "microban_155.xsb"),
        ("Microban II", "microban_II_135.xsb"),
        ("Box World", "box_world_100.xsb")
    ]

    def __init__(self, levels_dir: str, config: GameConfig, parse_func):
        self.levels_dir = levels_dir
        self.config = config
        self.packs: list[LevelPack] = []

        for name, fname in self.PACK_DEFINITIONS:
            path = os.path.join(levels_dir, fname)
            if os.path.exists(path):
                lvls = parse_func(path)
                self.packs.append(LevelPack(name, fname, lvls))

        # Validate current indices
        if self.config.current_pack_idx >= len(self.packs):
            self.config.current_pack_idx = 0
        cur_pack = self.packs[self.config.current_pack_idx]
        if self.config.current_level_idx >= len(cur_pack.levels):
            self.config.current_level_idx = 0

    @property
    def current_pack(self) -> LevelPack:
        return self.packs[self.config.current_pack_idx]

    @property
    def current_level(self):
        return self.current_pack.levels[self.config.current_level_idx]

    def total_levels_in_current_pack(self) -> int:
        return len(self.current_pack.levels)

    def total_levels_all_packs(self) -> int:
        return sum(len(p.levels) for p in self.packs)

    def total_solved_all_packs(self) -> int:
        count = 0
        for p_idx, pack in enumerate(self.packs):
            for l_idx in range(len(pack.levels)):
                if self.config.is_solved(p_idx, l_idx):
                    count += 1
        return count

    def set_level(self, pack_idx: int, lvl_idx: int):
        self.config.current_pack_idx = max(0, min(len(self.packs) - 1, pack_idx))
        cur_pack = self.packs[self.config.current_pack_idx]
        self.config.current_level_idx = max(0, min(len(cur_pack.levels) - 1, lvl_idx))
        self.config.save()

    def next_level(self):
        cur_pack = self.current_pack
        if self.config.current_level_idx < len(cur_pack.levels) - 1:
            self.config.current_level_idx += 1
        else:
            # Advance to next pack
            self.config.current_pack_idx = (self.config.current_pack_idx + 1) % len(self.packs)
            self.config.current_level_idx = 0
        self.config.save()

    def prev_level(self):
        if self.config.current_level_idx > 0:
            self.config.current_level_idx -= 1
        else:
            # Move to previous pack end
            self.config.current_pack_idx = (self.config.current_pack_idx - 1 + len(self.packs)) % len(self.packs)
            self.config.current_level_idx = len(self.current_pack.levels) - 1
        self.config.save()

    def next_unsolved_level(self) -> bool:
        """Find next unsolved level in current pack or subsequent packs."""
        start_p = self.config.current_pack_idx
        start_l = self.config.current_level_idx
        num_packs = len(self.packs)

        for p_offset in range(num_packs):
            p_idx = (start_p + p_offset) % num_packs
            pack = self.packs[p_idx]
            l_start = (start_l + 1) if p_offset == 0 else 0
            for l_idx in range(l_start, len(pack.levels)):
                if not self.config.is_solved(p_idx, l_idx):
                    self.set_level(p_idx, l_idx)
                    return True
        return False

    def prev_unsolved_level(self) -> bool:
        """Find previous unsolved level."""
        start_p = self.config.current_pack_idx
        start_l = self.config.current_level_idx
        num_packs = len(self.packs)

        for p_offset in range(num_packs):
            p_idx = (start_p - p_offset + num_packs) % num_packs
            pack = self.packs[p_idx]
            l_start = (start_l - 1) if p_offset == 0 else (len(pack.levels) - 1)
            for l_idx in range(l_start, -1, -1):
                if not self.config.is_solved(p_idx, l_idx):
                    self.set_level(p_idx, l_idx)
                    return True
        return False


# ---------------------------------------------------------------------------
# Levels & Settings Modal UI
# ---------------------------------------------------------------------------

class LevelsSettingsDialog:
    """
    Renders an interactive modal dialog overlay for level selection and game settings.
    """

    def __init__(self, manager: LevelsManager):
        self.manager = manager
        self.visible = False
        self.page = 0
        self.levels_per_page = 25

        # Fonts
        self.title_font: pygame.font.Font | None = None
        self.font: pygame.font.Font | None = None
        self.btn_font: pygame.font.Font | None = None

        self.buttons: list[tuple[pygame.Rect, str, Any, bool]] = []

    def _init_fonts(self):
        if self.title_font is None:
            self.title_font = pygame.font.SysFont("consolas", 20, bold=True)
            self.font = pygame.font.SysFont("consolas", 14, bold=True)
            self.btn_font = pygame.font.SysFont("consolas", 13, bold=True)

    def open(self):
        self.visible = True
        cur_lvl = self.manager.config.current_level_idx
        self.page = cur_lvl // self.levels_per_page

    def close(self):
        self.visible = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Returns True if the dialog consumed the event."""
        if not self.visible:
            return False

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for rect, text, callback, is_active in self.buttons:
                if rect.collidepoint(pos):
                    callback()
                    return True
            return True  # Consume clicks inside modal
        return True

    def draw(self, surface: pygame.Surface, win_w: int, win_h: int):
        if not self.visible:
            return
        self._init_fonts()

        # Dim background
        dim = pygame.Surface((win_w, win_h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 180))
        surface.blit(dim, (0, 0))

        # Modal Dialog Rect
        modal_w = min(780, win_w - 40)
        modal_h = min(620, win_h - 40)
        modal_x = (win_w - modal_w) // 2
        modal_y = (win_h - modal_h) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)

        # Dialog body
        pygame.draw.rect(surface, (22, 28, 38), modal_rect, border_radius=10)
        pygame.draw.rect(surface, (70, 90, 120), modal_rect, width=2, border_radius=10)

        self.buttons = []

        # Header Title
        title_surf = self.title_font.render("LEVELS & GAME SETTINGS", True, (240, 240, 240))
        surface.blit(title_surf, (modal_x + 24, modal_y + 18))

        # Close [X] button
        close_rect = pygame.Rect(modal_rect.right - 42, modal_y + 14, 28, 28)
        pygame.draw.rect(surface, (180, 50, 50), close_rect, border_radius=4)
        x_surf = self.btn_font.render("X", True, (255, 255, 255))
        surface.blit(x_surf, (close_rect.x + (close_rect.w - x_surf.get_width()) // 2,
                              close_rect.y + (close_rect.h - x_surf.get_height()) // 2))
        self.buttons.append((close_rect, "X", self.close, False))

        y = modal_y + 60

        # --- 1. Level Pack Selector Tabs ---
        pack_lbl = self.font.render("SELECT LEVEL PACK:", True, (160, 185, 215))
        surface.blit(pack_lbl, (modal_x + 24, y))
        y += 26

        tab_x = modal_x + 24
        for p_idx, pack in enumerate(self.manager.packs):
            is_cur = (p_idx == self.manager.config.current_pack_idx)
            btn_w = 210
            btn_h = 32
            rect = pygame.Rect(tab_x, y, btn_w, btn_h)

            def make_pack_cb(idx):
                def cb():
                    self.manager.set_level(idx, 0)
                    self.page = 0
                return cb

            btn_col = (40, 150, 210) if is_cur else (45, 55, 70)
            pygame.draw.rect(surface, btn_col, rect, border_radius=6)
            pygame.draw.rect(surface, (90, 115, 145), rect, width=1, border_radius=6)

            txt = self.btn_font.render(f"{pack.name} ({len(pack.levels)})", True, (255, 255, 255))
            surface.blit(txt, (rect.x + (rect.w - txt.get_width()) // 2, rect.y + (rect.h - txt.get_height()) // 2))
            self.buttons.append((rect, pack.name, make_pack_cb(p_idx), is_cur))
            tab_x += btn_w + 14

        y += 46

        # --- 2. Level Grid / Page Selector ---
        cur_pack = self.manager.current_pack
        tot_levels = len(cur_pack.levels)
        tot_pages = (tot_levels + self.levels_per_page - 1) // self.levels_per_page

        cur_lvl_num = self.manager.config.current_level_idx + 1
        grid_title = f"{cur_pack.name} – Playing Level #{cur_lvl_num} (Page {self.page + 1} of {tot_pages})"
        gt_surf = self.font.render(grid_title, True, (240, 240, 240))
        surface.blit(gt_surf, (modal_x + 24, y))

        # Page navigation buttons
        page_prev_rect = pygame.Rect(modal_rect.right - 180, y - 4, 70, 26)
        page_next_rect = pygame.Rect(modal_rect.right - 100, y - 4, 70, 26)

        def prev_page_cb():
            if self.page > 0:
                self.page -= 1

        def next_page_cb():
            if self.page < tot_pages - 1:
                self.page += 1

        pygame.draw.rect(surface, (45, 55, 70), page_prev_rect, border_radius=4)
        pygame.draw.rect(surface, (45, 55, 70), page_next_rect, border_radius=4)
        p1 = self.btn_font.render("< Prev", True, (240, 240, 240))
        p2 = self.btn_font.render("Next >", True, (240, 240, 240))
        surface.blit(p1, (page_prev_rect.x + (page_prev_rect.w - p1.get_width()) // 2, page_prev_rect.y + 4))
        surface.blit(p2, (page_next_rect.x + (page_next_rect.w - p2.get_width()) // 2, page_next_rect.y + 4))
        self.buttons.append((page_prev_rect, "PrevPage", prev_page_cb, False))
        self.buttons.append((page_next_rect, "NextPage", next_page_cb, False))

        y += 32

        # 5x5 Level Grid
        grid_start_x = modal_x + 24
        cell_w, cell_h = 135, 34
        start_idx = self.page * self.levels_per_page
        end_idx = min(tot_levels, start_idx + self.levels_per_page)

        for i in range(start_idx, end_idx):
            row = (i - start_idx) // 5
            col = (i - start_idx) % 5
            cx = grid_start_x + col * (cell_w + 10)
            cy = y + row * (cell_h + 8)
            cell_rect = pygame.Rect(cx, cy, cell_w, cell_h)

            is_current = (i == self.manager.config.current_level_idx)
            is_solved = self.manager.config.is_solved(self.manager.config.current_pack_idx, i)

            if is_current:
                cell_col = (50, 160, 220)
            elif is_solved:
                cell_col = (35, 95, 60)   # Green for solved
            else:
                cell_col = (38, 46, 58)

            pygame.draw.rect(surface, cell_col, cell_rect, border_radius=6)
            border_col = (255, 230, 80) if is_current else ((60, 180, 100) if is_solved else (65, 80, 100))
            pygame.draw.rect(surface, border_col, cell_rect, width=1, border_radius=6)

            badge = " [✓]" if is_solved else ""
            txt_str = f"Level {i + 1}{badge}"
            txt_col = (255, 255, 255) if (is_current or is_solved) else (190, 200, 210)
            t_surf = self.btn_font.render(txt_str, True, txt_col)
            surface.blit(t_surf, (cell_rect.x + (cell_rect.w - t_surf.get_width()) // 2,
                                  cell_rect.y + (cell_rect.h - t_surf.get_height()) // 2))

            def make_lvl_cb(target_lvl):
                def cb():
                    self.manager.set_level(self.manager.config.current_pack_idx, target_lvl)
                    self.close()
                return cb

            self.buttons.append((cell_rect, f"Lvl_{i}", make_lvl_cb(i), is_current))

        y += 5 * (cell_h + 8) + 12

        # Quick Jump Unsolved Buttons
        unsolved_prev_rect = pygame.Rect(modal_x + 24, y, 170, 30)
        unsolved_next_rect = pygame.Rect(modal_x + 204, y, 170, 30)

        def prev_unsolved_cb():
            if self.manager.prev_unsolved_level():
                self.close()

        def next_unsolved_cb():
            if self.manager.next_unsolved_level():
                self.close()

        pygame.draw.rect(surface, (45, 60, 80), unsolved_prev_rect, border_radius=5)
        pygame.draw.rect(surface, (45, 60, 80), unsolved_next_rect, border_radius=5)
        u1 = self.btn_font.render("<< Prev Unsolved", True, (240, 240, 240))
        u2 = self.btn_font.render("Next Unsolved >>", True, (240, 240, 240))
        surface.blit(u1, (unsolved_prev_rect.x + (unsolved_prev_rect.w - u1.get_width()) // 2, unsolved_prev_rect.y + 7))
        surface.blit(u2, (unsolved_next_rect.x + (unsolved_next_rect.w - u2.get_width()) // 2, unsolved_next_rect.y + 7))
        self.buttons.append((unsolved_prev_rect, "PrevUnsolved", prev_unsolved_cb, False))
        self.buttons.append((unsolved_next_rect, "NextUnsolved", next_unsolved_cb, False))

        y += 42

        # --- 3. Game Settings & Configurations (from Rust config) ---
        pygame.draw.line(surface, (55, 70, 90), (modal_x + 20, y), (modal_rect.right - 20, y), 1)
        y += 10

        cfg_lbl = self.font.render("GAME CONFIGURATION (from Rust sokoban-rs):", True, (160, 185, 215))
        surface.blit(cfg_lbl, (modal_x + 24, y))
        y += 24

        cfg = self.manager.config

        # Toggle 1: Auto switch next unsolved
        t1_rect = pygame.Rect(modal_x + 24, y, 340, 28)
        is_t1 = cfg.auto_switch_to_next_unsolved_level

        def toggle_t1():
            cfg.auto_switch_to_next_unsolved_level = not cfg.auto_switch_to_next_unsolved_level
            cfg.save()

        pygame.draw.rect(surface, (35, 75, 45) if is_t1 else (50, 50, 60), t1_rect, border_radius=4)
        t1_txt = f"[{'X' if is_t1 else ' '}] Auto-switch next level on win"
        t1_surf = self.btn_font.render(t1_txt, True, (240, 240, 240))
        surface.blit(t1_surf, (t1_rect.x + 10, t1_rect.y + 6))
        self.buttons.append((t1_rect, "ToggleAutoSwitch", toggle_t1, is_t1))

        # Toggle 2: Chessboard floor shading
        t2_rect = pygame.Rect(modal_x + 380, y, 340, 28)
        is_t2 = (cfg.even_square_shades > 0.0)

        def toggle_t2():
            cfg.even_square_shades = 0.0 if cfg.even_square_shades > 0.0 else 0.15
            cfg.save()

        pygame.draw.rect(surface, (35, 75, 45) if is_t2 else (50, 50, 60), t2_rect, border_radius=4)
        t2_txt = f"[{'X' if is_t2 else ' '}] Chessboard floor pattern"
        t2_surf = self.btn_font.render(t2_txt, True, (240, 240, 240))
        surface.blit(t2_surf, (t2_rect.x + 10, t2_rect.y + 6))
        self.buttons.append((t2_rect, "ToggleChessboard", toggle_t2, is_t2))

        y += 34

        # Toggle 3: Instant Move
        t3_rect = pygame.Rect(modal_x + 24, y, 340, 28)
        is_t3 = cfg.instant_move

        def toggle_t3():
            cfg.instant_move = not cfg.instant_move
            cfg.save()

        pygame.draw.rect(surface, (35, 75, 45) if is_t3 else (50, 50, 60), t3_rect, border_radius=4)
        t3_txt = f"[{'X' if is_t3 else ' '}] Instant move (skip animations)"
        t3_surf = self.btn_font.render(t3_txt, True, (240, 240, 240))
        surface.blit(t3_surf, (t3_rect.x + 10, t3_rect.y + 6))
        self.buttons.append((t3_rect, "ToggleInstantMove", toggle_t3, is_t3))

        # Close button at bottom
        apply_rect = pygame.Rect(modal_rect.right - 170, modal_rect.bottom - 46, 145, 34)
        pygame.draw.rect(surface, (40, 160, 220), apply_rect, border_radius=6)
        ap_surf = self.btn_font.render("Play Level", True, (255, 255, 255))
        surface.blit(ap_surf, (apply_rect.x + (apply_rect.w - ap_surf.get_width()) // 2, apply_rect.y + 8))
        self.buttons.append((apply_rect, "CloseDialog", self.close, False))
