from __future__ import annotations

from pathlib import Path

import yaml
from langchain_core.prompts import ChatPromptTemplate

_PROMPTS_DIR = Path(__file__).parent


def load_chat_prompt(name: str) -> ChatPromptTemplate:
    """
    Load a ChatPromptTemplate from a YAML file in the prompts directory.

    Replaces Semantic Kernel's prompt file registration:

        SK:   kernel.add_function(
                  prompt_template_config=PromptTemplateConfig.from_yaml(path),
                  plugin_name="explainer",
              )

        LC:   prompt = load_chat_prompt("explain_projection")
              chain  = prompt | llm | StrOutputParser()

    The YAML format expected:
        messages:
          - role: system
            content: "..."
          - role: human
            content: "Use {variable} placeholders."
    """
    path = _PROMPTS_DIR / f"{name}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    messages = [(m["role"], m["content"]) for m in data["messages"]]
    return ChatPromptTemplate.from_messages(messages)
