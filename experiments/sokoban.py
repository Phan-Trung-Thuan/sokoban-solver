"""
sokoban.py - Bộ giải Sokoban cải tiến (chạy độc lập, không cần giao diện).

Đồ án học phần Trí tuệ nhân tạo nâng cao - Đề tài Sokoban.
Các điểm khác so với solver.py của chương trình nhóm:
  * Mô hình hoá theo lần đẩy: mỗi nút là một cách xếp khối cùng vùng người
    chơi tới được; vị trí người chơi được chuẩn hoá về ô có chỉ số nhỏ nhất
    trong vùng đó. Ô được đánh chỉ số i = r*W + c.
  * Tiền xử lý ô chết và bảng khoảng cách đẩy D(b, g) bằng BFS kéo ngược;
    kiểm tra đóng băng 2x2 sau mỗi lần đẩy.
  * BFS, DFS, IDS (có bảng chuyển vị), Greedy và A* với ba heuristic h1, h2, h3.
    Bài toán ghép cặp giải bằng scipy.optimize.linear_sum_assignment.
  * Giới hạn số nút và thời gian; đếm nút mở rộng, nút sinh ra, biên lớn nhất.
  * Lời giải dựng lại thành chuỗi LURD và được kiểm tra bằng hàm mô phỏng độc lập.

Cách dùng:
    python3 sokoban.py <tệp.xsb> <số thứ tự màn> <giải thuật> [--no-deadlock]
    giải thuật: BFS, DFS, IDS, GREEDY-H3, ASTAR-H1, ASTAR-H2, ASTAR-H3
"""
from __future__ import annotations

import heapq
import sys
import time
from collections import deque

import numpy as np
from scipy.optimize import linear_sum_assignment

INF = 10 ** 9


# ----------------------------------------------------------------------------
# Đọc màn chơi
# ----------------------------------------------------------------------------
def parse_xsb(path: str) -> list[tuple[str, list[str]]]:
    """Đọc tệp XSB, trả về danh sách (tiêu đề, các dòng bản đồ)."""
    levels, grid, title = [], [], ''
    with open(path, encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = raw.rstrip('\n\r')
            if line.strip() and set(line) <= set('#@+$*. -_'):
                grid.append(line.replace('-', ' ').replace('_', ' '))
            else:
                if grid:
                    levels.append((title, grid))
                    grid = []
                if line.strip().startswith(';'):
                    title = line.strip()[1:].strip()
                elif line.strip():
                    title = line.strip()
    if grid:
        levels.append((title, grid))
    return levels


class Level:
    def __init__(self, rows: list[str], title: str = ''):
        self.title = title
        self.H = len(rows)
        self.W = max(len(r) for r in rows)
        W = self.W
        walls, goals, boxes, player = set(), set(), set(), None
        for r, row in enumerate(rows):
            for c in range(W):
                ch = row[c] if c < len(row) else ' '
                i = r * W + c
                if ch == '#':
                    walls.add(i)
                if ch in '.+*':
                    goals.add(i)
                if ch in '$*':
                    boxes.add(i)
                if ch in '@+':
                    player = i
        if player is None:
            raise ValueError('Màn chơi không có người chơi')
        self.walls = walls
        # Sàn = vùng người chơi tới được từ vị trí ban đầu (bỏ qua khối).
        floor, q = {player}, deque([player])
        while q:
            p = q.popleft()
            for d in self.dirs():
                n = p + d
                if self.inside(p, d) and n not in walls and n not in floor:
                    floor.add(n)
                    q.append(n)
        self.floor = floor
        self.goals = frozenset(g for g in goals if g in floor)
        self.goal_list = sorted(self.goals)
        self.init_boxes = frozenset(boxes)
        self.init_player = player
        self._pre_compute()

    # Hướng: (ký hiệu, độ dời chỉ số)
    def dirs(self):
        return (-self.W, self.W, -1, 1)

    def inside(self, p: int, d: int) -> bool:
        r, c = divmod(p, self.W)
        if d == -1:
            return c > 0
        if d == 1:
            return c < self.W - 1
        if d == -self.W:
            return r > 0
        return r < self.H - 1

    def neighbors(self, p: int):
        for ch, d in zip('udlr', self.dirs()):
            if self.inside(p, d):
                yield ch, d, p + d

    def _pull_bfs(self, goal: int) -> dict[int, int]:
        """Khoảng cách đẩy nhỏ nhất từ mọi ô tới goal: kéo ngược khối."""
        dist = {goal: 0}
        q = deque([goal])
        while q:
            b = q.popleft()
            for _, d, _ in self.neighbors(b):
                nb, p = b - d, b - 2 * d  # khối về nb, người lùi về p
                if nb in self.floor and p in self.floor and nb not in dist:
                    dist[nb] = dist[b] + 1
                    q.append(nb)
        return dist

    def _pre_compute(self):
        tables = [self._pull_bfs(g) for g in self.goal_list]
        self.push_dist = {}
        for b in self.floor:
            row = [t.get(b, INF) for t in tables]
            if min(row) < INF:
                self.push_dist[b] = row
        self.dead = {b for b in self.floor if b not in self.push_dist}
        self.goal_rc = [divmod(g, self.W) for g in self.goal_list]


# ----------------------------------------------------------------------------
# Heuristic
# ----------------------------------------------------------------------------
def manhattan_rows(lv: Level, boxes):
    rows = []
    for b in boxes:
        r, c = divmod(b, lv.W)
        rows.append([abs(r - gr) + abs(c - gc) for gr, gc in lv.goal_rc])
    return rows


def h1_nearest(lv: Level, boxes) -> int:
    return sum(min(row) for row in manhattan_rows(lv, boxes))


def h2_matching_manhattan(lv: Level, boxes) -> int:
    rows = np.array(manhattan_rows(lv, boxes))
    r, c = linear_sum_assignment(rows)
    return int(rows[r, c].sum())


def h3_matching_push(lv: Level, boxes) -> int:
    rows = [lv.push_dist.get(b, [INF] * len(lv.goal_list)) for b in boxes]
    if any(min(row) >= INF for row in rows):
        return INF
    a = np.array(rows, dtype=np.int64)
    r, c = linear_sum_assignment(a)
    s = int(a[r, c].sum())
    return INF if s >= INF else s  # INF nếu có ô chết


HEURISTICS = {'H1': h1_nearest, 'H2': h2_matching_manhattan, 'H3': h3_matching_push}


# ----------------------------------------------------------------------------
# Mô hình theo lần đẩy
# ----------------------------------------------------------------------------
class PushModel:
    def __init__(self, lv: Level, deadlock: bool = True):
        self.lv = lv
        self.deadlock = deadlock

    def reach(self, player: int, boxes) -> set[int]:
        lv, seen, q = self.lv, {player}, deque([player])
        while q:
            p = q.popleft()
            for _, _, n in lv.neighbors(p):
                if n in lv.floor and n not in boxes and n not in seen:
                    seen.add(n)
                    q.append(n)
        return seen

    def initial(self):
        b = self.lv.init_boxes
        return (min(self.reach(self.lv.init_player, b)), b)

    def is_goal(self, state) -> bool:
        return state[1] == self.lv.goals

    def frozen_2x2(self, boxes, nb: int) -> bool:
        """Đóng băng 2x2: một hình vuông 2x2 chứa nb toàn tường/khối, có khối không nằm trên đích."""
        lv, W = self.lv, self.lv.W
        r, c = divmod(nb, W)
        for dr in (-1, 0):
            for dc in (-1, 0):
                rr, cc = r + dr, c + dc
                if rr < 0 or cc < 0 or rr + 1 >= lv.H or cc + 1 >= W:
                    continue
                cells = (rr * W + cc, rr * W + cc + 1, (rr + 1) * W + cc, (rr + 1) * W + cc + 1)
                if all(x in boxes or x not in lv.floor for x in cells):
                    if any(x in boxes and x not in lv.goals for x in cells):
                        return True
        return False

    def successors(self, state):
        """Sinh (trạng thái mới, (khối, hướng)) cho mọi lần đẩy hợp lệ."""
        lv = self.lv
        player, boxes = state
        area = self.reach(player, boxes)
        out = []
        for b in sorted(boxes):
            for ch, d, nb in lv.neighbors(b):
                if b - d not in area:          # người phải đứng phía sau khối
                    continue
                if nb not in lv.floor or nb in boxes:
                    continue
                if self.deadlock and nb in lv.dead:
                    continue
                nboxes = (boxes - {b}) | {nb}
                if self.deadlock and self.frozen_2x2(nboxes, nb):
                    continue
                npl = min(self.reach(b, nboxes))
                out.append(((npl, frozenset(nboxes)), (b, d)))
        return out


# ----------------------------------------------------------------------------
# Kết quả
# ----------------------------------------------------------------------------
class Result:
    def __init__(self):
        self.status = 'NOSOL'      # SOLVED / NOSOL / NODE_LIMIT / TIMEOUT
        self.expanded = 0
        self.generated = 0
        self.max_frontier = 0
        self.pushes_list = []      # danh sách (khối, hướng)
        self.lurd = ''
        self.valid = None
        self.time = 0.0

    def as_dict(self):
        return {
            'status': self.status, 'expanded': self.expanded, 'generated': self.generated,
            'max_frontier': self.max_frontier,
            'pushes': len(self.pushes_list) if self.status == 'SOLVED' else None,
            'moves': len(self.lurd) if self.status == 'SOLVED' else None,
            'valid': self.valid, 'time': round(self.time, 4), 'lurd': self.lurd,
        }


class Limit(Exception):
    pass


def _path(parent, s):
    acts = []
    while parent[s] is not None:
        ps, a = parent[s]
        acts.append(a)
        s = ps
    return acts[::-1]


def solve(lv: Level, algorithm: str, deadlock: bool = True,
          node_limit: int = 300_000, time_limit: float = 60.0) -> Result:
    alg = algorithm.upper()
    m = PushModel(lv, deadlock)
    res = Result()
    t0 = time.perf_counter()

    def tick():
        if res.expanded >= node_limit:
            raise Limit('NODE_LIMIT')
        if time.perf_counter() - t0 > time_limit:
            raise Limit('TIMEOUT')

    start = m.initial()
    try:
        if alg in ('BFS', 'DFS'):
            parent = {start: None}
            frontier = deque([start])
            while frontier:
                s = frontier.popleft() if alg == 'BFS' else frontier.pop()
                tick()
                res.expanded += 1
                if m.is_goal(s):
                    res.status, res.pushes_list = 'SOLVED', _path(parent, s)
                    break
                for ns, a in m.successors(s):
                    res.generated += 1
                    if ns not in parent:
                        parent[ns] = (s, a)
                        frontier.append(ns)
                res.max_frontier = max(res.max_frontier, len(frontier))
        elif alg in ('GREEDY-H3', 'ASTAR-H1', 'ASTAR-H2', 'ASTAR-H3'):
            hf = HEURISTICS[alg.split('-')[1]]
            greedy = alg.startswith('GREEDY')
            h0 = hf(lv, start[1])
            if h0 < INF:
                g_best = {start: 0}
                parent = {start: None}
                cnt = 0
                heap = [(h0 if greedy else h0, cnt, 0, start)]
                closed = set()
                while heap:
                    _, _, g, s = heapq.heappop(heap)
                    if s in closed:
                        continue
                    tick()
                    closed.add(s)
                    res.expanded += 1
                    if m.is_goal(s):
                        res.status, res.pushes_list = 'SOLVED', _path(parent, s)
                        break
                    for ns, a in m.successors(s):
                        res.generated += 1
                        ng = g + 1
                        if ns in closed or ng >= g_best.get(ns, INF):
                            continue
                        h = hf(lv, ns[1])
                        if h >= INF:
                            continue
                        g_best[ns] = ng
                        parent[ns] = (s, a)
                        cnt += 1
                        heapq.heappush(heap, (h if greedy else ng + h, cnt, ng, ns))
                    res.max_frontier = max(res.max_frontier, len(heap))
        elif alg == 'IDS':
            limit = 0
            while True:
                tt = {start: 0}   # bảng chuyển vị: trạng thái -> độ sâu nhỏ nhất đã gặp trong vòng lặp này
                cutoff = False
                tick()
                res.expanded += 1
                if m.is_goal(start):
                    res.status = 'SOLVED'
                    break
                stack = [(start, iter(m.successors(start)))] if limit > 0 else []
                if limit == 0:
                    cutoff = True
                acts = []
                found = False
                while stack:
                    s, it = stack[-1]
                    try:
                        ns, a = next(it)
                    except StopIteration:
                        stack.pop()
                        if acts:
                            acts.pop()
                        continue
                    res.generated += 1
                    depth = len(stack)
                    if tt.get(ns, INF) <= depth:
                        continue
                    tt[ns] = depth
                    tick()
                    res.expanded += 1
                    if m.is_goal(ns):
                        res.status, res.pushes_list = 'SOLVED', acts + [a]
                        found = True
                        break
                    if depth < limit:
                        stack.append((ns, iter(m.successors(ns))))
                        acts.append(a)
                        res.max_frontier = max(res.max_frontier, len(stack))
                    else:
                        cutoff = True
                if found or not cutoff:
                    break
                limit += 1
        else:
            raise ValueError('Giải thuật không hợp lệ: ' + algorithm)
    except Limit as e:
        res.status = str(e)
    res.time = time.perf_counter() - t0
    if res.status == 'SOLVED':
        res.lurd = to_lurd(lv, res.pushes_list)
        res.valid = simulate(lv, res.lurd)
    return res


# ----------------------------------------------------------------------------
# Dựng chuỗi LURD và kiểm tra lời giải
# ----------------------------------------------------------------------------
def _walk(lv: Level, src: int, dst: int, boxes) -> str:
    if src == dst:
        return ''
    prev = {src: None}
    q = deque([src])
    while q:
        p = q.popleft()
        for ch, _, n in lv.neighbors(p):
            if n in lv.floor and n not in boxes and n not in prev:
                prev[n] = (p, ch)
                if n == dst:
                    out = []
                    while prev[n] is not None:
                        n, c = prev[n]
                        out.append(c)
                    return ''.join(out[::-1])
                q.append(n)
    raise RuntimeError('Không tìm được đường đi bộ')


def to_lurd(lv: Level, pushes) -> str:
    player, boxes = lv.init_player, set(lv.init_boxes)
    letter = {-lv.W: 'u', lv.W: 'd', -1: 'l', 1: 'r'}
    out = []
    for b, d in pushes:
        out.append(_walk(lv, player, b - d, boxes))
        out.append(letter[d].upper())
        boxes.remove(b)
        boxes.add(b + d)
        player = b
    return ''.join(out)


def simulate(lv: Level, lurd: str) -> bool:
    """Mô phỏng độc lập: chạy lại từng bước theo đúng luật Sokoban."""
    W = lv.W
    delta = {'u': -W, 'd': W, 'l': -1, 'r': 1}
    player, boxes = lv.init_player, set(lv.init_boxes)
    for ch in lurd:
        d = delta[ch.lower()]
        if not lv.inside(player, d):
            return False
        n = player + d
        if n in lv.walls or n not in lv.floor:
            return False
        if n in boxes:
            if not ch.isupper() or not lv.inside(n, d):
                return False
            nn = n + d
            if nn in lv.walls or nn not in lv.floor or nn in boxes:
                return False
            boxes.remove(n)
            boxes.add(nn)
        elif ch.isupper():
            return False
        player = n
    return boxes == set(lv.goals)


def load(path: str, index: int) -> Level:
    title, rows = parse_xsb(path)[index - 1]
    return Level(rows, title)


if __name__ == '__main__':
    import json
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    lv = load(sys.argv[1], int(sys.argv[2]))
    r = solve(lv, sys.argv[3], deadlock='--no-deadlock' not in sys.argv)
    print(json.dumps(r.as_dict(), ensure_ascii=False))
