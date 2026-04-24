# YH006: Speculation Game on LOB (PAMS)

Katahira-Chen 2019 Speculation Game (SG) decision rule を PAMS 0.2.2
(Hirano-Izumi 2023) の tick-scale LOB 環境に移植する。YH005_1 Phase 1 の 5
figure を LOB 世界で再現し、どの機構が LOB 微視構造下で保存され、どれが
壊れるかを切り分ける。

詳細仕様: [`SPEC.md`](SPEC.md)

## Conditions

| ID | 世界 | SG agents | wealth 分布 | 備考 |
|---|---|---|---|---|
| **C0** | aggregate-demand | N=1000 | Pareto (dynamic) | YH005_1 既存 output を流用、再実行しない |
| **C1** | LOB (PAMS) | なし | — | FCN baseline のみ |
| **C2** | LOB (PAMS) | N=100 | 一様 | wealth heterogeneity 無し ablation |
| **C3** | LOB (PAMS) | N=100 | Pareto α=1.5 | **主実験** |

## Layout

- `SPEC.md` — 実装仕様書 (PAMS API 詳細含む)
- `speculation_agent.py` — SG decision rule を `pams.agents.Agent` subclass 化
- `history_broadcast.py` — 全 SG agent で共有する cognitive history μ(t)
- `configs/` — C1/C2/C3 の config dict 生成関数
- `yh006_to_yh005_adapter.py` — PAMS 結果を YH005 互換 dict に変換
- `calibrate_c_ticks.py` — C1 から C_ticks=3×median|Δmid| を較正
- `run_experiment.py` — C1/C2/C3 の主実行エントリ
- `compare_figure.py` — 5 figure × 4 condition = 20 panel 比較図を生成
- `load_c0.py` — YH005_1/outputs/phase1_metrics.json を loader
- `smoke_test.py` — 縮小版 C3 で agent wiring sanity
- `tests/` — parity / roundtrip invariants / wealth conservation
- `outputs/` — 実験成果物 (git 管理外)

## 再現手順

```bash
cd experiments/
# 1) C_ticks calibration (C1 を走らせて median|Δmid|×3 を算出)
.venv/bin/python -u YH006/calibrate_c_ticks.py
# outputs/C_ticks_calibration.json が出来る

# 2) C1/C2/C3 を順次実行
.venv/bin/python -u YH006/run_experiment.py \
    --num-fcn 30 --num-sg 100 \
    --warmup 200 --main 1500 \
    --max-normal-orders 500
# outputs/C{1,2,3}_result.pkl

# 3) 5×4 panel 比較図 + metrics JSON
.venv/bin/python -u YH006/compare_figure.py
# outputs/yh006_comparison_5x4.png, yh006_metrics.json

# 4) 検証
.venv/bin/python -u YH006/tests/test_parity.py
.venv/bin/python -u YH006/tests/test_roundtrip_invariants.py
.venv/bin/python -u YH006/tests/test_wealth_conservation.py
```

## Phase 1 実行結果 (seed=777)

30 FCN + 100 SG × (warmup 200, main 1500), c_ticks ≈ 28.0 tick:

| metric | C0 (aggregate) | C1 (LOB FCN) | C2 (LOB SG uniform) | C3 (LOB SG Pareto) |
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

**主要所見**:
1. **round-trip horizon 分布が保存**: median 2.0 で C0 / C2 / C3 ほぼ同じ。
   LOB 微視構造が SG の時間スケールを壊さない。
2. **hold-ratio signature が LOB で強化**: passive_hold 0.25 → 0.33-0.35。
   SG agent が「逆張りし続ける」挙動は LOB でむしろ顕著。
3. **wealth Pareto α**: C0 は 2.54、C2/C3 は 1.9-2.0。C3 が tail 最重。
   ただし N=100 では N=1000 に比べ tail 推定精度が低く、scaling は大きな
   scope で要確認 (YH006 Phase 2 以降)。
4. **corr(\|ΔG\|, horizon) の funnel 構造**: C0 0.42 → C2 0.61 で LOB が
   相関を増幅。C3 は Pareto 初期化で散逸し 0.33 に落ちる (wealth
   heterogeneity が ΔG スケールの分散を増やすため相関が薄まる)。

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

- YH005: `../YH005/` — aggregate-demand baseline 実装の原典
- YH005_1: `../YH005_1/outputs/phase1_metrics.json` — C0 値の source
- 共通 analysis: `../../analysis/` — stylized facts 計算群 (tail_exponent 等)
- PAMS: https://github.com/masanorihirano/pams
- Katahira & Chen 2019: https://arxiv.org/abs/1909.03185
