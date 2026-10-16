"""
Sokoban search engine supporting BFS, DFS, Greedy Best-First Search, A*, and IDS.
Maintains an action search tree structure with 2D positions for visual rendering.
Each algorithm supports monodirectional and bidirectional search.
"""

from collections.abc import Iterator
from heapq import heappop, heappush
from typing import Any

Position = tuple[int, int]
Boxes = frozenset[Position]
State = tuple[Position, Boxes]


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
        'side',
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
        is_push: bool = False,
        side: str = 'FORWARD'
    ):
        self.nid = nid
        self.pid = pid
        self.action = action          # 'START', 'GOAL', 'up', 'down', 'left', 'right'
        self.depth = depth
        self.player = player
        self.boxes = boxes
        self.is_push = is_push
        self.side = side
        self.children: list[int] = []
        self.in_solution = False
        self.is_frontier = True
        self.x = 0.0
        self.y = 0.0


class SokobanSolver:
    """
    Step-by-step search engine for Sokoban using BFS, DFS, Greedy, A*, or IDS.
    Generates action search tree nodes with layout coordinates for visualization.
    """

    ALGORITHMS = ('BFS', 'DFS', 'GREEDY', 'A*', 'IDS')
    DIRECTIONS = ('MONODIRECTIONAL', 'BIDIRECTIONAL')

    ACTION_OFFSETS = [  # noqa: RUF012
        ('up', (0, -1)),
        ('down', (0, 1)),
        ('left', (-1, 0)),
        ('right', (1, 0))
    ]

    def __init__(self, level, algorithm: str = 'BFS', direction: str = 'MONODIRECTIONAL'):
        self.level = level
        self.algorithm = algorithm.strip().upper()
        self.algorithm = {
            'ASTAR': 'A*', 'GBFS': 'GREEDY', 'IDDFS': 'IDS'
        }.get(self.algorithm, self.algorithm)
        if self.algorithm not in self.ALGORITHMS:
            raise ValueError(f'Unknown algorithm: {algorithm!r}. Choose from {self.ALGORITHMS}.')
        self.direction = direction.strip().upper()
        if self.direction not in self.DIRECTIONS:
            raise ValueError(f'Unknown direction: {direction!r}. Choose from {self.DIRECTIONS}.')
        self.walls: set[tuple[int, int]] = level.walls
        self.goals: set[tuple[int, int]] = level.goals
        self.floors: set[Position] = getattr(level, 'floors', {
            (x, y) for y in range(level.height) for x in range(level.width)
            if (x, y) not in self.walls
        })
        self.corners: set[tuple[int, int]] = self._compute_corner_deadlocks()

        init_p = level.initial_player
        init_b = frozenset(level.initial_boxes)

        # Root node
        root = TreeNode(0, None, 'START', 0, init_p, init_b, False)
        root.x = 60.0
        root.y = 300.0

        self.nodes: list[TreeNode] = [root]
        # Entries are (priority, node ID); node IDs break heap ties in discovery order.
        self.frontier: list[tuple[int, int]] = []
        self._add_to_frontier(root)
        self.visited: set[tuple[tuple[int, int], frozenset[tuple[int, int]]]] = {(init_p, init_b)}
        self.best_cost: dict[tuple[tuple[int, int], frozenset[tuple[int, int]]], int] = {
            (init_p, init_b): 0
        }

        self.finished = False
        self.solved = False
        self.solution_path: list[int] = []
        self.solution_actions: list[str] = []
        self.current_node: int = 0
        # Counts processed nodes across directions and IDS iterations, excluding seed creation.
        self.steps_explored: int = 0
        self.depth_limit: int = 0
        self._depth_cutoff = False
        self.meeting_nodes: tuple[int, int] | None = None

        # Layout tracking per depth level
        self.depth_max_y: dict[int, float] = {0: 300.0}
        self._bidirectional = None
        if self.direction == 'BIDIRECTIONAL':
            # Import after the shared node/solver classes are defined.
            from bidirectional import BidirectionalSearch
            self._bidirectional = BidirectionalSearch(self)

    def _successors(self, player: Position, boxes: Boxes, *, reverse: bool = False
                    ) -> Iterator[tuple[str, State, bool]]:
        """Yield legal edges, or their exact inverses with the forward action label."""
        for action, (dx, dy) in self.ACTION_OFFSETS:
            if reverse:
                previous = (player[0] - dx, player[1] - dy)
                if previous not in self.floors or previous in boxes:
                    continue
                yield action, (previous, boxes), False
                ahead = (player[0] + dx, player[1] + dy)
                if ahead in boxes and ahead not in self.corners:
                    # Undo a push: the box was previously at the current player tile.
                    yield action, (previous, (boxes - {ahead}) | {player}), True
            else:
                target = (player[0] + dx, player[1] + dy)
                if target not in self.floors:
                    continue
                if target in boxes:
                    beyond = (target[0] + dx, target[1] + dy)
                    if beyond not in self.floors or beyond in boxes or beyond in self.corners:
                        continue
                    yield action, (target, (boxes - {target}) | {beyond}), True
                else:
                    yield action, (target, boxes), False

    def _heuristic(self, boxes: frozenset[tuple[int, int]]) -> int:
        """Lower bound on moves: sum each goal's distance to its nearest box.

        Walls, player travel, and competition for the same box are ignored.
        Allowing goals to share a nearest box underestimates the required pushes,
        even when there are extra boxes. A* reopens states if a cheaper path is found.
        """
        return sum(
            min((abs(gx - bx) + abs(gy - by) for bx, by in boxes), default=0)
            for gx, gy in self.goals
        )

    def _add_to_frontier(self, node: TreeNode) -> None:
        if self.algorithm in ('GREEDY', 'A*'):
            priority = self._heuristic(node.boxes)
            if self.algorithm == 'A*':
                priority += node.depth  # Every walk or push costs one move.
            heappush(self.frontier, (priority, node.nid))
        else:
            self.frontier.append((0, node.nid))

    def _restart_ids(self) -> None:
        """Start the next depth-limited DFS with fresh duplicate records and tree."""
        self.depth_limit += 1
        self._depth_cutoff = False
        root = self.nodes[0]
        root.children.clear()
        root.is_frontier = True
        self.nodes = [root]
        self.frontier = [(0, root.nid)]
        initial_state = (root.player, root.boxes)
        self.visited = {initial_state}
        self.best_cost = {initial_state: 0}
        self.current_node = 0
        self.depth_max_y = {0: root.y}

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
        if self.finished:
            return ('FINISHED', None)
        if self._bidirectional is not None:
            return self._bidirectional.step()

        while True:
            if not self.frontier:
                if self.algorithm == 'IDS' and self._depth_cutoff:
                    self._restart_ids()
                else:
                    self.finished = True
                    return ('FINISHED', None)

            if self.algorithm in ('GREEDY', 'A*'):
                _, cur_nid = heappop(self.frontier)
            elif self.algorithm == 'BFS':
                _, cur_nid = self.frontier.pop(0)
            else:
                _, cur_nid = self.frontier.pop()

            cur_node = self.nodes[cur_nid]
            cur_node.is_frontier = False
            # A shorter route may have superseded this queued A* or IDS node.
            if (self.algorithm not in ('A*', 'IDS') or
                    cur_node.depth == self.best_cost[(cur_node.player, cur_node.boxes)]):
                break

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
        for action, state, is_push in self._successors(p, b):
            if self.algorithm in ('A*', 'IDS'):
                should_visit = d + 1 < self.best_cost.get(state, float('inf'))
            else:
                should_visit = state not in self.visited

            if should_visit:
                if self.algorithm == 'IDS' and d == self.depth_limit:
                    # A valid unexplored successor needs a deeper iteration.
                    self._depth_cutoff = True
                    continue
                self.visited.add(state)
                if self.algorithm in ('A*', 'IDS'):
                    self.best_cost[state] = d + 1
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
                self._add_to_frontier(child)

        return ('SEARCHING', cur_nid)
