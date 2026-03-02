"""FRED Economic Data MCP Server.

Exposes Federal Reserve economic indicators as MCP tools, allowing any
MCP-compatible client (WealthPath, Claude Desktop, Claude Code, etc.) to
fetch live data from the Federal Reserve Economic Data (FRED) API.

Standalone usage:
    python -m wealthpath.agent.tools.fred_mcp_server

Requires:
    FRED_API_KEY environment variable (free at fred.stlouisfed.org)
"""

from __future__ import annotations

import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("fred-economic-data")

_FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

_TREASURY_SERIES = {
    "2y": "DGS2",
    "5y": "DGS5",
    "10y": "DGS10",
    "30y": "DGS30",
}


async def _latest_fred_value(series_id: str) -> str:
    """Fetch the most recent observation for a FRED series."""
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        return "FRED_API_KEY not configured"

    params = {
        "series_id": series_id,
        "api_key": api_key,
        "limit": 1,
        "sort_order": "desc",
        "file_type": "json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(_FRED_BASE, params=params, timeout=10.0)
        response.raise_for_status()

    observations = response.json().get("observations", [])
    if not observations:
        return f"No data available for series {series_id}"

    obs = observations[0]
    return f"{obs['value']} (as of {obs['date']})"


@mcp.tool()
async def get_current_inflation_rate() -> str:
    """
    Get the current US inflation rate index (CPI for All Urban Consumers)
    from the Federal Reserve Economic Data (FRED) database.

    Use this when the user asks about inflation, cost of living increases,
    purchasing power, or when grounding retirement projections in current
    economic conditions. The CPI value reflects actual current inflation,
    not a historical assumption.
    """
    result = await _latest_fred_value("CPIAUCSL")
    return f"Current US CPI (Consumer Price Index, All Urban Consumers): {result}"


@mcp.tool()
async def get_treasury_yield(maturity: str = "10y") -> str:
    """
    Get the current US Treasury constant maturity yield from FRED.

    Use this for safe withdrawal rate discussions, bond vs. equity allocation
    advice, or when comparing expected investment returns to the current
    risk-free rate. The 10-year yield is the standard benchmark for
    long-term financial planning.

    Args:
        maturity: Treasury maturity period. One of: 2y, 5y, 10y, 30y.
                  Defaults to 10y (the most common planning benchmark).
    """
    series_id = _TREASURY_SERIES.get(maturity, "DGS10")
    result = await _latest_fred_value(series_id)
    return f"US {maturity} Treasury constant maturity yield: {result}%"


@mcp.tool()
async def get_fed_funds_rate() -> str:
    """
    Get the current Federal Funds effective rate from FRED.

    Use this when discussing interest rates, high-yield savings account
    yields, money market returns, or the overall monetary policy
    environment affecting retirement planning decisions.
    """
    result = await _latest_fred_value("FEDFUNDS")
    return f"Federal Funds effective rate: {result}%"


if __name__ == "__main__":
    mcp.run()
