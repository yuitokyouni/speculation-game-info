# 金融マーケットABMの系譜を辿る

金融市場の Agent-Based Model (ABM) の主要論文を自力で Python 実装し、
各モデルの理論的主張を数値的に検証する。Cont-Bouchaud (1997) の
パーコレーションモデルから Katahira et al. (2019) の Speculation Game まで、
古典 (1997-2010) から最近の拡張までを系統的にカバーする。
東京大学 SCSLAB (陳研究室) への進学準備の一環として実施。

## 実装リスト

| ID | モデル | 論文 | 状態 |
|----|--------|------|------|
| YH001 | Cont-Bouchaud Percolation | Cont & Bouchaud (1997) | Done |
| YH002 | Lux-Marchesi | Lux & Marchesi (1999) Nature | Planned |
| YH003 | Minority Game | Challet & Zhang (1997) | Planned |
| YH004 | Grand Canonical MG | Jefferies et al. (2001) | Planned |
| YH005 | Speculation Game | Katahira et al. (2019) | Planned |

## ディレクトリ構造

```
experiments/
├── YH001/          Cont-Bouchaud (1997) — 完了
├── YH002/          Lux & Marchesi (1999) — 骨格のみ
├── YH003/          Challet & Zhang (1997) — 骨格のみ
├── YH004/          Jefferies et al. (2001) — 骨格のみ
└── YH005/          Katahira et al. (2019) — 骨格のみ

src/core/           共通シミュレーション基盤
analysis/           Stylized Facts 検証ツール
docs/               先行研究整理・仮説
archive/            旧コード退避
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
