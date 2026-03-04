from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from wealthpath.dependencies import get_ai_engine
from wealthpath.models.chat import ChatRequest, ChatResponse
from wealthpath.services.ai_engine import AIEngine

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    ai: AIEngine = Depends(get_ai_engine),
) -> StreamingResponse:
    """
    Stream tokens and tool-call status events as Server-Sent Events (SSE).

    Unified streaming endpoint that replaces /explain and /plan for new clients.
    The ReAct agent autonomously decides whether to call tools or answer directly.

    SSE event format — each chunk is "data: {json}\\n\\n":
      {"type": "status", "text": "..."}   — agent called a tool (transient status)
      {"type": "token",  "text": "..."}   — LLM output token (append to response)
      {"type": "done"}                    — stream complete (sentinel)

    ASP.NET Core equivalent: IAsyncEnumerable<T> returned from a controller action
      with [Produces("text/event-stream")]. FastAPI's StreamingResponse is the
      Python equivalent — it keeps the HTTP connection open and flushes chunks.

    Frontend reads this with fetch() + ReadableStream — no EventSource or SSE
    library needed, since EventSource doesn't support POST requests with a body.
    """
    return StreamingResponse(
        ai.stream_chat(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering (critical in Azure Container Apps)
            "Connection": "keep-alive",
        },
    )


@router.post("/explain", response_model=ChatResponse)
async def explain(
    request: ChatRequest,
    ai: AIEngine = Depends(get_ai_engine),
) -> ChatResponse:
    """
    Structured explanation via an LCEL chain (non-streaming).

    Kept as a non-streaming fallback and for tests. Prefer /stream for new clients.

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
    Agentic planning via a LangGraph ReAct agent (non-streaming).

    Kept as a non-streaming fallback and for tests. Prefer /stream for new clients.

    Python ecosystem equivalent of AutoGen's AssistantAgent pattern:
    the agent autonomously calls cohort and projection tools before answering.
    Falls back to the LCEL chain if no LLM is configured.
    """
    return await ai.chat(request)
