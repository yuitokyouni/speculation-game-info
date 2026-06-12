# Note: ΔG=0 除外 → RT 解釈 → funnel 指数の再測定 (S7.1)

作成: 2026-06-12、契機: Yuito 指摘「delta(G) を除くことで RT の解釈が変わっている可能性」
実測: `code/s71_phi_vs_dW_funnel.py`、`logs/S71_summary_for_diff.json`、
`outputs/figures/fig_S71_phi_vs_dW_funnel.png`、`outputs/tables/tab_S71_per_seed_{full,matched}.csv`

**結論 (先出し、S7.2 で更新)**: Yuito の懸念は妥当だった。S7.1 で「LOB funnel slope ~3倍
圧縮 (β)」と出したが、**S7.2 の de-selection gate で、その β は大部分が completion-selection
(α) と判明** — Yuito の事前予測通り。最終的に S7 の「機構ほぼ無傷 (α)」に近い所へ着地し、
**小さな真の残差 (~17% のフラット化) のみが機構由来**。funnel の主張は dossier「桁で浅い」→
S7「artifact, α」→ S7.1「β (3倍圧縮)」→ **S7.2「3倍の3/4は selection、真の機構効果は小」**
と 3 回転した。**だからこそ Yuito は dossier 反映前に gate を要求した — 正しかった**。
(当初の私の仮説「zero と spread は拡散の裏表」「F1 は q-blind 起因」は両方データに棄却済)

---

## 0. 実測サマリ (4 条件、matched support h≤32、共通 bin、pooled / per-seed mean)

| | b_φ (拡散指数) | b_ΔW=φ·q | amp=b_ΔW−b_φ | M_iqr(φ) Spearman |
|---|---:|---:|---:|---:|
| C0u (agg uniform) | **+0.36** | +0.31 | −0.05 | +0.93 |
| C0p (agg pareto)  | **+0.37** | +0.32 | −0.04 | +0.93 |
| C2 (LOB uniform)  | **+0.13** | +0.06 | −0.09 | +0.71 |
| C3 (LOB pareto)   | **+0.13** | +0.08 | −0.05 | +0.72 |

(full-range adaptive bin でも同傾向: agg b_φ≈0.45、LOB b_φ≈0.12。pooled matched と per-seed mean が一致 → 頑健)

---

## 1. 当初仮説の棄却

### 棄却1: 「zero と spread は同じ √τ 拡散の裏表」→ ✗
- spread は確かに拡散的 (agg b_φ≈0.36、√τ=0.5 よりやや sub-diffusive)
- だが zero 質量は **1/√τ で減らない**。zero-fraction は horizon に対し **非単調**
  (h=1 で ~0.02 → h≈2-3 でピーク ~0.6 → h=32 で ~0.1-0.2 へ減衰、fig 右パネル)
- → 「同じ拡散の裏表」という綺麗な話は成立しない。a_zero スカラーは非単調ゆえ無意味 (報告しない)

### 棄却2: 「F1 が null なのは q-blind な φ で測ったから、ΔW なら出る」→ ✗
- ΔW=φ·q で測っても wealth×world interaction は null:
  b_ΔW interaction = +0.043 [+0.001, +0.086] (CI が 0 をかろうじて外れる程度)、
  amp interaction = +0.031 [−0.007, +0.068] (0 跨ぎ)
- → **F1 は変数を変えても null**。S7 の「#2 (interaction) は落とす」判断は正しかった

---

## 2. zero 除外が cherry-picking でない理由 (Yuito 懸念への直接回答)

当初の心配「ゼロを除くと短 horizon を不均等に削り funnel を捏造しうる」は **杞憂**。実測では:
- zero-fraction の agg/LOB プロファイルは **ほぼ同形** (fig 右、LOB が長 horizon でわずかに高いだけ)
- zero は短 horizon に強く偏在していない (h=1 はむしろ最小、ピークは h≈2-3)
- → zero 除外は funnel を**水増ししない**むしろ保守的。`M_bin_var_nz` (zero 除外) が +0.99 で
  `M_bin_var_floor` (zero を −20.7 に floor) が −0.40 だった符号矛盾は、後者が
  「mixing 分散」を測る数値 artifact だっただけ (S7 ③ の結論は維持)
- **誠実な言い方**: 「ゼロを除いて funnel が出る」ではなく「funnel は nonzero spread が担い、
  zero 組成は agg/LOB でほぼ共通なので funnel 比較を歪めない」。但し書きは要らない

---

## 3. 覆った S7 結論: funnel magnitude は LOB で本当に弱い (α → β寄り)

S7 ② は matched-horizon の **Spearman slope** で agg 0.96 vs LOB 0.84 を「alpha-like (profile 同形)」
と判定し、「機構は per-RT で無傷、量だけ変わる (α)」と結論した。

**しかし Spearman は単調性しか見ず magnitude を飽和させる** (S7 自身が Limitations で警告)。
実 log-log 指数 b で測り直すと:
- **level (IQR 水準) は似ている** (S7 の IQR 比 ~0.75-1.0 と整合。fig 中央で LOB ΔW はむしろ高水準)
- **slope (指数 b) は ~3 倍フラット** (agg 0.36 vs LOB 0.13 on φ、0.31 vs 0.06 on ΔW)

→ S7 の「α (量だけ変わる、機構無傷)」は **over-claim**。完了 RT に限れば、**per-RT の
「保有期間とともに損益分散が広がる」勾配そのものが LOB で圧縮されている** (β 寄りの証拠)。

### caveat (2 つ、結論を弱めない範囲で明記)
1. **fill-selection**: LOB 完了 RT は約定したものに選択されている。flat な funnel は
   「機構が壊れた」のか「広 spread の長 RT が censoring で完了しない」のか分離不能。
   どちらでも **「realized per-RT funnel magnitude は減る」= S7 の『量だけ』は誤り** は成立
2. **離散性**: φ は小整数で IQR(φ) が粗く量子化 (fig 左の階段)。ただし連続な ΔW=φ·q でも
   同じ傾向 (LOB b=0.06 vs agg 0.31) なので結論は離散性に依存しない

---

## 4. q の役割 (副次発見)

amp = b_ΔW − b_φ は全条件で **≤ 0** (agg でも −0.04〜−0.05)。
→ q (=⌊w/B⌋) は funnel の **slope を急峻化しない**。むしろ ΔW の level を上げるだけ
(fig 中央: LOB ΔW は高 level・flat slope = 大口取引はあるが保有期間で分散が伸びない)。
富増幅機構は「保有期間 funnel の傾き」には乗らず、損益の絶対水準に乗る、と読み替えられる。

---

## 5. 報告言い換え (S7 diff / dossier 反映必須)

`stage_S7_diff.md` の以下を改訂:
- §② 「結果は明確に α (機構は無傷、量だけが変わる)」
  → 「**level は同水準だが slope (log-log 指数) は LOB で ~3 倍フラット**。Spearman では
    単調性が飽和し magnitude 差を見落としていた。realized per-RT funnel は LOB で圧縮
    (β 寄り)。fill-selection で『機構変質 vs 長 RT の censoring』は分離不能だが、
    いずれにせよ『量だけ変わる』は誤り」
- 統合 (b) §2(i) 「funnel 機構は per-RT で無傷 (α、S7)」
  → 「per-RT funnel の **傾きは LOB で圧縮** される (b: 0.36→0.13、S7.1)。
    level 保存 + slope 圧縮。freeze は RT 数だけでなく per-RT dispersion 勾配も変える」
- 統合 §3 「壊すべき機構の変質が存在しなかった」
  → この主張は **撤回**。傾きの圧縮という形で per-RT の変質が存在する

「F1 interaction を落とす」「zero-floor は artifact」という S7 の他の結論は **維持**。

---

## 6. 残課題 (優先度 Yuito 判断)

- ~~**fill-selection の分離**~~ → **S7.2 で実施・解決 (下記 §7)**
- **指数 b の CI を bootstrap で確定** (現状 per-seed mean の SE のみ。LOB の slope CI を出す) — 保留
- **matched support の cap 感度** (h≤16/64 で b 比が安定か。現状 32 のみ headline) — 保留

---

## 7. S7.2 — de-selection gate: β vs selection の分離 (2026-06-12、解決)

Yuito 指摘: 「level 保存・slope 圧縮」という S7.1 の β signature は selection-on-completion が
出す signature と同型。matched support 内でも上位 bin ほど LOB 完了 RT は fill-lucky な部分集合で
密度が落ちる → β とも α(selection)とも整合。分離しないと #2(i) は overclaim か vacuous。

### 手法: 無条件 structure function (position 非参照 = 完全 de-selection)

スクリプト: `code/s72_cognitive_structure_function.py`。出力: `logs/S72_summary_for_diff.json`、
`outputs/figures/fig_S72_structure_function.png`。

認知価格 P(t) の **無条件 structure function** S(h) = IQR_t(P(t+h) − P(t)) を測る。position を
一切参照しないので completion-selection も fill-luck も原理的に入らない。完了RT funnel
φ = a·(P(t_close)−P(t_open)) は S(h) 母集団の (選択された) 部分標本 → S(h) の指数 b_struct を
agg/LOB で比べれば「認知価格過程そのものが違うか」が分かる。

- データ源: agg = `simulate_aggregate` 再走 (Windows、PAMS 不要、決定的) の `cognitive_prices`。
  LOB = 既存 `data/_s59_cticks/PhaseA/prices_*.parquet` (6 seed, c_ticks=28) から
  P(t)=cumsum(quantize(Δmid, 28)) を再構成。
- **再構成式の検証**: agg で `cumsum(quantize(Δprices, 3))` が厳密 `cognitive_prices` と
  一致率 **1.0** (proper boundary)。boundary 規約差は P の定数シフトのみで structure function
  には無影響 (b 差 = 0.0000)。→ LOB 再構成も信頼できる。
  (LOB parity 0.33 は「S5.9 価格系列 ≠ S3 RT の別 run」を示すだけ、structure function は
  RT 非参照なので無関係)

### 結果

| | b_struct (無条件) | b_completed (S7.1) |
|---|---:|---:|
| agg (C0u/C0p) | **+0.36** | +0.36 |
| LOB (C2/C3) | **+0.30** [C2 0.31, C3 0.29] | +0.13 |
| ratio LOB/agg | **0.83** | 0.36 |

- **agg 対照が通った**: b_struct(0.36) ≈ b_completed(0.36)。凍結のない世界では無条件 funnel と
  完了RT funnel が一致 → 手法が valid、agg 側に selection なし
- **LOB**: b_struct(0.30) ≫ b_completed(0.13)。無条件の認知価格過程は agg より **約 17% しか
  フラットでない** (ratio 0.83) のに、完了RT funnel は **約 3 倍フラット** (ratio 0.36)

### 判定: β は大部分が selection (gate 解決)

slope 低下の内訳: 機構由来 0.36→0.30 (Δ=0.06)、selection 由来 0.30→0.13 (Δ=0.17)
→ **funnel slope 圧縮の約 3/4 は completion-selection**。LOB 完了 RT は fill-lucky で funnel が
フラットに見える部分集合だった。

- **S7.1 の「β (3倍圧縮、機構変質)」は大部分撤回**。S7 の「機構ほぼ無傷 (α)」に近い所へ着地
- **小さな真の残差** (~17%、ratio 0.83) のみが認知価格過程の genuine なフラット化
  (freeze が認知価格の 1 step あたり変動をわずかに抑える)
- → freeze の funnel への支配的効果は「**どの RT が完了するか**」(selection) であって
  「per-step 認知機構を変える」ことではない

### caveat と残り

- S7.2 は **無条件** structure function (entry-time も含めた完全 de-selection)。Yuito が指定した
  **位置依存**版 (全 open position の未実現 |Δφ|、凍結 entry 込み) とは厳密には別物。ただし
  無条件で ratio 0.83 vs 完了 0.36 という大差が出ており、selection が支配的という結論は
  位置依存版でも覆りにくい。位置依存 faithful 版は P(t)・凍結 entry が未永続化のため
  **LOB=Mac 再走が要る → optional 確認に格下げ** (gate は無条件版で決着)
- 6 seed (LOB 価格ファイルの存在数)。b_struct(LOB) CI は C2 [0.28,0.35] / C3 [0.25,0.33]、
  agg [0.35,0.38]。残差フラット化の有意性は seed 増で要確認だが、核心 (b_struct ≫ b_completed)
  は頑健
