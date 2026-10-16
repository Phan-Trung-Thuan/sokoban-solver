"""Incremental bidirectional searches over Sokoban's directed move graph."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from heapq import heappop, heappush
from itertools import combinations
from math import inf

from solver import Boxes, SokobanSolver, State, TreeNode


@dataclass
class _SearchSide:
    name: str
    frontier: list[tuple[int, int]] = field(default_factory=list)
    best: dict[State, int] = field(default_factory=dict)
    cutoff: bool = False


class BidirectionalSearch:
    """Coordinate two searches while retaining the game's step/replay interface.

    BFS uses the sum of the two frontier depths as a stopping bound. A* uses
    the maximum of the two admissible frontier f bounds, rather than stopping
    at its first meeting. IDS exhausts total move budgets in increasing order,
    split between forward and backward depth-limited DFS.
    """

    def __init__(self, solver: SokobanSolver):
        self.solver = solver
        self.initial = (solver.nodes[0].player, solver.nodes[0].boxes)
        self.forward_steps = 0
        self.backward_steps = 0
        self._reset_iteration()

    def _reset_iteration(self) -> None:
        solver = self.solver
        root = solver.nodes[0]
        root.children.clear()
        root.is_frontier = True
        solver.nodes = [root]
        solver.current_node = 0
        solver.meeting_nodes = None
        solver.visited = {self.initial}
        solver.best_cost = {self.initial: 0}
        self.forward = _SearchSide('FORWARD')
        self.backward = _SearchSide('BACKWARD')
        solver.frontier = self.forward.frontier
        solver.backward_frontier = self.backward.frontier
        self.forward.best[self.initial] = 0
        self._enqueue(self.forward, root)
        self._layout_y = {('FORWARD', 0): root.y}
        self._goal_roots = 0
        self._seeds = self._goal_states()
        self._seeded = False
        self._next_forward = True
        self._candidate: tuple[int, int] | None = None
        self._candidate_cost = inf

    def _goal_states(self) -> Iterator[State]:
        """All goal box arrangements and free player tiles, streamed incrementally."""
        solver = self.solver
        extra_count = len(self.initial[1]) - len(solver.goals)
        if extra_count < 0:
            return
        box_tiles = solver.floors | solver.goals | set(self.initial[1])
        for extra in combinations(sorted(box_tiles - solver.goals), extra_count):
            boxes = frozenset(solver.goals | set(extra))
            for player in sorted(solver.floors - boxes):
                yield player, boxes

    def _heuristic(self, side: _SearchSide, boxes: Boxes) -> int:
        if side is self.forward:
            return self.solver._heuristic(boxes)
        # Reverse search must restore every initial box, not merely cover goals.
        return sum(
            min((abs(tx - bx) + abs(ty - by) for bx, by in boxes), default=0)
            for tx, ty in self.initial[1]
        )

    def _enqueue(self, side: _SearchSide, node: TreeNode) -> None:
        algorithm = self.solver.algorithm
        if algorithm in ('DFS', 'IDS'):
            side.frontier.append((0, node.nid))
        else:
            priority = node.depth if algorithm == 'BFS' else self._heuristic(side, node.boxes)
            if algorithm == 'A*':
                priority += node.depth
            heappush(side.frontier, (priority, node.nid))

    def _discard_stale(self, side: _SearchSide) -> None:
        while side.frontier:
            entry = side.frontier[-1] if self.solver.algorithm in ('DFS', 'IDS') else side.frontier[0]
            node = self.solver.nodes[entry[1]]
            if side.best[(node.player, node.boxes)] == node.nid:
                return
            node.is_frontier = False
            if self.solver.algorithm in ('DFS', 'IDS'):
                side.frontier.pop()
            else:
                heappop(side.frontier)

    def _node(self, side: _SearchSide, state: State, pid: int | None,
              action: str, is_push: bool = False) -> TreeNode:
        solver = self.solver
        parent = solver.nodes[pid] if pid is not None else None
        depth = parent.depth + 1 if parent else 0
        node = TreeNode(len(solver.nodes), pid, action, depth, *state, is_push, side.name)
        node.x = 60 + depth * 75 if side is self.forward else 900 - depth * 75
        if parent:
            parent.children.append(node.nid)
            desired_y = parent.y + (len(parent.children) - 1) * 28
            last_y = self._layout_y.get((side.name, depth), parent.y - 24)
            node.y = max(desired_y, last_y + 24)
        else:
            node.y = 300 + self._goal_roots * 28
            self._goal_roots += 1
        self._layout_y[(side.name, depth)] = node.y
        solver.nodes.append(node)
        return node

    def _consider_meeting(self, side: _SearchSide, state: State, nid: int) -> None:
        other = self.backward if side is self.forward else self.forward
        other_id = other.best.get(state)
        if other_id is None:
            return
        pair = (nid, other_id) if side is self.forward else (other_id, nid)
        cost = sum(self.solver.nodes[index].depth for index in pair)
        if cost < self._candidate_cost:
            self._candidate = pair
            self._candidate_cost = cost
            self.solver.meeting_nodes = pair

    def _can_finish(self) -> bool:
        if self._candidate is None:
            return False
        algorithm = self.solver.algorithm
        if algorithm in ('DFS', 'GREEDY', 'IDS'):
            return True
        forward_bound = self.forward.frontier[0][0] if self.forward.frontier else inf
        backward_bound = self.backward.frontier[0][0] if self.backward.frontier else inf
        bound = (forward_bound + backward_bound if algorithm == 'BFS' else
                 max(forward_bound, backward_bound))
        return self._candidate_cost <= bound

    def _finish(self) -> tuple[str, list[int]]:
        solver = self.solver
        assert self._candidate is not None
        forward_id, backward_id = self._candidate
        path = []
        current = forward_id
        while current is not None:
            path.append(current)
            current = solver.nodes[current].pid
        path.reverse()
        # Backward links point toward a goal. Build ordinary forward replay nodes
        # so the existing board controls and push counts retain their semantics.
        current = backward_id
        while True:
            backward = solver.nodes[current]
            backward.in_solution = True
            if backward.pid is None:
                break
            parent = solver.nodes[backward.pid]
            replay = self._node(self.forward, (parent.player, parent.boxes),
                                path[-1], backward.action, backward.is_push)
            replay.is_frontier = False
            path.append(replay.nid)
            current = backward.pid
        for nid in path:
            solver.nodes[nid].in_solution = True
        solver.solution_path = path
        solver.solution_actions = [solver.nodes[nid].action for nid in path[1:]]
        solver.finished = True
        solver.solved = True
        return 'SOLVED', path

    def step(self) -> tuple[str, int | list[int] | None]:
        solver = self.solver
        if solver.goals <= self.initial[1]:
            solver.steps_explored += 1
            self.forward_steps += 1
            solver.nodes[0].is_frontier = False
            solver.nodes[0].in_solution = True
            solver.finished = solver.solved = True
            solver.solution_path = [0]
            return 'SOLVED', [0]

        if not self._seeded:
            state = next(self._seeds, None)
            if state is not None:
                root = self._node(self.backward, state, None, 'GOAL')
                self.backward.best[state] = root.nid
                self._enqueue(self.backward, root)
                return 'SEARCHING', solver.current_node
            self._seeded = True

        self._discard_stale(self.forward)
        self._discard_stale(self.backward)
        if self._can_finish():
            return self._finish()

        if solver.algorithm == 'IDS':
            # An exhausted side without cutoffs has explored its entire reachable
            # graph; otherwise both bounded searches must finish before deepening.
            complete = any(not side.frontier and not side.cutoff
                           for side in (self.forward, self.backward))
            if not complete and not self.forward.frontier and not self.backward.frontier:
                solver.depth_limit += 1
                self._reset_iteration()
                return 'SEARCHING', 0
        else:
            complete = not self.forward.frontier or not self.backward.frontier
        if complete:
            solver.finished = True
            for side in (self.forward, self.backward):
                for _, nid in side.frontier:
                    solver.nodes[nid].is_frontier = False
                side.frontier.clear()
            return 'FINISHED', None

        side = self.forward if self._next_forward else self.backward
        if not side.frontier:
            side = self.backward if side is self.forward else self.forward
        self._next_forward = side is self.backward
        _, nid = (side.frontier.pop() if solver.algorithm in ('DFS', 'IDS') else
                  heappop(side.frontier))
        node = solver.nodes[nid]
        node.is_frontier = False
        solver.current_node = nid
        solver.steps_explored += 1
        if side is self.forward:
            self.forward_steps += 1
        else:
            self.backward_steps += 1

        for action, state, is_push in solver._successors(
                node.player, node.boxes, reverse=side is self.backward):
            previous_id = side.best.get(state)
            if previous_id is not None:
                if solver.algorithm not in ('A*', 'IDS'):
                    continue
                if solver.nodes[previous_id].depth <= node.depth + 1:
                    continue
            if solver.algorithm == 'IDS':
                bound = solver.depth_limit // 2 if side is self.forward else (solver.depth_limit + 1) // 2
                if node.depth == bound:
                    side.cutoff = True
                    continue
            child = self._node(side, state, nid, action, is_push)
            side.best[state] = child.nid
            self._enqueue(side, child)
            if side is self.forward:
                solver.visited.add(state)
                solver.best_cost[state] = child.depth
            self._consider_meeting(side, state, child.nid)

        self._discard_stale(self.forward)
        self._discard_stale(self.backward)
        if self._can_finish():
            return self._finish()
        return 'SEARCHING', nid
