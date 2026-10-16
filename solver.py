"""
Sokoban Solver module supporting Breadth-First Search (BFS) and Depth-First Search (DFS).
Maintains an action search tree structure with 2D positions for visual rendering.
"""

from typing import Any


class TreeNode:
    """Represents a node in the action search tree."""
    __slots__ = (
        'action',
        'boxes',
        'children',
        'depth',
        'in_solution',
        'is_frontier',
        'is_push',
        'nid',
        'pid',
        'player',
        'x',
        'y'
    )

    def __init__(
        self,
        nid: int,
        pid: int | None,
        action: str,
        depth: int,
        player: tuple[int, int],
        boxes: frozenset[tuple[int, int]],
        is_push: bool = False
    ):
        self.nid = nid
        self.pid = pid
        self.action = action          # 'START', 'up', 'down', 'left', 'right'
        self.depth = depth
        self.player = player
        self.boxes = boxes
        self.is_push = is_push
        self.children: list[int] = []
        self.in_solution = False
        self.is_frontier = True
        self.x = 0.0
        self.y = 0.0


class SokobanSolver:
    """
    Step-by-step search engine for Sokoban using BFS or DFS.
    Generates action search tree nodes with layout coordinates for visualization.
    """

    ACTION_OFFSETS = [  # noqa: RUF012
        ('up', (0, -1)),
        ('down', (0, 1)),
        ('left', (-1, 0)),
        ('right', (1, 0))
    ]

    def __init__(self, level, algorithm: str = 'BFS'):
        self.level = level
        self.algorithm = algorithm.upper()  # 'BFS' or 'DFS'
        self.walls: set[tuple[int, int]] = level.walls
        self.goals: set[tuple[int, int]] = level.goals
        self.corners: set[tuple[int, int]] = self._compute_corner_deadlocks()

        init_p = level.initial_player
        init_b = frozenset(level.initial_boxes)

        # Root node
        root = TreeNode(0, None, 'START', 0, init_p, init_b, False)
        root.x = 60.0
        root.y = 300.0

        self.nodes: list[TreeNode] = [root]
        self.frontier: list[int] = [0]       # Queue (BFS) or Stack (DFS)
        self.visited: set[tuple[tuple[int, int], frozenset[tuple[int, int]]]] = {(init_p, init_b)}

        self.finished = False
        self.solved = False
        self.solution_path: list[int] = []
        self.solution_actions: list[str] = []
        self.current_node: int = 0
        self.steps_explored: int = 0

        # Layout tracking per depth level
        self.depth_max_y: dict[int, float] = {0: 300.0}

    def _compute_corner_deadlocks(self) -> set[tuple[int, int]]:
        """Identify non-goal corners that create immediate permanent deadlocks."""
        corners: set[tuple[int, int]] = set()
        for y in range(self.level.height):
            for x in range(self.level.width):
                pos = (x, y)
                if pos in self.walls or pos in self.goals:
                    continue
                up = (x, y - 1) in self.walls
                down = (x, y + 1) in self.walls
                left = (x - 1, y) in self.walls
                right = (x + 1, y) in self.walls
                if (up and left) or (up and right) or (down and left) or (down and right):
                    corners.add(pos)
        return corners

    def step(self) -> tuple[str, Any]:
        """
        Executes one expansion step of the search algorithm.
        Returns:
            ('SOLVED', solution_path) if solved,
            ('SEARCHING', current_node_id) while searching,
            ('FINISHED', None) if frontier exhausted without solution.
        """
        if self.finished or not self.frontier:
            self.finished = True
            return ('FINISHED', None)

        # BFS pops from front (FIFO), DFS pops from back (LIFO)
        if self.algorithm == 'BFS':
            cur_nid = self.frontier.pop(0)
        else:
            cur_nid = self.frontier.pop()

        cur_node = self.nodes[cur_nid]
        cur_node.is_frontier = False
        self.current_node = cur_nid
        self.steps_explored += 1

        p, b, d = cur_node.player, cur_node.boxes, cur_node.depth

        # Goal check: all goals must have a box
        if self.goals <= b:
            self.finished = True
            self.solved = True

            # Trace solution path back to root
            path: list[int] = []
            actions: list[str] = []
            curr: int | None = cur_nid
            while curr is not None:
                path.append(curr)
                self.nodes[curr].in_solution = True
                curr = self.nodes[curr].pid
            path.reverse()

            for nid in path[1:]:
                actions.append(self.nodes[nid].action)

            self.solution_path = path
            self.solution_actions = actions
            return ('SOLVED', path)

        # Expand available actions
        for action, (dx, dy) in self.ACTION_OFFSETS:
            np = (p[0] + dx, p[1] + dy)
            if np in self.walls:
                continue

            is_push = False
            if np in b:
                nb = (np[0] + dx, np[1] + dy)
                # Check obstacle or corner deadlock
                if nb in self.walls or nb in b or nb in self.corners:
                    continue
                nb_set = (b - {np}) | {nb}
                state = (np, nb_set)
                is_push = True
            else:
                state = (np, b)

            if state not in self.visited:
                self.visited.add(state)
                child_id = len(self.nodes)
                child = TreeNode(child_id, cur_nid, action, d + 1, state[0], state[1], is_push)
                cur_node.children.append(child_id)

                # Layout positioning: X increases with depth, Y branches around parent
                child.x = 60.0 + (d + 1) * 75.0
                k = len(cur_node.children)
                desired_y = cur_node.y + (k - 1) * 28.0
                last_y = self.depth_max_y.get(d + 1, cur_node.y - 20.0)
                y = max(desired_y, last_y + 24.0)
                self.depth_max_y[d + 1] = y
                child.y = y

                self.nodes.append(child)
                self.frontier.append(child_id)

        return ('SEARCHING', cur_nid)
