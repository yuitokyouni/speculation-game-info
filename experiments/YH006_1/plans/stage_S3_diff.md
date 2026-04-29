# Stage S3 diff — LOB ensemble + 4 条件 interaction 進捗ログ

S3 plan v2 に基づく実装・実行ログ。3 段階 (Mac sim → 転送 → Windows aggregation) の進捗を 1 行ずつ追記する形 (Yuito S3 v1 承認時要望)。

| Stage | Date | 状態 | Note |
|---|---|---|---|
| **0. plan v2 + 実装準備** | 2026-04-29 | **完了** | plan v2 反映、Mac/Windows 両側コード prep 済 (詳細下) |
| **1. Mac LOB 100 trial × 2 条件** | 2026-04-30 | **完了** | smoke PASS / determinism guard PASS / C2 100 + C3 100 完走、§3.8 censoring 重大 flag 100/100 件で発生 (Yuito 議論ポイント) |
| 2. Mac → Windows 転送 | 2026-04-30 | **完了 (git 経由)** | tar.gz は省略、parquet を直接 commit + push (S2 と同パターン、データ ~15MB と軽量のため) |
| 3. Windows aggregation | — | 未着手 | combine + aggregate_full_summary 実行 (Windows 側 git pull 後) |

---

## Stage 0: plan v2 + 実装準備 (2026-04-29 完了)

### plan v2 反映
- `plans/stage_S3_plan.md` を v1 → v2 に更新
- 修正 1 (§3.7): primary metric を bin_var_slope 符号 4 マスから interaction 値 (= LOB diff − aggregate diff) に変更、α/β/γ/δ 4 パターン判定基準を再定義
- 修正 2 (§3.8): LOB lifetime T 張り付きの positioning を「censoring 重大 flag」から「**仮説 A 中間予測の primary evidence**」に変更
- 修正 3 (§0.4): Windows-PAMS unavailable 真因を `pip install pams==0.2.2 --dry-run` 実調査で特定、v1 の lifelines 説は誤記として撤回:
  - PAMS 自体: `py3-none-any.whl` (pure Python)
  - 真因: `numpy<2.0.0` 制約 → `numpy 1.26.4` の Python 3.13 + Windows prebuilt wheel が PyPI 不在 → source build 要 → MSVC 不在で fail
  - 復旧パス: Python 3.12 ダウングレード or MSVC Build Tools install

### 実装着手
新規 / 変更ファイル:

| パス | 役割 | 行数 | 動作確認 |
|---|---|---:|---|
| `code/run_experiment.py` (編集) | `run_lob_trial` 追加 + dispatcher で LOB full-length 経路有効化 | +25 | syntax OK、import 解決 OK (Windows で PAMS は import されない経路) |
| `code/lob_ensemble.py` (新規) | Mac 側 LOB ensemble runner + determinism guard | 200 | syntax OK |
| `code/combine_ensemble_summaries.py` (新規) | Windows 側 step 1: 整合性チェック + ensemble_summary 結合 (200 → 400 行) | 130 | syntax OK |
| `code/aggregate_full_summary.py` (新規) | Windows 側 step 2: 4 条件 full summary + interaction + lifetime + figures + README append | 360 | syntax OK |

### Note: LOB の wealth_ts は単一 snapshot
S3 plan v2 §3.2 で記載のとおり、`run_lob_trial` は smoke fn と同じく終了時 1 snapshot のみ取る。corr_winit_wt_T1..T10 は同値 (= corr(w_init, w_final)) に degenerate するが、aggregate との比較は trial-level で機能する。複数 snapshot 化は将来 stage で必要なら custom Saver で実装、本 S3 では scope 外 (Yuito 確認事項にも記載)。

### 次のアクション (Mac 側)
1. Mac 側で `experiments/YH006_1` を `git pull` (本 commit を取得)
2. PAMS 0.2.2 venv 確認 (`pip install pams==0.2.2`、numpy<2.0)
3. smoke 1 trial (S3 plan §3.1):
   ```bash
   cd experiments/YH006_1
   python -c "from code.run_experiment import run_lob_trial_smoke; \
              import numpy as np; \
              r = run_lob_trial_smoke('C3', 9001); \
              assert np.all(~np.isnan(r.agents_df['w_init'])); \
              print(f'smoke PASS: n_rt={r.n_round_trips}, runtime={r.runtime_sec:.1f}s')"
   ```
4. determinism guard + full ensemble:
   ```bash
   python -m code.lob_ensemble  # default: --conds C2,C3 --n-trials 100
   ```
5. tar.gz バンドル → Windows 共有 (`logs/S3_mac_summary.json` 生成済を含めて)

---

## Stage 1: Mac LOB 100 trial × 2 条件 (2026-04-30 完了)

### 環境
- Mac venv: `experiments/.venv` (Python 3.12.7、PAMS 0.2.2、numpy 1.26.4、pandas 3.0.2)
- pyarrow 24.0.0 を本 stage で追加 install (parquet engine 不在で初回 guard 失敗、`pip install pyarrow` で resolve、`requirements.txt` 未更新)

### Mac 側で適用した実装 fix (Windows commit から漏れていた点)
- `code/run_experiment.py`: `sys.path` に `HERE` (=`code/`) を追加。Windows の S3 prep commit (`15700c1`) 時点では `from sg_agent import WInitLoggingSpeculationAgent` が PAMS 不在で実行されない経路だったため検出できなかった。Mac 側で smoke 初回実行時に `ModuleNotFoundError: No module named 'sg_agent'` が発生 → HERE を sys.path に追加して resolve。本修正は本 commit に同梱。

### §3.1 LOB smoke (C3 seed=9001, warmup=200/main=200)
| 指標 | 値 |
|---|---|
| n_round_trips | 3,521 |
| n_substitutions | 47 |
| runtime | 70.7s |
| `w_init` non-NaN assertion | PASS |
| `len(agents_df) == 100` assertion | PASS |
| w_init 範囲 | min=9, max=99, median=16 (Pareto α=1.5 整合) |

### §3.6 Determinism guard (LOB C3 seed=1000 × 2)
| 確認項目 | 結果 |
|---|---|
| `trial_1000.parquet` sha256 | MATCH (`0484bb795ad55d22...`) |
| `agents_1000.parquet` sha256 | MATCH (`ea793a8947654099...`) |
| `lifetimes_1000.parquet` sha256 | MATCH (`8144f2099f74b8f1...`) |
| `wealth_ts_1000.parquet` sha256 | MATCH (`93dc6bad78aa94c5...`) |
| rt_df semantic (8 cols `np.array_equal`) | PASS |
| 単 trial runtime | 178-181s (3 min) |
| log | `logs/runtime/20260430_005146_S3_lob_ensemble.log` |

→ **bit-一致 PASS、PAMS の `random.Random(seed)` + numpy `default_rng(seed)` が full bit-一致を提供する。subclass 副作用なし。**

### §3.3 / §3.4 LOB ensemble (C2/C3 各 100 trial)

`python -m code.lob_ensemble --skip-determinism --conds C2,C3 --n-trials 100` (8 worker、main_steps=1500、warmup=200)。

| cond | trial 完走 | 総 runtime | 単 trial runtime range | parquet 出力 |
|---|---|---:|---|---:|
| C2 | 100/100 | 4128s (~69 min) | 145-600s | 400 ファイル (4 schema × 100 trial) |
| C3 | 100/100 | 4075s (~68 min) | 143-543s | 400 ファイル |

データサイズ: C2 = 7.5 MB、C3 = 7.8 MB。S2 plan 見積 (~24 MB / trial) より遥かに小さい (LOB T=1500 vs aggregate T=50000 で 33x 短いため round-trip 数が少ない)。→ tar.gz バンドルせず git に直接 commit。

### Trial-level basic stats (4 条件比較に最低限の桁感)

| metric | C2 (LOB uniform) | C3 (LOB pareto) | C0u (S2、参考) | C0p (S2、参考) |
|---|---:|---:|---:|---:|
| n_round_trips mean (range) | 4,273 (2,212-7,594) | 4,777 (2,714-7,781) | ~10,500 / trial (推定) | ~10,500 / trial (推定) |
| forced_retired mean (range) | 10.0 (3-23) | 35.0 (16-48) | ~210 / trial (S2) | ~210 / trial (S2) |
| lifetime_samples mean | 110.9 / trial | 138.9 / trial | n/a | n/a |

→ **forced_retired: aggregate ~210 vs LOB C2 10 / C3 35** で約 6x-20x の差。LOB friction が agent bankruptcy を抑制する仮説 A の中間予測と整合。Pareto 軸では C2→C3 で 3.5x 増 (uniform で長く生き残る agents が Pareto 下では tail から速く失敗)。

### **§3.8 Lifetime censoring (Yuito 議論ポイント、plan §5 stop-trigger 関連)**

T=1500 で `lifetime_median > T/2 = 750` の trial 件数:

| cond | median > 750 件数 | pooled lifetime | conditional indicators |
|---|---:|---|---|
| C2 | **100/100 件** | median=1500 / p25=1500 / p90=1500 | censored sample 比率 90.1%、trial-level p25 mean = **1479.6** (= 25%-tile も T 張り付き) |
| C3 | **100/100 件** | median=1494 / p25=212 / p90=1500 | censored sample 比率 72.0%、trial-level p25 mean = **502.3** (= Pareto tail からの早期退場が 25 percentile に効く) |

判定基準 (plan §3.8): `lifetime_median > 750` が 50 trial 以上 / 100 → 「LOB で lifetime 延長」が **仮説 A 中間予測の primary evidence** として確定。本実測は **100/100、極端に強い primary evidence**。

**Plan §5 stop-trigger 該当性**:
> 「§3.8 で C3 censoring 重大 flag 件数が trial 全 100 件で発生 (= LOB 全 trial で 1 agent も substitute 起きてない)、これは仮説 A 中間予測の極端形なので Yuito 議論ポイント」

- **flag 件数 100/100 = trigger HIT** ⚠️
- 但し「1 agent も substitute 起きてない」(degenerate 形) には至らず: C2 で trial 平均 10 / C3 で 35 の forced_retired が発生
- → **median 統計が T 張り付きで信頼できないが、tail (p25) は C2/C3 で qualitatively 異なる挙動を示す** (C2 p25 ≈ 1480、C3 p25 ≈ 502、3x 差)
- → 補助 KPI として **p25 + conditional median (uncensored sample のみ) が必須**、Windows 側 `aggregate_full_summary.py` で 4 条件 × 全 lifetime 統計 (median / p25 / p90 / conditional median / censored 比率) を出して plan §3.8 通り図表化する
- → survival analysis (Kaplan-Meier) は引き続き Phase 2 scope 外 (S2 plan v2 §0.7 確定済) を継承

**Yuito 判断要請** (Windows aggregation の前か後かの選択):
1. (a) このまま Windows aggregation に進む — interaction 値、p25 4 条件比較、figures を出して総合判定
2. (b) Stop して plan §5 trigger を厳密に発動 — proposal Limitation framing を先に決めてから aggregation
3. (c) その他

本 diff.md は (a) を default 想定で push、Yuito が (b)(c) を選んだ場合は Windows 側 aggregation 着手前に巻き戻し可能。

### §3.7 Pooled bin_var_slope は Mac 側で計算しない方針継承
plan §3.5 / §3.7 の bin_var_slope pooled 計算は Windows 側 `aggregate_full_summary.py` で実施。Mac 側は trial parquet 出力に専念。

### Mac → Windows 転送
- `tar.gz` バンドル不要 (データ ~15MB と軽量、git 直 commit が S2 のパターン)
- `data/C2/` `data/C3/` (各 400 parquet) + `logs/S3_mac_summary.json` + `logs/runtime/*S3_*log` を本 commit に同梱

### S3_mac_summary.json
```json
{
  "stage": "S3-mac",
  "conds": ["C2", "C3"],
  "n_trials_per_cond": 100,
  "seed_base": 1000,
  "n_workers": 8,
  "main_steps": 1500,
  "warmup_steps": 200,
  "determinism_pass": true,
  "timestamp": "2026-04-30T03:18:18.340424"
}
```

(注: `--skip-determinism` で本 ensemble run を実行したため `determinism_pass: true` は default 値。実際の guard PASS は別 run で `logs/runtime/20260430_005146_S3_lob_ensemble.log` に記録済。)

---

## Stage 2: Mac → Windows 転送 (2026-04-30 完了 / git 経由)

tar.gz バンドルは Stage 1 §「データサイズ」のとおり省略、`data/C2/` `data/C3/` の parquet を本 commit に直接含めて git push。Windows 側で `git pull` するだけで Stage 3 に進める。

### Windows 整合性チェック (pull 後に実行する手順)
- ファイル数: `ls data/C2/ | wc -l` → 400、同 C3 → 400
- 1 trial sample: `pd.read_parquet('data/C2/trial_1000.parquet')` で n_rt 行数が桁通り (~3,000-5,000 行)
- agent parquet で `w_init` 列 non-NaN: `pd.read_parquet('data/C2/agents_1000.parquet')['w_init'].isna().sum() == 0`

---

## Stage 3: Windows aggregation (未着手)

(Yuito 判断 [(a) (b) (c)] 後、Windows 側で `combine_ensemble_summaries` + `aggregate_full_summary` 実行 → 本セクション追記)
