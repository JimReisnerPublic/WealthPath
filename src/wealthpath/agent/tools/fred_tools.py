"""Load the FRED MCP server tools as LangChain-compatible tools.

Uses langchain-mcp-adapters to bridge the MCP protocol with LangChain's
tool interface, allowing the LangGraph ReAct agent to call FRED tools
alongside its existing internal tools (cohort, projection, evaluate).

The FRED MCP server runs as a subprocess communicating over stdio —
the standard MCP transport for local servers. The MultiServerMCPClient
manages the subprocess lifecycle; callers must keep the returned client
alive and close it on shutdown.

Usage (in FastAPI lifespan):
    fred_tools, fred_client = await build_fred_tools(settings.fred_api_key)
    # ... use fred_tools in agent ...
    await fred_client.__aexit__(None, None, None)  # on shutdown
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)


async def build_fred_tools(fred_api_key: str) -> tuple[list, object | None]:
    """
    Spawn the FRED MCP server as a subprocess and return LangChain tools.

    Degrades gracefully in two situations:
    - FRED_API_KEY is empty: logs a warning, returns empty tool list.
    - langchain-mcp-adapters not installed: logs a warning, returns empty list.

    Returns:
        (tools, client) where tools is a list of LangChain BaseTool objects
        and client is the MultiServerMCPClient to keep alive. Client is None
        on graceful degradation.
    """
    if not fred_api_key:
        logger.warning(
            "FRED_API_KEY not set — FRED economic data tools will not be available. "
            "Get a free key at fred.stlouisfed.org and add it to .env."
        )
        return [], None

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        logger.warning(
            "langchain-mcp-adapters not installed — FRED tools unavailable. "
            "Run: pip install langchain-mcp-adapters"
        )
        return [], None

    client = MultiServerMCPClient(
        {
            "fred": {
                # Run the MCP server as a subprocess using the same Python interpreter.
                # stdio transport: client and server communicate over stdin/stdout.
                "command": sys.executable,
                "args": ["-m", "wealthpath.agent.tools.fred_mcp_server"],
                "env": {**os.environ, "FRED_API_KEY": fred_api_key},
                "transport": "stdio",
            }
        }
    )

    await client.__aenter__()
    tools = client.get_tools()
    logger.info(
        "FRED MCP server started — %d economic data tool(s) available.", len(tools)
    )
    return tools, client
