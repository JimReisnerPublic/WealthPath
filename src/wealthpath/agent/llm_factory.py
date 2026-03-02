from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_openai import AzureChatOpenAI

if TYPE_CHECKING:
    from wealthpath.config import Settings

logger = logging.getLogger(__name__)


def build_llm(settings: Settings) -> AzureChatOpenAI | None:
    """
    Create a LangChain AzureChatOpenAI instance.

    Replaces Semantic Kernel's kernel_factory / AzureChatCompletion:

        SK:   kernel = Kernel()
              kernel.add_service(AzureChatCompletion(deployment_name=..., ...))

        LC:   llm = AzureChatOpenAI(azure_deployment=..., ...)

    In LangChain, the LLM is a plain object you pass to chains or agents
    rather than a registry inside a Kernel container.
    """
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        logger.warning("Azure OpenAI credentials not set — AI features disabled.")
        return None

    return AzureChatOpenAI(
        azure_deployment=settings.azure_openai_deployment,
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )
