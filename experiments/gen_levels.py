"""
gen_levels.py - Sinh màn chơi Sokoban bằng phương pháp kéo ngược (seed cố định).

Bắt đầu từ trạng thái đích (mọi khối nằm trên ô đích), người chơi đi ngẫu nhiên
và kéo khối. Kéo là phép ngược của đẩy nên màn sinh ra chắc chắn có lời giải.

    python3 gen_levels.py   -> ghi tệp levels_L.xsb (L01–L12)
"""
import random

import sokoban as S

# Khung phòng (# tường, khoảng trắng là sàn). Ô đích được đặt trong vùng sàn.
ROOMS = [
    ["##########",
     "#        #",
     "#  ##    #",
     "#        #",
     "#    ##  #",
     "#        #",
     "##########"],
    ["###########",
     "#    #    #",
     "#         #",
     "##  ###  ##",
     "#         #",
     "#    #    #",
     "###########"],
    ["############",
     "#     #    #",
     "#  #     # #",
     "#  #  ##   #",
     "#     #  # #",
     "# ##       #",
     "#     #    #",
     "############"],
    ["############",
     "#    ##    #",
     "#          #",
     "#  ##  ##  #",
     "#          #",
     "#          #",
     "############"],
]


def pull_generate(room, n_boxes, n_steps, rng):
    rows = [list(r) for r in room]
    H, W = len(rows), len(rows[0])
    floor = [r * W + c for r in range(H) for c in range(W) if rows[r][c] == ' ']
    fset = set(floor)
    goals = set(rng.sample(floor, n_boxes))
    boxes = set(goals)
    free = [f for f in floor if f not in boxes]
    player = rng.choice(free)
    dirs = (-W, W, -1, 1)
    for _ in range(n_steps):
        d = rng.choice(dirs)
        n = player + d
        if n not in fset or n in boxes:
            continue
        behind = player - d       # khối nằm phía sau người chơi (ngược hướng đi)
        if behind in boxes and rng.random() < 0.6:
            boxes.remove(behind)
            boxes.add(player)     # kéo khối theo
        player = n
    return render(rows, goals, boxes, player)


def render(rows, goals, boxes, player):
    H, W = len(rows), len(rows[0])
    out = []
    for r in range(H):
        line = ''
        for c in range(W):
            i = r * W + c
            if rows[r][c] == '#':
                ch = '#'
            elif i == player:
                ch = '+' if i in goals else '@'
            elif i in boxes:
                ch = '*' if i in goals else '$'
            elif i in goals:
                ch = '.'
            else:
                ch = ' '
            line += ch
        out.append(line)
    return out


def bfs_nodes(rows):
    lv = S.Level(rows)
    r = S.solve(lv, 'BFS', node_limit=300_000, time_limit=60)
    return r.status, r.expanded, lv


def build(seed=2026):
    rng = random.Random(seed)
    cands = []
    for k in range(600):
        room = ROOMS[k % len(ROOMS)]
        nb = 2 + (k // len(ROOMS)) % 5          # 2..6 khối
        rows = pull_generate(room, nb, rng.randint(150, 600), rng)
        lv = S.Level(rows)
        if len(lv.init_boxes & lv.goals) > 0:   # mọi khối phải rời ô đích
            continue
        st, n, _ = bfs_nodes(rows)
        if st == 'SOLVED' and n >= 30:
            cands.append((n, nb, rows))
    cands.sort(key=lambda x: x[0])
    return cands


def make_unsolvable(rows):
    """L08: dời một khối sát tường vào ô chết (dính tường, đoạn tường không có đích)."""
    lv = S.Level(rows)
    W = lv.W
    for b in sorted(lv.init_boxes - lv.goals):
        for x in sorted(lv.dead):
            if x in lv.init_boxes or x == lv.init_player:
                continue
            wall_n = sum(1 for d in lv.dirs() if x + d in lv.walls)
            if wall_n != 1:          # đúng một mặt sát tường: dính tường, không phải kẹt góc
                continue
            grid = [list(r) for r in rows]
            br, bc = divmod(b, W)
            xr, xc = divmod(x, W)
            grid[br][bc] = ' '
            grid[xr][xc] = '$'
            new = [''.join(r) for r in grid]
            nlv = S.Level(new)
            if len(nlv.init_boxes) == len(lv.init_boxes) and \
               S.h3_matching_push(nlv, nlv.init_boxes) >= S.INF:
                return new
    raise RuntimeError('Không tạo được màn vô nghiệm')


def select(cands):
    hard = cands[-4:]                       # L09–L12: bốn màn khó nhất
    rest = cands[:-4]
    idx = [round(i * (len(rest) - 1) / 6) for i in range(7)]
    easy = [rest[i] for i in idx]           # L01–L07: rải đều theo độ khó
    l08 = make_unsolvable(easy[3][2])
    return [e[2] for e in easy] + [l08] + [h[2] for h in hard]


if __name__ == '__main__':
    levels = select(build())
    with open('levels_L.xsb', 'w', encoding='utf-8') as f:
        for i, rows in enumerate(levels, 1):
            f.write('; L%02d\n' % i)
            f.write('\n'.join(rows) + '\n\n')
    print('Đã ghi levels_L.xsb (%d màn)' % len(levels))
