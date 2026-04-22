# YH006: Speculation Game on LOB (PAMS)

Katahira-Chen 2019 Speculation Game の decision rule を
PAMS (Hirano-Izumi 2023) tick-scale LOB 環境に移植し、
wealth heterogeneity → volatility clustering の因果が
LOB 微視構造下で保存されるかを検証する。

## Scope (Lite)
- **E0**: PAMS FCN baseline (reference stylized facts)
- **E1**: + SG agents, uniform initial wealth
- **E2**: + SG agents, Pareto initial wealth (α=1.5) ← 主実験

## Predecessors
- YH005: Katahira 2019 Speculation Game aggregate-demand 実装
- ABIDES (jpmorganchase/abides-jpmc-public) は 2025/6 archived、PAMS 採用

## Stack
- PAMS 0.2.x (https://github.com/masanorihirano/pams)
- Python 3.12

## Layout
- `speculation_agent.py` — SG decision rule を PAMS Agent subclass に
- `run_experiment.py` — E0/E1/E2 実行エントリ
- `configs/` — 各実験の JSON config
- `analysis/` — stylized facts 分析、YH005 からの流用を含む
- `notebooks/` — sanity / exploration
- `outputs/` — 実験成果物 (git 管理外)
