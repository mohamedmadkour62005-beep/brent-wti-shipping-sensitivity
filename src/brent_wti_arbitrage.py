"""Screen the Brent-WTI differential against transparent export-cost assumptions.

This is an educational logistics-arbitrage screen, not an executable trading
model. It deliberately separates an observable benchmark spread from assumed
costs so that every simplification can be challenged and changed.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv
from plotly.subplots import make_subplots

from eia_client import DEFAULT_ROUTE, EIADataError, fetch_series


DEFAULT_START_DATE = "2015-01-01"
WTI_SERIES_ID = "RWTC"
BRENT_SERIES_ID = "RBRTE"
BARRELS_PER_CARGO = 700_000


@dataclass(frozen=True)
class CostCase:
    """One transparent all-in cost assumption for the screening exercise."""

    name: str
    cushing_to_usgc_usd_per_bbl: float
    tanker_freight_usd_per_bbl: float
    terminal_insurance_finance_usd_per_bbl: float

    @property
    def total_usd_per_bbl(self) -> float:
        return (
            self.cushing_to_usgc_usd_per_bbl
            + self.tanker_freight_usd_per_bbl
            + self.terminal_insurance_finance_usd_per_bbl
        )


# These are deliberately illustrative—not Baltic Exchange observations or a
# freight quote. They make it possible to test sensitivity before adding a
# licensed/live freight data source.
COST_CASES = (
    CostCase("low_cost", 2.00, 1.50, 0.75),
    CostCase("base_cost", 2.00, 2.50, 0.75),
    CostCase("high_cost", 2.00, 4.00, 0.75),
)


def build_dataset(
    api_key: str | None = None,
    start_date: str = DEFAULT_START_DATE,
    route: str = DEFAULT_ROUTE,
) -> pd.DataFrame:
    """Fetch aligned daily EIA Brent and WTI spot benchmarks in dollars/bbl."""

    wti = fetch_series(
        route,
        WTI_SERIES_ID,
        start_date,
        api_key=api_key,
        expected_unit="$/BBL",
    ).rename("wti_cushing_usd_per_bbl")
    brent = fetch_series(
        route,
        BRENT_SERIES_ID,
        start_date,
        api_key=api_key,
        expected_unit="$/BBL",
    ).rename("brent_europe_usd_per_bbl")
    dataset = pd.concat([brent, wti], axis=1, join="inner").dropna().sort_index()
    if dataset.empty:
        raise EIADataError("Brent and WTI returned no overlapping daily observations.")
    return dataset


def add_export_screen(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate benchmark differential and sensitivity netbacks for each case.

    The result is a *screen*: a positive value says the two benchmarks exceed
    the stated cost assumption. It does not establish a tradable arbitrage.
    """

    required = {"brent_europe_usd_per_bbl", "wti_cushing_usd_per_bbl"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Cannot calculate export screen; missing: {sorted(missing)}")

    result = df.copy()
    result["brent_wti_spread_usd_per_bbl"] = (
        result["brent_europe_usd_per_bbl"] - result["wti_cushing_usd_per_bbl"]
    )
    for case in COST_CASES:
        prefix = case.name
        result[f"{prefix}_total_cost_usd_per_bbl"] = case.total_usd_per_bbl
        result[f"{prefix}_indicative_netback_usd_per_bbl"] = (
            result["brent_wti_spread_usd_per_bbl"] - case.total_usd_per_bbl
        )
        result[f"{prefix}_screen_positive"] = (
            result[f"{prefix}_indicative_netback_usd_per_bbl"] > 0
        )
    return result


def _episode_starts(flag: pd.Series) -> pd.Series:
    """Return the first observation of each consecutive true interval."""

    return flag & ~flag.shift(1, fill_value=False)


def summarise_screen(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create cost-case and base-case episode summaries without P&L claims."""

    rows: list[dict[str, float | int | str]] = []
    for case in COST_CASES:
        flag_column = f"{case.name}_screen_positive"
        netback_column = f"{case.name}_indicative_netback_usd_per_bbl"
        positive = df[flag_column]
        rows.append(
            {
                "cost_case": case.name,
                "total_cost_usd_per_bbl": case.total_usd_per_bbl,
                "positive_screen_days": int(positive.sum()),
                "positive_screen_day_rate_pct": 100 * float(positive.mean()),
                "positive_screen_episodes": int(_episode_starts(positive).sum()),
                "median_indicative_netback_usd_per_bbl": float(df[netback_column].median()),
                "maximum_indicative_netback_usd_per_bbl": float(df[netback_column].max()),
            }
        )

    base_case = next(case for case in COST_CASES if case.name == "base_cost")
    base_flag = df[f"{base_case.name}_screen_positive"]
    starts = _episode_starts(base_flag)
    episode_id = starts.cumsum().where(base_flag)
    episodes: list[dict[str, float | int | pd.Timestamp]] = []
    for identifier, group in df.loc[base_flag].groupby(episode_id.loc[base_flag]):
        episodes.append(
            {
                "episode_number": int(identifier),
                "start_date": group.index.min(),
                "end_date": group.index.max(),
                "observations": int(len(group)),
                "max_indicative_netback_usd_per_bbl": float(
                    group[f"{base_case.name}_indicative_netback_usd_per_bbl"].max()
                ),
                "mean_indicative_netback_usd_per_bbl": float(
                    group[f"{base_case.name}_indicative_netback_usd_per_bbl"].mean()
                ),
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(episodes)


def plot_export_screen(df: pd.DataFrame, output_path: Path) -> None:
    """Write a standalone chart comparing the observable spread and netbacks."""

    required = {
        "brent_wti_spread_usd_per_bbl",
        "base_cost_indicative_netback_usd_per_bbl",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Cannot plot export screen; missing: {sorted(missing)}")

    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(
        go.Scatter(
            x=df.index,
            y=df["brent_wti_spread_usd_per_bbl"],
            name="Brent − WTI benchmark spread",
            line={"color": "#1f77b4", "width": 2.3},
            hovertemplate="%{x|%d %b %Y}<br>Brent − WTI: $%{y:.2f}/bbl<extra></extra>",
        ),
        secondary_y=False,
    )
    for case, colour, dash in zip(
        COST_CASES,
        ["#54a24b", "#e45756", "#f58518"],
        ["dot", "solid", "dash"],
        strict=True,
    ):
        figure.add_trace(
            go.Scatter(
                x=df.index,
                y=df[f"{case.name}_indicative_netback_usd_per_bbl"],
                name=f"{case.name.replace('_', ' ').title()} netback (${case.total_usd_per_bbl:.2f}/bbl cost)",
                line={"color": colour, "width": 2 if case.name == "base_cost" else 1.4, "dash": dash},
                hovertemplate=(
                    "%{x|%d %b %Y}<br>Indicative netback: "
                    "$%{y:.2f}/bbl<extra></extra>"
                ),
            ),
            secondary_y=True,
        )

    base_starts = _episode_starts(df["base_cost_screen_positive"])
    starts = df.loc[base_starts]
    figure.add_trace(
        go.Scatter(
            x=starts.index,
            y=starts["base_cost_indicative_netback_usd_per_bbl"],
            name="Base-cost screen episode start",
            mode="markers",
            marker={"color": "#7f3c8d", "size": 8, "symbol": "triangle-up"},
            hovertemplate=(
                "%{x|%d %b %Y}<br>Base-cost screen first turns positive"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
    )
    figure.update_layout(
        title="Brent–WTI Export Screen: US Gulf Coast to Europe Cost Sensitivity",
        template="plotly_white",
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        margin={"l": 70, "r": 70, "t": 105, "b": 60},
    )
    figure.update_xaxes(title_text="Date")
    figure.update_yaxes(title_text="Benchmark spread ($/bbl)", secondary_y=False)
    figure.update_yaxes(
        title_text="Indicative netback after assumed costs ($/bbl)",
        zeroline=True,
        zerolinecolor="#666666",
        secondary_y=True,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(output_path, include_plotlyjs=True, full_html=True)


def print_report(summary: pd.DataFrame) -> None:
    """Print an auditable screen-frequency report, not a financial backtest."""

    print("Brent-WTI logistics-arbitrage screening report")
    print("  Positive screen = Brent - WTI exceeds stated all-in cost assumption")
    for row in summary.itertuples(index=False):
        print(
            f"  {row.cost_case} (${row.total_cost_usd_per_bbl:.2f}/bbl): "
            f"{row.positive_screen_days:,} days "
            f"({row.positive_screen_day_rate_pct:.1f}%), "
            f"{row.positive_screen_episodes:,} episodes"
        )
    print("  Screen only - not an executable arbitrage, P&L, or return backtest.")


def parse_args() -> argparse.Namespace:
    """Parse the command-line interface."""

    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Screen Brent-WTI benchmark spreads against assumed export costs."
    )
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--api-key", help="Overrides EIA_API_KEY in .env/environment.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "output",
        help="Folder for exported data, screen episodes, and HTML chart.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the EIA fetch, sensitivity calculations, and exports."""

    load_dotenv()
    args = parse_args()
    dataset = add_export_screen(
        build_dataset(api_key=args.api_key, start_date=args.start_date)
    )
    summary, episodes = summarise_screen(dataset)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    data_path = args.output_dir / "brent_wti_export_screen_data.csv"
    summary_path = args.output_dir / "brent_wti_export_screen_summary.csv"
    episodes_path = args.output_dir / "brent_wti_base_cost_episodes.csv"
    chart_path = args.output_dir / "brent_wti_export_screen.html"
    dataset.reset_index().to_csv(data_path, index=False, float_format="%.4f")
    summary.to_csv(summary_path, index=False, float_format="%.4f")
    episodes.to_csv(episodes_path, index=False, float_format="%.4f")
    plot_export_screen(dataset, chart_path)
    print_report(summary)
    print(f"\nSaved {len(dataset):,} observations to {data_path}")
    print(f"Saved sensitivity summary to {summary_path}")
    print(f"Saved base-cost episodes to {episodes_path}")
    print(f"Saved interactive chart to {chart_path}")


if __name__ == "__main__":
    try:
        main()
    except EIADataError as error:
        raise SystemExit(f"ERROR: {error}") from error
