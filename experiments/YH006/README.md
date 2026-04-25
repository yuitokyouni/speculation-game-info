# YH006: Speculation Game on LOB (PAMS)

Katahira-Chen 2019 Speculation Game (SG) decision rule を PAMS 0.2.2
(Hirano-Izumi 2023) の tick-scale LOB 環境に移植する。YH005_1 Phase 1 の 5
figure を LOB 世界で再現し、どの機構が LOB 微視構造下で保存され、どれが
壊れるかを切り分ける。

詳細仕様: [`SPEC.md`](SPEC.md)

## Conditions — 2×2 (world × wealth), N=100 固定

|  | uniform init | Pareto α=1.5 init |
|---|---|---|
| **aggregate-demand** | **C0u** (N=100) | **C0p** (N=100) |
| **LOB (PAMS)** | **C2** (N=100) | **C3** (N=100, 主実験) |

LOB 側には更に流動性 null として **C1** (FCN baseline, SG なし) を併走。

Reference (2×2 には含めない、N scaling 補遺):
- 旧 C0: N=1000 aggregate-demand uniform (YH005_1 output, 有限サイズ効果の基準)

## Layout

- `SPEC.md` — 実装仕様書 (PAMS API 詳細含む)
- `speculation_agent.py` — SG decision rule を `pams.agents.Agent` subclass 化
- `history_broadcast.py` — 全 SG agent で共有する cognitive history μ(t)
- `configs/` — C1/C2/C3 の config dict 生成関数
- `yh006_to_yh005_adapter.py` — PAMS 結果を YH005 互換 dict に変換
- `calibrate_c_ticks.py` — C1 から C_ticks=3×median|Δmid| を較正
- `run_experiment.py` — C1/C2/C3 の主実行エントリ (LOB 側)
- `aggregate_sim.py` — aggregate-demand SG simulator (YH005 simulate の
  YH006 local fork、`wealth_mode` ∈ {uniform, pareto} 対応。uniform は
  YH005 simulate と同 seed で bit-一致)
- `run_aggregate_c0.py` — N=100 の C0u / C0p を生成 (2×2 aggregate 側)
- `compare_figure.py` — 5 figure × 4 condition (2×2) の比較図生成
- `load_c0.py` — C0u / C0p / 旧 C0 (N=1000 reference) の metrics loader
- `smoke_test.py` — 縮小版 C3 で agent wiring sanity
- `tests/` — parity / roundtrip invariants / wealth conservation
- `outputs/` — 実験成果物 (git 管理外)

## 再現手順

```bash
cd experiments/
# 1) C_ticks calibration (C1 を走らせて median|Δmid|×3 を算出)
.venv/bin/python -u YH006/calibrate_c_ticks.py
# outputs/C_ticks_calibration.json が出来る

# 2) C1/C2/C3 を順次実行 (LOB 側)
.venv/bin/python -u YH006/run_experiment.py \
    --num-fcn 30 --num-sg 100 \
    --warmup 200 --main 1500 \
    --max-normal-orders 500
# outputs/C{1,2,3}_result.pkl

# 2b) C0u / C0p を N=100 で生成 (aggregate-demand 側)
.venv/bin/python -u YH006/run_aggregate_c0.py
# outputs/c0u_metrics.json, outputs/c0p_metrics.json + 5×2 figure

# 3) 5×4 panel 比較図 + metrics JSON (2×2 cell × 5 figure)
.venv/bin/python -u YH006/compare_figure.py
# outputs/yh006_comparison_5x4.png, yh006_metrics.json

# 4) 検証
.venv/bin/python -u YH006/tests/test_parity.py
.venv/bin/python -u YH006/tests/test_roundtrip_invariants.py
.venv/bin/python -u YH006/tests/test_wealth_conservation.py
```

## Phase 1 実行結果 (seed=777)

### pre-2×2 (旧: C0=N=1000 との混成、N scaling が濁っていた)

30 FCN + 100 SG × (warmup 200, main 1500), c_ticks ≈ 28.0 tick:

| metric | C0 ref (aggregate, N=1000) | C1 (LOB FCN) | C2 (LOB SG uniform, N=100) | C3 (LOB SG Pareto, N=100) |
|---|---|---|---|---|
| num_round_trips | 10,419,681 | 0 | 879 | 1,080 |
| median horizon | 2.0 | — | 2.0 | 2.0 |
| mean horizon | 3.30 | — | 3.26 | 3.37 |
| max horizon | 476 | — | 36 | 33 |
| α_hill (wealth p90) | 2.54 | — | 1.98 | 1.91 |
| median wealth | 31 | — | 49 | 32 |
| corr(\|ΔG\|, horizon) | 0.42 | — | 0.61 | 0.33 |
| active_hold | 0.237 | 0 | 0.324 | 0.327 |
| passive_hold | 0.251 | 0 | 0.353 | 0.330 |
| idle | 0.088 | — | 0.004 | 0.005 |

→ aggregate vs LOB の差と N=1000 vs N=100 の差が分離できない。
以下の 2×2 (全て N=100) で確定させる。

### 2×2 (world × wealth, N=100 統一) — **TODO: `run_aggregate_c0.py` 実行後に記入**

|  | uniform init | Pareto α=1.5 init |
|---|---|---|
| **aggregate-demand** | C0u (pending) | C0p (pending) |
| **LOB (PAMS)** | C2 (上表流用) | C3 (上表流用) |

**主要所見** (pre-2×2 ベース、2×2 で再評価予定):
1. **round-trip horizon 分布が保存**: median 2.0 で C0 ref / C2 / C3 ほぼ同じ。
   LOB 微視構造が SG の時間スケールを壊さない (ただし N=1000 vs N=100 混成で、
   2×2 で N 固定して要再確認)。
2. **hold-ratio signature が LOB で強化?**: passive_hold 0.25 → 0.33-0.35。
   SG agent が「逆張りし続ける」挙動は LOB でむしろ顕著に見える。
   N=100 aggregate (C0u) との比較で LOB 固有性か N 効果かを分離。
3. **wealth Pareto α**: C0 ref 2.54 vs C2/C3 1.9-2.0 は N 差に起因の可能性大。
   2×2 で N 固定して再確認。
4. **corr(\|ΔG\|, horizon) の funnel 構造**: C0 ref 0.42 → C2 0.61 の増幅主張は
   N=1000 vs N=100 の confound があるので保留。C0u / C0p で再確認。

**実行時間** (Apple Silicon, single thread):
C1 56s + C2 13s + C3 15s ≈ 1.5 分 (calibration 別途 55s)。
Smoke test 0.5s。全 test < 10s。

**LOB artifact** (Phase 1 既知):
- zero-fill open 率 ≈ 30% (流動性不足で不一致)。
  LIMIT_ORDER (mid±10%, ttl=3) で置換したので book O(N²) 経路は回避。
- `lob_mtm` (PAMS cash + asset×price) は ±数千ドルに分散。
  これは SG agent の sizing q=⌊w/B⌋ が cost basis を LOB 単位で負にする
  artifact。`sg_wealth` (cognitive) とは分離して追跡。

## 検証 (全 pass)

- `test_parity.py`: seed 固定で bit 一致
- `test_roundtrip_invariants.py`: open_t < close_t, entry_action ∈ {±1},
  entry_quantity ≥ 1, delta_G ↔ cognitive_prices 再構成一致
- `test_wealth_conservation.py`: sg_wealth ≥ 0 かつ有界

## 参照

- YH005: `../YH005/` — aggregate-demand baseline 実装の原典 (`aggregate_sim.py`
  は YH005 simulate の YH006-local fork、uniform モードで bit-parity)
- YH005_1: `../YH005_1/outputs/phase1_metrics.json` — N=1000 reference row の source
- 共通 analysis: `../../analysis/` — stylized facts 計算群 (tail_exponent 等)
- PAMS: https://github.com/masanorihirano/pams
- Katahira & Chen 2019: https://arxiv.org/abs/1909.03185
