"""Minimal EIA APIv2 client shared by the Brent-WTI screening module."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests


API_BASE_URL = "https://api.eia.gov/v2"
DEFAULT_ROUTE = "petroleum/pri/spt"
EIA_BROWSER_URL = "https://www.eia.gov/opendata/browser/petroleum/pri/spt"
PAGE_SIZE = 5_000
REQUEST_TIMEOUT_SECONDS = 30


class EIADataError(RuntimeError):
    """Raised when the EIA API cannot provide a requested series."""


def _api_key(api_key: str | None) -> str:
    key = api_key or os.getenv("EIA_API_KEY")
    if not key:
        raise EIADataError(
            "No EIA API key found. Set EIA_API_KEY in .env or pass --api-key. "
            "Register at https://www.eia.gov/opendata/."
        )
    return key


def _failure(series_id: str, reason: str) -> EIADataError:
    return EIADataError(
        f"Could not retrieve EIA series '{series_id}': {reason}. "
        f"Check the EIA API browser: {EIA_BROWSER_URL}"
    )


def fetch_series(
    route: str,
    series_id: str,
    start_date: str,
    *,
    api_key: str | None = None,
    expected_unit: str | None = None,
) -> pd.Series:
    """Fetch all daily observations for a series, following EIA pagination."""

    endpoint = f"{API_BASE_URL}/{route.strip('/')}/data/"
    rows: list[dict[str, Any]] = []
    offset = 0
    total: int | None = None
    while True:
        params = [
            ("api_key", _api_key(api_key)),
            ("frequency", "daily"),
            ("data[0]", "value"),
            ("facets[series][]", series_id),
            ("start", start_date),
            ("length", str(PAGE_SIZE)),
            ("offset", str(offset)),
            ("sort[0][column]", "period"),
            ("sort[0][direction]", "asc"),
        ]
        try:
            response = requests.get(endpoint, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise _failure(series_id, str(exc)) from exc

        api_response = payload.get("response", {})
        page = api_response.get("data", [])
        if not isinstance(page, list):
            raise _failure(series_id, "the response did not contain a data list")
        if total is None:
            try:
                total = int(api_response.get("total", 0))
            except (TypeError, ValueError) as exc:
                raise _failure(series_id, "the response had an invalid total") from exc
        rows.extend(page)
        if not page or len(rows) >= total or len(page) < PAGE_SIZE:
            break
        offset += len(page)

    if not rows:
        raise _failure(series_id, f"no daily rows were returned on or after {start_date}")
    frame = pd.DataFrame(rows)
    if not {"period", "value", "units"}.issubset(frame.columns):
        raise _failure(series_id, "required period, value, or units fields were missing")
    if expected_unit and set(frame["units"].dropna().astype(str)) != {expected_unit}:
        raise _failure(series_id, f"expected unit {expected_unit} was not returned")
    frame["date"] = pd.to_datetime(frame["period"], errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["date", "value"])
    if frame.empty:
        raise _failure(series_id, "all returned values were invalid")
    result = (
        frame.drop_duplicates(subset="date", keep="last")
        .sort_values("date")
        .set_index("date")["value"]
        .astype(float)
    )
    result.index.name = "date"
    return result
