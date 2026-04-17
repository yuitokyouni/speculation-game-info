"""YH005: Katahira et al. (2019) Speculation Game の再現実装

GCMG をベースに、以下の拡張を加えたモデル:
- 往復取引制約 (round-trip): 反対シグナルが出るまで hold
- 板ロット量 B: 注文サイズ = floor(wealth / B)
- 認知価格 P(t): 戦略評価用の仮想価格と実価格の分離
- 量子化閾値 C: 価格変動を {-1, 0, +1} に離散化

11 の stylized facts のうち 10 を同時に再現することが報告されている。
"""
