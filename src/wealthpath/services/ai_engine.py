from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from wealthpath.models.chat import ChatRequest, ChatResponse

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)

# Maps tool function names → human-readable status shown in the chat UI while
# the agent waits for a tool result.
_TOOL_STATUS: dict[str, str] = {
    "get_cohort_median_income": "Looking up cohort income data...",
    "get_cohort_median_net_worth": "Looking up cohort net worth data...",
    "evaluate_retirement_plan": "Running plan evaluation...",
    "get_median_projection": "Running retirement projection...",
}


def _build_lc_messages(request: ChatRequest) -> list:
    """
    Convert WealthPath ChatRequest messages to LangChain message objects.

    Injects a comprehensive context header into the first user message so the
    agent is grounded in the user's specific situation — household profile,
    retirement plan inputs, current score, and SHAP key drivers.

    SK equivalent:  ChatHistory.add_system_message() + ChatHistory.add_user_message()
    LC equivalent:  plain list of HumanMessage / AIMessage — messages are first-class,
                    not wrapped in a registry or session object.
    """
    h = request.household
    ctx = request.context or {}

    lines: list[str] = [
        "[User household]",
        f"Age: {h.age} | Household size: {h.household_size}",
        f"Income: ${h.income:,.0f}/yr | Net worth: ${h.net_worth:,.0f}"
        f" | Investable savings: ${h.investable_savings:,.0f}",
    ]

    # Retirement plan inputs (from EvaluationRequest, forwarded via context)
    plan_parts: list[str] = []
    ret_age = ctx.get("planned_retirement_age")
    life_exp = ctx.get("life_expectancy")
    spending = ctx.get("annual_spending_retirement")
    ss = ctx.get("social_security_annual")
    savings_rate = ctx.get("savings_rate")
    equity_frac = ctx.get("equity_fraction")

    if ret_age is not None:
        plan_parts.append(f"Planned retirement age: {int(ret_age)}")
    if life_exp is not None:
        plan_parts.append(f"Life expectancy: {int(life_exp)}")
    if spending is not None:
        plan_parts.append(f"Annual spending in retirement: ${spending:,.0f}/yr")
    if ss is not None:
        plan_parts.append(f"Guaranteed income (SS + pension + other, combined): ${ss:,.0f}/yr (SS is time-weighted if it starts after retirement age — raw SS × years_receiving_SS / years_in_retirement)")
    if savings_rate is not None:
        plan_parts.append(f"Savings rate: {savings_rate:.0%}")
    if equity_frac is not None:
        plan_parts.append(f"Equity allocation: {equity_frac:.0%}")
    if plan_parts:
        lines.append("")
        lines.append("[Retirement plan]")
        lines.extend(plan_parts)

    # Current score
    prob = ctx.get("success_probability")
    label = ctx.get("success_label")
    if prob is not None:
        score_str = f"[Current retirement score: {prob:.0%}"
        if label:
            score_str += f" — {label}"
        lines.append("")
        lines.append(score_str + "]")

    # SHAP key drivers — tell the agent what is actually driving the score
    drivers = ctx.get("top_drivers", [])
    if drivers:
        lines.append("")
        lines.append("[Key drivers of your score]")
        for d in drivers:
            pp = round(abs(d.get("shap_value", 0)) * 100)
            sign = "+" if d.get("direction") == "positive" else "−"
            lines.append(f"  {d.get('display_name', d.get('feature', ''))}: {sign}{pp}pp")

    context_header = "\n".join(lines)

    lc_messages: list = []
    for i, msg in enumerate(request.messages):
        if msg.role == "user":
            # Prepend context to the first user message only; subsequent turns
            # already carry it through the conversation history.
            content = f"{context_header}\n\n{msg.content}" if i == 0 else msg.content
            lc_messages.append(HumanMessage(content=content))
        else:
            lc_messages.append(AIMessage(content=msg.content))

    return lc_messages


class AIEngine:
    """
    LangChain / LangGraph AI engine — replaces the Semantic Kernel wrapper.

    Two complementary interaction patterns (mirroring SK and AutoGen respectively):

    1. LCEL chain  (explain endpoint):
       Structured prompt → LLM → parsed string output.
       SK equivalent:  result = await kernel.invoke_prompt(prompt)
       LC equivalent:  result = await (prompt | llm | StrOutputParser()).ainvoke({...})

    2. ReAct agent (stream_chat endpoint):
       Autonomous tool-calling loop managed by a LangGraph state graph.
       AutoGen equivalent:  await agent.initiate_chat(user_proxy, message=question)
       LangGraph:          async for event in agent.astream_events({...}, version="v2")
    """

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        agent: CompiledStateGraph | None = None,
    ) -> None:
        self._llm = llm
        self._agent = agent

    @property
    def ready(self) -> bool:
        return self._llm is not None

    async def explain(self, request: ChatRequest) -> ChatResponse:
        """
        Structured explanation via an LCEL chain (non-streaming fallback).

        LCEL (LangChain Expression Language) uses the pipe operator to compose
        a pipeline:  prompt | llm | parser
        This is analogous to SK's function composition / prompt chaining.
        """
        if not self.ready:
            return ChatResponse(
                answer=(
                    "AI engine is not configured. "
                    "Please set Azure OpenAI credentials in .env."
                ),
                sources=[],
            )

        # Extract the last user message as the question
        last_user = next(
            (m for m in reversed(request.messages) if m.role == "user"), None
        )
        question = last_user.content if last_user else ""

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are WealthPath, a retirement readiness assistant. "
                        "You explain projections and run scenario analyses based on "
                        "the user's profile. You are not a licensed financial adviser. "
                        "For specific fund/product recommendations or tax advice "
                        "(Roth conversions, withdrawal sequencing), direct the user "
                        "to a qualified CFP or RIA and offer to model the scenario instead."
                    ),
                ),
                (
                    "human",
                    (
                        "Household: age={age}, income={income}, "
                        "net_worth={net_worth}, education={education}\n\n"
                        "Question: {question}{context_section}"
                    ),
                ),
            ]
        )

        # The pipe operator builds an LCEL chain: prompt → llm → parser
        chain = prompt | self._llm | StrOutputParser()

        answer = await chain.ainvoke(
            {
                "age": request.household.age,
                "income": f"${request.household.income:,.0f}",
                "net_worth": f"${request.household.net_worth:,.0f}",
                "education": request.household.education.value,
                "question": question,
                "context_section": (
                    f"\n\nContext: {request.context}" if request.context else ""
                ),
            }
        )

        return ChatResponse(answer=answer, sources=["SCF data", "Monte Carlo simulation"])

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Agentic planning via a LangGraph ReAct agent (non-streaming fallback).

        The agent graph runs autonomously:
          [START] → agent node → (tool call?) → tools node → agent node → [END]

        The LLM decides which tools (cohort lookup, projection) to call and in
        what order — exactly like AutoGen's AssistantAgent deciding which plugin
        to invoke during a conversation turn.
        """
        if not self._agent:
            # Graceful degradation: fall back to the simpler LCEL chain.
            return await self.explain(request)

        lc_messages = _build_lc_messages(request)
        result = await self._agent.ainvoke({"messages": lc_messages})
        last_message = result["messages"][-1]

        return ChatResponse(
            answer=last_message.content,
            sources=["SCF data", "Monte Carlo simulation"],
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Stream tokens and tool-call status events from the LangGraph ReAct agent.

        Uses astream_events() to expose fine-grained lifecycle events — this is
        the key capability that makes the agent's "thinking" visible to the user:

          on_tool_start        → "Looking up cohort data..." status event
          on_chat_model_stream → individual LLM output tokens

        SK equivalent: no direct equivalent — SK's InvokeAsync streaming returns
          a token stream but doesn't expose tool-call lifecycle events mid-stream.
          This level of observability is a LangGraph-specific capability.

        AutoGen equivalent: roughly message_handler callbacks on AssistantAgent,
          but LangGraph's astream_events() is more granular and structured.

        Yields SSE-formatted strings consumed by the frontend ReadableStream:
          data: {"type": "status", "text": "..."}   — agent called a tool
          data: {"type": "token",  "text": "..."}   — LLM output token
          data: {"type": "done"}                    — stream finished
        """
        def _sse(payload: dict) -> str:
            # SSE format: "data: {json}\n\n" — the double newline is the event delimiter
            return f"data: {json.dumps(payload)}\n\n"

        if not self._agent:
            yield _sse({"type": "token", "text": "AI engine is not configured. Please set Azure OpenAI credentials in .env."})
            yield _sse({"type": "done"})
            return

        lc_messages = _build_lc_messages(request)

        try:
            async for event in self._agent.astream_events(
                {"messages": lc_messages}, version="v2"
            ):
                kind = event["event"]

                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    status_text = _TOOL_STATUS.get(tool_name, f"Using {tool_name}...")
                    yield _sse({"type": "status", "text": status_text})

                elif kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    # chunk.content is empty during tool-call decisions (the LLM is
                    # outputting structured tool_call JSON, not text). Only emit tokens
                    # when there is actual text content — the final answer to the user.
                    if chunk and chunk.content:
                        yield _sse({"type": "token", "text": chunk.content})

        except Exception:
            logger.exception("stream_chat error")
            yield _sse({"type": "token", "text": "\n\n[An error occurred while generating the response.]"})

        finally:
            yield _sse({"type": "done"})
