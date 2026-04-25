# YH007: Self-organized Speculation Game — 論文3 再現

**状態**: 骨格 (Step 1 = paper3 精読 → `paper3_spec.md` 起こしが次の着手点)。
YH006 Lite (Phase 1) が 2026-04-25 に一段落 (`docs/findings.md` §YH006 参照)、
YH007 が SG 系譜の次フェーズ。Katahira, Chen (2021 頃) "Self-organized
speculation game for the spontaneous emergence of financial stylized facts"
*Physica A* (PDF: `../YH005/papers/self-organized speculation game ....pdf`)
の再現。

元 SG (YH005) は **認知閾値 C を外生パラメータとしてチューニング**しなければ stylized facts が出ない。自己組織化 SG は **C を内生化** し、stylized facts が "spontaneously" に現れることを示す論文。SG 系譜の到達点。

---

## 位置付け

| | YH005 Lite | YH005_1 Phase 1 | YH006 Lite (Phase 1) | **YH007 SelfOrg** |
|---|---|---|---|---|
| 世界 | aggregate | aggregate | **LOB (PAMS)** + aggregate | aggregate (Phase 1) → LOB (Phase 2 検討) |
| C | 外生固定 (3.0) | 外生固定 | 外生固定 (LOB は 3×median\|Δmid\|=28 tick 較正) | **内生 (自己組織化)** |
| 主題 | 機構分析 (Null test) | 3 層機構の 5-figure 数値実証 | 2×2 (world × wealth, N=100): LOB friction が dynamic-wealth 自己組織化を弱める交互作用 −0.27 を確認 | **C の自己組織化** |
| 状態 | 完了 (2026-04) | 完了 (2026-04-22) | 完了 (2026-04-25) | **着手前** |

---

## 目的 (TODO: 論文3 の PDF を精読して確定)

想定される主張 (仮):
1. C を適応的に更新する (例: 過去 `|Δp|` のパーセンタイル) だけで stylized facts が自動で現れる
2. C の初期値に対して **頑健** (self-organization の特徴)
3. YH005 で外生チューニングしていた Hill α / vol ACF などが、C 内生化で論文1 同等の値に落ち着く
4. M や B の範囲に対しても広くロバスト

→ **精読後に本セクションを書き直す** (`paper3_spec.md` を起こすのが良い)

---

## モデル仕様 (TODO: PDF 精読後に埋める)

論文3 の核は「C の更新則」。候補 (いずれも**要精査**):

**(仮1)** 過去 Tw ステップの `|Δp|` の median (or percentile) で C を再定義:
```
C(t) = median(|Δp(t-Tw+1..t)|)
```
→ パーセンタイル基準で分布の "裾" を毎回同じ比率で捉える

**(仮2)** Exponential moving average:
```
C(t) = (1-η)·C(t-1) + η·|Δp(t)|
```

**(仮3)** wealth に応じて個人別 C_i:
```
C_i(t) = f(w_i(t))
```

→ 論文3 の式 (○) を確認して確定。

---

## 実装方針

**YH005 の `simulate.py` を再利用** して `C` を毎ステップ更新するフックを追加するのが最小改変。

```python
# 擬似コード (草案)
def simulate_selforg(N, M, S, T, B, C_init=3.0, Tw=100, seed=42, ...):
    # YH005 の simulate と同じ初期化
    ...
    C_history = np.zeros(T)
    dp_buffer = deque(maxlen=Tw)
    C = C_init

    for t in range(T):
        # ... D = Σ a·q, Δp = D/N, p += Δp
        dp_buffer.append(abs(dp))
        if len(dp_buffer) >= Tw:
            C = np.median(dp_buffer)    # (仮1) の場合
        h = quantize(dp, C)              # C を使って量子化
        # ... 以下 YH005 と同じ
        C_history[t] = C
    return {..., "C_history": C_history}
```

**parity テスト対象外** (C 内生化で bit-parity 概念は成立しない。C を外生固定した mode で YH005 と bit-parity する疎通テストは書く)。

---

## 実行 (予定)

```bash
cd experiments/YH007
python run_simulation.py selforg --seed 777
python run_simulation.py robustness --C_init_list 0.5,1,3,10,30
python run_simulation.py compare_exog_vs_selforg --seed 777
```

メイン出力:
- `results.png` — 論文3 main figure 再現 (構成は TODO)
- `results_robustness.png` — C_init ロバスト性
- `results_compare.png` — 外生 C (YH005) vs 自己組織化 C (YH007)

---

## ディレクトリ構成 (案)

```
experiments/YH007/
├── model.py / simulate.py      # YH005 を継承 + C 更新フック
├── analysis.py                 # YH005 を import (stylized facts は共通)
├── selforg.py                  # 自己組織化モード本体
├── robustness.py               # C_init スキャン
├── compare_exog_vs_selforg.py  # 比較図
├── run_simulation.py           # CLI
├── tests/                      # C 外生固定で YH005 と bit-parity
├── outputs/
└── paper3_spec.md              # 論文3 精読ノート (Step 1)
```

---

## 検証 (受け入れ基準、TODO: 論文3 から抽出)

- C 内生化で **Hill α ∈ [3, 5]** (外生チューニングと同等)
- `|r| ACF at τ=50 ≈ 0.2` (論文1 Fig. 7 と同等)
- C の初期値を `{0.5, 1, 3, 10, 30}` と振っても stylized facts が同等 (ロバスト性)
- C 外生固定モードで YH005 と bit-parity

---

## 実装前にやること (Step 1, YH005 流儀)

1. **論文3 PDF を精読して `paper3_spec.md` を起こす** (YH005 における `YH005_PLAN.md` に相当)
   - C 更新則の**正確な式**
   - 論文中の main figure 一覧
   - 論文1/論文2 との差分 (モデル変更点) を箇条書き
   - 仕様ホール (論文未規定箇所) を列挙
2. 仕様ホールに対する **設計選択** を決定 (Yuito / Desktop Claude 承認)
3. 実装 (YH005 流儀: `model.py → simulate.py → analysis.py → tests → main figures → README`)

---

## YH006 からの引き継ぎ事項

YH006 Phase 1 終了時 (`docs/findings.md` §YH006「次フェーズ (YH007 / Phase 2) で
検証したい仮説」) から流れてきた未解決課題。**全て YH007 本題 (C 内生化) と
直交する LOB 側課題** だが、YH007 を LOB 世界に拡張する局面で同居するため
ここに記録しておく。Aggregate 世界での YH007 Phase 1 (C 内生化単体) には
影響しない。

| # | 引き継ぎ項目 | YH007 での扱い |
|---|---|---|
| 1 | 100 trial bootstrap CI / ensemble | YH007 は最初から ensemble 設計にすることで吸収 (C 内生化のロバスト性主張に必須) |
| 2 | LIMIT_ORDER open 拡張 (zero-fill 30% 改善) | YH007 LOB 拡張時に必要。aggregate Phase 1 では不要 |
| 3 | iterative C_ticks calibration | **YH007 で自然に解決**: C 内生化 = self-consistent ticks → 単方向較正の循環依存が消える |
| 4 | MMFCNAgent order_volume sensitivity scan | YH007 LOB 拡張時に必要 |
| 5 | warmup/main 定常性のスケール依存性 | YH007 LOB 拡張時に必要 |
| 6 | lob_mtm 発散 (2-account 設計の論文 limitation 段落) | YH007 LOB 拡張時に必要 |

**引き継ぎ方針**: YH007 は aggregate 世界での C 内生化 (Phase 1) を先に完了
させ、その後 LOB 拡張 (Phase 2) で #2, #4, #5, #6 を一括処理する。#1 は
Phase 1 から組み込む。#3 は内生化で自動解決。

---

## YH006 で固定された制約 (touch しない)

- **aggregate_sim parity 契約**: `experiments/YH006/aggregate_sim.py` は
  uniform mode × 4 seeds (1, 42, 777, 12345) で YH005 simulate と bit-parity、
  Pareto mode × 2 seeds で determinism、uniform vs Pareto × 3 seeds で
  divergence の **計 9 ケース** が必須 (`experiments/YH006/tests/test_aggregate_parity.py`)。
  YH007 が aggregate_sim を継承する場合、この parity を絶対に壊さない。
- **C_ticks 互換**: YH006 LOB 較正値 ≈ 28 tick (= 3 × median\|Δmid\|, seed=777)。
  YH007 で C を内生化する際、外生固定モードを残し、同一 seed で YH006 と
  bit-parity (or 同等の stylized facts) が出ること。
- **PAMS subclass-only**: pams 0.2.2 を patch しない。YH007 LOB 拡張時も
  `SpeculationAgent` / `MMFCNAgent` の subclass 路線を踏襲。

---

## 未解決 (Yuito 確認事項)

1. ~~**YH006 を先にやるか、YH007 を先にやるか**~~ → **YH006 Phase 1 完了 (2026-04-25)**、YH007 が次。
2. **Paper 3 精読を Yuito が先に行うか、実装前に claude が PDF を読んで spec を起こすか**。YH005 では Yuito が論文を読みながら `PLAN.md` を一緒に作った。
3. **Paper 3 の正式書誌**: タイトル "Self-organized speculation game for the spontaneous emergence of financial stylized facts" は確認済み。掲載誌・年・DOI は要確認 (`../YH005/papers/self-organized speculation game ....pdf` から)。
4. **YH007 の世界選択**: aggregate-only (Phase 1) → LOB 拡張 (Phase 2) でいくか、最初から LOB に行くか。本 README は **aggregate Phase 1 → LOB Phase 2** の順を提案 (C 内生化単体の効果を aggregate で先に確定させたい意図)。

---

## 参考文献

- Katahira, K., Chen, Y. (20XX). Self-organized speculation game for the spontaneous emergence of financial stylized facts. *Physica A*, **XXX**, XXX–XXX. [論文3, 書誌要確認]
- Katahira, K., Chen, Y., Hashimoto, G., Okuda, H. (2019). *Physica A*, **524**, 503–518. [論文1]
- Katahira, K., Chen, Y. (2019). arXiv:1909.03185. [論文2]
