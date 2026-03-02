from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.messages import SystemMessage

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are WealthPath, a retirement readiness assistant. You explain how projections
are calculated and run scenario analyses — you are not a licensed financial adviser,
broker-dealer, or tax professional.

When answering a question:
1. Call relevant tools to ground your response in real data.
2. Explain results in plain language — avoid financial jargon.
3. Offer scenario comparisons rather than prescriptive recommendations.
   Good: "Retiring at 63 instead of 60 changes your score from 68% to 74%."
   Avoid: "You should delay retirement."
4. Be encouraging but realistic about outcomes.

Boundary rule: If a user asks which specific funds, securities, or products to
invest in, or asks for tax advice (Roth conversions, withdrawal sequencing, etc.),
decline that specific part with something like: "I can model how changing your
equity allocation affects your score, but for specific investment product or tax
recommendations you'd want to speak with a CFP or RIA." Then offer to run the
relevant scenario instead.
"""


def build_planning_agent(
    llm: BaseChatModel,
    tools: list,
) -> CompiledStateGraph:
    """
    Build a LangGraph ReAct agent — the Python ecosystem equivalent of AutoGen.

    AutoGen pattern (C# / Python):
        agent = AssistantAgent("planner", llm, plugins=[cohort_plugin, projection_plugin])
        await agent.initiate_chat(user_proxy, message=question)

    LangGraph equivalent:
        agent = create_react_agent(llm, tools, prompt=system_message)
        result = await agent.ainvoke({"messages": [HumanMessage(content=question)]})

    The ReAct (Reason + Act) loop LangGraph runs automatically:
        1. LLM receives the conversation + tool schemas.
        2. LLM either calls a tool (ToolMessage added to state) or gives a final answer.
        3. If a tool was called, output is appended and the loop goes back to step 1.
        4. Loop ends when the LLM responds without calling any tools.

    Unlike AutoGen's explicit multi-agent conversation pattern, LangGraph represents
    this as a state graph: [START] → agent_node ⇄ tools_node → [END].
    The graph is compiled once and reused for every request.
    """
    from langgraph.prebuilt import create_react_agent

    system_message = SystemMessage(content=_SYSTEM_PROMPT)
    # state_modifier was renamed to prompt in LangGraph 0.2+
    agent = create_react_agent(llm, tools, prompt=system_message)
    logger.info("LangGraph ReAct agent built with %d tool(s).", len(tools))
    return agent
