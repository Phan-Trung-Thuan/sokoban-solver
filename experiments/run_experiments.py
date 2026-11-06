"""
run_experiments.py - Chạy toàn bộ thực nghiệm cho bộ giải cải tiến (sokoban.py).

Ghi mỗi lần chạy thành một dòng JSON trong results_improved.jsonl.
Có thể dừng giữa chừng và chạy lại: các lần chạy đã có kết quả sẽ được bỏ qua.

    python3 run_experiments.py [ngân_sách_giây]
"""
import json
import os
import platform
import sys
import time

import sokoban as S

OUT = 'results_improved.jsonl'
NODE_LIMIT, TIME_LIMIT = 300_000, 60.0

JOBS = []
# E1 - Bảng 6, Bảng 7: 60 màn Microban đầu tiên
for alg in ('BFS', 'GREEDY-H3', 'ASTAR-H1', 'ASTAR-H2', 'ASTAR-H3'):
    for i in range(1, 61):
        JOBS.append(('E1', 'microban_155.xsb', i, alg, True))
# E3 - Bảng 8, Hình 8: 12 màn L01–L12, đủ 7 giải thuật
for alg in ('BFS', 'DFS', 'IDS', 'GREEDY-H3', 'ASTAR-H1', 'ASTAR-H2', 'ASTAR-H3'):
    for i in range(1, 13):
        JOBS.append(('E3', 'levels_L.xsb', i, alg, True))
# E4 - Hình 9: tắt cơ chế cắt deadlock
for alg in ('BFS', 'ASTAR-H3'):
    for i in range(1, 13):
        JOBS.append(('E4', 'levels_L.xsb', i, alg, False))


def main():
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 1e9
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding='utf-8'):
            j = json.loads(line)
            done.add((j['exp'], j['file'], j['level'], j['alg'], j['deadlock']))
    t0 = time.perf_counter()
    cache = {}
    with open(OUT, 'a', encoding='utf-8') as out:
        for exp, f, i, alg, dl in JOBS:
            if (exp, f, i, alg, dl) in done:
                continue
            if time.perf_counter() - t0 > budget:
                break
            if (f, i) not in cache:
                cache[(f, i)] = S.load(f, i)
            lv = cache[(f, i)]
            r = S.solve(lv, alg, deadlock=dl, node_limit=NODE_LIMIT, time_limit=TIME_LIMIT)
            row = {'exp': exp, 'file': f, 'level': i, 'boxes': len(lv.init_boxes),
                   'alg': alg, 'deadlock': dl, **r.as_dict(),
                   'python': platform.python_version()}
            out.write(json.dumps(row, ensure_ascii=False) + '\n')
            out.flush()
    print('done %d/%d' % (sum(1 for _ in open(OUT, encoding='utf-8')), len(JOBS)))


if __name__ == '__main__':
    main()
