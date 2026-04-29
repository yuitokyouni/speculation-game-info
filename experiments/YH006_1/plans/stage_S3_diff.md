# Stage S3 diff — LOB ensemble + 4 条件 interaction 進捗ログ

S3 plan v2 に基づく実装・実行ログ。3 段階 (Mac sim → 転送 → Windows aggregation) の進捗を 1 行ずつ追記する形 (Yuito S3 v1 承認時要望)。

| Stage | Date | 状態 | Note |
|---|---|---|---|
| **0. plan v2 + 実装準備** | 2026-04-29 | **完了** | plan v2 反映、Mac/Windows 両側コード prep 済 (詳細下) |
| 1. Mac LOB 100 trial × 2 条件 | — | 未着手 | Mac で `python -m code.lob_ensemble` 実行待ち |
| 2. Mac → Windows 転送 | — | 未着手 | tar.gz バンドル + Windows 整合性チェック |
| 3. Windows aggregation | — | 未着手 | combine + aggregate_full_summary 実行 |

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

## Stage 1: Mac LOB 100 trial × 2 条件 (未着手)

(Mac 実行後に追記)

---

## Stage 2: Mac → Windows 転送 (未着手)

(転送後に追記)

---

## Stage 3: Windows aggregation (未着手)

(`combine_ensemble_summaries` + `aggregate_full_summary` 実行後に追記)
