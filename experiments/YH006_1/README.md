# YH006_1 — Phase 2 結果サマリ

## Stage S1 (tentative) — Phase 1 データ再分析

**実行範囲**: 4 / 4 条件で完走 (C0u, C0p, C2, C3)

### 5 主指標 (点推定、CI は S1-secondary で取る)

| cond | n_rt | Pearson | Spearman | Kendall | binVar slope | qreg slope diff |
|---|---:|---:|---:|---:|---:|---:|
| C0u | 1,041,712 | 0.3535 | 0.1944 | 0.1561 | -0.2033 | 0.5833 |
| C0p | 1,049,903 | 0.3471 | 0.1923 | 0.1545 | -0.2308 | 0.5965 |
| C2 | 879 | 0.6091 | 0.4221 | 0.3416 | -0.1758 | 1.8182 |
| C3 | 1,080 | 0.3329 | 0.2816 | 0.2216 | -0.1727 | 0.9444 |

### Interaction = (C3 − C2) − (C0p − C0u)

| indicator | full | first half | second half |
|---|---:|---:|---:|
| rho_pearson | -0.2699 | -0.2178 | -0.3161 |
| rho_spearman | -0.1384 | -0.0610 | -0.2214 |
| tau_kendall | -0.1184 | -0.0589 | -0.1862 |
| bin_var_slope | +0.0305 | -0.1270 | +0.2823 |
| qreg_slope_diff | -0.8869 | -0.5049 | -1.1997 |

### Plan B 先取り指標

| cond | corr(w_init, h) | skew(high − low) | Hill α (|ΔG|) |
|---|---:|---:|---:|
| C0u | -0.0006 | -0.1343 | 1.9196 |
| C0p | -0.0027 | -0.0963 | 1.9650 |
| C2 | nan | -0.6847 | 3.1687 |
| C3 | nan | -0.0356 | 2.9352 |

### S1 (tentative) の役割と判定

本 Stage は (a) 5 指標実装 sanity check / (b) Phase 1 → Phase 2 schema アダプタ確定 / (c) 桁感の事前確認、の 3 点に scope 限定。**plan A/B 分岐判定は出さない**。最終確定は S3 完了後の S1-secondary (100 trial bootstrap CI) で行う。S2/S3 は本 S1 結果に関わらず実行される。

### Layer 2 timescale concern (Phase 2 scope 外)

Phase 1 LOB の T=1500 は Katahira 標準 T=50000 より 33x 短く、本 sim 長を超える長期での F1 持続性は未検証。Phase 2 では検証せず、最終 README + proposal Limitations 節に明記する。

---

## Stage S2 — aggregate baseline 100 trial ensemble

**実行範囲**: C0p: 100 trial, C0u: 100 trial

### 主指標 ensemble mean ± 95% CI (bootstrap 10,000 resample)

| metric | C0u (mean [CI]) | C0p (mean [CI]) |
|---|---|---|
| rho_pearson | +0.3472 [+0.3457, +0.3488] | +0.3469 [+0.3456, +0.3482] |
| rho_spearman | +0.1942 [+0.1932, +0.1952] | +0.1943 [+0.1933, +0.1952] |
| tau_kendall | +0.1560 [+0.1552, +0.1568] | +0.1561 [+0.1553, +0.1568] |
| bin_var_slope | -0.3141 [-0.3395, -0.2885] | -0.3242 [-0.3475, -0.3002] |
| q90_q10_slope_diff | +0.5932 [+0.5909, +0.5956] | +0.5914 [+0.5891, +0.5938] |
| corr_w_init_h | +0.0003 [-0.0001, +0.0008] | -0.0004 [-0.0009, +0.0001] |
| skew_high_minus_low | -0.1138 [-0.1188, -0.1069] | -0.1170 [-0.1199, -0.1142] |
| hill_alpha | +2.4583 [+2.1666, +2.8041] | +2.8228 [+2.4205, +3.2410] |
| lifetime_median | +389.6300 [+388.6350, +390.6400] | +387.8200 [+386.8949, +388.7450] |
| lifetime_p90 | +907.4260 [+904.8580, +909.9820] | +905.0120 [+902.3360, +907.7132] |
| wealth_persistence_rho | -0.0083 [-0.0261, +0.0089] | -0.0103 [-0.0328, +0.0120] |
| forced_retire_rate | +0.0021 [+0.0021, +0.0021] | +0.0021 [+0.0021, +0.0021] |

### Pooled bin variance slope (S2 plan v2 修正 1, Yuito 指示 #1)

- **C0u**: pooled bin_var_slope = -0.4036
- **C0p**: pooled bin_var_slope = -0.2879

### Sub-checkpoint: q90_q10_slope_diff trial 間 SD

- **C0u**: SD = 0.0121 → **OK (<=0.3)**
- **C0p**: SD = 0.0121 → **OK (<=0.3)**

### Lifetime censoring flag (S2 plan v2 修正 3)

- **C0u**: censoring 重大 flag 0 件 (median ≤ T/2)
- **C0p**: censoring 重大 flag 0 件 (median ≤ T/2)

### Determinism guard

C0u seed=1000 × 2 回独立実行: **PASS (rt_df + agents_df bit-一致)**

### LOB SG agent subclass smoke (S2 plan v2 修正 4)

C3 short smoke: **SKIPPED** (Windows env で PAMS 不在、Mac で別途実行予定)

### Layer 2 timescale concern (Phase 2 scope 外、再掲)

Phase 1 LOB の T=1500 は Katahira 標準 T=50000 より 33x 短く、本 sim 長を 超える長期での F1 持続性は未検証。Phase 2 では検証せず、最終 README + proposal Limitations 節に明記する。
