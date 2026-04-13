"""シミュレーションパラメータ定義

デフォルト値は Katahira & Chen (2019) Table 1 に準拠。
各パラメータに出典を併記する。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SimConfig:
    # --- エージェント ---
    N: int = 301            # エージェント数 (奇数; Katahira & Chen 2019)
    n_c_init: float = 1.0   # 初期 Chartist 比率
    n_strategies: int = 2   # 各 Chartist のストラテジ数

    # --- 情報構造 ---
    M: int = 3              # メモリ長 (Katahira & Chen 2019, M=3)
    C: float = 0.02         # 量子化閾値

    # --- Type V ---
    f_sensitivity: float = 0.05   # Value-signal 感度
    f_noise_std: float = 0.01     # シグナルノイズ

    # --- 市場 ---
    initial_price: float = 1000.0
    liquidity: float = 1e4
    value_signal: float = 1000.0  # 外部バリューシグナル初期値

    # --- スイッチング (Brock & Hommes 1998) ---
    switching: bool = False
    beta: float = 1.0       # 選択強度
    ema_alpha: float = 0.05 # fitness EMA 減衰率

    # --- シミュレーション ---
    T: int = 10000          # ステップ数
    seed: int = 42
