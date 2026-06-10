# YH006_1 設計レビュー (2026-06-10) — S5.9 / S6 進行と並行した設計上の問題点の指摘

レビュー範囲: S6 plan v1 (A3 ablation)、S5.9 plan v1 + 実装 (`c_ticks_self_consistency.py`)、
KPI 体系 (L2/L3)、集計インフラ。dossier §9 で既に認知済みの limitation
(P2、T=1500、MMFCN scan 範囲、単一市場、2-account 設計、null の射程) は重複指摘しない。

ステータス凡例: 🔴 結論の妥当性に直結 / 🟡 解釈・検出力に影響 / ⚪ 工程・再現性の問題

---

## 🔴 指摘 1: L3 判定の shrinkage ratio は分母がほぼゼロで数値的に破綻している

**事実** (`tab_S3_interaction.csv` / `S5_summary_for_diff.json`):

- S3 trial-level interaction は **5 指標すべてで CI が 0 を跨ぐ**
  (例: bin_var_slope +0.0046 [−0.054, +0.064])
- S5 の L2 判定はこの上に ratio = |A1|/|S3| を構築した結果、ratio が
  **0.09〜3.81 と乱高下**して 0/5 fail。これは A1 の効果の問題ではなく
  「ほぼ 0 の分母で割った」算術の問題
- S6 の L3 は同じ機構 (ratio ≤ 0.7) を踏襲しており、同じ破綻を再生産する

**より深い問題 — estimand の二重化**: trial-level bin_var_slope interaction の平均は
+0.005 なのに、物語の根拠である pooled interaction は ≈ −0.18 と符号すら違う。
trial 単位の Spearman ρ (1 trial の少数 RT を 15 bin に切る) と 100-trial pooled の
Spearman ρ は**別の推定対象**であり、KPI は前者で判定し、仮説判定の物語は後者
(CI なしの点推定) で語っている。審査者視点では「有意でない指標で判定基準を作り、
有意性検定のない指標で結論を主張している」と映る。

**対処 (実施済み)**: `aggregate_ablation_a3_summary.py` に pooled bin_var_slope の
**seed-cluster bootstrap CI** (trial 単位 resample × 500) を補助分析として実装。
pooled interaction / pooled shrinkage も CI 付きで出力する。pre-registered の L3 も
計算するが、README に分母不安定の注記を自動挿入。

**推奨 (Yuito 判断)**: L3 の第一判定を「ratio ≤ 0.7」から「paired shrinkage
(C3 − C3_A3、seed ペア) の CI が 0 を排除し、かつ pooled shrinkage CI が 0 を排除」
に差し替える。ratio は参考値に格下げ。

---

## 🔴 指摘 2: A3 の horizon 打ち切り交絡 — funnel 指標そのものが cap で機械的に変わる

τ_max=121 で agent を強制退場させると、**horizon > ~121 の round trip は構造的に
生成不能**になる (agent はポジションを cap を超えて保持できない)。一方 C3 の RT は
horizon 最大 ~1500 まで分布する。bin_var_slope は horizon bin 上の Var(log|ΔG|) の
勾配なので、**C3_A3 と C3 の比較は異なる horizon support 上の量の比較**になる。

帰結: C3_A3 の slope が C0u/C2_A1 側にシフトしても、それは
(a) wealth persistence の破壊 (仮説 A revised が主張したい因果) ではなく
(b) 長 horizon bin の消失という打ち切り artifact
かもしれない。plan §0.4 は「lifetime 分布の変化はトートロジー」という注意を入れて
いるが、**outcome 指標自体の support 変化**には触れていない。examiner が最初に突く
タイプの交絡。

**対処 (実施済み)**: 集計に matched-horizon 補助分析を追加
(`compute_matched_horizon_pooled`: 全 7 条件を h ≤ τ_max に制限して pooled slope を
再計算、`tab_S6_pooled_bin_var_matched_horizon.csv`)。同一 support 上で C3 vs C3_A3 の
gap が保たれれば因果主張は生存、消えれば打ち切り artifact の疑い濃厚。
新規 sim 不要・既存 parquet から計算可能。

---

## 🔴 指摘 3: A3 の DiD が非対称 — uniform 側の cap 対照 (C2_A3) が無い

A1 では C2_A1 と C3_A1 の**両腕**を走らせ、interaction =
(C3_A1 − C2_A1) − (C0p − C0u) で「q 固定という操作自体の非特異的効果」を差し引いた。
S6 は C3_A3 のみ走らせ、A3 interaction = **(C3_A3 − C2) − (C0p − C0u)** と定義している
— ablated 腕 (capped Pareto) を **un-capped uniform** と比較する形。

cap には wealth persistence と無関係な非特異的効果がある (指摘 2 の horizon 打ち切り、
agent 世代交代の頻発、若い agent 比率の上昇など)。C2_A3 (uniform + cap) が無いと、
これらの効果が **Pareto 腕にだけ** 乗り、interaction に混入する。plan §3.2 は
「A1 + A3 の combine は scope 外」としているが、C2_A3 は A1 との combine ではなく
**A3 自身の対照腕**であり、A1 protocol との一貫性からも本来必要。

**推奨**: C3_A3 の結果が「シフトあり」に出た場合は、C2_A3 × 100 trial (sim コストは
C3_A3 と同等) を S6.5 として追加し、対称 DiD (C3_A3 − C2_A3) − (C0p − C0u) で再判定
する。「シフトなし (仮説 A revised fail)」なら C2_A3 は不要 (非特異的効果ごと null)。

---

## 🔴 指摘 4: S5.9 の実装が pre-registered 主判定を計算できない形で書かれていた

plan §4 の主成功条件は「**funnel gap の維持** (pooled bin_var_slope の |Δ| ≤ 0.05)」、
副次に survival (matched S(1499))。しかし commit 済の `c_ticks_self_consistency.py`
v1.0 は **n_rt (RT 件数) しか記録せず**、RT 明細も lifetime も保存しないため、
funnel も survival も**事後計算が不可能**だった。plan が予告した
`data/C2_cticks/`, `data/C3_cticks/` への S3-schema 出力も determinism guard も
実装されていない。つまり v1.0 のまま走らせると「Δn_rt による H_friction/H_trigger
判別」(plan の副次診断) だけが残り、主判定はスキップされる。

**対処 (実施済み、v1.1)**:
- RT 明細 + lifetime samples を `data/_s59_cticks/{PhaseA,PhaseB}/` に永続化
  (S3 と同 schema、`adapter.py` 流用)
- pooled bin_var_slope (analysis.py から逐語 inline — Mac venv に statsmodels が
  無いため) + censored_frac (≈ matched S(T−1)) を phase 間 paired 比較
- plan §4 の pre-registered 閾値 (|Δ| ≤ 0.05 / > 0.10) による judgment を JSON に出力
- 収束診断 (指摘 5) を追加
- 縮小 smoke (T=300, 1 seed) で end-to-end 動作確認済。censored_frac は
  C2 0.89 / C3 0.71 と S3 の 0.91 / 0.73 にほぼ整合

残課題: determinism guard は未追加 (S5.9 は canonical data を生成しない一過性測定
なので優先度低と判断したが、plan §3.3 との差分として diff に明記すること)。

---

## 🟡 指摘 5: 「1 パス再較正」は self-consistency ではない — 収束診断が無かった

c_ticks は固定点問題 (閾値 → 取引活動 → volatility → 閾値) なのに、S5.9 は 1 回だけ
再較正して止める設計。c_ticks' で再走した市場の volatility は再び変わるので、
1 パスで「self-consistent になった」とは言えない。plan は「1 パス」と明示しているが
**非収束をどう検出するかが未定義**だった。

**対処 (実施済み)**: Phase B の出力 price 系列から再々較正値 c_ticks'' を計算し、
`c_ticks''/c_ticks'` を収束診断として JSON/log に出力。smoke (T=300) では
C2 0.99 / C3 0.89 — C3 は 1 ステップでまだ 11% 動いており、本番 (T=1500) で
この比が 1 に近くなければ「P2 は 1 パスでは閉じない」ことが定量的に言える。

---

## 🟡 指摘 6: S5.9 の判定閾値 |Δ| ≤ 0.05 は 6 seed の検出力を確認せずに置かれている

pooled bin_var_slope の 6-seed 推定は 100-trial 推定よりはるかに分散が大きい。
S6 集計で 100-trial pooled slope の bootstrap CI 幅が判明するので、それを √(100/6) 倍
した概算が 0.05 を超えるなら、**noise だけで「主張修正」側に倒れる**偽陽性リスクが
高い。判定は点推定の |Δ| でなく paired Δ の不確かさ込みで読むべき。
(v1.1 で per-seed の RT 明細を保存するので、seed-paired Δ の評価は事後計算可能。)

---

## 🟡 指摘 7: A3 は wealth persistence「だけ」を切る instrument ではない

強制交代は (i) wealth persistence に加えて (ii) ポジション・在庫、(iii) agent の
内部状態 (学習・戦略状態)、(iv) population の年齢構成、をまとめて破壊する。
C3_A3 で funnel が戻っても、特定できるのは「長寿命 agent の何かが原因」までで、
「**initial wealth distribution の persistence** が原因」(仮説 A revised の文言) には
論理的に届かない。

**推奨 (S7 候補)**: A4 = **wealth shuffle ablation** — 生存 agent 間で sg_wealth を
周期 K step で permute する。marginal wealth 分布・agent 集団・学習状態・horizon
support をすべて保ったまま、**個体の wealth rank persistence のみ**を破壊する、
仮説 A revised に対して最も鋭い instrument。A3 が部分支持に終わった場合の次の一手
として plan 化する価値が高い。

---

## 🟡 指摘 8: τ_max 較正は pre-registered 規則から逸脱しており、かつ単一点

- GLOSSARY の規則は「τ_max = L_50 × 0.5 (L_50 = lifetime 中央値)」。実際は censoring
  73% で中央値が T に張り付くため p25 を採用し「L_50」とラベルし続けている
  (`S6_tau_max_calibration.json` の rule 欄)。判断自体は合理的だが、**事後的な規則
  変更**であることを diff/論文で明示しないと pre-registration の体裁が崩れる
- 単一 τ_max=121 では dose-response が見えない。「効かなかった」場合に
  (a) cap が弱すぎた のか (b) 機構が無い のか識別不能。candidates (b) τ=20 /
  (a) τ=743 は較正 JSON に並記済みなので、主結果が曖昧なら数 seed の感度走査を
  S6.5 に追加するのが安い保険

---

## ⚪ 工程・インフラの問題 (簡潔に)

9. **S5 (A1) の interaction 計算に潜在的 seed 不整合**: `aggregate_ablation_summary.py`
   は dropna 後に**位置で**条件間をペアリングしており、NaN 落ちが起きると seed が
   ずれて DiD が壊れる (S5 実データでは drop 0 件で実害なし)。S6 版では seed merge に
   変更済み。S5 を再集計する機会があれば同修正を推奨
10. **ensemble_summary.parquet の in-place 上書き**: stage ごとに 400→600→700 行と
    同一ファイルを上書き拡張。git 履歴で復元可能だが、versioned filename
    (ensemble_summary_s6.parquet 等) の方が事故に強い
11. **README 追記の冪等性なし**: 集計を 2 回走らせると §S6 が二重追記される
    (A1 版と同じ既知の癖)。S6 版には `--skip-readme` を付けた
12. **S6 の runtime 見積が楽観的**: plan は 600-800 秒/trial を想定したが、本日の
    smoke 実測は 1 run に 17 CPU 分超 (S3 比 ~2.5-3x)。100 trial × 8 worker で
    4-5 時間想定に補正。6/8 の前回実行はこの長さの途中で中断されたと推測される
    (stop trigger の 6h/trial には依然届かない)
13. **集計の実行 platform 逸脱**: plan は §3.7 を Windows 担当とするが、本日は Mac で
    実行する (pandas/scipy のみで platform 非依存)。script 側で platform を log/JSON に
    記録するようにした。Windows での再実行による数値一致確認を推奨

---

## 追記 (同日夜): S6 A3 の実行不能の原因確定と設計欠陥 2 件

S6 の 100 trial は実行凍結した。smoke 1 run が 5h22m 未完 → 計装ラン + cProfile で原因確定:

**(a) 計算爆発の機構** — C3 が速いのは市場が凍結するから。A3 は cap が全 agent を
同期波 (`_last_substitute_t=0` 起点、step 121k で 100 体一斉) でリフレッシュし続ける
ため鎮静化せず、step ~600-700 で持続スパイラルに突入 (100step に 879 秒 = C3 比 490x、
売り板に 2,636 件滞留、平均 71 約定/step)。コストの内訳は PAMS の O(板サイズ) 操作
(`get_price_volume` 55%、`list.remove` の `Order.__eq__` 2.65 億回、cancel 毎 heapify)。
Phase 1 設計 A' の既知スパイラル (speculation_agent.py ヘッダ「book 300→1600」) が
A3 の活動水準で再燃した形。100 trial は 20h+ 必要で stop trigger 該当。

**(b) より根本的な設計欠陥 — substitute の wealth 再抽選が Pareto でない**:
`_substitute()` の新 wealth は `B + U(0,100)` (speculation_agent.py:430 付近)。
つまり C3_A3 は「Pareto 分布を保って個体を入れ替える」のではなく「全員を低い均一
初期値へ flatten していく」操作で、仮説 A revised の検証として解釈が成立しない
(指摘 7 の具体化)。性能を直しても A3 のままでは claim できる因果が変わってしまう。

**判断待ち (Yuito)**: A3 を修正 (波の脱同期 + Pareto 再抽選化 + τ_max 再考) して
続行するか、**A4 (wealth shuffle: 生存 agent 間で sg_wealth を周期 permute) に
乗り換えるか**。A4 は (i) Pareto marginal を正確に保存、(ii) 注文フローを変えない
ので計算爆発も起きない、(iii) persistence のみを切る — 推奨は A4。

---

## 本日の実施事項 (実験進行)

1. LOB Phase 1 前提テスト 4 件 PASS (plan §3.4 ゲート)
2. **S6 A3 ensemble をバックグラウンド起動** (c3-check → smoke → determinism →
   100 trial)。c3-check は rt/lifetimes とも MATCH (6/8 の結果を再確認)
3. `c_ticks_self_consistency.py` v1.1 (指摘 4・5 の対処) + 縮小 smoke PASS
4. `aggregate_ablation_a3_summary.py` 新規実装 (plan §3.7 全項目 + 指摘 1 の pooled
   bootstrap CI + 指摘 2 の matched-horizon 補助分析 + 指摘 9 の seed-paired 修正)
5. S6 sim 完了後: S6 集計 → S5.9 本番 (C2/C3 × seed 1000-1005、Phase A+B) の順で実行予定
