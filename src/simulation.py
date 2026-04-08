"""simulation.py – Main simulation loop (clean version).

Theoretical basis:
  - Chartist side: Speculation Game (Katahira & Chen 2019)
  - Fundamentalist side: continuous restoring force (demand ∝ mispricing)
  - Switching: Brock & Hommes (1998) softmax on fitness
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field

from .utils.config          import SimConfig
from .utils.history         import PriceHistory
from .agents.chartist       import ChartistAgent
from .agents.fundamentalist import FundamentalistAgent
from .market.nav            import NAVProcess


@dataclass
class SimResult:
    price:         np.ndarray
    nav:           np.ndarray
    nc:            np.ndarray
    delta_p:       np.ndarray
    excess_demand: np.ndarray
    config:        SimConfig = field(repr=False)

    @property
    def log_return(self) -> np.ndarray:
        return np.diff(np.log(self.price), prepend=np.log(self.price[0]))


class Simulation:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)

    def run(self) -> SimResult:
        cfg = self.cfg
        rng = self.rng

        nav_proc = NAVProcess(cfg.NAV, cfg.nav_sigma, cfg.seed)
        history  = PriceHistory(cfg.M, cfg.C, cfg.seed)

        n_c = max(1, int(cfg.n_c_init * cfg.N))
        n_f = cfg.N - n_c

        agents_c = [
            ChartistAgent(i, cfg.M, cfg.S, cfg.B, rng, max_qty=cfg.max_qty)
            for i in range(n_c)
        ]
        agents_f = [
            FundamentalistAgent(i, cfg.B, rng, sensitivity=cfg.f_sensitivity,
                                max_qty=cfg.f_max_qty)
            for i in range(n_f)
        ]

        p = cfg.p0
        P = 0.0   # Cognitive price (cumulative quantized changes)

        price_arr = np.empty(cfg.T)
        nav_arr   = np.empty(cfg.T)
        nc_arr    = np.empty(cfg.T)
        dp_arr    = np.empty(cfg.T)
        D_arr     = np.empty(cfg.T)

        for t in range(cfg.T):
            nav   = nav_proc.step()
            H     = history.get()
            p_old = p

            # ── Brock-Hommes switching ────────────────────────────────
            if cfg.switching and t >= cfg.switch_warmup and t % cfg.switch_freq == 0:
                agents_c, agents_f = self._switch(agents_c, agents_f, cfg, rng)

            # ── Chartist orders ───────────────────────────────────────
            D_c = 0.0
            for ag in agents_c:
                action = ag.decide(H)
                qty    = ag.order_qty()
                if action != 0:
                    if ag.position == 0:
                        ag.open_position(action, qty, P, p)
                    else:
                        ag.close_position(P, p)
                D_c += action * qty

            # ── Fundamentalist continuous restoring force ─────────────
            n_f_current = len(agents_f)
            D_f = sum(ag.get_demand(p, nav, n_f_current) for ag in agents_f)

            D = D_c + D_f

            # ── Price update ──────────────────────────────────────────
            # No clipping: original Speculation Game (Katahira & Chen 2019)
            # has no max_move. Adding it creates two artifacts:
            #   (1) decouples observed history from actual price moves
            #   (2) suppresses noise so tiny drifts become visible/cumulative
            delta_p = D / cfg.N
            p_new   = max(p + delta_p, cfg.p_floor)

            h_t = history.update(delta_p)
            P  += h_t

            # ── Fitness updates ───────────────────────────────────────
            for ag in agents_f:
                ag.update_fitness(p_old, p_new, nav)

            # ── Bankruptcy replacement (chartists only) ───────────────
            for ag in agents_c:
                if ag.is_bankrupt():
                    ag.reset(rng)

            price_arr[t] = p_new
            nav_arr[t]   = nav
            nc_arr[t]    = len(agents_c) / cfg.N
            dp_arr[t]    = delta_p
            D_arr[t]     = D
            p = p_new

        return SimResult(price=price_arr, nav=nav_arr, nc=nc_arr,
                         delta_p=dp_arr, excess_demand=D_arr, config=cfg)

    def _switch(self, agents_c, agents_f, cfg, rng):
        """Brock & Hommes (1998) softmax switching on mean fitness."""
        beta = cfg.beta

        fit_c = np.array([ag.fitness() for ag in agents_c]) if agents_c else np.zeros(1)
        fit_f = np.array([ag.fitness() for ag in agents_f]) if agents_f else np.zeros(1)
        U_c = float(fit_c.mean())
        U_f = float(fit_f.mean())

        # Normalize by pooled std so beta operates on unit-free scale
        all_fit = np.concatenate([fit_c, fit_f])
        sigma   = float(all_fit.std())
        if sigma > 1e-12:
            U_c_n = U_c / sigma
            U_f_n = U_f / sigma
        else:
            U_c_n, U_f_n = 0.0, 0.0

        # Softmax
        max_u = max(U_c_n, U_f_n)
        e_c = float(np.exp(np.clip(beta * (U_c_n - max_u), -30, 0)))
        e_f = float(np.exp(np.clip(beta * (U_f_n - max_u), -30, 0)))
        new_nc = e_c / (e_c + e_f) if (e_c + e_f) > 0 else cfg.n_c_init

        # Apply directly — no artificial smoothing
        target_nc = np.clip(new_nc, 0.05, 0.95)
        target_c  = max(1, min(cfg.N - 1, round(target_nc * cfg.N)))
        target_f  = cfg.N - target_c

        # Convert agents between types
        while len(agents_c) > target_c:
            ag = agents_c.pop()
            agents_f.append(FundamentalistAgent(
                ag.id, cfg.B, rng, w0=ag.w, sensitivity=cfg.f_sensitivity,
                max_qty=cfg.f_max_qty))

        while len(agents_f) > target_f:
            ag = agents_f.pop()
            agents_c.append(ChartistAgent(
                ag.id, cfg.M, cfg.S, cfg.B, rng, w0=ag.w,
                max_qty=cfg.max_qty))

        return agents_c, agents_f
