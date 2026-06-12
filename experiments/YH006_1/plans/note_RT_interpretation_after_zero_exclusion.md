# Note: ΔG=0 除外による RT 解釈の変化 (S7 後の整理)

作成: 2026-06-12、契機: Yuito 指摘「delta(G) を除くことで RT の解釈が変わっている可能性」

S7 で canonical metric を `M_bin_var_floor` (旧) から `M_iqr` (新) に切り替えた。`M_iqr` 自体は zero を除外しないが、診断指標として `M_bin_var_nz` も併用しており、また「zero-P&L 組成 artifact だった」という結論は zero RT の扱いの違いに依存している。**結論を「funnel 機構は無傷」と書く前に、何を "RT" として測っているかを明示する必要がある**。

---

## 1. S7 で起きた指標シフトの再整理

| 指標 | 定義 | zero-ΔG RT の扱い | 何を測るか |
|---|---|---|---|
| `M_bin_var_floor` (旧) | Spearman(log h, Var(log max(\|ΔG\|, 1e-9))) | log floor で −20.7 に固定 | **zero RT の比率変化** に支配される (実質 artifact) |
| `M_bin_var_nz` (診断) | Spearman(log h, Var(log \|ΔG\| \| \|ΔG\|>0)) | **完全除外** | nonzero RT 集団内の対数広がり |
| `M_iqr` (canonical) | Spearman(log h, IQR(ΔG)) | 含むが median が 0 付近のため影響限定的 | 集団全体の中央 50% 幅 |
| `M_sd` (代替) | Spearman(log h, SD(ΔG)) | 含む、外れ値感度高 | 集団全体の分散 |

`frac_zero_slope` (= Spearman(log h, 各 bin の zero 比率)) は **全条件で負** (C0u −0.40, C0p −0.43, C2 −0.20, C3 −0.14)。**短 horizon ほど zero-ΔG が多く、長 horizon ほど少ない**。これは SG の認知利益 φ_i = Σ_{k=t0+1..t} h(k) の構造から自然な帰結 (短 h ほど Σh=0 になりやすい)。

## 2. 「RT の解釈」が変わる 3 つの軸

### (a) 母集団選択バイアス (`M_bin_var_nz` 系)
zero RT を除外すると、**短 horizon の RT を不均等に多く除外**する (frac_zero_slope の符号より)。

- 旧解釈 (all RT): 「全 RT について、長期 RT ほど損益分散が広い」
- 新解釈 (nonzero RT): 「**cognitive 利益が 0 でなかった RT に限れば**、長期 RT ほど対数分散が広い」

これは別の母集団を見ている。前者には wash trades (cognitive 利益 0 で閉じた取引) が含まれる、後者は除外。論文化時に「*conditional on nonzero ΔG*」と注記しないと over-claim になる。

### (b) IQR は zero を含むが「ロバスト」とは別の話 (`M_iqr` の解釈)
`M_iqr` は zero を除外しないので母集団選択バイアスは生じないが、別の問題がある:

- ΔG 分布の中央 50% は **ΔG = 0 を中心とする狭い帯** に集中している (cognitive 利益が正負対称、zero mass が大きい)
- 短 horizon では zero mass が大きく IQR ≈ 0
- 長 horizon では zero mass が縮小し IQR が広がる
- → `M_iqr > 0` は「**広がり**」というより「**zero mass の薄まり**」を測っている可能性

**検証提案**: `M_iqr` を nonzero RT に conditioning して計算し、Spearman を再評価。
- 仮に nonzero conditioning で M_iqr が ≈ 0 になるなら、`M_iqr > 0` の主因は zero mass dilution であって funnel ではない
- 仮に同等の正値が残るなら、`M_iqr` は genuine spread を捉えている
- これを S7 補遺として 1 run 追加するのが最小コストの追加検証

### (c) Freeze と "ΔG=0 RT" の関係 (LOB 固有の交絡)
LOB では完了 RT が ~10-30% (censoring 70-90%)。完了 RT のうち zero-ΔG な物は:

- **tick boundary effect**: open tick と close tick が同一だと p の cognitive 量子化 h で Σh=0 になりやすい (とくに c_ticks ≈ 3·median|Δmid| の coarse granularity 下で)
- **fill timing**: LOB の MARKET fill が遅延し、cognitive 上は同 step 内で open + close が落ちて Σh=0 になる経路

LOB の "freeze" は (i) censoring (= not closed) と (ii) zero-ΔG close (= closed but cognitively flat) の **両方を含む量** として再定義できる可能性がある。S7 ① dose-response で `ρ(ov, censored) = +0.07` (流動性 8 倍で censoring 不動) を見たが、`ρ(ov, frac_zero_dG)` は測っていない。**この測定が freeze の "二層構造" を分解する**。

## 3. 報告言い換えの推奨 (proposal/dossier 向け)

S7 diff の現行 wording: 「funnel 機構は per-RT で無傷 (α)」
推奨 wording: 「**(i)** RT が cognitive 利益 0 でない場合に限れば funnel 機構は per-RT で無傷 (α); **(ii)** zero-ΔG RT は短 horizon に偏在し、freeze の二次的指標として別途記述する」

具体的な書き換え箇所:
- `stage_S7_diff.md` §② 「α/β probe — 結果は明確に α」→ 「α-like (nonzero RT subpopulation で per-RT 機構同形、母集団全体での解釈は §3.1 注記参照)」
- `stage_S7_diff.md` 統合 (b) 中心主張 §2 「funnel 機構は per-RT で無傷 (α、S7)」→ 「nonzero-ΔG RT に限れば funnel 機構は per-RT で無傷 (α-like、S7); zero-ΔG RT の組成変化は freeze の二次指標」

「壊すべき機構の変質が存在しなかった」(統合 §3 の主張) は依然として妥当だが、**「壊すべき」の対象が all RT ではなく nonzero RT の funnel** に絞られる点を補足する。

## 4. 追加検証の最小セット (S7.1 候補、優先度判断は Yuito)

| ID | 内容 | コスト | 期待される弁別 |
|---|---|---|---|
| V1 | `M_iqr` を nonzero conditioning で再計算 (4 条件、既存 parquet で済む) | < 30 min | (b) 軸の決着、zero mass dilution か genuine spread か |
| V2 | dose-response で `ρ(ov, frac_zero_dG)` を追加測定 (既存 6 seed × 4 ov 流用) | < 30 min | (c) 軸の決着、freeze の二層構造 |
| V3 | 短 horizon (h ≤ 5) の RT に絞って `M_iqr` 再計算 | < 30 min | zero mass の影響が最大の領域での挙動 |
| V4 | matched-horizon の IQR を nonzero conditioning で再計算 (§② 表) | < 30 min | α verdict が母集団選択に依存していないか |

V1-V4 はいずれも既存 data ロードで完結、新規 sim 不要。**S7.1 として束ねて 1 セッションで実施可能**。

## 5. 「funnel 機構そのもの」の最低限定義 (もし論文化するなら必要)

S7 までの議論では「funnel」を以下のいずれの意味でも使ってきた:
- (D1) Spearman(\|ΔG\|, h) — Pearson の単調変換、母集団全 RT
- (D2) per-bin spread (IQR/Var) の log h 単調性、母集団全 RT
- (D3) per-bin spread の log h 単調性、母集団 = nonzero RT のみ
- (D4) matched-horizon での IQR profile の同一性 (α verdict)

論文化時には**いずれか 1 つを primary 定義に固定**し、他は付録扱い。元 論文1 Fig.7 の "funnel" は (D1)/(D2) に対応し、本研究もそれに合わせるなら canonical は `M_iqr` で正しい (D2)。ただし「zero mass dilution との分離」(§2(b)) は方法論上の責務として明記する。

---

## まとめ

Yuito の懸念は妥当。S7 で確定した「funnel 機構は無傷」結論は **nonzero-ΔG RT 集団についての主張に絞り込んで再述すべき**。zero-ΔG RT は (i) 短 horizon に偏在し、(ii) freeze と並ぶ "cognitive flat close" として LOB 固有の二次的指標になりうる。

最優先の補強検証は V1 (nonzero conditioning での `M_iqr` 再計算) と V2 (`ρ(ov, frac_zero_dG)`)。両方とも既存 parquet で完結し合計 1 時間未満。S7.1 として実施を推奨。
