# YH007: Self-organized Speculation Game — 論文3 再現

**状態: 計画策定済 (paper3_spec.md v0.1)、未実装**。Katahira-Chen-Akiyama (2021) "Self-organized Speculation Game for the spontaneous emergence of financial stylized facts" *Physica A* (PDF: `katahira2021 self-organized.pdf`、抽出 txt: `katahira2021_extracted.txt`) の再現。

→ **canonical spec は [`paper3_spec.md`](./paper3_spec.md)**。本 README は概略のみ。

---

## 位置付け (改訂版、2026-06-12)

| | YH005 Lite | YH006 / YH006_1 | **YH007 SOSG** |
|---|---|---|---|
| N | 外生固定 (1000 or 100) | 外生固定 | **内生 (BTW analogy で自己組織化)** |
| S | 任意 (S=2 主) | S=2 | **S=1 (削減、論文1+2 で正当化済)** |
| C | 外生固定 (3.0) | 外生固定 | **外生固定 (3.0、変更なし)** |
| 主題 | 機構分析 (Null test) | LOB 移植 + freeze 機構 | **N の自己組織化 / SOC analogy** |
| 削減パラメタ | — | — | (N, S) → 計 5 → 3 |

**注: 当初 README で「C を内生化」と記述していたが、精読の結果 SOSG の主題は「N の内生化」であることが判明**。C は依然として外生固定 (3.0)。詳細は `paper3_spec.md` §0-1。

---

## モデル骨子 (詳細は paper3_spec.md §1)

- **Inflow**: 毎時刻 t、新規 player 1 名が `w_init = 10·B` で参入 (BTW の砂粒落下に対応)
- **Outflow**: player は `w_i(t) < B` になると退場 (BTW の閾値超え崩壊に対応)
- **Wealth conservation (近似)**: Σw_in ≈ Σw_maker + Σw_exit (Eq.8、time-averaged)
- **N(t) 収束**: B=9 で N* ≈ 700、収束時間 ~5000 step (Fig.1)
- **Stylized facts**: 11 中 10 を再現 (gain/loss asymmetry のみ未再現、元 SG と同じ)
- **Quasi-critical**: vol ACF が log decay (true critical の power-law ではない)

---

## 実装方針 (詳細は paper3_spec.md §3, §7)

YH005 `simulate.py` を fork して **N を動的リスト化**するのが最小改変。コード変更点は paper3_spec.md §3.1 に列挙:
1. agent を動的リスト化 (insertion/removal を support)
2. 入場ロジック (1/step, w_init=10B, 新規戦略 RNG seed = derived)
3. 退場ロジック (w<B でリスト除外、保有 position は強制 close → wealth 反映)
4. logging 追加 (N_history, inflow/outflow_count, w_*_cum)
5. Δp の分母を動的 N(t) に変更

bit-parity は要求しない (N 動的化で RNG 順が根本的に変わる)。代わりに **SF readout の数値一致** (誤差 < 10%) を契約。

---

## 実行 (予定、Step 2 以降)

```bash
cd experiments/YH007
python code/run_baseline.py --B 9 --T 50000 --seed 777     # Fig.1 + Fig.2 再現
python code/run_robustness.py --B 9,18,27 --T 50000 --n_trial 20    # Fig.4 再現
python code/run_sf_validation.py --T 50000 --n_trial 100    # Hill α, vol ACF
```

メイン出力:
- `outputs/figures/fig_N_history.png` — Fig.1 (B=9 単 trial)
- `outputs/figures/fig_return_series.png` — Fig.2
- `outputs/figures/fig_N_vs_B.png` — Fig.4
- `outputs/figures/fig_powerlaw_returns.png` — Fig.5
- `outputs/figures/fig_powerlaw_wealth.png` — Fig.6
- `outputs/figures/fig_volacf.png` — Fig.7
- `outputs/figures/fig_inflow_outflow.png` — Fig.8/9

---

## ディレクトリ構成 (案)

```
experiments/YH007/
├── paper3_spec.md              # ★ canonical spec (本 README はこのリンク先優先)
├── katahira2021 self-organized.pdf
├── katahira2021_extracted.txt  # pdftotext 抽出 (精読用)
├── code/
│   ├── selforg_sim.py          # YH005 simulate.py を fork + N 動的化
│   ├── run_baseline.py
│   ├── run_robustness.py
│   ├── run_sf_validation.py
│   └── analysis.py             # YH005 analysis を import 流用
├── tests/                      # SF readout parity (誤差 < 10%)
└── outputs/{figures,tables,runtime_logs}/
```

---

## 受け入れ基準 (paper3_spec.md §5 参照)

| 指標 | 論文値 | YH007 目標 |
|---|---|---|
| N* (B=9) | ~700 | 600-800 (±15%) |
| 収束所要時間 (B=9) | ~5000 step | ≤ 10000 |
| Hill α (|r|, B=9) | 4.56 | 3.5-5.5 |
| Δw/B Hill α | 3.38 | 2.5-4.5 |
| vol ACF τ=50 | ~0.1-0.2 | > 0.05 |
| vol ACF type | log > power | LR test 有意 |
| B → N* monotonicity | Fig.4 で明示 | ρ(B, N*) > 0.9 |

---

## YH006_1 (LOB / freeze 結果) との接続

YH006_1 S5.x-S7 で「LOB friction → 91% censoring → outflow rate ≈ 0」が確定 (canonical metric M_iqr では funnel 機構そのものは無傷だが、agent turnover は実質停止)。

含意 (paper3_spec.md §6):
- SOSG の Eq.7/8 (inflow-outflow balance) は outflow > 0 を要求
- **LOB-on-SOSG (naive 移植) は成立しない**: Σw_in が monotonically 蓄積、N(t) が発散
- SOSG-on-LOB を実現するには outflow 補強機構 (τ_max cap / entry stochastic gate / market maker 明示化) が必要 — これは YH008 以降の研究テーマ

逆に **aggregate 世界 (YH005 sim) では outflow ~99%** (S2 結果) なので、YH007 baseline (aggregate, paper3 全面再現) は素直に成立する見込み。

---

## 残作業

### Step 1 ✓ (完了, 2026-06-12)
- 論文3 PDF を精読し `paper3_spec.md` v0.1 起草
- 旧 README の「C 内生化」誤識別を本書で訂正

### Step 2 (次)
- `code/selforg_sim.py` を最小実装し Fig.1 + Fig.2 を 1 seed で再現
- 受け入れ: §5 表の最初 2 行 (N* と収束時間)

### Step 3
- 100 trial で SF readout (Hill α, vol ACF)、§5 表の残り検証

### Step 4
- B ∈ {9, 18, 27} robustness scan、Fig.4 再現

### Step 5 (option、YH006_2 完了後)
- LOB 移植準備、outflow 補強機構の smoke

---

## 参考文献

- Katahira K., Chen Y., Akiyama E. (2021). Self-organized Speculation Game for the spontaneous emergence of financial stylized facts. *Physica A: Statistical Mechanics and its Applications* 580, 126103. DOI: 10.1016/j.physa.2021.126103
- Bak P., Tang C., Wiesenfeld K. (1987/1988). Self-organized criticality. *Physical Review A* 38, 364. [BTW sandpile 原典]
- 論文1 (Katahira et al. 2019, *Physica A* 524): SG 原典 — YH005 が再現
- 論文2 (Katahira-Chen 2020, *JSSC*): heterogeneous round-trip — YH005_1 が再現
- 論文3 (本文献): SOSG — YH007 で再現予定
