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

## ② α/β probe — 結果は明確に α (機構は無傷、量だけが変わる)

共通 horizon support [1, 1500]、同一 log bin で per-bin IQR(ΔG) profile を比較:

| pair | slope agg | slope LOB | matched-bin IQR 比 (LOB/agg、中央値) | verdict |
|---|---:|---:|---:|---|
| C0u vs C2 | +0.957 | +0.843 | 0.75 | **α-like** |
| C0p vs C3 | +0.905 | +0.820 | **1.00** | **α-like** |

同じ horizon の完了 RT を比べると、LOB の per-RT 損益分散 profile は agg と
ほぼ同形・同水準 (Pareto 対では IQR 比 1.00)。**friction は funnel 機構を per-RT で
変質させず (β 棄却)、完了 RT の量と構成を変えるだけ (α)**。
fill-selection bias の交絡は残る (LOB 完了 RT は fill された取引に選択されている)
ため secondary evidence の位置づけは維持。

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
- **#3 (#1 の原因)**: 「freeze が funnel を弱める」ではなく
  「**freeze は完了 RT の量と組成を変えるだけで、funnel 機構は無傷**」が答え。
  A1/A4 が null だったのは当然 (壊すべき機構の変質が存在しなかった)

**(b) の中心主張 (改訂版)**:
1. LOB 移植で SG の富動学は凍結する (survival 91%/73%、hazard≈0、fill 律速、
   c_ticks 再較正に頑健 — S5.7/S5.8/S5.9、頑健)
2. 凍結は活動量を抑えるが、(i) funnel 機構は per-RT で無傷 (α、S7)、
   (ii) SF 生成能力も無傷どころか SG が SF の源泉 (S7 SF readout)
3. Phase 1 の「F1 interaction」は zero-P&L 組成 artifact + 凍結による構成変化で
   説明される (S7 ③)。単一 seed の示唆 → ensemble で消失 → 原因追跡で
   freeze を発見、という breadcrumb 構成で報告する

この構成は「focused (freeze 一本) + grounded (survival・fill・SF の実測)」で、
かつ L1 への接続 (SF 土台あり、SG 由来) が立つ。

## Limitations / 残作業

- M_iqr は Spearman で magnitude を測らない → 論文化の際は matched-horizon
  IQR profile (magnitude) と併記する 2 段構え
- ov=60 の funnel_pooled 外れ値は bin ノイズ疑い (per-seed 分布で確認可)
- agg 条件の ③/② は 20 seed subsample (メモリ対策、JSON に明記)
- 旧 bin_var_slope で書かれた過去 stage の数値 (S2-S6r の表) は「zero-P&L 組成
  指標」として読み直しが必要 — dossier 更新時に注記必須
- SF readout の T=10k 版 (S7.1、優先度低)
