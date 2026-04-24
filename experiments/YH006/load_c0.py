"""C0 (aggregate-demand baseline) を YH005_1 の output から読み込む。

YH005_1 は既に phase1_metrics.json に 5 figure 分の metrics を JSON 化済み。
C0 行は 20 panel 比較図で「aggregate-demand reference」として表示する。
再実行はしない (SPEC.md §1 の C0 項目と整合)。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

HERE = Path(__file__).resolve().parent
YH005_1_METRICS = HERE.parent / "YH005_1" / "outputs" / "phase1_metrics.json"


def load_c0_metrics() -> Dict[str, Any]:
    """YH005_1 の phase1_metrics.json を dict で返す。"""
    if not YH005_1_METRICS.exists():
        raise FileNotFoundError(
            f"YH005_1 metrics not found at {YH005_1_METRICS}. "
            f"Run `experiments/YH005_1/phase1_mechanism_figures.py` first."
        )
    with open(YH005_1_METRICS) as f:
        return json.load(f)


if __name__ == "__main__":
    m = load_c0_metrics()
    print("C0 (YH005_1 aggregate-demand) summary:")
    print(f"  params N={m['params']['N']} T={m['params']['T']}")
    print(f"  num_round_trips = {m['price_stats']['num_round_trips']}")
    print(f"  wealth α_hill   = {m['wealth']['alpha_hill_xmin_p90']:.3f}")
    print(f"  horizon median  = {m['horizon']['median_horizon']:.1f}")
    print(f"  passive_hold    = {m['hold_ratio']['passive_hold']:.3f}")
    print(f"  active_hold     = {m['hold_ratio']['active_hold']:.3f}")
