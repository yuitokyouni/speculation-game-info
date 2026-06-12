# Stage S7 diff — freeze→funnel 統合分析の結果 (③符号矛盾 / ①dose-response / ②α-β / SF readout)

実行日: 2026-06-12 (Mac)。対象 open point は Yuito 指示の 3 点 + SF readout。
スクリプト: `code/s7_doseresponse_runs.py` (追加 sim 15 本)、
`code/s7_freeze_funnel_analysis.py` (統合分析)。
出力: `tab_S7_{metric_candidates, bin_diagnosis, doseresponse, matched_horizon, sf_readout}.csv`、
`fig_S7_doseresponse.png`、`logs/S7_summary_for_diff.json`。

---

## ③ 符号矛盾の解消 — 旧 bin_var_slope は zero-P&L 組成の指標だった

**機構が確定した。** 旧 `bin_var_slope` は `Var(log max(|ΔG|, 1e-9))` で、ΔG=0 の
RT が log(1e-9)≈−20.7 に張り付くため、bin 分散は実質「bin 内の zero-P&L RT 比率」
で決まる。証拠: agg 条件で `M_bin_var_floor` と `frac_zero_slope` が小数 3 桁まで
一致 (C0u: −0.398 / −0.398、C0p: −0.433 / −0.433)。

zero を除外 or robust spread に切り替えると **全条件で funnel は強く正**:

| 指標 | C0u | C0p | C2 | C3 |
|---|---:|---:|---:|---:|
| M_bin_var_floor (旧、artifact) | −0.398 | −0.433 | −0.059 | −0.126 |
| M_bin_var_nz (zero 除外) | +0.991 | +0.996 | +0.908 | +1.000 |
| **M_iqr (canonical 採用)** | **+0.977** | **+0.967** | **+0.840** | **+0.941** |
| rho_pearson(h,\|ΔG\|) (参照) | +0.344 | +0.347 | +0.256 | +0.275 |

**Canonical 指標 = M_iqr** (bin 中心 log h vs IQR(ΔG) の Spearman ρ、
選定規則は pre-stated: agg 2 条件で正 + LOB < agg、優先順 M_iqr → M_sd → M_bin_var_nz)。

**重大な帰結 — object #1 (marginal funnel weakening) の再評価**:
符号一貫指標では「agg ≫ LOB」の劇的な funnel 減衰は**ほぼ消える**
(C0u +0.98 vs C2 +0.84、C0p +0.97 vs C3 +0.94)。Phase 2 で「F1」と呼んでいた
agg/LOB 差は、(a) zero-P&L 組成の artifact + (b) freeze による RT 数・構成の変化
であって、**funnel 構造そのものの変質ではない**。
(注意: Spearman は単調性指標で magnitude を測らない。magnitude は ② で評価)

> ⚠ **S7.1 で部分改訂 (2026-06-12、下記「S7.1」節)**: ここで使った M_iqr は **Spearman**
> で、単調性が飽和して magnitude を隠す。実 log-log 指数 b で matched support (h≤32) で
> 測ると **LOB funnel slope は agg の約 3 倍フラット** (b_φ: 0.36→0.13)。「ほぼ消える」のは
> 単調性 (= funnel が存在するか) であって、勾配 (= どれだけ強い funnel か) は LOB で本当に
> 圧縮されている。「funnel 構造そのものの変質ではない」は **slope レベルでは撤回**
> (level は同水準だが slope は圧縮)。zero-P&L artifact の結論 (前段) は維持。

## ② α/β probe — 結果は明確に α (機構は無傷、量だけが変わる) → ⚠ S7.1 で β寄りに改訂

> ⚠ **S7.1 で改訂 (下記「S7.1」節)**: 本節の slope は **Spearman** であり magnitude を
> 測れていない。実 log-log 指数で matched support (h≤32、共通 bin) を測ると、level は
> 同水準だが **slope (指数 b) は LOB で約 3 倍フラット** (b_φ: 0.36 vs 0.13、b_ΔW: 0.31 vs 0.06)。
> → 「per-RT で変質させず (β 棄却)」は **撤回**。完了 RT に限れば per-RT の funnel 勾配は
> LOB で圧縮されている (β 寄り)。「量だけ変わる (α)」は誤り。ただし fill-selection bias
> (完了 RT のみ観測) で「機構変質 vs 長 RT の censoring」は分離不能 (S7.1 残課題)。

共通 horizon support [1, 1500]、同一 log bin で per-bin IQR(ΔG) profile を比較:

| pair | slope agg | slope LOB | matched-bin IQR 比 (LOB/agg、中央値) | verdict |
|---|---:|---:|---:|---|
| C0u vs C2 | +0.957 | +0.843 | 0.75 | **α-like** |
| C0p vs C3 | +0.905 | +0.820 | **1.00** | **α-like** |

同じ horizon の完了 RT を比べると、LOB の per-RT 損益分散 profile は agg と
ほぼ同形・同水準 (Pareto 対では IQR 比 1.00)。~~**friction は funnel 機構を per-RT で
変質させず (β 棄却)、完了 RT の量と構成を変えるだけ (α)**~~ ← **S7.1 で撤回、下記参照**。
fill-selection bias の交絡は残る (LOB 完了 RT は fill された取引に選択されている)
ため secondary evidence の位置づけは維持。

> ⚠ **S7.1**: 「同形・同水準」は **level (IQR 比)** の話で正しいが、profile の **slope** は
> 別物。Spearman ではなく log-log OLS 指数 b で測ると agg 0.31 vs LOB 0.06 (ΔW)。level 一致 +
> slope 圧縮 = 「量 (level) は変わらないが per-RT の funnel 勾配は変質」→ β 寄り。

## ① liquidity dose-response — mediator 鎖は確認、funnel 鎖は「動かすものが無い」

order_volume {15, 30, 60, 120} × 6 seed (C3、1x は data/C3 流用):

| ov | n_rt/trial | censored_frac | funnel_pooled (M_iqr) |
|---:|---:|---:|---:|
| 15 | 4,082 | 0.715 | +0.64 |
| 30 | 4,212 | 0.722 | +0.92 |
| 60 | 5,169 | 0.708 | +0.08 (外れ値、bin ノイズ疑い) |
| 120 | 6,090 | 0.724 | +0.87 |

- **liquidity → 活動量**: ρ(ov, n_rt) = +0.69 — mediator 第 1 リンクは確認
- **liquidity → funnel**: ρ = +0.13 (n.s.) — ③ の帰結と整合。canonical 指標では
  funnel は全水準で既に正 (≈ agg 水準) であり、**「liquidity で回復すべき funnel
  欠損がそもそも無い」**。dose-response は「freeze→funnel 因果」ではなく
  「funnel は freeze に頑健」を示した
- 意外な発見: ρ(ov, censored) = +0.07 — **liquidity を 8 倍にしても censoring は
  ~0.72 で不動**。凍結は流動性供給で量的に動く (RT 数) が、生存構造は動かない。
  S5.6 の ε=0.254 の解釈を精緻化する (活動量は弾性的、freeze 自体は非弾性的)

## SF readout — Q2 への直接回答: SF は LOB で立っており、SG 由来

C2/C3 (SG あり、S5.9 価格系列 6 seed) vs FCN-only (SG なし、3 seed)、T=1500:

| source | 超過尖度 | ACF\|r\| lag1/5/10 | Hill α (上位5%) |
|---|---:|---|---:|
| C2 (SG+FCN) | **+8.6** | 0.66 / 0.24 / 0.14 | **3.0** |
| C3 (SG+FCN) | **+7.9** | 0.62 / 0.19 / 0.11 | **3.3** |
| FCN-only | −0.7 | 0.22 / 0.04 / 0.07 | 13.0 |

**fat tail (尖度 ~8、Hill α ≈ 3 = 実証研究の cubic law 水準) と vol clustering
(ACF\|r\| の緩やかな減衰) が LOB+SG で明確に出現し、SG を抜くと消える。**
91% censoring (凍結) 下でも、稀な SG 取引が SF を生成している。
→ 計画書 Q2 の懸念 (「SF が立たない土台に L1 を積むのか」) は**棄却**:
L1 の前提 (LOB で SF が立つ) はデータで確保された。帰属も FCN 支配ではなく
SG 由来と確定 (Q1 の文脈でも「SG は凍結していても市場を駆動している」)。
caveat: T=1500・6 seed の readout。ACF の長 lag 減衰・Hill の安定性は
T=10k 価格ロギング再走で確認するのが望ましい (S7.1 候補、優先度は下がった)。

---

## 統合 — 3 object の最終整理と (b) の物語

- **#2 (wealth×world interaction)**: 落とす (A1/A4 null + CI 0 跨ぎ、確定済み)
- **#1 (marginal funnel weakening)**: **大部分が指標 artifact だった**。
  符号一貫指標では agg/LOB の funnel 差は小さく、matched-horizon では機構同形 (α)
- **#3 (#1 の原因)**: ~~「freeze が funnel を弱める」ではなく「freeze は完了 RT の量と
  組成を変えるだけで、funnel 機構は無傷」が答え~~ → **S7.1 で改訂**: freeze は完了 RT の
  量・組成を変える **だけでなく**、per-RT funnel の **slope も ~3 倍圧縮**する (level は保存)。
  「funnel 機構は無傷」「壊すべき機構の変質が存在しなかった」は **撤回** — 勾配の圧縮という
  形で per-RT の変質が存在する。A1/A4 (q 切替) が null だったのは、変質が q 経路ではなく
  freeze (fill 律速) 経路だから、と整合的に読める

**(b) の中心主張 (改訂版)**:
1. LOB 移植で SG の富動学は凍結する (survival 91%/73%、hazard≈0、fill 律速、
   c_ticks 再較正に頑健 — S5.7/S5.8/S5.9、頑健)
2. 凍結は活動量を抑えるが、(i) ~~funnel 機構は per-RT で無傷 (α、S7)~~ → **S7.1 改訂**:
   per-RT funnel の **level は保存・slope は LOB で ~3 倍圧縮** (b_φ 0.36→0.13)。
   freeze は RT 数だけでなく per-RT dispersion 勾配も変える (β 寄り、fill-selection 交絡あり)、
   (ii) SF 生成能力は無傷どころか SG が SF の源泉 (S7 SF readout)
3. Phase 1 の「F1 interaction」は zero-P&L 組成 artifact + 凍結による構成変化で
   説明される (S7 ③)。単一 seed の示唆 → ensemble で消失 → 原因追跡で
   freeze を発見、という breadcrumb 構成で報告する
   (補足 S7.1: F1 = wealth×world interaction は ΔW=φ·q 指数で測っても null、変数非依存に確定)

この構成は「focused (freeze 一本) + grounded (survival・fill・SF の実測)」で、
かつ L1 への接続 (SF 土台あり、SG 由来) が立つ。

## S7.1 — funnel を φ vs ΔW=φ·q で分解、実 log-log 指数 b で再測定 (2026-06-12)

契機: Yuito 指摘「delta(G) を除くことで RT の解釈が変わっている可能性」。
スクリプト: `code/s71_phi_vs_dW_funnel.py`。出力: `logs/S71_summary_for_diff.json`、
`outputs/figures/fig_S71_phi_vs_dW_funnel.png`、`outputs/tables/tab_S71_per_seed_{full,matched}.csv`。
詳細 note: `plans/note_RT_interpretation_after_zero_exclusion.md`。

**S7 の「α / 機構無傷」を覆した。** funnel を `delta_g` (= φ、per-unit 認知利益、q-blind) で
測っていたこと、および Spearman が magnitude を飽和させていたことが根因。

### 実測 (matched support h≤32、共通 bin、pooled / per-seed mean 一致)

| | b_φ (拡散指数) | b_ΔW=φ·q | amp=b_ΔW−b_φ | M_iqr(φ) Spearman |
|---|---:|---:|---:|---:|
| C0u (agg uniform) | **+0.36** | +0.31 | −0.05 | +0.93 |
| C0p (agg pareto)  | **+0.37** | +0.32 | −0.04 | +0.93 |
| C2 (LOB uniform)  | **+0.13** | +0.06 | −0.09 | +0.71 |
| C3 (LOB pareto)   | **+0.13** | +0.08 | −0.05 | +0.72 |

(full-range adaptive bin でも同傾向: agg b_φ≈0.45 / LOB b_φ≈0.12)

### 結論

1. **funnel magnitude は LOB で本当に弱い (slope ~3 倍フラット)**。Spearman (S7 §②) は
   単調性が飽和し magnitude 差を隠していた。level (IQR 水準) は同程度 — slope だけが圧縮。
   → S7 の「α (量だけ変わる)」は誤り、β 寄り (realized per-RT funnel 勾配が圧縮)。
2. **q は funnel slope を急峻化しない** (amp ≤ 0)。富増幅は level に乗り、保有期間勾配には
   乗らない。「F1 を ΔW で測れば interaction が出る」仮説も棄却 (b_ΔW interaction
   +0.043 [+0.001,+0.086]、amp interaction +0.031 [−0.007,+0.068] でほぼ 0 跨ぎ)。
3. **zero 除外は cherry-picking でない**: zero-fraction は agg/LOB ほぼ同形・非単調
   (h≈2-3 でピーク→減衰)、短 horizon 偏在せず → funnel 比較を歪めない。S7 ③ の
   zero-floor artifact 結論は維持。
4. caveat: **fill-selection** (完了 RT のみ観測) で「機構変質 vs 長 RT の censoring」は
   分離不能。**離散性** (φ 小整数) は連続な ΔW で同傾向を確認して打ち消し済。

## Limitations / 残作業

- ~~M_iqr は Spearman で magnitude を測らない → 論文化の際は matched-horizon
  IQR profile (magnitude) と併記する 2 段構え~~ → **S7.1 で実施 (指数 b)。slope 圧縮を確定**
- **[保留・次やること] fill-selection の分離**: censored RT 込みの survival-aware funnel
  推定 (打ち切り込み quantile regression 等) で「per-RT 機構変質 vs 長 RT の censoring」を
  分ける。S7.1 の β寄り結論の機構帰属を確定する核心 (Yuito 指示 2026-06-12 で保留)
- **[保留・次やること] 指数 b の bootstrap CI**: 現状 per-seed mean の SE のみ。LOB の
  slope CI と matched cap 感度 (h≤16/64) を bootstrap で確定 (Yuito 指示 2026-06-12 で保留)
- ov=60 の funnel_pooled 外れ値は bin ノイズ疑い (per-seed 分布で確認可)
- agg 条件の ③/② は 20 seed subsample (メモリ対策、JSON に明記)
- 旧 bin_var_slope で書かれた過去 stage の数値 (S2-S6r の表) は「zero-P&L 組成
  指標」として読み直しが必要 — dossier 更新時に注記必須
- SF readout の T=10k 版 (S7.1、優先度低)
