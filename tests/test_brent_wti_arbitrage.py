"""Regression tests for the transparent Brent-WTI export screen."""

from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from brent_wti_arbitrage import (  # noqa: E402
    add_export_screen,
    summarise_screen,
)


class BrentWtiExportScreenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prices = pd.DataFrame(
            {
                "brent_europe_usd_per_bbl": [90.0, 88.0, 100.0],
                "wti_cushing_usd_per_bbl": [80.0, 85.0, 90.0],
            },
            index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
        )

    def test_screen_applies_explicit_cost_cases(self) -> None:
        result = add_export_screen(self.prices)
        self.assertEqual(result.iloc[0]["brent_wti_spread_usd_per_bbl"], 10.0)
        self.assertEqual(result.iloc[0]["base_cost_total_cost_usd_per_bbl"], 5.25)
        self.assertEqual(
            result.iloc[0]["base_cost_indicative_netback_usd_per_bbl"], 4.75
        )
        self.assertTrue(result.iloc[0]["base_cost_screen_positive"])
        self.assertFalse(result.iloc[1]["base_cost_screen_positive"])

    def test_summary_collapses_consecutive_positive_days_to_episode(self) -> None:
        result = add_export_screen(self.prices)
        summary, episodes = summarise_screen(result)
        base = summary.loc[summary["cost_case"] == "base_cost"].iloc[0]
        self.assertEqual(base["positive_screen_days"], 2)
        self.assertEqual(base["positive_screen_episodes"], 2)
        self.assertEqual(len(episodes), 2)


if __name__ == "__main__":
    unittest.main()
