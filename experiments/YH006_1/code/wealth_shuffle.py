"""S6r A4 ablation — wealth shuffle saver hook (Phase 1 非改変).

A4 = 周期 K step ごとに全 SG agent の `sg_wealth` を permute する ablation。
agent subclass (A1/A3 方式) ではなく Logger の step 終端 callback で介入する:

- marginal wealth 分布は permutation により厳密保存 (multiset 不変)
- agent 集団・学習状態・position・注文フローは非破壊
  → A3 で起きた市場活動の regime change (= PAMS O(板) 操作との掛け算で
    計算爆発) が構造的に起きない
- shuffle 無効条件は素の OrderTrackingSaver を使う (コードパス分岐) ため、
  既存 7 条件の bit-一致は構造的に保証される

発火規則 (plan §0.3): `t >= warmup_steps` かつ `(t − warmup_steps + 1) % K == 0`
→ main session の K step 経過ごと、step 終端で permute。T=1500, K=121 で 12 回。

RNG: `random.Random(seed * 1_000_003 + 41)` — agent / PAMS runner の prng と
独立な専用 stream。同 seed 2 run の determinism は guard (ablation_a4_ensemble
§2) で検証する。

注意 (plan §0.2): adapter.round_trips_to_df の w_open/w_close 再構成は shuffle
イベントを考慮しないため A4 条件下では無効な列になる。L 判定が使う
horizon/delta_g/q/agents_df (w_init, w_final = agent state 直読) は非影響。
"""

from __future__ import annotations

import random
from typing import List, Optional

from custom_saver import OrderTrackingSaver  # type: ignore


class WealthShuffleSaver(OrderTrackingSaver):
    """OrderTrackingSaver + 周期 K の sg_wealth permutation (A4)。"""

    def __init__(self, shuffle_period: int, warmup_steps: int, seed: int) -> None:
        super().__init__()
        if shuffle_period < 1:
            raise ValueError(f"shuffle_period must be >= 1, got {shuffle_period}")
        self.shuffle_period = int(shuffle_period)
        self.warmup_steps = int(warmup_steps)
        self._shuffle_rng = random.Random(seed * 1_000_003 + 41)
        self.simulator = None          # run_lob_trial_smoke が構築後に注入
        self._sgs: Optional[List] = None
        self.n_shuffles: int = 0
        self.shuffle_times: List[int] = []

    def _resolve_sgs(self) -> List:
        """SG agent list を遅延解決 (agents は runner.main() 中に確定するため)。"""
        if self._sgs is None:
            from sg_agent import WInitLoggingSpeculationAgent  # type: ignore
            assert self.simulator is not None, \
                "WealthShuffleSaver.simulator 未注入 (runner 構築後に set すること)"
            self._sgs = [
                a for a in self.simulator.agents
                if isinstance(a, WInitLoggingSpeculationAgent)
            ]
            assert len(self._sgs) > 0, "SG agent が見つからない"
        return self._sgs

    def process_market_step_end_log(self, log) -> None:  # type: ignore[override]
        super().process_market_step_end_log(log)
        t = int(log.market.get_time())
        if t < self.warmup_steps:
            return
        if (t - self.warmup_steps + 1) % self.shuffle_period != 0:
            return
        sgs = self._resolve_sgs()
        wealths = [int(a.sg_wealth) for a in sgs]
        self._shuffle_rng.shuffle(wealths)
        for a, w in zip(sgs, wealths):
            a.sg_wealth = w
        self.n_shuffles += 1
        self.shuffle_times.append(t)
