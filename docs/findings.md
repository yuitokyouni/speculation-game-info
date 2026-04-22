# Findings: 各実験で確認済みの事項

**目的**: 新しい YH を着手する前にここを grep / 通読することで、前の実験で既に確認済みの数値 / 設計判断 / 失敗ルートを再度踏まないようにする。

**書き方の方針**:
- 各 YH 完了時にセクションを追記する。
- **確認済み事実** (数値、定性的結論、設計判断) と **次フェーズで検証すべき仮説 / 保留事項** を分けて書く。
- 再現可能な parameter と seed は明記 (再検証できるように)。

---

## YH001 — Cont-Bouchaud Percolation (完了, 2025-04)

**確認済み**:
- パーコレーション cluster-size 分布が power-law (τ ≈ 2.5 付近) を再現、return が heavy tail。

**保留**: 特になし (シリーズの導入として完了)。

---

## YH005 Lite — Speculation Game 最小実装 + 3 モデル比較 (完了, 2026-04)

**使用 parameter**: `N=1000, M=5, S=2, B=9, C=3.0, p0=100.0`。log-return ではなく `Δp = D/N` を使う (論文1 Eq. 5 準拠、p ≤ 0 問題回避)。

**確認済み**:
- **Parity**: reference ↔ vectorized の bit-parity を 5 seeds × (default / S=1 / Null A / Null B) で検証、pytest で常時 green。§7 RNG 消費順の契約が機能することを実証。
- **Baseline stylized facts** (`T=20000, seed=777`): std(r)=3.26e-3, vol_acf(τ=200)=+0.016, kurt(w=1)=3.63, kurt(w=640)=-0.40, Hill α=4.53。論文1 Fig. 4 の α≈3.8 と整合。aggregational Gaussianity を数値で確認。
- **Null tests** (`T=50000, seed=777`): baseline |r| ACF(50)=+0.119 vs Null A=+0.005 / Null B=+0.017。baseline/null 比 ~10-24x、論文2 Fig. 11 と定性一致。
- **3 モデル比較** (`S=1, T=50000, seed=123`): MG Hill α≈10^14 (離散化 artifact), GCMG Hill α≈1429 (very thin), **SG Hill α=4.33** (power-law)。vol ACF も SG のみ slow decay を示す。
- **設計ホール 8 項目** (§4.1-4.8) は `experiments/YH005/README.md` の表で固定。以後これに従う。特に:
  - 4.1 argmax tie-break: 現 j* が argmax 集合に含まれれば継続、さもなくば argmax から uniform
  - 4.5 Null B は literal 解釈 (position 非参照)
  - 4.9 return 定義は Δp = D/N (log-return ではない)

**失敗ルートのメモ**:
- 3 モデル比較を log-return で最初に書いたら MG の 77% の step で p ≤ 0 になり NaN 化 → Δp 基準に切り替えた。今後の parameter scan でも log-return が破綻しうることを意識する。

**次フェーズで検証したい仮説**:
- T=50000 baseline の |r| ACF(50)=0.119 は論文1 Fig. 7 fit の 0.211 より低め。100 trial 平均で収束するか要確認 → Phase 2 で検証。

---

## YH005_1 — Phase 1: 3 層機構の数値実証 (完了, 2026-04-22)

**使用 parameter**: `N=1000, M=5, S=2, T=50000, B=9, C=3.0, seed=777, p0=100.0, order_size_buckets=(50, 100)`。1 trial。

**確認済み (5 figure)**:
- **Wealth Pareto**: Hill α (xmin=p90) = **2.54** (論文2 Fig. 4: 1.94)。単一 trial 揺らぎの範囲、[1.5, 3] 内。tail は我々がやや軽い。
- **Round-trip horizon**: K=10,419,681 件、median=2 / mean=3.3 / max=484 steps。log-log で明確な右下がり (論文2 Fig. 8 と定性一致)。
- **ΔG vs horizon**: corr(|ΔG|, τ) = **+0.416**。明確な漏斗形 (論文2 Fig. 7)。
- **Action ratio (M=5)**: passive_hold=**0.251**, active_hold=0.237, buy=sell=0.212, idle=0.088。論文2 Fig. 10 (M=5) と同水準。buy ≈ sell で対称性維持。
- **Order size 時系列**: mean(small/med/large) = 415.9 / 0.8 / 0.1、peak(large)=12 agents/step。large burst が r(t) 高 vol 期と visual に同期。ただし large 件数は tail が軽い分少なめ。

**simulate ログの拡張 (YH005 本体に追加)**:
- `round_trips` dict (K レコード, 6 配列: agent_idx, open_t, close_t, entry_action, entry_quantity, delta_G)
- `num_orders_by_size{,_buy,_sell}` (T×3 配列、bucket: small≤50 < medium≤100 < large)
- 新 state `entry_step` を Agent に追加 (open 時記録、close/substitute でクリア)
- **RNG 消費順不変** — 既存 14 parity ケースに新 9 配列の bit-parity チェックを重ねて全通過。invariant 4 追加も通過。

**性能**: T=50000 × N=1000 × S=2 × M=5 で vectorized 実装 97.5 秒 (Apple Silicon)。Phase 2 の 100 trial × 7M × 15B = 10500 run で単純掛け算すると 285 時間。並列化 + さらなる vectorize 改善が必須。

**失敗ルートのメモ**:
- 最初 `plot_hold_ratio` で N を hard-code していなかったが、sim_result から推定 (buy+sell+act+pas の max) する方式で対応。num_idle を別 key で返す形に simulate 側を変えない。
- p ≤ 0 チェック: seed=777 では n(p≤0)=0、prices ∈ [92, 107] に収まる。log_return 安全。ただし B を下げたり C を上げる parameter scan では要再確認。

**次フェーズで検証したい仮説**:
- 100 trial 平均で Hill α が論文値 1.94 に近づくか (Phase 2)
- parameter scan (M-B phase diagram、kurtosis vs S, vs C) で機構が parameter-robust か (Phase 2)
- 論文1 Fig. 11 (asymmetry), Fig. 12 (leverage), Fig. 13 (gain/loss asymmetry) は **post-processing のみで出せる** (新規 simulate 不要、round_trips と h_series から計算可能) → Phase 3 で追加予定

**YH006 着手時の注意点** (これを見て重複回避):
- YH005 Lite の simulate は bit-parity 契約が重要。YH006 で論文1 全 11 stylized facts を網羅する際、simulate の RNG 順を絶対に壊さない。ログ追加だけなら parity 維持可能。
- 設計ホール 8 項目は YH005 README で確定しているので YH006 でも同じ選択を踏襲すること。
- round_trips / order size bucket のログ構造は YH005_1 で確立した形をそのまま使える。
