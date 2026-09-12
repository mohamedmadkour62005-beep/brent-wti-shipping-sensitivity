# Brent-WTI Spread: USGC-to-Europe Shipping-Cost Sensitivity

## Purpose

This module asks a narrow, practical question: after applying a deliberately simple cost estimate, when did the observable **Brent minus WTI** benchmark spread exceed a notional cost of moving crude from the U.S. Gulf Coast (USGC) to Europe?

It is a logistics-arbitrage **screen**, not an executable arbitrage model, price forecast, or trading strategy. The output is designed to show how a market relationship can be tested against physical frictions, then challenged with sensitivities.

## Method

Daily EIA spot-price series are aligned by date:

| Benchmark | EIA series | Delivery basis |
|---|---|---|
| WTI | `RWTC` | Cushing, Oklahoma FOB |
| Brent | `RBRTE` | Europe FOB |

```text
Benchmark spread = Brent − WTI
Indicative export netback = Benchmark spread − assumed all-in cost
```

The assumed all-in cost is not sourced from live Baltic Exchange assessments. It is an explicit placeholder for an illustrative 700 kbbl cargo: Cushing-to-USGC transport ($2.00/bbl), tanker freight ($1.50, $2.50, or $4.00/bbl), and terminal/insurance/financing allowance ($0.75/bbl). The three total-cost cases are therefore $4.25, $5.25, and $6.75/bbl.

## Result: 2015 to 12 September 2026 run

| All-in cost case | Positive-screen days | Share of observations | Distinct episodes | Median indicative netback |
|---|---:|---:|---:|---:|
| Low: $4.25/bbl | 1,297 | 44.7% | 115 | -$0.40/bbl |
| Base: $5.25/bbl | 937 | 32.3% | 121 | -$1.40/bbl |
| High: $6.75/bbl | 525 | 18.1% | 94 | -$2.90/bbl |

The base screen turning positive on roughly one-third of dates does **not** mean one-third of dates offered a trade. It only means the benchmark differential exceeded these stated placeholder costs. The lower median netback across the full sample also highlights that the screen is sensitive to a small number of wide-dislocation episodes.

## Interpretation and limits

A positive reading is a prompt to investigate, not a deal ticket. WTI Cushing and Brent Europe are different benchmarks, locations, and timing conventions. A real cargo decision would require current cargo-specific freight and bunker costs, loading window, vessel availability, quality/assay adjustment, pipeline and terminal capacity, destination differential, credit, inventory financing, hedging basis, demurrage, taxes, sanctions/compliance, and price risk during transit. The route itself may be commercially inferior to alternatives.

That restraint is the point of the exercise: the model makes the logistics assumption visible, rather than hiding it behind an apparently precise number. The next credible enhancement would be to replace the assumed freight input with a dated public or licensed USGC-to-Europe tanker assessment while retaining the same sensitivity framework.

## Files

- `output/brent_wti_export_screen.html` — interactive chart; purple triangles mark the first day of a positive base-cost episode.
- `output/brent_wti_export_screen_data.csv` — daily benchmarks, all costs, netbacks, and boolean screens.
- `output/brent_wti_export_screen_summary.csv` — the table above in machine-readable form.
- `output/brent_wti_base_cost_episodes.csv` — consecutive positive base-cost periods collapsed to one episode.

Data source: [EIA Open Data](https://www.eia.gov/opendata/). The EIA identifies the 3:2:1 crack spread as a refinery-yield approximation and publishes the daily spot-price data used here; this module uses the same EIA petroleum spot-price route for the two crude benchmarks.
