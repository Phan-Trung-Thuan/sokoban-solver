# Thực nghiệm – heuristic h1, h2, h3

Thư mục này chứa bộ giải cải tiến và các script đo số liệu dùng trong báo cáo.

| File | Nội dung |
|---|---|
| `sokoban.py` | Bộ giải cải tiến: h1 (khối → đích gần nhất), h2 (ghép cặp Hungarian, `scipy.optimize.linear_sum_assignment`), h3 (ghép cặp theo số lần đẩy thật, ô chết → ∞), cắt deadlock 2×2 |
| `run_experiments.py` | Chạy thí nghiệm E1, E3, E4 → `results_improved.jsonl` |
| `bench.py` | Đo bộ giải gốc của repo (`solver.py`) trên 60 màn Microban → `results_baseline.jsonl` |
| `gen_levels.py` | Sinh bộ màn khó `levels_L.xsb` (L01–L12) |
| `make_figures.py` | Vẽ Hình 7, 8, 9 từ file kết quả |

## Chạy lại

```bash
pip install numpy scipy matplotlib pygame
cd experiments
python3 sokoban.py microban_155.xsb 3 ASTAR-H2     # giải 1 màn
python3 run_experiments.py                          # chạy lại toàn bộ (có thể dừng/chạy tiếp)
cd .. && python3 experiments/bench.py experiments/results_baseline.jsonl
cd experiments && python3 make_figures.py
```

Giải thuật hỗ trợ: `BFS`, `DFS`, `IDS`, `GREEDY-H3`, `ASTAR-H1`, `ASTAR-H2`, `ASTAR-H3`; thêm `--no-deadlock` để tắt cắt deadlock.
