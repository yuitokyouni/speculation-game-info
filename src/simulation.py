"""simulation.py – Main simulation loop (v3)."""
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
        """Log returns of the price series."""
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

        agents_c: list[ChartistAgent]       = [
            ChartistAgent(i, cfg.M, cfg.S, cfg.B, rng) for i in range(n_c)]
        agents_f: list[FundamentalistAgent] = [
            FundamentalistAgent(i, cfg.B, rng, sensitivity=cfg.f_sensitivity)
            for i in range(n_f)]

        p = cfg.p0
        P = 0.0

        price_arr = np.empty(cfg.T)
        nav_arr   = np.empty(cfg.T)
        nc_arr    = np.empty(cfg.T)
        dp_arr    = np.empty(cfg.T)
        D_arr     = np.empty(cfg.T)

        for t in range(cfg.T):
            nav   = nav_proc.step()
            H     = history.get()
            p_old = p

            # Switching
            if cfg.switching and t >= cfg.switch_warmup and t % cfg.switch_freq == 0:
                agents_c, agents_f = self._switch(agents_c, agents_f, cfg, rng)

            # ── Chartist orders ────────────────────────────────────────
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

            # ── Fundamentalist continuous restoring force ──────────────
            D_f = sum(ag.get_demand(p, nav) for ag in agents_f)

            D = D_c + D_f

            # ── Price update ───────────────────────────────────────────
            raw_dp  = D / cfg.N
            delta_p = np.clip(raw_dp, -p * cfg.max_move, p * cfg.max_move)
            p_new   = max(p + delta_p, cfg.p_floor)
            h_t     = history.update(raw_dp)
            P      += h_t

            # Update fundamentalist fitness
            for ag in agents_f:
                ag.update_fitness(p_old, p_new, nav)

            # Bankruptcy replacement (chartists only; fundamentalists don't lose wealth)
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
        beta = cfg.beta
        U_c  = float(np.mean([ag.fitness() for ag in agents_c])) if agents_c else 0.0
        U_f  = float(np.mean([ag.fitness() for ag in agents_f])) if agents_f else 0.0

        max_u = max(U_c, U_f)
        e_c   = float(np.exp(np.clip(beta * (U_c - max_u), -30, 0)))
        e_f   = float(np.exp(np.clip(beta * (U_f - max_u), -30, 0)))
        new_nc = e_c / (e_c + e_f) if (e_c + e_f) > 0 else cfg.n_c_init

        cur_nc = len(agents_c) / cfg.N
        delta  = np.clip(new_nc - cur_nc, -cfg.switch_max_delta, cfg.switch_max_delta)
        target_nc = np.clip(cur_nc + delta, 0.05, 0.95)
        target_c  = max(1, min(cfg.N - 1, round(target_nc * cfg.N)))
        target_f  = cfg.N - target_c

        while len(agents_c) > target_c:
            ag = agents_c.pop()
            agents_f.append(FundamentalistAgent(
                ag.id, cfg.B, rng, w0=ag.w, sensitivity=cfg.f_sensitivity))

        while len(agents_f) > target_f:
            ag = agents_f.pop()
            agents_c.append(ChartistAgent(
                ag.id, cfg.M, cfg.S, cfg.B, rng, w0=ag.w))

        return agents_c, agents_f
