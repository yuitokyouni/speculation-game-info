# YH005 Speculation Game Lite — 実装計画 (Step 1)

本ドキュメントは実装前の計画書。Step 2 (実装) は Yuito (および必要なら Desktop Claude) の承認後に着手する。

---

## § 1. リポジトリ構造と既存実装サマリ

### 1.1 ディレクトリ配置 (観測された現物)

```
speculation-game-info/
├── README.md                       # シリーズ概要 (YH001-005 表あり)
├── requirements.txt                # numpy, matplotlib, scipy, powerlaw, networkx
├── LICENSE, .gitignore
├── analysis/                       # 古い stylized facts 補助 (YH001 向け)
│   ├── stylized_facts.py           # summarize() — hill/acf/kurtosis 1 発
│   ├── tail_exponent.py            # hill_estimator()
│   └── volatility_clustering.py    # abs_return_autocorrelation()
├── docs/                           # literature.md, hypotheses.md — 参考
├── src/                            # 旧 scaffold。K=3, log_return 基準で SG と不整合
│   ├── config.py, run.py
│   └── core/                       # history/market/agent_type_c/v/switching
└── experiments/
    ├── YH001/  Cont-Bouchaud  — 完成 (model.py, run_simulation.py, tail_analysis.py, results.png)
    ├── YH002/  Lux-Marchesi   — 完成 (論文 PDF 同梱)
    ├── YH003/  Minority Game  — 完成 (model.py: 9.1KB, README 詳細)
    ├── YH004/  GCMG           — 完成 (model.py: 11.2KB, README 詳細, 論文 PDF 同梱)
    └── YH005/  Speculation Game — プレースホルダのみ (model.py 11行 docstring、run_simulation.py 4行、README TODO)
```

**pyproject.toml / setup.py は存在しない。** 各実験は `cd experiments/YHxxx && python run_simulation.py` でローカル実行する前提。`from model import simulate` のローカル import。

**tests/ ディレクトリは存在しない。** テストはこれまでどの YH でも書かれていない (README 内の「層3 検証」と呼ばれる動作確認ロジックが run_simulation.py に組み込まれている)。本 YH005 では pytest 方式で新規に導入する。

### 1.2 YH001–004 の `simulate()` 関数まとめ

| 項目 | YH001 | YH002 | YH003 | YH004 |
|------|-------|-------|-------|-------|
| モジュール | `experiments/YH001/model.py` | `experiments/YH002/model.py` | `experiments/YH003/model.py` | `experiments/YH004/model.py` |
| 関数名 | `simulate` | `simulate` | `simulate` | `simulate` |
| seed 型 | `int=42` | `int=42` | `int=42` | `int=42` |
| RNG | `np.random.default_rng(seed)` | 同左 | 同左 | 同左 |
| 返り値型 | `dict` | `dict` | `dict` | `dict` |
| 価格返し | `returns` (Δp) のみ | `prices, returns (log-diff)` | **無し** (attendance のみ) | **無し** (excess のみ) |
| p0 受取 | — | 内部定数 1000 | — | — |
| 主キー | `returns, cluster_sizes` | `prices, returns, z, x, params, zbar` | `attendance, winner, actions, chosen_idx, real_gain, scores_snapshots, final_strategies, final_scores` | `attendance, active, winner, excess, real_gain, personal_final` |

### 1.3 シリーズ共通規約 (観測)

- **seed**: int を引数で受け、`np.random.default_rng(seed)` で Generator 作成。グローバル状態は使わない。
- **返り値**: dict。キー名は camel ではなく snake。`final_*` で末期スナップショット。
- **価格**: MG/GCMG は価格を計算していない。SG は必要 (論文の核が価格動学)。
- **命名**: `N, M, S, T, seed` が共通パラメータ名。
- **ファイル配置**: `model.py` (本体), `run_simulation.py` (実行+図), `README.md` (実験ノート)、`results.png` (出力図) を実験ディレクトリ内に同居。**共通ユーティリティは `analysis/` にあるが古いので、本タスクでは再利用せず YH005 内に自己完結させる** (§5 で詳述)。
- **import スタイル**: `from model import simulate` (ローカル import、パッケージ化はしていない)。

### 1.4 YH005 を追加する際の配置案 (提案、Yuito の承認事項)

**案 A: 既存のシリーズ規約に従い、YH005 内で自己完結**

```
experiments/YH005/
├── model.py                  # Agent+Market クラスの参照実装 (run_reference)
├── simulate.py               # ベクトル化 simulate() + parity 版
├── analysis.py               # log_returns, vol_acf, ccdf, hill, kurtosis
├── history.py                # K=5 base encoder + quantize (SG 専用)
├── _mg_gcmg_baseline.py      # YH003/YH004 の simulate を import + S=1 ラッパ
├── reproduce_null_tests.py   # 論文2 Fig.11 再現
├── compare_three_models.py   # 3モデル比較図
├── README.md                 # 設計選択表を含む
├── tests/
│   └── test_parity.py
├── outputs/                  # *.png, *.json (results.png は既存規約に従い直下)
└── (results.png)             # 既存シリーズ規約のメイン出力図
```

- 既存シリーズ規約 (`experiments/YHxxx/{model.py, run_simulation.py, README.md, results.png}`) と完全整合
- ローカル import のみで動く (`cd experiments/YH005 && pytest tests/`)
- 旧仕様の `src/core/history.py` (K=3, log_return) は使わず、SG 用に自己完結

**案 B: リポジトリルートに `yh_common/` パッケージを新設** (Step 0 プロンプト原案)

```
yh_common/{__init__.py, _mg_history.py}
yh005_speculation_game/{__init__.py, model.py, simulate.py, analysis.py, _mg_gcmg_baseline.py}
tests/test_parity.py
scripts/{reproduce_null_tests.py, compare_three_models.py}
outputs/{*.png, *.json}
```

- 将来 `yh_common` を YH006/007 でも再利用できる
- が、YH001–004 は `yh_common` を使っていないので「共通」の実体は YH005 専用になってしまう
- パッケージ import (`from yh005_speculation_game.simulate import simulate`) となり、既存の `cd experiments/YHxxx && python run_simulation.py` 流儀と齟齬

**推奨: 案 A。** 既存シリーズ規約の踏襲が最優先。Step 0 プロンプトが想定した `yh_common/` の実体は「K=5 history encoder + quantize」だけで小さい。これは `experiments/YH005/history.py` に置くのが素直。

---

## § 2. YH003 (MG) と YH004 (GCMG) の詳細

### 2.1 YH003 `simulate()` 詳細

**シグネチャ** (`experiments/YH003/model.py:117`):
```python
simulate(
    N: int,
    M: int,
    S: int,
    T: int,
    seed: int = 42,
    track_scores_at: tuple[int, ...] = (),
    record_attendance: bool = True,
) -> dict
```

**返り値 dict のキー**:
- `attendance: (T,) int64` — 各ステップの A 側人数 (+1 を選んだ数)
- `winner: (T,) int8` — 勝ち側 ±1
- `actions: (T, N) int8` — 各エージェントの選択 ±1
- `chosen_idx: (T, N) int16` — 各エージェントが選んだ戦略 index
- `real_gain: (N,) int64` — 全期間の実利得
- `scores_snapshots: dict[int, (N,S) int64]`
- `final_strategies: (N, S, 2**M) int8`
- `final_scores: (N, S) int64`

**価格更新則**: **無し**。excess = `2*attendance - N` を後処理で計算可能。Δp = excess/N で共通 $\Delta p = D/N$ 規則に揃えられる。

**S=1 動作**: ✓ 動く。`np.argmax(scores + perturb, axis=1)` は (N, 1) 配列に対して全て 0 を返す。戦略が 1 本なので inductive learning は消える (argmax が自明)。ただし `perturb = rng.uniform(0, 0.5, size=(N, 1))` の RNG 消費は残る (bit-parity には影響しないが、reference 実装と並べるときの RNG 数を揃える必要あり)。

**p0**: 受け取らない。**価格を計算していないので問題にならない。** 比較図では呼び出し側で `p = p0 + cumsum(excess/N)` と後処理。

**seed/RNG**: `np.random.default_rng(seed)` — 他 YH と同じ。

**log-return の計算責任**: simulate 側では計算しない。呼び出し側で `excess → Δp → p → log-return`。

### 2.2 YH004 `simulate()` 詳細

**シグネチャ** (`experiments/YH004/model.py:152`):
```python
simulate(
    N: int,
    M: int,
    S: int,
    T_win: int,              # sunken-losses 窓幅 (YH003 と名前が違う)
    T_total: int,            # 総ステップ数 (YH003 の T に相当)
    r_min_static: float | None = None,
    lam: float | None = None,
    seed: int = 42,
) -> dict
```

**返り値 dict のキー**:
- `attendance: (T_total,) int32` — A 側人数
- `active: (T_total,) int32` — 非 abstain 人数
- `winner: (T_total,) int8` — 勝ち側 ±1 (全員 abstain のとき `rng.random()` で coin flip)
- `excess: (T_total,) int32` — `actions.sum()` を直接返す (MG と違って abstain がいるので 2A-N ではない)
- `real_gain: (N,) int64`
- `personal_final: (N,) int8` — 個人 rolling r_i の最終値

**価格更新則**: **無し**。`excess` が直接とれるので `Δp = excess / N`。

**S=1 動作**: ✓ 動く。`np.argmax` は同様に 0 を返す。`best_scores = scores[arange(N), chosen]` が (N, 1) スライスになる点だけ注意 — 型は numpy が自動で shape (N,) にしてくれる。

**p0**: 受け取らない。`cumsum` で後処理。

**r_min の扱い**: `r_min_static` か `lam` のどちらかを必ず指定。比較図では `r_min_static=0` (論文のデフォルト中央値) を使う。`lam=None`、`r_min_static=0.0` が Lite 比較の標準。

**T_win のデフォルト**: 無し。比較図では論文に従い `T_win=50`。

**active 数のログ**: `active: (T_total,)` として返される。1 ステップ ≥1 ならば OK、0 になったら coin flip (`rng.random()` を 1 回消費)。

**log-return の計算責任**: simulate 側では計算しない。

### 2.3 3 モデル比較での呼び出し設計

3 モデルを同一形式 (log-returns 時系列 + ACF + CCDF) に揃える。疑似コード:

```python
# MG
res = yh003_sim(N=1000, M=5, S=1, T=50000, seed=123)
excess = 2 * res["attendance"].astype(np.int64) - N       # (T,)
dp = excess / N                                            # (T,)
p = p0 + np.cumsum(dp)                                     # (T,)

# GCMG
res = yh004_sim(N=1000, M=5, S=1, T_win=50, T_total=50000,
                r_min_static=0.0, seed=123)
dp = res["excess"].astype(np.float64) / N                  # (T,)
p = p0 + np.cumsum(dp)

# SG
res = yh005_sim(N=1000, M=5, S=1, T=50000, B=9, C=3.0, seed=123, p0=p0)
p = res["prices"]                                          # 既に (T,) 価格系列

# 共通の log-return 変換
log_r = np.diff(np.log(p))   # 負価格は NaN にする前処理を挟む
```

---

## § 3. Speculation Game の仕様 (論文1・論文2 からの抽出)

**注:** 論文 1 (Katahira et al. 2019 Physica A 524:503-518) と論文 2 (Katahira & Chen 2019 arXiv:1909.03185) の PDF はリポジトリ内に見当たらない (`experiments/YH002/` と `experiments/YH004/` にはそれぞれの対応論文 PDF がある)。本 §3 は Step 0 プロンプト本体に書かれた仕様記述 (著者が論文から抽出済みと明記している) を一次情報として採用する。§10 で論文 PDF を提供するよう依頼する。

### 3.1 履歴と量子化

- **量子化** (Eq. 6):
  ```
  h(t) = +2  if Δp > C
         +1  if 0 < Δp ≤ C
          0  if Δp == 0
         -1  if -C ≤ Δp < 0
         -2  if Δp < -C
  ```
  不等号境界は論文の通り厳守 (`±C` は内側=±1、外側=±2)。`Δp == 0` は exact equality で判定 (float 比較 `==`、量子化後の discrete 値のみ下流に流れるので誤差は実害なし)。

- **quinary 履歴 μ**: 過去 M 期の `h ∈ {-2..+2}` を +2 シフトで {0..4} に持ち上げ、底 5 の整数として表現:
  ```
  μ = d_{t-M} · 5^(M-1) + d_{t-M+1} · 5^(M-2) + ... + d_{t-1} · 5^0
  ```
  shift-in は `μ' = (μ * 5) % (5^M) + d_new`。

- **H(0)**: 論文 p.6 "randomly initialized" — 全エージェント共通に `rng.integers(0, 5^M)` を 1 回。

### 3.2 価格更新 (Eq. 4, 5)

```
D(t)  = Σ_i  a_i^{j*}(t) · q_i(t)          (整数、int64)
Δp    = D(t) / N                             (float)
p(t)  = p(t-1) + Δp,   p(0) = p0            (float、デフォルト p0=100.0)
```

**対数価格は使わない。** 論文1 p.9 で log-return が認知閾値 C の意味を壊すと明記されている。

### 3.3 認知価格 (Eq. 7)

```
P(t) = P(t-1) + h(t),   P(0) = 0   (整数、int64)
```

実 Δp が巨大でも h(t) は {-2..+2} にクリップされるため、P(t) は h の累積のみ。戦略評価はこれを使う。

### 3.4 注文量 (Eq. 2) と 初期 wealth (Eq. 3)

```
q_i(t)   = floor(w_i(t) / B)                 (整数、int64)
w_i(0)   = B + rng.integers(0, 100)          (整数、int64)
```

B は正整数 (baseline 9)。

### 3.5 戦略テーブル

- shape: `(N, S, 5^M)` int8
- 値: 一様 iid で `{-1, 0, +1}` から抽選 (rng.choice)

### 3.6 戦略ゲイン (Eq. 8, 9) と wealth 更新 (Eq. 10, 11)

認知価格ベース:
```
ΔG_i^j(t)  = a_i^j(t_0) · (P(t) - P(t_0))       (int64)
G_i^j(t)   = G_i^j(t_0) + ΔG_i^j(t)
```

wealth は close 時のみ更新:
```
Δw_i(t)    = ΔG_i^{j*}(t) · q_i(t_0)            (f = identity)
w_i(t)     = w_i(t_0) + Δw_i(t)
```

**ラウンドトリップ中の volume 凍結**: open → close 間は wealth が動かない、したがって q_i も open 時点の値 `entry_quantity` を close まで保持 (論文の "opening and closing volumes are the same" の実装)。

### 3.7 破産置換

`w_i(t) < B` になったらそのエージェントを新規エージェントで置換:
- 新戦略テーブル `(S, 5^M)` を `{-1, 0, +1}` から一様 iid 抽選
- 新 wealth = `B + rng.integers(0, 100)`
- position = 0, entry_* = 0, virtual_* = 0, G = 0
- 新 active_idx を `[0, S)` から一様抽選

### 3.8 Effective action 決定表 (唯一の真理、他箇所に別版を書かない)

戦略推奨 `rec ∈ {-1, 0, +1}` × 現 `position ∈ {-1, 0, +1}` の 9 パターン:

| position | rec | effective | quantity       | 分類           |
|:--------:|:---:|:---------:|:--------------:|:---------------|
|    0     |  0  |     0     |       0        | idle           |
|    0     | +1  |    +1     | `⌊w/B⌋`        | open (long)    |
|    0     | -1  |    -1     | `⌊w/B⌋`        | open (short)   |
|   +1     |  0  |     0     |       0        | active_hold    |
|   +1     | +1  |     0     |       0        | passive_hold   |
|   +1     | -1  |    -1     | `entry_qty`    | close          |
|   -1     |  0  |     0     |       0        | active_hold    |
|   -1     | -1  |     0     |       0        | passive_hold   |
|   -1     | +1  |    +1     | `entry_qty`    | close          |

4 分類 (論文2 Fig. 10):
- `buy   = (effective == +1)`
- `sell  = (effective == -1)`
- `active_hold  = (position!=0 ∧ rec==0)`
- `passive_hold = (position!=0 ∧ rec==position)`
- `idle` は 4 分類に含まれない残り (position==0 ∧ rec==0)。**不変条件: buy+sell+active+passive+idle == N**。

### 3.9 Virtual round-trip ロジック

各エージェントは S 個の戦略全てについて仮想状態 `(v_pos[j], v_ep[j], v_ea[j])` を持つ。毎ステップ `j ≠ active_idx` について:

- `rec_ij = strategies[i, j, μ_t]` (μ_t は**このステップ決定に使った** μ、h(t) 観測前の値)
- `v_pos[j] == 0` ∧ `rec_ij ∈ {-1, +1}` → **virtual open**:
  - `v_pos[j] = rec_ij`
  - `v_ep[j]  = P(t)` (h(t) 観測**後**の新しい P)
  - `v_ea[j]  = rec_ij`
- `v_pos[j] != 0` ∧ `rec_ij ∈ {0, v_pos[j]}` → **hold** (何もしない)
- `v_pos[j] != 0` ∧ `rec_ij == -v_pos[j]` → **virtual close**:
  - `ΔG_j = v_ea[j] · (P(t) - v_ep[j])`
  - `G[j] += ΔG_j`
  - virtual 状態クリア

**active 戦略 j*** は virtual 更新対象外 (処理重複を避ける、実 G 更新で既にカバーされる)。

### 3.10 戦略切替 (レビュー) のタイミング

**active 戦略 j* が実ラウンドトリップを close したステップのみ** レビュー:

1. `G[i, :]` の argmax 集合を計算
2. 現 j* が argmax 集合に含まれていれば**継続** (RNG 消費なし)
3. 含まれていなければ argmax 集合から `rng.choice` で一様抽選 → 新 j**
4. 新 j** に virtual position が残っていれば (`v_pos[j**] != 0`) クリア。**G は更新しない** (論文1 p.7 "aborted … will not be updated")。
5. `active_idx[i] = j**`。次ステップから j** を使う。

アイドル中・ポジション保持中・virtual close のみのステップではレビューを走らせない。

### 3.11 ステップ内の処理順 (厳守)

1. `μ_t = 現在の μ` を記録 (このステップの決定用スナップショット)
2. 各エージェント i について `rec[i] = strategies[i, active_idx[i], μ_t]`
3. §3.8 の表で `(effective[i], quantity[i], kind[i])`
4. `D = Σ effective * quantity`, `Δp = D/N`, `p ← p + Δp`
5. `h = quantize(Δp, C)`, `μ ← shift_in(μ, h+2)`, `P ← P + h`
    - `history_mode='exogenous'` のみ次ステップの μ を `rng.integers(0, 5^M)` で再抽選 (P は常に実 h で更新)
6. close エージェントに対し: `ΔG = entry_action * (P - entry_price)`, `G[i, active_idx] += ΔG`, `w[i] += ΔG * entry_quantity`, position=0, entry_* クリア
7. open エージェントに対し: position=effective, entry_price=P, entry_action=effective, entry_quantity=quantity
8. 全 N × (S-1) ペアの virtual 更新 (§3.9, `j == active_idx` スキップ)
9. close が起きたエージェントについて **エージェント index 順に**:
   - 戦略レビュー (§3.10、RNG 消費の可能性)
   - 破産判定 (w[i] < B なら substitute、RNG 3 回消費)

---

## § 4. 仕様ホール (論文で明示されていない設計判断)

全 8 項目。各項目について (a) 論文の該当箇所、(b) 推奨選択、(c) 理由、(d) 代替案、を記載。**最終決定は Yuito / Desktop Claude**。

### 4.1 argmax G の tie-break 規則

- **(a) 論文該当箇所**: 論文1 p.7 "the best is selected, continues to use it"。複数が best の場合は未規定。
- **(b) 推奨**: 現 j* が argmax 集合に含まれれば継続、含まれなければ argmax 集合から `rng.choice` で一様抽選。
- **(c) 理由**:
  1. "continues to use" の文言は「現在使っているものを続ける」と素直に読める。
  2. 全員同点の初期状態で継続バイアスを作らず、spurious な virtual abort を最小化。
  3. 頻繁に flip すると §3.10 の virtual abort が多発し G がリセットされ learning が機能しない。
- **(d) 代替案**: (d1) 毎回 argmax 集合から一様抽選 (継続しない) — 初期 flipping が過剰。(d2) 決定的に index が小さい方を選ぶ — seed 依存がなくなるが偏りが出る。

### 4.2 H(0) の初期化

- **(a) 論文該当箇所**: 論文1 p.6 "randomly initialized"。範囲やエージェント間の共通性は未規定。
- **(b) 推奨**: `rng.integers(0, 5^M)` を 1 回、**全エージェント共通** (グローバル履歴)。
- **(c) 理由**: H(t) は実価格経路由来なのでエージェント間で共通なのが自然。t=0 でのみ仮想的な履歴を与える必要があり、一様ランダムが偏りがない。全ゼロ初期化だと μ=0 に最初だけ全員が集まるため transient が長くなる。
- **(d) 代替案**: (d1) 全ゼロ (μ=0) — transient が長い。(d2) 各エージェント独立ランダム — 各エージェントが異なる μ を見るのは仕様矛盾 (履歴はグローバル)。

### 4.3 初期 active_idx の決め方

- **(a) 論文該当箇所**: 未規定。
- **(b) 推奨**: 各エージェント独立に `rng.integers(0, S)` (一様ランダム)。
- **(c) 理由**: G=0 で全戦略同点の初期状態で §4.1 の tie-break を呼ぶと ill-defined (argmax 集合 = 全戦略、「継続」も未定義)。一様抽選が最も偏らない。
- **(d) 代替案**: (d1) 全員 `active_idx=0` — 人工的。(d2) 初期 μ に基づく greedy — rec=0 の戦略も混じるので idle agent が偏る。

### 4.4 substitute 時の active_idx

- **(a) 論文該当箇所**: 未規定。
- **(b) 推奨**: §4.3 と同じ、`rng.integers(0, S)` で一様抽選。
- **(c) 理由**: 置換直後も G=0 で同点なので §4.3 と同構造。
- **(d) 代替案**: 同上。

### 4.5 Null test B (ランダム取引モード) の意思決定ルール

- **(a) 論文該当箇所**: 論文2 Fig. 11(b) キャプション "round-trip trade was randomly opened with a probability p = 0.5 without referencing the price history as well as the current position"。
- **(b) 推奨**:
  - §3.11 ステップ 3 の前で各エージェント `u = rng.random()` を 1 回。
  - `position == 0` なら:
    - `u < p` のとき further `rng.random()` でさらに ±1 を 0.5 ずつ決定 (2 回目の random())。それを rec とする。
    - `u ≥ p` なら rec = 0。
  - `position != 0` なら:
    - `u < p` のとき rec = `-position` (close)。
    - `u ≥ p` なら rec = 0 (passive hold)。
  - 戦略テーブル・履歴は意思決定に使わない。価格からの h(t) 計算は通常通り (認知世界を壊さない)。
- **(c) 理由**: 論文2 キャプションの "p=0.5 without referencing price history as well as the current position" の自然な実装。ただし「current position も参照しない」と取ると position!=0 でも +1 や -1 を出し得て、これは表 §3.8 では `passive_hold` や `close` のどちらにでも解釈され得る。実装上 close と open を対称に扱うため「position!=0 ならランダムに close するかしないか」の解釈を採用。**この解釈は確認したい点の一つ。**
- **(d) 代替案**: (d1) position 非参照で strictly `rec ∈ {-1, 0, +1}` を 1/3 ずつ — passive_hold と close の比率が変わる。(d2) "current position を参照しない" を「戦略テーブル内の position 相当の情報を参照しない」と読む — 実質 SG と区別つかない。

### 4.6 Null test A (外生履歴モード) の P(t) 扱い

- **(a) 論文該当箇所**: 論文2 Fig. 11(a) "exogenous common history"。P(t) の扱いは未規定。
- **(b) 推奨**: **実 h(t) から通常通り P(t) = P(t-1) + h(t) を更新**。μ のみ次ステップに向けて `rng.integers(0, 5^M)` で uniform 再抽選。
- **(c) 理由**:
  1. 外生履歴の意図は「戦略テーブルのインデックス µ を実価格経路から切り離すこと」であり、認知世界 P を壊すことではない。
  2. P を壊すと戦略評価 (§3.6 の ΔG = a · (P(t) - P(t_0))) が無意味になり、破壊の原因が「外生 μ 」なのか「壊れた P 」なのか切り分けられない。
- **(d) 代替案**: (d1) P も exogenous h にリンクさせない (別途 random h を生成) — 論文の論点がぼやける。

### 4.7 価格が負になった (extreme state) ときの log-return

- **(a) 論文該当箇所**: 論文1 Appendix B で「極端 state」処理への言及あり、明示的なルールはない。
- **(b) 推奨**: `p(t) ≤ 0` になった場合、log-return の該当 index を NaN にして stylized facts 解析から除外。シミュレーション自体は続行 (Δp は加算し続ける、p は負に潜る可能性がある)。
- **(c) 理由**: シミュレーション途中で停止するより、計測時に NaN マスクする方が汎用。N=1000 のベースラインでは T=50000 でほぼ発生しないが、エッジケース対応として必要。
- **(d) 代替案**: (d1) 負価格を検出したら run 全体を破棄 — 計算リソースの無駄。(d2) 価格を `max(p, ε)` でクリップ — 統計が歪む。

### 4.8 Close 時の D(t) 寄与に使う quantity

- **(a) 論文該当箇所**: 論文の "opening and closing volumes are the same" のみ。
- **(b) 推奨**: 実 close の D(t) 寄与は `entry_quantity` (open 時点で確定した q)。現在 wealth 由来の `⌊w/B⌋` ではない。
- **(c) 理由**:
  1. 「opening と closing で volume が同じ」の素直な実装。
  2. ラウンドトリップ中 wealth 不変 (§3.6) なので、close 時に `⌊w/B⌋` で再計算しても本来は同じ値になるはず。entry_quantity を使うことで「ラウンドトリップ中 w が変わらない」invariant を実装で強制できる。
- **(d) 代替案**: (d1) close 時に `⌊w/B⌋` 再計算 — 上記理由で本来同値、ただし破産直前や数値的 edge で食い違うリスクあり。

---

## § 5. Lite スコープの実装計画

### 5.1 実装するもの

- SG の**参照実装** (`model.py::run_reference`): per-agent クラス (Agent+Market)、可読性優先、S 個の戦略全部を毎ステップ評価する素直な実装。
- SG の**ベクトル化実装** (`simulate.py::simulate`): numpy で N 軸 + S 軸をベクトル化。reference と bit-parity (§7 の RNG 消費契約に従って seed 一致)。
- Null test A / B のモード引数: `simulate(..., history_mode='endogenous'|'exogenous', decision_mode='strategy'|'random', random_open_prob=0.5)`。
- **5 つの stylized facts** (`analysis.py`):
  1. `volatility_acf(returns, max_lag)` — `Corr(|r(t+τ)|, |r(t)|)`
  2. `return_acf(returns, max_lag)` — `Corr(r(t+τ), r(t))`
  3. `ccdf(x, normalize=True)` — 補完累積分布 + Hill MLE tail index
  4. `kurtosis(returns, window)` — aggregational window
  5. `log_returns_from_prices(p)` — `np.diff(np.log(p))`、p≤0 は NaN
- 論文2 Fig. 11 **再現スクリプト** (`reproduce_null_tests.py`): baseline / Null A / Null B 3 条件。
- **3 モデル比較図** (`compare_three_models.py`): YH003 / YH004 / YH005 を S=1, N=1000, M=5, T=50000 で同時実行し 3×3 グリッドで可視化。
- **README** (`README.md`): §4 設計選択、§3 モデル仕様サマリ、検証結果、参考文献。
- **pytest ユニットテスト** (`tests/test_parity.py`): §8 の受け入れ基準を全てコードで検証。

### 5.2 実装しないもの (YH007 送り)

- M–B phase diagram 全パラメータスキャン
- Gini 係数、Pareto tail 指数、round-trip horizon、action ratio の集計関数
- 論文1 Fig. 2–13 の完全再現
- Physica A 2021 Self-organized Speculation Game
- GARCH residuals / conditional heavy tails

「将来のために下準備として書いておく」も禁止。

### 5.3 ファイル構成 (案 A 採用、§1.4 提案)

```
experiments/YH005/
├── model.py                          # run_reference() + Agent + Market class
├── simulate.py                       # simulate() ベクトル化版 + parity 版
├── analysis.py                       # 5 つの stylized facts 関数
├── history.py                        # K=5 base encoder + quantize_price_change
├── _mg_gcmg_baseline.py              # YH003/YH004 の simulate をラップ (S=1 で log-returns まで出す)
├── reproduce_null_tests.py           # 論文2 Fig.11 再現スクリプト
├── compare_three_models.py           # 3モデル比較スクリプト
├── README.md                         # Step 2 で書き換え
├── tests/
│   ├── __init__.py
│   └── test_parity.py                # pytest テスト
├── outputs/                          # 実行で生成される .png, .json
│   ├── null_tests.png
│   ├── null_tests_metrics.json
│   ├── three_models_comparison.png
│   └── three_models_metrics.json
└── results.png                       # 既存シリーズ規約のメイン図 (compare_three_models のコピー or 別図)
```

既存プレースホルダ 3 ファイル (`model.py`, `run_simulation.py`, `README.md`) は上書き。`memo.txt` は保持 (空)。

**注:** `run_simulation.py` は既存規約のエントリポイント名。`reproduce_null_tests.py` と `compare_three_models.py` が主スクリプトなので、`run_simulation.py` は「両方をまとめて実行するランチャー」か、もしくは廃止する。Yuito の好みを §10 で聞く。

---

## § 6. 3 モデル比較スクリプトの具体設計

### 6.1 既存 YH003 / YH004 の呼び出し

`experiments/YH005/` から `experiments/YH003/model.py`, `experiments/YH004/model.py` を直接 import する必要がある。方法は 2 択:

**方法 A**: sys.path 操作
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "YH003"))
from model import simulate as yh003_simulate
```

**方法 B**: importlib で動的 import (同名 `model` モジュールの衝突回避)

方法 A は `model.py` が YH005 にも YH003 にもあるので、同じ process で両方 import すると名前衝突。YH005 自身の `model.py` は `from .model import ...` (相対 import) で呼んで、YH003 と YH004 は `importlib.util.spec_from_file_location` で読み込む。これは `_mg_gcmg_baseline.py` の中に閉じ込める。

```python
# _mg_gcmg_baseline.py
import importlib.util
from pathlib import Path

def _load_external_model(yh_id: str):
    p = Path(__file__).parent.parent / yh_id / "model.py"
    spec = importlib.util.spec_from_file_location(f"{yh_id}_model", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

_yh003 = _load_external_model("YH003")
_yh004 = _load_external_model("YH004")

def run_mg(N, M, T, seed, p0=100.0):
    res = _yh003.simulate(N=N, M=M, S=1, T=T, seed=seed, record_attendance=True)
    excess = 2 * res["attendance"].astype(np.float64) - N
    dp = excess / N
    p = p0 + np.cumsum(dp)
    return {"prices": p, "excess": excess}

def run_gcmg(N, M, T, seed, p0=100.0, T_win=50, r_min_static=0.0):
    res = _yh004.simulate(N=N, M=M, S=1, T_win=T_win, T_total=T,
                          r_min_static=r_min_static, seed=seed)
    dp = res["excess"].astype(np.float64) / N
    p = p0 + np.cumsum(dp)
    return {"prices": p, "excess": res["excess"]}
```

### 6.2 各モデルの S=1 動作確認

- YH003: S=1 で動く (§2.1)。ただし `simulate(..., S=1, ...)` で `rng.uniform(0, 0.5, size=(N, 1))` が消費される。気にしない (log-return 統計に影響なし)。
- YH004: S=1 で動く (§2.2)。同様。
- YH005: S=1 で動くように実装 (S-1=0 の virtual 更新ループが空回り)。

### 6.3 p0 を受け取らない問題の対処

MG / GCMG は p0 を受け取らないので、呼び出し側で `p = p0 + cumsum(Δp)` と後処理。SG は内部で p0 を受け取る (§3.2)。log-return 計算は 3 モデルで統一:
```python
p = np.where(p > 0, p, np.nan)
log_r = np.diff(np.log(p))
```

### 6.4 価格更新則が揃わない問題の対処

3 モデル全てで `Δp = excess / N` に揃える (YH003/YH004 はそもそも価格を持たないので後処理で統一、SG は仕様通り)。log-return は 3 モデル同じ方法で計算。

### 6.5 3×3 図レイアウト

| 行 | YH003 MG | YH004 GCMG | YH005 SG |
|:--:|:--------:|:----------:|:--------:|
| 1  | r(t) 時系列 [0, 10000] | 同左 | 同左 |
| 2  | vol ACF ρ_v(τ) log-log, τ ∈ [1, 500] | 同左 | 同左 |
| 3  | CCDF P(|r| ≥ x) log-log、正規化 (mean 0, std 1) | 同左 | 同左 |

- y 軸スケール: Row 1 は各モデル独立 (リターン規模が桁違いになり得る)。Row 2/3 は共通にしたい (比較が目的)。
- 出力: `outputs/three_models_comparison.png` (300 dpi, 12×10 inches)
- メトリクス JSON: `outputs/three_models_metrics.json` に各モデルの stylized_facts_summary。

### 6.6 期待される定性的結果

- **Row 1**: MG/GCMG は低振幅 & Gaussian-like、SG は明らかな clustering。
- **Row 2**: MG/GCMG は vol ACF が lag 数ステップで 0 に落ちる、SG は slow decay (lag 100+ でも正)。
- **Row 3**: MG/GCMG は Gaussian テール、SG は power-law テール。

---

## § 7. RNG 消費順の契約 (参照版 ↔ ベクトル化版の bit-parity)

### 7.1 初期化 (この順で 1 回ずつ)

1. `strategies = rng.choice([-1, 0, 1], size=(N, S, 5^M))` — int8 戦略テーブル
2. `init_u100 = rng.integers(0, 100, size=N)` — 初期 wealth 生成用 (`w = B + init_u100`)
3. `init_active = rng.integers(0, S, size=N)` — 初期 active_idx
4. `mu0 = rng.integers(0, 5^M)` — H(0)

### 7.2 毎ステップ (エージェント index 0..N-1 の順)

意思決定フェーズ:
- `decision_mode == 'random'` の場合、各エージェント:
  1. `u = rng.random()` (1 回)
  2. `position[i] == 0` かつ `u < p`: さらに `rng.random()` を 1 回 (direction 決定用)、`+1` if < 0.5 else `-1`
  3. それ以外は direction RNG を消費しない

履歴更新フェーズ:
- `history_mode == 'exogenous'` の場合、step 末に **1 回**: `rng.integers(0, 5^M)` で次ステップの μ を再抽選

ステップ末、**エージェント index 順**に、close が起きた i について:
- **戦略レビュー**: argmax 集合を計算、現 active_idx が含まれていれば RNG 消費なし、そうでなければ `rng.choice(argmax_indices)` を 1 回
- **破産判定**: `w[i] < B` のとき 3 回消費:
  1. `rng.choice([-1, 0, 1], size=(S, 5^M))` (新戦略)
  2. `rng.integers(0, 100)` (新 wealth)
  3. `rng.integers(0, S)` (新 active_idx)

### 7.3 ベクトル化版の一致戦略

ベクトル化しても、上記消費順を厳密に守る。特に close/substitute は「エージェント index 順」なのでベクトル化できない部分が残る。該当する i のインデックス配列を取り、for-loop で RNG を消費する (他は全部ベクトル化)。

### 7.4 確認方法

`tests/test_parity.py` で `np.array_equal(ref_result, vec_result)` をキー別に全部確認 (§8.1)。

---

## § 8. 受け入れ基準

Step 2 完了時に以下を全て満たす:

### 8.1 parity テスト (pytest 緑)

- `(N=30, M=3, S=2, T=300, B=9, C=3.0)` で seed ∈ {1, 2, 7, 42, 100} の 5 ケース、`simulate` と `run_reference` の出力が全て `np.array_equal`:
  - `prices`, `h_series`, `cognitive_prices`, `final_wealth`, `num_substitutions`, `total_wealth`, `num_buy`, `num_sell`, `num_active_hold`, `num_passive_hold`
- 同条件の S=1 で seed ∈ {1, 2, 7}
- Null A (`history_mode='exogenous'`) で seed 1 ケース
- Null B (`decision_mode='random'`) で seed 1 ケース
- 毎ステップ `num_buy + num_sell + num_active_hold + num_passive_hold + num_idle == N`
- `cognitive_prices[t] == cumsum(h_series)[t]`
- 同一 seed 2 回で全出力一致 (決定性)
- seed を変えると prices が必ず変わる

### 8.2 Null test 再現スクリプト

- `outputs/null_tests.png` が生成される
- `|r| ACF at lag 50`:
  - baseline: > 0.15
  - Null A: |ACF| < 0.05
  - Null B: |ACF| < 0.05
- JSON 出力 `outputs/null_tests_metrics.json` に 3 条件分の stylized_facts_summary

### 8.3 3 モデル比較図

- `outputs/three_models_comparison.png` が生成される
- 目視確認: SG の Row 2 vol ACF が MG/GCMG より明らかに上にある (slow decay)
- SG の Row 3 CCDF が明らかに heavier tail
- JSON 出力 `outputs/three_models_metrics.json`

### 8.4 T=20000, N=1000, M=5, S=2, B=9, C=3.0, seed=777 ベースライン

参考値 (論文1 と整合するはず):

- `vol_acf_at_200 ≈ 0.01–0.05`
- `ret_acf_at_14` が noise zone (|ACF| < 0.05)
- `kurtosis_at_1 >> kurtosis_at_640` (aggregational Gaussianity)
- Hill MLE tail index `α ∈ [3, 5]` (論文1 Fig. 4 の α ≈ 3.8)

これらはテストにはしない (計算時間の関係)。`README.md` の「観測された数値」表に記載。

### 8.5 README

- §4 の設計選択表 8 項目が全て記載されている
- モデル仕様サマリ (Eq. 番号付き)
- Lite スコープで削った項目と YH007 への送付予定
- 検証結果 (§8.4 の数値)
- 参考文献: 論文1, 論文2, Challet-Zhang 1997 (MG), Jefferies et al. 2001 (GCMG)

---

## § 9. Step 2 (実装) の進行順

各ステップで**動く成果物**を作ってから次に進む。途中で壊れたら止めて報告。

- **9-1**: `history.py` — K=5 base encoder、`quantize_price_change(dp, C)`、`shift_in(mu, d, M)`。スタンドアロンで単体テスト可能 (`pytest -k history`)。
- **9-2**: `model.py::run_reference` — Agent+Market クラス参照実装。小規模 `(N=10, M=2, S=2, T=100)` で `print(prices[:10])` が動くことを確認。
- **9-3**: `simulate.py::simulate` — ベクトル化版。§7 の RNG 消費順を厳守。
- **9-4**: `tests/test_parity.py` — §8.1 の 5 seeds parity。**ここが通らなければ 9-5 以降に進まない。**
- **9-5**: `analysis.py` — 5 つの stylized facts 関数。独立にテスト可能 (正規乱数で sanity check: `return_acf` が lag 1 で ~0、`volatility_acf` が ~0、`kurtosis` が ~3)。
- **9-6**: `_mg_gcmg_baseline.py` — YH003/YH004 の importlib ラッパ。
- **9-7**: `reproduce_null_tests.py` — 論文2 Fig. 11 再現。
- **9-8**: `compare_three_models.py` — 3 モデル比較図。
- **9-9**: `README.md` — §4 設計選択 + §3 仕様 + §8 検証結果。

各段階で Yuito に進捗を報告し、必要なら PR を分ける。

---

## § 10. 質問・未解決事項

### 10.1 論文 PDF の入手

論文1 (Katahira et al. 2019 Physica A) と論文2 (Katahira & Chen 2019 arXiv:1909.03185) の PDF がリポジトリに無い (YH002 と YH004 にはある)。Step 2 で詳細を参照する必要があるため、以下のいずれかを希望:

- **希望 A**: PDF を `experiments/YH005/` に置いてもらう (arXiv は無料で配布可能、Physica A は著者版なら可)。
- **希望 B**: 現状の Step 0 プロンプトに書かれた仕様記述を一次情報として実装を進める。§3 の方程式は全部プロンプトに記載済みなので実装は可能だが、曖昧な細部で論文本文を読み返す必要が出てきたら個別に質問する。

### 10.2 Null B の current position を参照するか否か

§4.5 の設計ホール。論文2 Fig. 11(b) キャプション "without referencing the price history as well as the current position" を、推奨では「戦略テーブルは使わないが position!=0 のときは close/passive hold の決定だけは position に依存する (そうでないと close できない)」と解釈した。これは論文の文言の素直な読みではない。

選択肢:
- **(A) 推奨通り**: position==0 のとき rec ∈ {-1, 0, +1}、position!=0 のとき rec ∈ {0, -position} (close か hold)。ラウンドトリップ構造は保持。
- **(B) strict 解釈**: 毎ステップ独立に rec を確率的に決める、position は一切参照しない。→ 表 §3.8 の `rec == position` セル (passive_hold, 発生確率 1/3) も出現するので、close と hold と continue open が混ざる形になる。

Desktop Claude / Yuito の判断を仰ぎたい。

### 10.3 `run_simulation.py` の扱い

既存シリーズは `experiments/YHxxx/run_simulation.py` をメインエントリとしている。YH005 では `reproduce_null_tests.py` と `compare_three_models.py` の 2 スクリプトが実体で、`run_simulation.py` をどうするか:

- **(A)** 両方を順に走らせるランチャーにする。
- **(B)** `run_simulation.py` を廃止し、README に 2 スクリプトの使い方だけ書く。
- **(C)** `run_simulation.py` = `compare_three_models.py` のエイリアス。

### 10.4 `results.png` の中身

既存シリーズは `experiments/YHxxx/results.png` をメイン出力図として README に埋め込んでいる。YH005 では 2 つの図 (`null_tests.png`, `three_models_comparison.png`) が生成される。どちらを `results.png` にするか:

- **(A)** 3 モデル比較 (SG の優位性が一目で分かる)。
- **(B)** null tests (SG のメカニズムの検証)。
- **(C)** 両方を縦に繋いだ compound 図。

### 10.5 YH003/YH004 の S=1 動作での RNG 消費

S=1 で `perturb = rng.uniform(0, 0.5, size=(N, 1))` や同様の (N, 1) 形状の RNG 消費が発生する。これ自体は動作上問題ないが、「S=1 比較」と謳うときに「inductive learning が実質無効」という主張を正確にするため、README で明記する (Yuito に共有)。

### 10.6 N=1000 に揃える件

YH003 の標準 N は 101、YH004 も 101 (Figure 1 再現時)。比較図では N=1000 に揃えるが、これは YH003/YH004 の従来使用から外れる。両者とも N=1000 で動く (simulate にアサーションなし)。ただし YH003 の attendance/excess は N=1000 で桁が上がり、`int64` で overflow しないかは大丈夫 (|excess| ≤ N=1000、dtype は int64)。

### 10.7 3 モデル比較の trial 数

Step 0 プロンプトでは「T=50000, seed=123 で 1 trial」。時間があれば 10 trial 平均が理想だが、Lite スコープでは 1 trial で十分か:

- 1 trial: 高速 (1–5 分)、ただし SG の slow decay は seed によって多少ブレる。
- 10 trial 平均: vol ACF のブレが目視で問題にならなくなる、ただし 10–50 分かかる。

README に「時間があれば 10 trial 平均したい」旨の note を入れるのが §4.3 の指示だが、実際にどちらを現物として走らせるかは確認したい。

---

**以上が Step 1 の計画書。Yuito の確認・修正指示を受けて Step 2 (実装) に移行する。**
