# Stage S6r plan v1 — Ablation A4: wealth shuffle (C2_A4 / C3_A4 × 100 trial、A3 差し替え)

| 項目 | 値 |
|---|---|
| Stage | S6r — S6 (A3) の再設計。A4 = wealth shuffle ablation |
| Status | 実行中 (Yuito 指示 2026-06-11「A4の追走頼んだ」を起案承認とみなす。完了後レビュー) |
| 想定 runtime | Mac のみ ~3-4h (equiv check + smoke + determinism + 200 trial)。Windows 作業なし |
| 新規 sim | LOB 200 trial (C2_A4 / C3_A4 × 100、Mac) |
| 前提 | S6 (A3) は凍結 ([[design_review_20260610]] 追記)。S5.9 完了 (funnel maintained / H_friction) |

---

## 0. 背景 — なぜ A3 を捨てて A4 か

S6 (A3 lifetime cap) は 2026-06-10 に 2 つの理由で凍結した
(`plans/design_review_20260610.md` 追記に診断詳細):

1. **実行不能**: cap の同期リスポーン波が市場の凍結 (=C3 が速い理由) を壊し続け、
   PAMS の O(板サイズ) 板操作と掛け合わさって step ~600-700 以降
   100 step に 879 秒の持続スパイラル。100 trial に 20h+。
2. **検証として不成立 (より根本的)**: `_substitute()` の新 wealth は
   `B + U(0,100)` であり **Pareto 再抽選ではない**。C3_A3 は「Pareto 分布を
   保ったまま個体を入れ替える」のではなく「全員を低い均一初期値へ flatten する」
   操作で、仮説 A revised (initial wealth distribution の persistence が dominant)
   の検証にならない。

**A4 (wealth shuffle)**: 周期 K step ごとに、生存 SG agent 間で `sg_wealth` を
ランダム permute する。

- (i) **marginal wealth 分布を厳密に保存** (permutation なので multiset 不変)
- (ii) **agent 集団・学習状態・position・注文フローを非破壊** — 市場活動が
  変わらないので A3 型の計算爆発が構造的に起きない
- (iii) **個体の wealth rank persistence のみを破壊** — 仮説 A revised に対する
  最も鋭い instrument (design review 指摘 7 の A4 提案を採用)
- (iv) C2_A4 (uniform + shuffle) を対照腕として同時に走らせ、**対称 DiD**
  (C3_A4 − C2_A4) − (C0p − C0u) で shuffle 操作自体の非特異的効果を差し引く
  (指摘 3 の A3 非対称 DiD 問題の解消)

## 0.2 実装方式 — saver hook (Phase 1 非改変)

A1/A3 と異なり agent subclass を作らない。shuffle は市場 step 境界で
`Logger.process_market_step_end_log` から発火する:

- `code/wealth_shuffle.py::WealthShuffleSaver(OrderTrackingSaver)` —
  step 終端 callback で `(t − warmup + 1) % K == 0` のとき全 SG agent の
  `sg_wealth` を permute。専用 RNG `random.Random(seed * 1_000_003 + 41)`
  (agent / PAMS の prng と独立、determinism 保証)
- shuffle 無効条件 (既存 7 条件) は素の `OrderTrackingSaver` を使うため
  **既存挙動との bit-一致が構造的に保証される** (コードパス自体が分岐)
- `speculation_agent.py` (Phase 1) への変更ゼロ → aggregate parity 再走不要

**既知の副作用 (記録)**: `adapter.round_trips_to_df` の `w_open`/`w_close`
再構成は shuffle イベントを考慮しないため **A4 条件下では無効な列**になる。
L 判定が使う `horizon`/`delta_g`/`q`/`agents_df` の実測値 (w_init, w_final =
agent state 直読) は影響を受けない。diff に明記し、A4 の w_open/w_close を
使う分析を禁止する。

## 0.3 K (shuffle 周期) の較正

**K = 121** (primary) = S6 τ_max と同値。理由: A3 が破壊しようとした
persistence と同じ timescale で rank persistence を破壊し、A3 (凍結) との
物語接続を保つ。T=1500 main で **12 回** shuffle。
感度 (K ∈ {25, 500} × 数 seed) は主結果が曖昧な場合のみ S6r.1 として追加。

## 0.4 KPI (pre-registered、design review 指摘 1 を反映した差し替え)

数字を見る前に確定する判定:

- **Primary — pooled interaction**: 9 条件 pooled bin_var_slope
  (seed-cluster bootstrap 500、`aggregate_ablation_a3_summary.py` の機構流用)。
  A4 interaction = (C3_A4 − C2_A4) − (C0p − C0u)。
  判定: **pooled A4 interaction の絶対値が pooled S3 interaction より縮小し、
  pooled shrinkage (S3 − A4) の bootstrap CI が 0 を排除** → 仮説 A revised 支持。
- **Secondary — paired shrinkage (trial-level)**: seed ペアで
  shrinkage = S3_int − A4_int の bootstrap CI が 0 排除 + 縮小方向。
- **旧 L3 ratio (≤ 0.7) は参考値に格下げ** — S3 trial-level interaction が
  全 metric で CI 0 跨ぎ (L2 0/5 の前例) のため分母不安定 (指摘 1)。
- **Manipulation check (成功条件ではない)**: `wealth_persistence_rho` が
  C3_A4 で 0 方向へ、`corr_winit_wt_Tk` の早期減衰。shuffle すれば下がるのは
  トートロジーなので claim には使わない (S6 plan §0.4 の流儀を継承)。
- **shuffle の非特異的効果の監視**: C2_A4 − C2 の主指標差。大きければ
  「shuffle 操作自体が funnel に効く」= DiD の対照腕が機能した証拠として報告。

## 1. 作業項目 (全部 Mac、Windows 不要)

1. `config.py`: `CondSpec.wealth_shuffle: bool = False` 追加 + `C2_A4`/`C3_A4` 定義
2. `code/wealth_shuffle.py` 新規 + `run_experiment.py` (`shuffle_period` kwarg、
   `SimResult.n_shuffles`) + `parallel.py` passthrough
3. **C3 等価チェック**: 新 code で C3 seed=1000 を 1 run、`data/C3/` と semantic 一致
   (S6 と同 protocol。shuffle-off 経路の非破壊確認)
4. **A4 smoke**: C3_A4 seed=1000 1 run —
   `n_shuffles == 12`、runtime < 1200s (stop trigger)、rt の q 多様性が退化しない
5. **Determinism guard**: C3_A4 seed=1000 × 2 → rt_df / lifetimes semantic 一致
6. **Ensemble**: C2_A4 / C3_A4 × seed 1000-1099 → `data/C2_A4/`, `data/C3_A4/`
7. 集計 (後続、データ完走後): `aggregate_ablation_a4_summary.py` —
   a3 版を対称 DiD (C3_A4 − C2_A4) + §0.4 KPI に改造、ensemble_summary 700→900 行

## 2. Stop triggers

- §3 equiv check fail (shuffle-off 経路が既存挙動を破壊)
- §4 smoke runtime > 1200s (A3 型スパイラルの兆候 — A4 では理論上起きないはずなので
  発生したら設計見直し)
- §5 determinism fail (RNG 配線ミス)
- §6 ensemble 中 mean runtime > 2x C3 (= ~900s/trial 超)

## 3. Yuito 確認事項 (完了後レビュー)

1. K=121 の採否 (感度 S6r.1 が必要か)
2. §0.4 KPI 差し替え (ratio 格下げ、pooled CI primary 化) の追認
3. C2_A4 対照腕込みの対称 DiD の追認
4. S6 (A3) の扱い: 廃止して S6r で置換 / 修正して併走。推奨は廃止
   (design review 追記の欠陥 (b) により A3 は修正しても検証として弱い)
5. pooled A4 interaction の判定 → 仮説 A revised の最終判定

---

## 改訂履歴

| Version | 内容 |
|---|---|
| v1.0 | S6r 初版。S6 (A3) 凍結 (性能スパイラル + substitute wealth 非 Pareto) を受け、A4 wealth shuffle へ差し替え。saver hook 方式で Phase 1 非改変、C2_A4 対照腕で対称 DiD、KPI は pooled bootstrap CI を primary に pre-register (design review 指摘 1/3/7 反映)。K=121 (= S6 τ_max)。 |
