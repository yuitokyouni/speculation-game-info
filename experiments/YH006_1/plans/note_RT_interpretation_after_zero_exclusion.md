# Note: ΔG=0 除外 → RT 解釈 → funnel 指数の再測定 (S7.1)

作成: 2026-06-12、契機: Yuito 指摘「delta(G) を除くことで RT の解釈が変わっている可能性」
実測: `code/s71_phi_vs_dW_funnel.py`、`logs/S71_summary_for_diff.json`、
`outputs/figures/fig_S71_phi_vs_dW_funnel.png`、`outputs/tables/tab_S71_per_seed_{full,matched}.csv`

**結論 (先出し)**: Yuito の懸念は妥当で、追跡したら **S7 の結論を 1 つ覆した**。
当初の私の仮説 2 つ (「zero と spread は同じ拡散の裏表」「F1 は q-blind な φ で測ったから null」) は
**両方ともデータに棄却された**。代わりに、funnel を Spearman でなく **実 log-log 指数 b** で
測ると、matched horizon で **LOB funnel は agg の約 3 倍フラット** であることが判明。
S7 の「機構は per-RT で無傷 (α)」は magnitude を Spearman が飽和させて隠していた over-claim。

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

- **fill-selection の分離**: censored RT の counterfactual spread を推定する survival-aware
  funnel 推定 (例: 打ち切り込みの quantile regression)。これが「機構変質 vs 選択」を分ける
- **指数 b の CI を bootstrap で確定** (現状 per-seed mean の SE のみ。LOB の slope CI を出す)
- **matched support の cap 感度** (h≤16/64 で b 比が安定か。現状 32 のみ headline)
