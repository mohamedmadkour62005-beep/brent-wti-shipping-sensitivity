# Brent-WTI Shipping-Cost Sensitivity

An explainable physical-market screen that compares the daily **Brent-WTI benchmark spread** with transparent, illustrative US Gulf Coast (USGC)-to-Europe movement-cost assumptions.

It complements a refinery-margin project by focusing on logistics and arbitrage conditions: when does the benchmark price difference exceed a rough assumed cost of getting crude from Cushing through the USGC to Europe?

> This is a screening exercise—not an executable arbitrage model, trade recommendation, P&L calculation, or return backtest.

## Method

The module downloads daily EIA spot prices from `petroleum/pri/spt`:

| Benchmark | EIA series ID | Published basis |
|---|---|---|
| WTI | `RWTC` | Cushing, Oklahoma FOB |
| Brent | `RBRTE` | Europe FOB |

```text
Benchmark spread = Brent − WTI
Indicative netback = Benchmark spread − assumed all-in cost
```

The all-in cost is explicitly a sensitivity input, rather than a claim to use live freight assessments:

| Case | Cushing-to-USGC | Tanker freight | Terminal / insurance / finance | Total |
|---|---:|---:|---:|---:|
| Low | $2.00/bbl | $1.50/bbl | $0.75/bbl | $4.25/bbl |
| Base | $2.00/bbl | $2.50/bbl | $0.75/bbl | $5.25/bbl |
| High | $2.00/bbl | $4.00/bbl | $0.75/bbl | $6.75/bbl |

A positive screen says only that the two EIA benchmarks exceed the stated cost assumption. It is a prompt for cargo-specific investigation, not proof of a feasible trade.

## Run it

1. Register for a free key at [EIA Open Data](https://www.eia.gov/opendata/).
2. Copy `.env.example` to `.env` and replace the placeholder with the key.
3. Create an environment and install dependencies:

   ```powershell
   py -3.14 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. Run the screen:

   ```powershell
   python src\brent_wti_arbitrage.py
   ```

   Optionally choose another start date:

   ```powershell
   python src\brent_wti_arbitrage.py --start-date 2018-01-01
   ```

## Outputs

The script writes a self-contained interactive chart and three CSV files to `output/`:

```text
brent_wti_export_screen.html
brent_wti_export_screen_data.csv
brent_wti_export_screen_summary.csv
brent_wti_base_cost_episodes.csv
```

Purple triangles in the chart identify the first date of a consecutive positive base-cost screen episode. Read the [one-page shipping sensitivity note](notes/brent_wti_shipping_sensitivity_note.md) for results and limitations.

## Essential limitations

The model compares different benchmarks, locations, and timing conventions. Real export economics require contemporaneous vessel and bunker quotes, loading windows, quality/assay differentials, pipeline and terminal capacity, destination price differentials, hedging basis, inventory finance, demurrage, taxes, sanctions/compliance, and transit price risk. The selected route may not be commercially optimal.

## Tests

```powershell
python -m unittest discover -s tests -v
```
