"""
Action Search Tree Visualizer for Sokoban.
Renders an interactive tree diagram of search actions with smooth camera panning,
zooming, node color coding, and real-time solution path highlights.
"""

import math
import pygame
from solver import SokobanSolver, TreeNode

# Action symbol mappings
ACTION_SYMBOLS = {
    'up': 'U',
    'down': 'D',
    'left': 'L',
    'right': 'R',
    'START': 'S'
}

ARROW_SYMBOLS = {
    'up': '^',
    'down': 'v',
    'left': '<',
    'right': '>',
    'START': 'S',
    'GOAL': 'G'
}


class TreeViewer:
    """
    Renders the action search tree within a specified screen rectangle.
    Supports free panning and zooming, with optional automatic search following.
    """

    def __init__(self):
        self.rect = pygame.Rect(0, 0, 100, 100)
        self.cam_x: float = 60.0
        self.cam_y: float = 300.0
        self.target_cam_x: float = 60.0
        self.target_cam_y: float = 300.0
        self.zoom: float = 1.0
        self.target_zoom: float = 1.0

        self.auto_follow = False
        self.dragging = False
        self.drag_start_pos = (0, 0)
        self.drag_start_cam = (0.0, 0.0)

        # Fonts
        self.font_header: pygame.font.Font | None = None
        self.font_node: pygame.font.Font | None = None
        self.font_legend: pygame.font.Font | None = None

        self._pulse_timer = 0.0

    def init_fonts(self):
        if self.font_header is None:
            self.font_header = pygame.font.SysFont("consolas", 14, bold=True)
            self.font_node = pygame.font.SysFont("consolas", 11, bold=True)
            self.font_legend = pygame.font.SysFont("consolas", 12, bold=False)

    def set_rect(self, rect: pygame.Rect):
        self.rect = rect

    def reset_view(self):
        self.auto_follow = False
        self.dragging = False
        self.cam_x = 100.0
        self.cam_y = 300.0
        self.target_cam_x = 100.0
        self.target_cam_y = 300.0
        self.zoom = 1.0
        self.target_zoom = 1.0

    def _stop_following(self):
        self.auto_follow = False
        self.target_cam_x = self.cam_x
        self.target_cam_y = self.cam_y

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                self._stop_following()
                self.target_zoom = self.zoom
                self.dragging = True
                self.drag_start_pos = event.pos
                self.drag_start_cam = (self.cam_x, self.cam_y)
            elif event.button == 4 and self.rect.collidepoint(event.pos):  # Scroll up -> Zoom in
                self._stop_following()
                self.target_zoom = min(2.5, self.target_zoom * 1.15)
            elif event.button == 5 and self.rect.collidepoint(event.pos):  # Scroll down -> Zoom out
                self._stop_following()
                self.target_zoom = max(0.25, self.target_zoom / 1.15)
            elif event.button == 3 and self.rect.collidepoint(event.pos):  # Right click -> reset
                self.reset_view()

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                dx = event.pos[0] - self.drag_start_pos[0]
                dy = event.pos[1] - self.drag_start_pos[1]
                self.cam_x = self.drag_start_cam[0] - dx / self.zoom
                self.cam_y = self.drag_start_cam[1] - dy / self.zoom
                self.target_cam_x = self.cam_x
                self.target_cam_y = self.cam_y

        elif event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()) and event.y:
                self._stop_following()
                self.target_zoom = max(0.25, min(2.5, self.target_zoom * 1.15 ** event.y))

        elif event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                if self.auto_follow:
                    self._stop_following()
                else:
                    self.auto_follow = True

    def update(self, dt: float, solver: SokobanSolver | None, replay_nid: int | None = None):
        self._pulse_timer += dt * 5.0

        # Following is opt-in; manual navigation keeps its position during search/replay.
        if self.auto_follow and not self.dragging and solver and solver.nodes:
            if replay_nid is not None and replay_nid < len(solver.nodes):
                target_node = solver.nodes[replay_nid]
                self.target_cam_x = target_node.x
                self.target_cam_y = target_node.y
            elif not solver.finished and solver.current_node < len(solver.nodes):
                target_node = solver.nodes[solver.current_node]
                self.target_cam_x = target_node.x
                self.target_cam_y = target_node.y

        # Smooth navigation also works before a solver exists and after completion.
        if not self.dragging:
            self.cam_x += (self.target_cam_x - self.cam_x) * min(1.0, dt * 6.0)
            self.cam_y += (self.target_cam_y - self.cam_y) * min(1.0, dt * 6.0)
            self.zoom += (self.target_zoom - self.zoom) * min(1.0, dt * 8.0)

    def world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        cx = self.rect.x + self.rect.width // 2
        cy = self.rect.y + self.rect.height // 2
        sx = cx + int((wx - self.cam_x) * self.zoom)
        sy = cy + int((wy - self.cam_y) * self.zoom)
        return (sx, sy)

    def draw(
        self,
        surface: pygame.Surface,
        solver: SokobanSolver | None,
        replay_nid: int | None = None
    ):
        self.init_fonts()

        # Clip drawing inside tree rect
        clip_rect = self.rect
        surface.set_clip(clip_rect)

        # Background
        pygame.draw.rect(surface, (16, 20, 28), clip_rect)

        # Subtle grid background
        grid_step = int(60 * self.zoom)
        if grid_step > 15:
            cx = self.rect.x + self.rect.width // 2
            cy = self.rect.y + self.rect.height // 2
            start_x = self.rect.x + int((-(self.cam_x % 60) * self.zoom)) % grid_step
            start_y = self.rect.y + int((-(self.cam_y % 60) * self.zoom)) % grid_step
            for x in range(start_x, self.rect.right, grid_step):
                pygame.draw.line(surface, (24, 30, 42), (x, self.rect.top), (x, self.rect.bottom), 1)
            for y in range(start_y, self.rect.bottom, grid_step):
                pygame.draw.line(surface, (24, 30, 42), (self.rect.left, y), (self.rect.right, y), 1)

        if solver and solver.nodes:
            nodes = solver.nodes
            cur_active_id = solver.current_node

            # Keep the active branch and solution visible even in large searches.
            max_draw = min(len(nodes), 2000)
            drawn_ids = set(range(max_draw))
            drawn_ids.update(solver.solution_path)
            current = cur_active_id
            while current is not None and current not in drawn_ids:
                drawn_ids.add(current)
                current = nodes[current].pid
            if solver.meeting_nodes:
                for meeting in solver.meeting_nodes:
                    current = meeting
                    while current is not None:
                        drawn_ids.add(current)
                        current = nodes[current].pid
            drawn_nodes = [nodes[nid] for nid in sorted(drawn_ids)]

            if solver.meeting_nodes:
                first, second = (nodes[nid] for nid in solver.meeting_nodes)
                pygame.draw.line(surface, (200, 130, 255),
                                 self.world_to_screen(first.x, first.y),
                                 self.world_to_screen(second.x, second.y), 2)

            # 1. Draw connecting lines
            for node in drawn_nodes:
                if node.pid is not None and node.pid < len(nodes):
                    parent = nodes[node.pid]
                    p_pos = self.world_to_screen(parent.x, parent.y)
                    c_pos = self.world_to_screen(node.x, node.y)

                    # Highlight solution branches in glowing green
                    if node.in_solution and parent.in_solution:
                        pygame.draw.line(surface, (40, 240, 110), p_pos, c_pos, max(2, int(3 * self.zoom)))
                    else:
                        line_col = (55, 75, 100)
                        pygame.draw.line(surface, line_col, p_pos, c_pos, max(1, int(1 * self.zoom)))

            # 2. Draw nodes
            base_radius = max(6, min(22, int(11 * self.zoom)))
            pulse_offset = int(math.sin(self._pulse_timer) * 3)

            for node in drawn_nodes:
                sx, sy = self.world_to_screen(node.x, node.y)

                # Skip offscreen nodes
                if not (self.rect.left - 40 <= sx <= self.rect.right + 40 and
                        self.rect.top - 40 <= sy <= self.rect.bottom + 40):
                    continue

                radius = base_radius
                is_active = (node.nid == cur_active_id and not solver.finished)
                is_replay = (replay_nid is not None and node.nid == replay_nid)

                # Determine color
                if is_replay:
                    color = (255, 150, 20)      # Replay active: Bright Orange
                    radius += 3
                elif is_active:
                    color = (255, 220, 50)      # Active expanding: Bright Yellow
                    radius += 2
                elif node.in_solution:
                    color = (40, 230, 110)      # Solution path: Emerald Green
                    radius += 2
                elif node.nid == 0:
                    color = (160, 110, 255)     # Root: Purple
                elif node.is_frontier:
                    color = ((185, 120, 255) if node.side == 'BACKWARD' else
                             (0, 200, 255))
                else:
                    color = (80, 100, 125)      # Visited: Slate Blue

                # Outer pulse ring for active or replay node
                if is_active or is_replay:
                    ring_col = (255, 240, 100) if is_active else (255, 180, 50)
                    pygame.draw.circle(surface, ring_col, (sx, sy), radius + 4 + pulse_offset, 2)

                # Node circle
                pygame.draw.circle(surface, color, (sx, sy), radius)
                pygame.draw.circle(surface, (255, 255, 255), (sx, sy), radius, 1)

                # If push action, draw a small inner ring/box indicator
                if node.is_push:
                    pygame.draw.circle(surface, (255, 180, 80), (sx, sy), max(2, radius // 2), 1)

                # Action letter/symbol inside circle if zoom is sufficient
                if self.zoom >= 0.7:
                    sym = ARROW_SYMBOLS.get(node.action, node.action[:1].upper())
                    txt_col = (20, 20, 20) if (is_active or is_replay or node.in_solution) else (240, 240, 240)
                    txt = self.font_node.render(sym, True, txt_col)
                    surface.blit(txt, (sx - txt.get_width() // 2, sy - txt.get_height() // 2))

        # Reset clip for overlay banners
        surface.set_clip(None)

        # Panel Border
        pygame.draw.rect(surface, (60, 75, 95), clip_rect, 2)

        # Top Banner / Status inside tree panel
        banner_h = 52
        banner_rect = pygame.Rect(clip_rect.x, clip_rect.y, clip_rect.width, banner_h)
        pygame.draw.rect(surface, (12, 16, 24), banner_rect)
        pygame.draw.line(surface, (50, 65, 85), (banner_rect.left, banner_rect.bottom), (banner_rect.right, banner_rect.bottom), 1)

        algo_name = solver.algorithm if solver else "BFS"
        if solver and solver.direction == "BIDIRECTIONAL":
            algo_name = f"Bi {algo_name}"
        if solver and solver.algorithm == "IDS":
            algo_name += f" limit {solver.depth_limit}"
        status_txt = "IDLE"
        if solver:
            if solver.solved:
                status_txt = f"SOLVED! ({len(solver.solution_actions)} moves)"
            elif solver.finished:
                status_txt = "NO SOLUTION"
            else:
                status_txt = "SEARCHING..."

        title_str = f"ACTION SEARCH TREE [{algo_name}] - {status_txt}"
        title_surf = self.font_header.render(title_str, True, (240, 240, 240))
        title_y = banner_rect.y + (32 - title_surf.get_height()) // 2
        surface.blit(title_surf, (banner_rect.x + 10, title_y))
        detail_text = (f"States checked: {solver.steps_explored:,}" if solver else
                       "Drag: pan | Wheel: zoom | Right-click: reset")
        detail_surf = self.font_legend.render(detail_text, True, (180, 195, 215))
        surface.blit(detail_surf, (banner_rect.x + 10, banner_rect.y + 32))
        camera_text = f"Camera: {'Follow' if self.auto_follow else 'Free'} (F)"
        camera_surf = self.font_legend.render(camera_text, True, (180, 195, 215))
        surface.blit(camera_surf, (
            banner_rect.right - camera_surf.get_width() - 10, banner_rect.y + 32
        ))

        # Bottom Legend Bar
        legend_h = 24
        legend_rect = pygame.Rect(clip_rect.x, clip_rect.bottom - legend_h, clip_rect.width, legend_h)
        pygame.draw.rect(surface, (12, 16, 24), legend_rect)
        pygame.draw.line(surface, (50, 65, 85), (legend_rect.left, legend_rect.top), (legend_rect.right, legend_rect.top), 1)

        legend_items = [
            ((255, 220, 50), "Active"),
            ((0, 200, 255), "Frontier"),
            ((80, 100, 125), "Explored"),
            ((40, 230, 110), "Solution"),
            ((255, 150, 20), "Replay Step")
        ]
        cur_x = legend_rect.x + 12
        for dot_col, label in legend_items:
            pygame.draw.circle(surface, dot_col, (cur_x + 5, legend_rect.y + legend_h // 2), 5)
            lbl_surf = self.font_legend.render(label, True, (200, 205, 215))
            surface.blit(lbl_surf, (cur_x + 14, legend_rect.y + (legend_h - lbl_surf.get_height()) // 2))
            cur_x += 18 + lbl_surf.get_width() + 14
