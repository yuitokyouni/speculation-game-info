"""Quick smoke test — run baseline for a short period."""
from src.utils.config import SimConfig
from src.simulation import Simulation

cfg = SimConfig(
    N=300, T=3000, M=3,
    f_sensitivity=0.05,
    n_c_init=0.9,
    switching=False,
    seed=42,
)

print(f"Running smoke test: N={cfg.N}, T={cfg.T}, nc={cfg.n_c_init}")
res = Simulation(cfg).run()

print(f"Price range: [{res.price.min():.1f}, {res.price.max():.1f}]")
print(f"NAV deviation mean: {((res.price - res.nav) / res.nav * 100).mean():.2f}%")
print(f"nc range: [{res.nc.min():.3f}, {res.nc.max():.3f}]")
print("Smoke test OK.")
