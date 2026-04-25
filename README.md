# 金融マーケットABM　キャッチアップ

金融市場の Agent-Based Modelの主要論文をPython 実装し、
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
| YH005 | Speculation Game (Lite) | Katahira et al. (2019) + Katahira & Chen (2019) | Done |
| YH005_1 | SG Phase 1: 3 層機構の数値実証 (論文2 Fig. 2/4/7/8/10 再現) | Katahira & Chen (2019) | Done |
| YH006 | Speculation Game Full (論文1+2 完全再現) | Katahira et al. (2019) + Katahira & Chen (2019) | 骨格のみ |
| YH007 | Self-organized Speculation Game | Katahira & Chen (Physica A 2021) | 骨格のみ |

## ディレクトリ構造

```
experiments/
├── YH001/          Cont-Bouchaud (1997) — 完了
├── YH002/          Lux & Marchesi (1999) — 骨格のみ
├── YH003/          Challet & Zhang (1997) — 骨格のみ
├── YH004/          Jefferies et al. (2001) — 骨格のみ
├── YH005/          Katahira et al. (2019) Lite — 完了 (Null test + 3モデル比較)
├── YH005_1/        SG Phase 1: 3 層機構の数値実証 — 完了 (論文2 Fig. 2/4/7/8/10)
├── YH006/          SG Full (論文1+2 完全再現) — 骨格のみ
└── YH007/          Self-organized SG (論文3) — 骨格のみ

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
