# Paper 3 (Katahira-Chen-Akiyama 2021) 精読仕様

| | |
|---|---|
| Title | Self-organized Speculation Game for the spontaneous emergence of financial stylized facts |
| Authors | Kei Katahira, Yu Chen, Eizo Akiyama |
| Venue | *Physica A* (Elsevier), DOI: 10.1016/j.physa.2021.126103 (S0378437121005008) |
| Submitted | 2020-12-17 |
| Source | `experiments/YH007/katahira2021 self-organized.pdf`, txt: `katahira2021_extracted.txt` |

---

## 0. 一行サマリ

**SOSG は「N の内生化」モデル**。BTW sandpile analogy で agent の inflow (= 砂粒の落下) と outflow (= 雪崩) を内生的に balance させ、外生パラメタを (N, S, M, B, C) の 5 → (M, B, C) の 3 に削減。C は依然として外生固定 (C=3)。

**YH007 README.md の旧記述「C を内生化」は誤り**。本 spec に従って書き直すこと。

---

## 1. モデル定義 (論文 §2)

### 1.1 状態空間
- N(t): 時刻 t での参加者数 (内生、可変、典型値 ~700 in B=9)
- 各 player i は wealth w_i(t) と単一戦略テーブル (S=1) を保持
- M=5 (memory size、論文 §3.1 固定)
- B=9, C=3 (baseline、論文 §3.1)
- price p(t)、初期値 p(0)=100

### 1.2 Inflow (= "slow drive")
- 毎時刻 t、新規 player 1 名が固定 wealth `w_init = 10·B` で市場に参入
- BTW analogy: 1 grain/step の砂粒落下

### 1.3 Outflow (= "avalanche threshold")
- player i は `w_i(t) < B` になった時点で市場から退場
- 退場 = 数量 1 単位の注文も出せなくなった状態 (∵ Eq.1 の floor で q_i=0)
- BTW analogy: 局所 slope が閾値を超えた格子点が崩壊

### 1.4 注文・約定 (YH005 と同じ)
- 行動 a_i(t) ∈ {-1 (sell), 0 (hold), +1 (buy)}
- 数量 q_i(t) = floor(w_i(t) / B) — 開閉同一
- long 保有中は buy 禁止、short 保有中は sell 禁止 (open しか取れない)
- Δp = (1/N(t)) · Σ_j a_j(t)·q_j(t) (Eq.2、market maker 存在前提)
- return r(t) = ln p(t) − ln p(t−1)

### 1.5 認知 (YH005 と同じ)
- C = 3 で h(t) を量子化: h ∈ {-2, -1, 0, +1, +2}
- 認知価格 P(t) = P(t-1) + h(t)
- 認知利益 φ_i(t) = a_i(t0) · (P(t) - P(t0)) = a_i(t0) · Σ_{k=t0+1..t} h(k)
- **wealth 更新は認知世界経由**: w_i(t) = w_i(t0) + φ_i(t) · q_i(t0) (Eq.6)
- 注: これは LOB の実損益ではなく、認知利益で wealth を更新する設計 (paper §2 後段で「self-finance は仮定しない、差分は externally adjusted」と明言)

### 1.6 戦略 (S=1 で固定)
- 各 player は M=5、history-length に応じた 5^5 = 3125 エントリの戦略テーブル 1 枚を**入場時に乱数で生成、以後不変**
- inductive learning なし (S=1 で論文1 と同等の SF 再現性を [13] で確認済として正当化)
- N と S が両方削減され、Speculation Game の主要パラメタは (M, B, C) の 3 つに収束

---

## 2. 主結果 (論文 §3)

### 2.1 N(t) の自己組織化 (Fig.1, Fig.4)
- B=9 で N(t) は数千ステップで ~700 に収束 (大きな揺らぎ ±数十残存)
- B 依存: B=9 → N* ≈ 700, B=18 → N* ≈ 数千 (時間も長期化)
- 「N* は B のみで決まる」が論文の主張

### 2.2 平均的 inflow-outflow balance (Eq.7, Eq.8, Fig.8/9)
- BTW: ΣN_in ≈ ΣN_out (砂粒数の保存) → N* converge
- SOSG: Σw_in ≈ Σw_maker + Σw_exit (Eq.8、wealth flow の balance)
- w_in は 1 player × 10B × t で線形増加 (青線)
- w_maker (market maker 取得) が outflow の大半 (赤線、O(1) × w_exit)
- w_exit (破産退場 player の持ち出し) が残り (緑線)
- 注: SOSG の outflow は **wealth が market maker に流出する経路** が主、**player 退場による直接持ち出しは副次的**。これは sandpile の砂粒消滅と analogy 上の差異 (paper §3.3 が議論)

### 2.3 Stylized facts (paper §3.2.2, Figs.5-7)
- |r| の cumulative distribution に power law (tail index α ≈ 4.56、B=9 で 20 trial × T=50000)
- 単一 trial の Δw/B = w_i(t) − w_i(t0) (= φ·q、Eq.6 右辺) も power-law (α ≈ 3.38、860,995 RTs)
- vol ACF は power-law ではなく logarithmic decay (→ "quasi-critical" であって critical ではない)
- 11 SF 中 10 を再現、唯一未再現は gain/loss asymmetry (これは元 SG と同じ limitation)

### 2.4 BTW との対比 (paper §3.2 全般)
| | BTW sandpile | SOSG |
|---|---|---|
| Slow drive | 1 grain/step | 1 player/step (w=10B) |
| Threshold | local slope > L_c | w_i < B |
| Avalanche | landslide chain | bankrupt event |
| Conserved | grains | wealth (近似) |
| Lattice | L × L 固定 | (なし、空間構造なし) |
| Power law | size dist of avalanche | dist of |r|, Δw/B |
| Criticality | critical | **quasi-critical** (vol ACF が log decay) |

---

## 3. YH005 → YH007 実装差分 (実装方針)

### 3.1 必要な機能拡張 (YH005 simulate からの差分)
1. `agent` を**動的リスト**に変更 (N(t) 可変、N は実行時に変動)
2. **入場ロジック**: 毎時刻 1 player を生成、`w_init=10B`、新規戦略テーブルを seed-derived RNG で生成
3. **退場ロジック**: `w_i(t) < B` の player を list から除外 (保有 position があれば強制 close + wealth に反映)
4. logging: `N_history[t]`, `inflow_count[t]`, `outflow_count[t]`, `w_in_cum[t]`, `w_exit_cum[t]`, `w_maker_cum[t]`
5. price update Eq.2 で `N(t)` を分母に使う (静的 N=1000 を動的 N(t) に置換)

### 3.2 不変な部分 (YH005 から流用可能)
- 認知世界 (h, H, P, φ) の計算 — 完全一致
- 戦略テーブルの ε-greedy / argmax 選択 (S=1 なので tie-break 不要、選択ロジックも自明)
- round-trip 単位の wealth 更新 (Eq.6) — 認知利益経由は YH005 と同じ
- order size bucket logging
- baseline parameter (M=5, B=9, C=3, p0=100)

### 3.3 削除する部分
- S>1 の strategy 選択 (SOSG は S=1 固定)
- 固定 N での substitute 機構 (Phase 1 の `_resample_agent` 系)
- C の外生指定 UI (固定値 3 で hardcode)

### 3.4 parity 戦略
- **bit-parity は要求しない** (N が動的化されるため RNG 消費順が根本的に変わる)
- 代わりに「**SF readout parity**」を契約: SOSG (N 内生) と YH005 (N=N*, S=1, 同 seed) で stylized facts の **数値が誤差 < 10%**
- 比較用 YH005 run の N は SOSG の収束 N* から逆算

---

## 4. 実装ホール (paper 未規定箇所)

### H1. 戦略テーブル生成の RNG seed
- 論文には新規 player の strategy 生成手順が明示されていない
- 設計選択: `rng = default_rng(global_seed * 100_000 + player_id)` で player ごとに独立化、再現性確保

### H2. 退場時の保有 position の扱い
- 論文には「w_i < B で退場」とだけある
- 設計選択: 退場前に強制 close (現在価格で round-trip clear)、cognitive φ を 1 回計算、wealth に反映してから除外
- 代替案: position ごと「消滅」させる (wealth conservation を諦める) — 論文の Eq.8 と整合させるなら強制 close 推奨

### H3. 初期化 (t=0 の player 数)
- 論文 Fig.1 を見ると t=0 で N(0)=0 から立ち上がっている
- 設計選択: N(0)=0、 t=1 で player 1 が単独で参入 (Δp = a·q / 1)、t=2 で 2 名と続く
- 注: 最初の数百ステップは N が小さく Δp が ill-behaved、warmup 1000-2000 steps を logging 開始から除外

### H4. price が 0 以下になる場合
- N が小さい初期で起こりうる
- 設計選択: YH005 と同じく、p(t) = max(p(t-1) + Δp, ε) で floor (ε=1e-9)、log-return では floor 値を使う

### H5. simulation 終了時の N
- 論文は T=50000 で打ち切るが、t=T 時点で残った player を outflow にカウントするかは未規定
- 設計選択: T 時点の残存 player は outflow にカウント**しない** (open ended、Eq.8 の評価は転換期 1000-2000 step 後の安定区間のみで取る)

---

## 5. 受け入れ基準 (paper 3 から抽出)

| 指標 | 論文値 | YH007 目標 | tolerance |
|---|---|---|---|
| N(t) 収束値 (B=9) | ~700 | 600-800 | ±15% |
| 収束所要時間 (B=9) | ~5000 step | 5000-10000 | upper bound |
| Hill α (|r| tail, B=9) | 4.56 | 3.5-5.5 | ±20% |
| Δw/B Hill α | 3.38 | 2.5-4.5 | ±30% |
| vol ACF τ=50 (B=9, 100 trial) | ~0.1-0.2 (Fig.7) | > 0.05 | non-zero |
| vol ACF 型 | logarithmic | logarithmic > power | LR test |
| B robustness | N* ↑ as B ↑ (Fig.4) | ρ(B, N*) > 0.9 | scan {9, 18, 27} |

---

## 6. YH006_1 結果との接続

### 6.1 「freeze は SOSG の前提を破る」可能性
- YH006_1 S5.x-S7 で LOB friction が 91% censoring を生む (= bankrupt rate ≈ 0)
- SOSG の Eq.7/8 は outflow rate > 0 を必要とする
- **LOB-on-SOSG では Eq.8 の balance が崩れる** (Σw_in ≫ Σw_out) → N(t) が monotonically increase
- 直接の含意: **SOSG-on-LOB は naive 移植では成立しない**。outflow を補強する追加機構が必要

### 6.2 補強候補 (YH008 以降の future work)
- (a) τ_max cap (lifetime 上限) — Phase 2 の A3 ablation と同じ機構
- (b) entry を w_in 依存にする (Eq.8 を成立させる stochastic gate)
- (c) market maker を明示モデル化し w_maker の outflow 経路を作る (paper §3.3 Fig.9 の赤線)

### 6.3 YH006_1 で確定した SOSG 設計上の含意
- aggregate (YH005 simulate) では outflow rate ~99% (S2 結果) → SOSG 移植は aggregate 世界では問題なく成立
- LOB 移植は本質的拡張が必要

---

## 7. 実施計画 (Step 1 = paper 精読、Step 2 = 最小実装)

### Step 1 (完了): 本 spec 起草
本 `paper3_spec.md` を確定。YH007 README から「C 内生化」記述を削除し本 spec へリンク。

### Step 2: 最小実装 (aggregate 世界、N 内生のみ)
- `experiments/YH007/code/selforg_sim.py`: YH005 `simulate.py` を fork して N 動的化
- `experiments/YH007/code/run_baseline.py`: B=9, M=5, C=3, T=50000, seed=777 で 1 trial 走らせ Fig.1 (N(t)) と Fig.2 (r(t)) を再現
- 受け入れ: §5 表の **最初 2 行** (N* ≈ 700、収束 ~5000 step)

### Step 3: Stylized facts validation
- 100 trial で Hill α, vol ACF を測定し §5 表の残り基準を確認
- Fig.5/6/7 相当のプロットを `outputs/figures/` に保存

### Step 4: B robustness scan
- B ∈ {9, 18, 27} で各 20 trial、Fig.4 相当を再現

### Step 5 (オプション): LOB 移植準備 (YH006_2 完了後)
- 上記 §6.2 の補強案を実装、SOSG-on-LOB を smoke test

---

## 8. 改訂履歴
| Version | 日付 | 内容 |
|---|---|---|
| v0.1 | 2026-06-12 | 初版。論文 §1-4 精読、6 章 (YH006_1 接続) を独自に追加 |
