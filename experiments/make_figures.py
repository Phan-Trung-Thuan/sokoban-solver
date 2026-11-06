"""make_figures.py - Vẽ Hình 7, 8, 9 của báo cáo từ results_improved.jsonl và levels_L.xsb."""
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

import sokoban as S

plt.rcParams.update({'font.family': 'DejaVu Serif', 'font.size': 11})
R = [json.loads(l) for l in open('results_improved.jsonl', encoding='utf-8')]


def get(exp, alg, lvl, dl=True):
    for r in R:
        if r['exp'] == exp and r['alg'] == alg and r['level'] == lvl and r['deadlock'] == dl:
            return r


# ---------------- Hình 7: bàn chơi L08 và L10 ----------------
def draw_board(ax, lv, title, highlight=None):
    W, H = lv.W, lv.H
    for i in range(W * H):
        r, c = divmod(i, W)
        y = H - 1 - r
        if i in lv.walls:
            ax.add_patch(Rectangle((c, y), 1, 1, color='#6b4f3a', ec='#4a3627', lw=0.6))
        elif i in lv.floor:
            ax.add_patch(Rectangle((c, y), 1, 1, color='#f4efe6', ec='#d9d2c5', lw=0.6))
        if i in lv.goals:
            ax.add_patch(Circle((c + .5, y + .5), .13, color='#d9534f'))
        if i in lv.init_boxes:
            ec = '#c0392b' if i == highlight else '#7a5a1e'
            lw = 2.5 if i == highlight else 1.0
            ax.add_patch(Rectangle((c + .14, y + .14), .72, .72, color='#d9a74a', ec=ec, lw=lw))
        if i == lv.init_player:
            ax.add_patch(Circle((c + .5, y + .5), .3, color='#2f6db5'))
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=11)


l08, l10 = S.load('levels_L.xsb', 8), S.load('levels_L.xsb', 10)
stuck = [b for b in l08.init_boxes if b in l08.dead][0]
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
draw_board(axes[0], l08, '(a) L08: khối viền đỏ đã dính tường trên', stuck)
draw_board(axes[1], l10, '(b) L10: %d khối' % len(l10.init_boxes))
plt.tight_layout()
plt.savefig('fig7_levels.png', dpi=200)
plt.close()

# ---------------- Hình 8: số nút trên L09–L12 ----------------
algs = ['BFS', 'DFS', 'IDS', 'GREEDY-H3', 'ASTAR-H1', 'ASTAR-H2', 'ASTAR-H3']
names = ['BFS', 'DFS', 'IDS', 'Greedy-h3', 'A*-h1', 'A*-h2', 'A*-h3']
colors = ['#8c8c8c', '#b3b3b3', '#5c5c5c', '#e0a040', '#a0c4e8', '#4f8fcf', '#1f4e8c']
lv_ids = [9, 10, 11, 12]
fig, ax = plt.subplots(figsize=(10, 4.2))
w = 0.11
for k, (a, n, col) in enumerate(zip(algs, names, colors)):
    xs, ys = [], []
    for j, l in enumerate(lv_ids):
        r = get('E3', a, l)
        xs.append(j + (k - 3) * w)
        ys.append(max(r['expanded'], 1))
        if r['status'] != 'SOLVED':
            ax.text(j + (k - 3) * w, r['expanded'] * 1.25, '×', color='red', ha='center', fontsize=13)
    ax.bar(xs, ys, w, label=n, color=col)
ax.set_yscale('log')
ax.set_xticks(range(len(lv_ids)))
ax.set_xticklabels(['L%02d' % l for l in lv_ids])
ax.set_ylabel('Số nút mở rộng (log)')
ax.set_title('Bộ giải cải tiến trên các màn khó (× : vượt giới hạn 300.000 nút)')
ax.spines[['top', 'right']].set_visible(False)
ax.legend(ncol=7, loc='upper center', bbox_to_anchor=(0.5, -0.1), frameon=False, fontsize=9)
plt.tight_layout()
plt.savefig('fig8_hard_levels.png', dpi=200)
plt.close()

# ---------------- Hình 9: BFS có / không cắt deadlock ----------------
ids = [l for l in range(1, 13) if l != 8]
off = [get('E4', 'BFS', l, False) for l in ids]
on = [get('E3', 'BFS', l, True) for l in ids]
fig, ax = plt.subplots(figsize=(9, 3.8))
x = range(len(ids))
ax.bar([i - .2 for i in x], [r['expanded'] for r in off], .4, color='#c8c8c8', label='BFS không cắt deadlock')
ax.bar([i + .2 for i in x], [r['expanded'] for r in on], .4, color='#2f6db5', label='BFS có cắt deadlock')
for i, r in zip(x, off):
    if r['status'] != 'SOLVED':
        ax.text(i - .2, r['expanded'] * 1.25, '×', color='red', ha='center', fontsize=13)
ax.set_yscale('log')
ax.set_xticks(list(x))
ax.set_xticklabels(['L%02d' % l for l in ids])
ax.set_ylabel('Số nút mở rộng (log)')
ax.spines[['top', 'right']].set_visible(False)
ax.legend(frameon=False, loc='upper left')
plt.tight_layout()
plt.savefig('fig9_deadlock.png', dpi=200)
plt.close()
print('ok')
