"""S7 — liquidity dose-response 追加 sim (Mac 側).

freeze→funnel 因果リンク (#3) 確立のための liquidity scan seed 拡張:
  - S5.6 既存: order_volume {15, 30, 60, 120} × seed {1000, 1001} (cond=C3)
  - 1x (=30) は data/C3 と bit-一致設計なので data/C3 の 100 seed を流用
  - 本 script: {15, 60, 120} × seed {1002-1005} = 12 run を追加
    → 各水準 6 seed (1x は 100 seed) の dose-response が組める
  - 併せて FCN-only (num_sg=0) × seed {1000-1002} の価格系列を取得
    (SF readout の帰属ベースライン: SG 凍結下で SF が FCN 由来か SG 由来か)

Run (Mac):
  cd experiments/YH006_1
  python -m code.s7_doseresponse_runs
"""

from __future__ import annotations

import logging
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

HERE = Path(__file__).resolve().parent
YH006_1 = HERE.parent
for _p in (str(YH006_1), str(HERE)):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

DATA_DIR = YH006_1 / "data"
LOGS_DIR = YH006_1 / "logs"

ORDER_VOLUMES = [15, 60, 120]      # 1x(=30) は data/C3 流用のため除外
NEW_SEEDS = [1002, 1003, 1004, 1005]
FCN_ONLY_SEEDS = [1000, 1001, 1002]


def setting_label(order_volume: int) -> str:
    ratio = order_volume / 30
    if ratio == 0.5:
        return "mmfcn_05x"
    if ratio == int(ratio):
        return f"mmfcn_{int(ratio)}x"
    return f"mmfcn_ov{order_volume}"


def _worker_c3(args: Tuple[int, int]) -> Tuple[int, int, float, int, Optional[str]]:
    order_vol, seed = args
    try:
        from run_experiment import run_one_trial
        out_dir = DATA_DIR / "mmfcn_sensitivity" / f"{setting_label(order_vol)}_{seed}"
        res = run_one_trial(
            "C3", seed, out_dir=out_dir, is_lob_smoke=False,
            mmfcn_order_volume=(None if order_vol == 30 else order_vol),
        )
        return (order_vol, seed, res.runtime_sec, res.n_round_trips, None)
    except Exception:
        import traceback
        return (order_vol, seed, 0.0, 0, traceback.format_exc())


def _worker_fcn_only(seed: int) -> Tuple[int, int, Optional[str]]:
    """FCN-only (num_sg=0) T=1500、価格系列のみ保存。"""
    try:
        import random as _r
        import numpy as np
        import pandas as pd
        from pams.runners import SequentialRunner  # type: ignore
        from configs.c3 import make_config  # type: ignore
        from custom_saver import OrderTrackingSaver  # type: ignore
        from mm_fcn_agent import MMFCNAgent  # type: ignore
        from sg_agent import WInitLoggingSpeculationAgent  # type: ignore
        from config import LOB_PARAMS as p

        cfg = make_config(
            warmup_steps=p["warmup_steps"], main_steps=p["main_steps"],
            num_sg_agents=0, c_ticks=p["c_ticks"],
            max_normal_orders=p["max_normal_orders"],
        )
        cfg["FCNAgents"]["numAgents"] = p["num_fcn"]
        cfg["SGAgents"]["class"] = "WInitLoggingSpeculationAgent"
        saver = OrderTrackingSaver()
        r = SequentialRunner(settings=cfg, prng=_r.Random(seed), logger=saver)
        r.class_register(WInitLoggingSpeculationAgent)
        r.class_register(MMFCNAgent)
        r.main()
        prices = [log["market_price"]
                  for log in sorted(saver.market_step_logs,
                                    key=lambda x: x["market_time"])
                  if log["market_time"] >= p["warmup_steps"]]
        out_dir = DATA_DIR / "_s7_fcn_only"
        out_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({
            "t": np.arange(len(prices), dtype=np.int64),
            "mid": np.asarray(prices, dtype=np.float64),
        }).to_parquet(out_dir / f"prices_{seed:04d}.parquet")
        return (seed, len(prices), None)
    except Exception:
        import traceback
        return (seed, 0, traceback.format_exc())


def main() -> None:
    (LOGS_DIR / "runtime").mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("S7-runs")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fh = logging.FileHandler(
            LOGS_DIR / "runtime" / f"{ts}_S7_doseresponse.log", encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    jobs = [(ov, s) for ov in ORDER_VOLUMES for s in NEW_SEEDS]
    logger.info(f"S7 dose-response runs: {len(jobs)} C3-jobs "
                f"(ov × seed) + {len(FCN_ONLY_SEEDS)} FCN-only")
    n_err = 0
    with ProcessPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(_worker_c3, j) for j in jobs]
        futs_f = [ex.submit(_worker_fcn_only, s) for s in FCN_ONLY_SEEDS]
        for f in futs:
            ov, seed, rt, n_rt, err = f.result()
            if err:
                n_err += 1
                logger.error(f"[c3] ov={ov} seed={seed} ERROR\n{err}")
            else:
                logger.info(f"[c3] ov={ov} seed={seed} done: "
                            f"runtime={rt:.0f}s n_rt={n_rt:,}")
        for f in futs_f:
            seed, n_p, err = f.result()
            if err:
                n_err += 1
                logger.error(f"[fcn-only] seed={seed} ERROR\n{err}")
            else:
                logger.info(f"[fcn-only] seed={seed} done: n_prices={n_p}")
    logger.info(f"S7 runs complete, errors={n_err}")


if __name__ == "__main__":
    main()
