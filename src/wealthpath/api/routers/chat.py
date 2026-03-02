from __future__ import annotations

from fastapi import APIRouter, Depends

from wealthpath.dependencies import get_ai_engine
from wealthpath.models.chat import ChatRequest, ChatResponse
from wealthpath.services.ai_engine import AIEngine

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/explain", response_model=ChatResponse)
async def explain(
    request: ChatRequest,
    ai: AIEngine = Depends(get_ai_engine),
) -> ChatResponse:
    """
    Structured explanation via an LCEL chain.

    LangChain equivalent of SK's kernel.invoke_prompt():
        chain = prompt | llm | StrOutputParser()
        result = await chain.ainvoke({...})
    """
    return await ai.explain(request)


@router.post("/plan", response_model=ChatResponse)
async def plan(
    request: ChatRequest,
    ai: AIEngine = Depends(get_ai_engine),
) -> ChatResponse:
    """
    Agentic planning via a LangGraph ReAct agent.

    Python ecosystem equivalent of AutoGen's AssistantAgent pattern:
    the agent autonomously calls cohort and projection tools before answering.
    Falls back to the LCEL chain if no LLM is configured.
    """
    return await ai.chat(request)
