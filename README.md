# Automated Weather Prediction Market Trading Bot

An autonomous quantitative trading bot that exploits systematic mispricing in Polymarket weather temperature markets by combining professional-grade meteorological forecast models with statistical post-processing to generate calibrated probability estimates.

---

## Motivation

Polymarket hosts binary prediction markets on daily maximum temperature across cities worldwide. Prices in these markets are set by retail participants who lack access to ensemble weather forecasts and have no systematic model for translating forecast uncertainty into calibrated probabilities.

The ECMWF IFS (Integrated Forecasting System) produces a 51-member ensemble updated four times daily at 00, 06, 12, and 18 UTC. These ensembles quantify forecast uncertainty through ensemble spread — a signal that retail market participants do not price in. The result is a systematic edge: when the ECMWF IFS ensemble assigns materially different probabilities to a temperature bucket than the current market price, the model is likely right and the market is likely wrong.

The edge is strongest in secondary cities (Kuala Lumpur, Melbourne) where market depth is thin and bot competition is low, relative to high-liquidity markets like New York or London.

---

## System Architecture

The system is built on [NautilusTrader](https://nautilustrader.io), a high-performance live trading engine, using a message-bus actor architecture where each component is independently responsible for one stage of the pipeline.

```
┌─────────────────────────────────────────────────────────────────┐
│                        60-Minute Cycle                          │
│                                                                 │
│  Open-Meteo API          IEM / METAR                            │
│  ECMWF IFS      ──────►  Historical    ──────►  PostgreSQL DB   │
│  51-member ENS          Observations            (Training Data) │
│       │                                              │          │
│       ▼                                              ▼          │
│  ForecastIngestor    ObservationIngestor    CalibratorActor     │
│       │                    │                EMOS L-BFGS-B fit   │
│       └────────┬───────────┘                     │              │
│                ▼                                 ▼              │
│          StateActor  ◄──────── Calibrated params (a,b,c,d)     │
│                │                                                │
│                ▼                                                │
│          PredictorActor                                         │
│          Skew-Normal CDF → bucket probabilities                 │
│                │                                                │
│                ▼                                                │
│          WeatherStrategy                                        │
│          Edge detection + Kelly sizing                          │
│                │                                                │
│                ▼                                                │
│          Polymarket CLOB  (limit GTC orders)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## ML Techniques

### Ensemble Model Output Statistics (EMOS) — Primary Model

Raw ECMWF IFS ensemble forecasts are systematically biased and under/overdispersed. EMOS is a statistical post-processing regression technique that corrects these errors by fitting a parametric predictive distribution to the ensemble output using historical forecast–observation pairs.

The predictive distribution used is a **Skew-Normal**, parameterised by:

```
μ_calibrated  =  a + b · μ_ensemble          (bias-corrected mean)
σ²_calibrated =  c + d · σ²_ensemble         (spread-corrected variance)
α             =  α_ensemble                  (skewness, passed through)
```

Parameters `a, b, c, d` are fitted per city per forecast lead day by minimising the **negative log-likelihood** of the observed temperatures under the predictive distribution, using the L-BFGS-B optimiser via `scipy.optimize.minimize`:

```python
log_likelihood = skewnorm.logpdf(actuals, a=alpha, loc=mu, scale=sigma)
loss = -log_likelihood.sum()
```

**Training setup:**
| Parameter | Value |
|---|---|
| Lookback window | 90 days |
| Minimum training samples | 30 observations |
| Refit schedule | Weekly (Sunday 02:00 UTC) |
| Optimiser | L-BFGS-B |
| Initial values | `a=0, b=1, c=1.23 (°C) / 4.0 (°F), d=1` |
| Bounds on `b` | `[0.1, 3.0]` |
| Bounds on `c, d` | `[c_init, ∞), [0.05, ∞)` |

The initialisation at `b=1, d=1` represents the identity mapping (raw ensemble), so the model degrades gracefully to uncalibrated ensemble output when data is insufficient.

**Why EMOS over a neural approach:** EMOS produces a full calibrated predictive distribution — not just a point estimate — which is exactly what is needed to compute the probability that the maximum temperature falls within a specific bucket range. It is also interpretable, sample-efficient (works with 30 observations), and robust to distribution shift.

### Probability Estimation

Once EMOS parameters are fitted, the probability assigned to each market bucket `[T_low, T_high]` is computed analytically as a CDF integral over the calibrated Skew-Normal distribution:

```python
P(bucket) = skewnorm.cdf(T_high, a=α, loc=μ, scale=σ) 
          - skewnorm.cdf(T_low,  a=α, loc=μ, scale=σ)
```

This produces a full probability distribution across all temperature buckets for an event, which is then compared against live Polymarket ask prices to identify mispriced contracts.

### Additional Engines (Built, Not Yet Wired)

| Engine | File | Purpose |
|---|---|---|
| KDE | `src/predictors/engine/kde.py` | Non-parametric density estimation over ensemble members using Silverman bandwidth; alternative to the Skew-Normal when forecast distributions are multi-modal |
| IDR | `src/predictors/engine/idr.py` | Isotonic Distribution Regression via `sklearn`; monotone calibration as an alternative post-processor |

---

## Benchmark Statistics

EMOS is a well-established technique in numerical weather prediction. On operational ensemble systems (ECMWF, GFS), published benchmarks show:

- **10–30% CRPS improvement** over raw ensemble output after calibration (Gneiting et al., 2005)
- **Coverage rates within 2–3% of nominal** for 80% and 90% prediction intervals
- Outperforms climatological baselines at lead times of 1–7 days

The calibration objective — NLL minimisation — is equivalent to optimising the sharpness of the predictive distribution subject to calibration, which directly maximises the information value of the probability estimates used for trading.

The trading edge threshold is set at **8% divergence** between model probability and market ask price, a conservative filter that targets high-confidence mispricing rather than marginal signals.

---

## Trading Strategy

### Signal Generation

Two tactics operate simultaneously per market:

**Best Bet** — Buy YES when the model assigns materially higher probability than the market price:
```
edge = P_model(YES) - ask_YES
fire if edge ≥ 0.08
```

**Fade the Impossible** — Buy NO when the model assigns near-zero probability to the event:
```
fire if P_model(YES) ≤ 0.02 and (P_model(NO) - ask_NO) ≥ 0.08
```

### Position Sizing

Positions are sized using the **fractional Kelly criterion**:

```
f*      = edge / (1 - price)       (full Kelly fraction)
stake   = min(f* × 0.50 × balance, $10.00)
```

Kelly fraction is set to 50% of full Kelly to reduce variance. The $10 hard cap per trade limits single-bet exposure to 10% of the starting bankroll. Sizing uses the live free USDC balance from the NautilusTrader portfolio, so stakes automatically shrink after losses and grow after wins.

---

## Autonomy

Once started, the system requires no human intervention:

- **60-minute timer** triggers forecast refresh, prediction, and strategy evaluation
- **Weekly EMOS refit** keeps calibration current as seasonal patterns shift
- **Quote tick subscriptions** maintain live bid/ask across all active markets
- **Duplicate checks** prevent re-entry into positions already held
- **Fill and resolution logging** records every trade entry and P&L outcome

---

## Stack

| Component | Technology |
|---|---|
| Execution engine | NautilusTrader 1.227 |
| Exchange | Polymarket (CLOB) |
| Forecast data | Open-Meteo API (ECMWF IFS `ecmwf_ifs025`, 51-member ENS, free) |
| Observation data | IEM (Iowa Environmental Mesonet), METAR |
| Statistical modelling | SciPy, NumPy, scikit-learn |
| Database | PostgreSQL (SQLAlchemy) |
| Language | Python 3.14 |
