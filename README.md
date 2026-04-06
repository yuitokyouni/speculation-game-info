# J-REIT ABM

Agent-Based Model of the J-REIT market extending Katahira & Chen (2019) Speculation Game.

## Research Question

When Chartist ratio n_c exceeds a critical threshold, does J-REIT price
deviate from NAV in a phase-transition-like manner, and does this generate
the same pattern seen in Konishi (2025) — where technical indicators (TSF,
ATR, DMI) become highly predictive?

## Model Structure

```
N agents = n_c * N Chartists + (1 - n_c) * N Fundamentalists

Chartists   : Speculation Game (Katahira & Chen 2019)
              - Strategy table over M-period price history (quantized by C)
              - Cognitive price P(t) for strategy evaluation
              - Round-trip trading constraint

Fundamentalists : NAV-based mean-reverting traders (continuous restoring force)
              - demand = sensitivity * (NAV - price) / NAV * max_qty
              - Real market price for wealth update

Strategy switching (Brock & Hommes 1998):
              n_c(t) = softmax(beta * U_c(t-1)) over {Chartist, Fundamentalist}
```

## Directory Structure

```
src/
  agents/
    chartist.py          # Speculation Game agent
    fundamentalist.py    # NAV-based continuous restoring force agent
  market/
    engine.py            # MarketEngine (price formation, quantization)
    nav.py               # NAV process (fixed or random walk)
  analysis/
    stylized_facts.py    # Katahira (2019) Table 2 verification
    validation.py        # TSF/ATR/ADX + LightGBM pipeline (nc vs accuracy)
  utils/
    config.py            # SimConfig dataclass
    history.py           # Quantized price history H(t)
  simulation.py          # Main loop + SimResult
  run.py                 # Entry point with 4-panel plot
tests/
notebooks/
results/
```

## Quick Start

```bash
pip install -e .
python smoke_test.py
python -m src.run --N 500 --T 10000 --beta 5.0 --nc 0.5
```

## Parameters

| Symbol | Description | Default |
|--------|-------------|---------|
| N | Total agents | 1000 |
| M | Memory length | 5 |
| S | Strategies per agent | 2 |
| B | Board lot | 9 |
| C | Cognitive threshold | 3.0 |
| beta | Intensity of choice | 2.0 |
| NAV | Fixed fundamental value | 1000.0 |
| f_sensitivity | Fundamentalist restoring force | 0.5 |
| n_c_init | Initial Chartist ratio | 0.5 |
| T | Time steps | 50000 |

## References

- Katahira, K., Chen, Y., et al. (2019). Physica A, 524, 503-518.
- Brock, W. A., & Hommes, C. H. (1998). Journal of Economic Dynamics and Control, 22, 1235-1274.
- Konishi, K. (2025). SMTRI Report, March 3.
