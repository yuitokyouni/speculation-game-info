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
