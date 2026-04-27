"""Tool-calling agent loop using the OpenAI chat completions API."""
from __future__ import annotations

import json
from typing import Any, Callable

from deep_research.llm import get_client
from deep_research.tools.search import web_search
from deep_research.tools.fetch import fetch_page
from deep_research.tools.github_search import github_search
from deep_research.tools.github_read import github_read

# ---------------------------------------------------------------------------
# Tool registry: maps tool names → (callable, OpenAI tool definition)
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "web_search": {
        "function": web_search,
        "definition": {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web using DuckDuckGo and return results as JSON.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query to look up on the web"},
                        "max_results": {"type": "integer", "description": "Maximum number of results to return", "default": 5},
                    },
                    "required": ["query"],
                },
            },
        },
    },
    "fetch_page": {
        "function": fetch_page,
        "definition": {
            "type": "function",
            "function": {
                "name": "fetch_page",
                "description": "Fetch a web page and extract its main text content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL of the web page to fetch and extract text from"},
                    },
                    "required": ["url"],
                },
            },
        },
    },
    "github_search": {
        "function": github_search,
        "definition": {
            "type": "function",
            "function": {
                "name": "github_search",
                "description": "Search GitHub for code, repositories, or issues using the gh CLI.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "mode": {"type": "string", "description": "Search mode: code, repos, or issues", "default": "code"},
                        "max_results": {"type": "integer", "description": "Max results", "default": 5},
                    },
                    "required": ["query"],
                },
            },
        },
    },
    "github_read": {
        "function": github_read,
        "definition": {
            "type": "function",
            "function": {
                "name": "github_read",
                "description": "Fetch and return the content of a file from a GitHub repository.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "Repository in owner/repo format"},
                        "path": {"type": "string", "description": "File path within the repository"},
                        "ref": {"type": "string", "description": "Branch or commit ref", "default": "HEAD"},
                    },
                    "required": ["repo", "path"],
                },
            },
        },
    },
}


def run_agent(
    system_prompt: str,
    user_message: str,
    tools: list[str],
    *,
    model: str = "gpt-5.5",
    max_iterations: int = 15,
    reasoning_effort: str = "medium",
) -> str:
    """Run a tool-calling agent loop until the model produces a final text answer.

    Args:
        system_prompt: System instructions for the agent.
        user_message: The user's request.
        tools: List of tool names from TOOL_REGISTRY to make available.
        model: Model name/deployment to use.
        max_iterations: Safety limit on tool-call round-trips.
        temperature: Sampling temperature.

    Returns:
        The model's final text response.
    """
    client = get_client()
    tool_defs = [TOOL_REGISTRY[t]["definition"] for t in tools]

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    for _ in range(max_iterations):
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "tools": tool_defs,
        }
        if model.startswith(("gpt-5", "o1", "o3", "o4")):
            kwargs["reasoning_effort"] = reasoning_effort
            kwargs["max_completion_tokens"] = 16384
        else:
            kwargs["temperature"] = 0.7
        response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        msg = choice.message

        # Normalize the assistant message to a plain dict for re-sending
        assistant_msg: dict[str, Any] = {"role": "assistant"}
        if msg.content:
            assistant_msg["content"] = msg.content

        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]

        messages.append(assistant_msg)

        # If the model is done (no tool calls), return the text
        if not msg.tool_calls:
            return msg.content or ""

        # Execute each tool call and append results
        for tc in msg.tool_calls:
            tool_name = tc.function.name
            tool_result: str
            try:
                if tool_name not in TOOL_REGISTRY:
                    tool_result = json.dumps({"error": f"Unknown tool: {tool_name}"})
                else:
                    args = json.loads(tc.function.arguments)
                    fn = TOOL_REGISTRY[tool_name]["function"]
                    tool_result = fn(**args)
            except Exception as e:
                tool_result = json.dumps({"error": f"Tool execution failed: {e}"})

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_result,
            })

    # If we hit the iteration cap, ask for a summary
    messages.append({
        "role": "user",
        "content": "Please provide your final summary based on the research so far.",
    })
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""
