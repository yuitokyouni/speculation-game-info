# YH006: Speculation Game Full — 論文1+2 完全再現

**状態: 骨格 (未実装)**。YH005 Lite が切り捨てた項目を完成させる位置づけ。

Katahira et al. (2019) *Physica A* **524**, 503–518 (論文1) と Katahira & Chen (2019) arXiv:1909.03185 (論文2) の **Fig. を全部** 定量再現する。YH005 の core (`model.py` / `simulate.py` / `analysis.py` / `history.py`) をそのまま再利用し、上に「100 trial ensemble 基盤」「スキャン駆動」「拡張解析」を被せる。

---

## 位置付け

| | YH005 Lite | **YH006 Full** | YH007 |
|---|---|---|---|
| スコープ | 論文1+2 の核 | 論文1+2 の全 Fig. | 論文3 (自己組織化 SG) |
| Trial 数 | 1 | **≥100 (ensemble)** | TBD |
| パラメータ | 単点 (N=1000, M=5, S=2, B=9, C=3.0) | **(M, B) スキャン** | C を内生化 |
| C | 外生固定 | 外生固定 | 内生 (自己組織化) |
| 主要出力 | `results_null_tests.png` / `results_compare_three.png` | `results.png` (多パネル) + スキャン図 | TBD |

---

## 目的 (YH005 が送った項目を全て拾う)

1. **11 stylized facts 全項目** の再現 (論文1 Table 2 / Fig. 2–9)
2. **M–B phase diagram** — `(M, B)` 平面でのスキャン、各 cell で stylized facts を測定
3. **100 trial ensemble 平均** — YH005 は 1 trial、`|r| ACF at τ=50 ≈ 0.119` は論文値 0.21 より低い (finite-sample)。100 trial で論文値に収束するか確認
4. **wealth 分布** — Gini 係数、Pareto tail 指数 `α_w` (論文2 Fig. 8)
5. **Round-trip horizon 分布** — open → close までの step 数分布 (論文2 Fig. 9)
6. **Action ratio の時間変動** — buy/sell/active_hold/passive_hold/idle の動的推移 (論文2 Fig. 10)
7. **GARCH residuals / conditional heavy tails** — `r(t) / σ̂(t)` の裾が Gaussian か (Cont 2001 の SF 項目)
8. **Aggregational Gaussianity の完全曲線** — window を連続変化させた kurtosis(w) (論文1 Fig. 6)

---

## 実行 (予定)

```bash
cd experiments/YH006

# 100 trial ensemble (§8.4 baseline を 100 回、~数十分)
python run_simulation.py ensemble --n_trials 100 --seed_base 777

# M–B phase diagram (所要時間注意)
python run_simulation.py phase_diagram --M_list 3,5,7,9 --B_list 5,9,17

# 論文1 Fig. 2–13 / 論文2 Fig. 1–10 の個別再現
python run_simulation.py paper1_figs
python run_simulation.py paper2_figs
```

メイン出力:
- `results.png` — 論文1 Table 2 相当の 11 SF サマリ図 (ensemble 平均)
- `results_phase_diagram.png` — M–B 平面の stylized facts マップ
- `results_wealth.png` — Gini / Pareto tail / round-trip horizon
- `outputs/*.json` — 全メトリクス

---

## ディレクトリ構成 (案)

```
experiments/YH006/
├── model.py                    # YH005 から再利用 (相対参照 or コピー)
├── simulate.py                 # 同上
├── analysis.py                 # 拡張: Gini, Pareto MLE, GARCH, round-trip, action ratio
├── history.py                  # YH005 から流用
├── ensemble.py                 # seed ループ + trial 平均
├── phase_diagram.py            # (M, B) スキャン
├── paper1_figures.py           # 論文1 Fig. 2–13 再現
├── paper2_figures.py           # 論文2 Fig. 1–10 再現 (Null test は YH005 済み)
├── run_simulation.py           # CLI ランチャー
├── tests/
├── outputs/
├── results.png
├── results_phase_diagram.png
└── results_wealth.png
```

**設計方針**: YH005 の core は bit-parity 済みで信用できる。`from pathlib import Path; sys.path.insert(0, str(Path(__file__).parent.parent / "YH005"))` で import して上乗せ解析のみを書く。**core は複製しない**。

---

## 追加解析関数 (analysis.py への追加 TODO)

| 関数 | 入力 | 出力 | 対応 Fig. |
|------|------|------|---|
| `gini(wealth)` | `w: (N,)` | float | 論文2 Fig. 8 |
| `pareto_tail(wealth)` | `w: (N,)` | `(α_w, x_min)` Clauset MLE | 論文2 Fig. 8 inset |
| `round_trip_horizons(position_ts)` | `pos: (T, N) int8` | `horizons: list[int]` | 論文2 Fig. 9 |
| `action_ratios(num_buy, num_sell, num_active, num_passive)` | 各 `(T,)` | `(T, 5) float` | 論文2 Fig. 10 |
| `garch_residual_stats(returns)` | `r: (T,)` | dict (scaled ACF, kurtosis) | Cont 2001 SF6 |

**simulate 側の拡張が必要な出力**:
- `position_ts: (T, N) int8` — round-trip horizon 算出用 (現状は `final_wealth` のみ)。メモリ `T=50000 × N=1000` = 50MB、許容範囲。

---

## 検証 (受け入れ基準、TODO 埋める)

### 100 trial ensemble

- `|r| ACF at τ=50` の 100 trial 平均が **[0.18, 0.24]** に入る (論文1 Fig. 7 inset `0.2853·exp(-0.006τ)` → τ=50 で 0.211)
- Hill α の 100 trial 平均が **[3.0, 5.0]** (論文1 Fig. 4)
- vol ACF at τ=200 の 100 trial 平均が **[0.01, 0.05]**

### M–B phase diagram

- `(M=5, B=9)` を中心に、いずれの統計量も **monotone な M/B 依存** を示す (TODO: 論文1 Fig. 11/12 を参照して具体閾値を決める)

### wealth

- Gini ≈ 0.5 (TODO: 論文2 Fig. 8 から実数値)
- Pareto tail exponent `α_w ∈ [1.5, 2.5]`

---

## 依存

- YH005 の `model.py` / `simulate.py` / `history.py` (再利用)
- 追加: `scipy.stats`, `arch` (GARCH)、もしくは 自前 GARCH(1,1) を `analysis.py` に

---

## 既知の制約 (YH006 でもスコープ外)

- 自己組織化 (C 内生) → YH007
- Lux-Marchesi / Cont-Bouchaud との比較 → 別実験
- 実データとの quantitative 一致 (S&P500 の α との比較など) → 本研究の範囲外

---

## 未解決 (Yuito 確認事項)

1. **スコープ確認**: 本 YH006 = "Lite が送った項目を全部拾う" 解釈で良いか。代替案として "論文2 の wealth 系解析に特化" もあり。
2. **Ensemble size**: 100 trial で確定か (T=50000 × 100 ≈ 数十分〜1h)
3. **phase diagram の粒度**: `(M, B)` を何点ずつ振るか (論文1 Fig. 11 は ... TODO)
4. **position_ts 出力の追加**: YH005 の `simulate.py` を改変して `position_ts: (T, N)` を返すようにするか、YH006 側で wrapper 書くか

---

## 参考文献

- Katahira, K., Chen, Y., Hashimoto, G., Okuda, H. (2019). *Physica A*, **524**, 503–518. [論文1]
- Katahira, K., Chen, Y. (2019). arXiv:1909.03185. [論文2]
- Cont, R. (2001). Empirical properties of asset returns. *Quantitative Finance*, **1**, 223–236. [SF 定義]
- Clauset, A., Shalizi, C.R., Newman, M.E.J. (2009). Power-law distributions in empirical data. *SIAM Review*, **51**, 661–703. [Pareto tail MLE]
