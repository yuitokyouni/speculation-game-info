"""Phase 2 SG agent subclasses.

S2 plan v2 §0.3 (Yuito 指示 #3): w_init logging 用 subclass を実装。
S5/S6 用 (q_const, lifetime cap) は別 stage で同じパターンの subclass を追加予定。

Phase 1 monkey patch 禁止 (Brief §4.4) のため subclass で実装。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

# Phase 1 SpeculationAgent を read-only で import
HERE = Path(__file__).resolve().parent
YH006 = HERE.parent.parent / "YH006"
if str(YH006) not in sys.path:
    sys.path.insert(0, str(YH006))

from speculation_agent import SpeculationAgent  # noqa: E402  (read-only 流用)


class WInitLoggingSpeculationAgent(SpeculationAgent):
    """w_init (= sg_wealth at setup completion) を agent attribute として永続化。

    Phase 1 SpeculationAgent.setup() は wealth_mode 分岐で sg_wealth を draw する
    が、その値を agent attribute として保存し続けない (sg_wealth は round-trip
    で更新されるため)。本 subclass は setup() 末尾で self.w_init を保存し、
    sim 終了時に agent-level parquet で生涯初期 wealth が直接取れるようにする。
    """

    def setup(
        self,
        settings: Dict[str, Any],
        accessible_markets_ids: List[int],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().setup(settings, accessible_markets_ids, *args, **kwargs)
        # super().setup() の末尾で self.sg_wealth = w (uniform / pareto draw 値)
        # が確定している。ここで w_init として永続化する。
        self.w_init: int = int(self.sg_wealth)
