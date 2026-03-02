from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from wealthpath.models.chat import ChatRequest, ChatResponse

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langgraph.graph.state import CompiledStateGraph


class AIEngine:
    """
    LangChain / LangGraph AI engine — replaces the Semantic Kernel wrapper.

    Two complementary interaction patterns (mirroring SK and AutoGen respectively):

    1. LCEL chain  (explain endpoint):
       Structured prompt → LLM → parsed string output.
       SK equivalent:  result = await kernel.invoke_prompt(prompt)
       LC equivalent:  result = await (prompt | llm | StrOutputParser()).ainvoke({...})

    2. ReAct agent (plan endpoint):
       Autonomous tool-calling loop managed by a LangGraph state graph.
       AutoGen equivalent:  await agent.initiate_chat(user_proxy, message=question)
       LangGraph:          result = await agent.ainvoke({"messages": [HumanMessage(...)]})
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
        Structured explanation via an LCEL chain.

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
                "question": request.question,
                "context_section": (
                    f"\n\nContext: {request.context}" if request.context else ""
                ),
            }
        )

        return ChatResponse(answer=answer, sources=["SCF data", "Monte Carlo simulation"])

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Agentic planning via a LangGraph ReAct agent.

        The agent graph runs autonomously:
          [START] → agent node → (tool call?) → tools node → agent node → [END]

        The LLM decides which tools (cohort lookup, projection) to call and in
        what order — exactly like AutoGen's AssistantAgent deciding which plugin
        to invoke during a conversation turn.
        """
        if not self._agent:
            # Graceful degradation: fall back to the simpler LCEL chain.
            return await self.explain(request)

        question = (
            f"I am {request.household.age} years old, income "
            f"${request.household.income:,.0f}, net worth "
            f"${request.household.net_worth:,.0f} "
            f"({request.household.education.value} education). "
            f"{request.question}"
        )

        result = await self._agent.ainvoke(
            {"messages": [HumanMessage(content=question)]}
        )
        last_message = result["messages"][-1]

        return ChatResponse(
            answer=last_message.content,
            sources=["SCF data", "Monte Carlo simulation"],
        )
