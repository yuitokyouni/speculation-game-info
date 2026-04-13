# speculation-game-info

Speculation Game (Katahira & Chen 2019, Physica A 524:503-518) に
情報構造の異質性を導入し、市場の Stylized Facts が
エージェントの情報利用様式からどう内生するかを調べる。

## 構成

```
src/core/        シミュレーション本体
experiments/     番号付き実験（再現→拡張の順）
analysis/        Stylized Facts 検証ツール
docs/            先行研究整理・仮説
archive/jreit_v1 旧 J-REIT ABM（参考保存）
```

旧 J-REIT ABM のフルコードは [`archive/jreit-abm`](../../tree/archive/jreit-abm) ブランチにも保存。

## セットアップ

```bash
pip install -e .
python src/run.py
```

## 参考文献

- Katahira & Chen (2019). Speculation Game. *Physica A*, 524, 503-518.
- Brock & Hommes (1998). Heterogeneous beliefs and routes to chaos. *JEDC*, 22, 1235-1274.
