from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from wealthpath.agent.llm_factory import build_llm
from wealthpath.agent.planning_agent import build_planning_agent
from wealthpath.agent.tools.cohort_tools import build_cohort_tools
from wealthpath.agent.tools.evaluate_tools import build_evaluate_tools
from wealthpath.agent.tools.fred_tools import build_fred_tools
from wealthpath.agent.tools.projection_tools import build_projection_tools
from wealthpath.api.routers import chat, cohort, evaluate, health, projection
from wealthpath.dependencies import (
    get_scf_service,
    get_settings,
    get_simulation_engine,
    get_surrogate_model_service,
)
from wealthpath.services.ai_engine import AIEngine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage async resources that cannot be created inside @lru_cache.

    The FRED MCP server runs as a subprocess (stdio transport) and must be
    started with await, making it incompatible with the synchronous @lru_cache
    pattern used for the other services. Building the AI engine here also
    consolidates all startup logic in one place.
    """
    settings = get_settings()
    llm = build_llm(settings)

    fred_tools, fred_client = await build_fred_tools(settings.fred_api_key)

    agent = None
    if llm is not None:
        tools = (
            build_cohort_tools(get_scf_service())
            + build_projection_tools(get_simulation_engine())
            + build_evaluate_tools(
                get_surrogate_model_service(), get_simulation_engine()
            )
            + fred_tools
        )
        agent = build_planning_agent(llm, tools)
        logger.info(
            "WealthPath agent ready with %d tool(s) (%d from FRED MCP server).",
            len(tools),
            len(fred_tools),
        )

    app.state.ai_engine = AIEngine(llm=llm, agent=agent)

    yield

    if fred_client is not None:
        await fred_client.__aexit__(None, None, None)
        logger.info("FRED MCP server stopped.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="WealthPath",
        description="AI-powered income and wealth projection planner",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(health.router)
    app.include_router(projection.router)
    app.include_router(cohort.router)
    app.include_router(chat.router)
    app.include_router(evaluate.router)
    return app


app = create_app()
