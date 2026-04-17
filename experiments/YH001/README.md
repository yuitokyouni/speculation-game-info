# YH001: Cont-Bouchaud (1997) Percolation Model

Cont & Bouchaud (1997) "Herd behavior and aggregate fluctuations in financial markets" の再現実装。

## 目的

ランダムグラフによるherding（群衆行動）がfat tailを内生的に生むことを確認する。

## 実行

```bash
cd experiments/YH001
python run_simulation.py
```

`results.png` に6パネルの図が出力される。

## パラメータ

| パラメータ | デフォルト | 意味 |
|-----------|----------|------|
| N | 10000 | エージェント数 |
| c | 0.9 | 協調パラメータ (0 < c < 1) |
| a | 0.01 | 取引活性度 |
| λ | 1.0 | market depth |
| T | 50000 | ステップ数 |

## 出力 (6パネル)

1. リターン時系列 — volatility clustering の視覚確認
2. リターン分布 vs ガウス分布 (linear)
3. 対数スケール裾比較 (log-linear)
4. クラスターサイズ分布 (log-log) — 理論: P(W) ~ W^{-5/2}
5. Excess kurtosis 表示
6. c vs kurtosis 感度分析 — c→1 で kurtosis 急増

## 参考文献

Cont, R. & Bouchaud, J.-P. (2000). Herd behavior and aggregate fluctuations in financial markets.
*Macroeconomic Dynamics*, 4(2), 170-196. (Working paper: 1997)
