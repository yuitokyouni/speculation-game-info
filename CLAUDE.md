# CLAUDE.md – Claude Code 引き継ぎドキュメント

このファイルはClaude Code（Opus）への完全な引き継ぎ用。
会話履歴なしでそのまま作業を開始できるように、研究背景・設計・現状・タスクを全て記載する。

---

## 0. 研究姿勢（最優先）

**データ・先行研究・結果に対して誠実であること。** これは他の全てに優先する。

- 望む結果を出すためにパラメータを調整しない。仮説に合わない結果でも正直に報告する。
- モデルへの追加機構は必ず理論的根拠（先行研究の引用）を持たせる。「見栄えが良くなる」「数値的に安定する」は理由にならない。安全弁のつもりで入れた機構が主要なダイナミクスを生み出していた事例（max_move clipが96%発火していた件）を忘れない。
- 先行研究との矛盾に気付いたら真剣に追う。原論文がChartistだけで安定するのに我々の実装が崩壊していた → 追ったら実装バグだった、という発見はこの姿勢から得られた。
- 結果が小さくても、効果が弱くても、それが事実なら事実として書く。

---

## 1. 研究の目的

**J-REIT市場のAgent-Based Model (ABM)**を構築し、以下の2つの仮説を検証する。

**仮説A（相転移）**：Chartist比率 `n_c` が閾値を超えると、市場価格がNAVから相転移的に乖離する。

**仮説B（内生的発生）**：Chartist優勢局面において、小西（2025, SMTRI）で予測貢献度が高かった
TSF・ATR・DMI_ADXが有効に機能し、LightGBM正解率が上昇する。

小西（2025）の観察：「2024年のJ-REIT市場はテクニカル指標単独で72.8%の予測精度を達成」

ABMの必要性：機械学習は"What/When"を示すが"Why"を説明しない。
ABMは「Chartist比率の上昇がテクニカル指標の有効性を生む」という因果的説明を提供する。

---

## 2. モデル理論

### Speculation Game（Katahira & Chen 2019, Physica A 524:503-518）
- Minority Gameを拡張したABM（Yu Chen先生が共著者 = SCSLABへの直接接続）
- エージェントは過去M期の量子化価格変動H(t)を見てbuy/sell/holdを決定
- ラウンドトリップ取引制約：反対シグナルが出るまでhold
- 認知世界（Cognitive Price P(t)）でStrategy評価、実世界で富更新
- 11個のStyled Factsのうち10個を再現

### Brock & Hommes (1998, JEDC 22:1235-1274)
- Fundamentalist vs Chartistの内生的スイッチング
- n_c(t) = softmax(β * U_c(t-1))

### 本モデルの拡張
全員ChartistのオリジナルSpeculation Gameに
Fundamentalist（NAVベース連続復元力型）を追加し、
Brock-Hommes型の内生的スイッチングを導入。

---

## 3. ディレクトリ構造

```
src/
├── agents/
│   ├── chartist.py        # Speculation Game agent
│   └── fundamentalist.py  # 連続復元力型NAVエージェント
├── market/nav.py          # NAVプロセス
├── analysis/validation.py # TSF/ATR/ADX + LightGBM pipeline
├── utils/
│   ├── config.py          # SimConfig dataclass
│   └── history.py         # 量子化価格履歴H(t)
├── simulation.py          # メインループ
└── run.py                 # エントリーポイント
```

---

## 4. 主要設計決定事項

### Fundamentalistを連続復元力モデルにした理由
Round-trip型だとポジションを持った後はhold(0)を返す→継続的な買い圧力ゼロ→価格崩壊。
連続復元力モデル：`demand = sensitivity * (NAV - price) / NAV * order_qty`
J-REIT市場の機関投資家（裁定業者）が乖離幅に比例してポジション調整する行動と整合。

### max_qty=50キャップの理由
富が爆発的成長するとorder_qtyが大きくなりNaN overflow発生。
`min(50, floor(w/B))`でハードキャップ。（初期典型qty≈6の約8倍）

### fitnessをEMA of ROIにした理由
「最後の取引PnL」は一発の運不運で振れすぎ→スイッチング暴走。
EMA（指数移動平均）の実現ROIを使用：`roi = real_gain / open_price_real`

### スイッチング平滑化の理由
βが高すぎると nc が0⇔1を激しく振動。
switch_freq=150（150step毎）、switch_max_delta=0.08（±8%/イベント）で制限。

---

## 5. 確認済みの動作と現状の問題

### 動作確認済みコマンド
```bash
python smoke_test.py
# または
python -c "
from src.utils.config import SimConfig
from src.simulation import Simulation
cfg = SimConfig(N=300, T=6000, M=3, f_sensitivity=0.05, n_c_init=0.9, switching=False, seed=42)
res = Simulation(cfg).run()
print(f'price=[{res.price.min():.0f},{res.price.max():.0f}]')
print(f'dev={((res.price-res.nav)/res.nav*100).mean():.2f}%')
"
# Expected: price=[993,1006], dev=-0.1%
```

### nc vs LightGBM精度（仮説Bの予備確認）
```
nc=0.2 → accuracy=0.697
nc=0.5 → accuracy=0.698
nc=0.9 → accuracy=0.740  ← Chartist優勢で精度が上がる ✓
```

### 現状の問題点

**問題1：NAV乖離が小さすぎる（±0.3%）**
実際のJ-REIT市場ではP/NAVが0.8〜1.3（±20-30%乖離）。
現モデルでは相転移の「見栄え」が弱い。

根本原因：max_qty=50キャップがSpeculation Gameの
「富裕エージェントによる断続的大量注文」メカニズムを抑制している。

**問題2：内生的スイッチングの動作未確認**
switching=Trueでの長時間シミュレーションが未実施。

**問題3：LightGBM精度の差が小さい（4%ポイント差）**
目標：nc低→55%以下、nc高→65%以上の対比を作りたい。

---

## 6. Claude Codeへのタスク（優先順）

### タスク1：より大きなNAV乖離を生む設定探索

目標：NAV乖離の標準偏差が5%以上になるパラメータを探す。

```python
# 試す方向性：
# A) max_qty=100 + f_sensitivity=0.01（Fundamentalistをさらに弱く）
# B) M=5 + C=1.5（閾値を下げて感度上げる）
# C) log-wealthスケーリングでキャップをなくす: qty = int(log(w/B + 1))
```

### タスク2：内生的スイッチングの動作確認

```python
from utils.config import SimConfig
from simulation import Simulation

cfg = SimConfig(
    N=500, T=15000, M=3, f_sensitivity=0.05,
    beta=3.0, n_c_init=0.5,
    switching=True,
    switch_freq=100, switch_warmup=1000, switch_max_delta=0.1,
    seed=42
)
res = Simulation(cfg).run()
# nc(t)が0.3〜0.8の間で変動し、高nc局面でNAV乖離が大きい、を確認
```

### タスク3：パラメータスイープ実験（論文Figure 1）

固定ncを0.1〜0.99まで変えて以下の表を作成：

| nc | NAV乖離std(%) | vol_cluster | LightGBM精度 |
|----|--------------|-------------|-------------|
| 0.1 | ? | ? | ? |
| ... | | | |

これが相転移図になる。

### タスク4：最終4パネルプロット生成

```bash
python src/run.py --N 500 --T 15000 --beta 3.0 --nc 0.5 --out results/final.png
```

期待する4パネル：
1. 価格 vs NAV の時系列
2. NAV乖離率 (p-NAV)/NAV
3. nc(t) の時系列（内生的変動）
4. 散布図：横軸=平均nc, 縦軸=LightGBM正解率（正の相関が仮説B）

---

## 7. インストール・実行

```bash
pip install -e .

# 動作確認（30秒以内）
python smoke_test.py
```

---

## 8. 論文の位置付け（SCSLABへの接続）

**新規性3点**
1. Speculation GameにFundamentalistを追加→J-REIT固有のNAV乖離メカニズムを内生的に生成
2. Brock & Hommes (1998)スイッチング機構をSpeculation Gameに接続
3. ABMが生成した時系列で小西(2025)の分析を再現→「Chartist優勢でテクニカル指標が有効」を証明

**対象の先行研究**
- Katahira & Chen (2019): Speculation Gameの直接の親論文（Yu Chen先生が共著者）
- Brock & Hommes (1998): スイッチング機構の理論的根拠
- Konishi (2025): J-REIT実証分析（本モデルが説明しようとする対象）

Yu Chen先生はSpeculation Gameの共著者なので、
「先生の研究を拡張してJ-REIT市場に適用した」という文脈でTMI院試に使う。
