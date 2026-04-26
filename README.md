# 金融マーケットABMの系譜を辿る

金融市場の Agent-Based Model (ABM) の主要論文を自力で Python 実装し、
各モデルの理論的主張を数値的に検証する。Cont-Bouchaud (1997) の
パーコレーションモデルから Katahira et al. (2019) の Speculation Game まで、
古典 (1997-2010) から最近の拡張までを系統的にカバーする。
東京大学 SCSLAB (陳研究室) への進学準備の一環として実施。

## 実装リスト

| ID | モデル | 論文 | 状態 |
|----|--------|------|------|
| YH001 | Cont-Bouchaud Percolation | Cont & Bouchaud (1997) | Done (findings 記載済) |
| YH002 | Lux-Marchesi Volatility Clustering | Lux & Marchesi (2000) IJTAF (Param Set I) | Done (findings 記載済) |
| YH003 | Minority Game | Challet & Zhang (1997) | Done (findings 記載済) |
| YH004 | Grand Canonical MG | Jefferies et al. (2001) | Done (findings 記載済) |
| YH005 | Speculation Game Lite | Katahira & Chen (2019) arXiv:1909.03185 (論文2) | Done (findings 記載済) |
| YH005_1 | SG Phase 1: 3 層機構の数値実証 (論文2 Fig. 2/4/7/8/10 再現) | Katahira & Chen (2019) | Done (findings 記載済) |
| YH005_2 | 論文1 Fig 11/12/13 (asymmetry / leverage / gain-loss) — aggregate post-processing | Katahira et al. (2019) Physica A 524 (論文1) | Planned (5-6 月着手目安) |
| YH006 | SG を PAMS-LOB に移植 (2×2 world × wealth, N=100) | Katahira & Chen (2019) + Hirano-Izumi 2023 PAMS | Phase 1 完了 (findings 記載済) |
| YH006_1 | YH006 Phase 2: F1 interaction の機構解明 (wealth 階級別 funnel) | — | Planned |
| YH007 | Self-organized SG on LOB | Katahira & Chen (Physica A 2021) | Open (詳細記述 別途) |

**経緯メモ (transparency)**: 旧版表で `YH006 = Speculation Game Full (論文1+2 完全再現)` だった entry を 2026-04 に **`YH006 = LOB 移植` に意味変更**。実装は YH005_1 の 5 figure を PAMS-LOB 上で再現し 2×2 (world × wealth) 比較に拡張する方向 (`experiments/YH006/SPEC.md` §0)。これに伴い、旧 YH006 で予定していた**論文1 Fig 11/12/13 (aggregate post-processing)** は新設 `YH005_2` に retire。

## ディレクトリ構造

```
experiments/
├── YH001/          Cont-Bouchaud (1997) — 完了
├── YH002/          Lux & Marchesi (2000) Param Set I — 完了
├── YH003/          Challet & Zhang (1997) MG — 完了
├── YH004/          Jefferies et al. (2001) GCMG — 完了
├── YH005/          Katahira-Chen (2019) Speculation Game Lite — 完了 (Null test + 3 モデル比較)
├── YH005_1/        SG Phase 1: 3 層機構の数値実証 — 完了 (論文2 Fig. 2/4/7/8/10)
├── YH005_2/        論文1 Fig 11/12/13 (asymmetry / leverage / gain-loss) — 未着手
├── YH006/          SG on PAMS-LOB (2×2 world × wealth) — Phase 1 完了
├── YH006_1/        YH006 Phase 2: F1 interaction 機構解明 — 未着手
└── YH007/          Self-organized SG on LOB — 詳細記述 別途

docs/
├── literature.md   先行研究整理
├── hypotheses.md   検証したい仮説
└── findings.md     各 YH の確認済み事項 (重複作業防止、新しい YH 着手前に読む)
```

各実験ディレクトリは `model.py` (モデル本体), `run_simulation.py` (実行・可視化),
`README.md` (実験ノート) を含む。

## セットアップ

```bash
pip install -r requirements.txt
cd experiments/YH001
python run_simulation.py
```

## 使用技術

- Python 3.x
- NumPy, SciPy, Matplotlib
- powerlaw (Clauset-Shalizi-Newman テール推定)
- NetworkX (ランダムグラフ生成、必要に応じて)

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE) を参照。
