"""MAF middleware for logging, caching, and retry."""
from __future__ import annotations

import asyncio
import hashlib
import json
import time

# Pre-import to avoid circular import in MAF 1.2.0
import agent_framework._agents  # noqa: F401

from agent_framework._middleware import (
    ChatContext,
    FunctionInvocationContext,
    chat_middleware,
    function_middleware,
)

from deep_research.log import log

# ---------------------------------------------------------------------------
# Chat middleware — logs every LLM round-trip
# ---------------------------------------------------------------------------


@chat_middleware
async def llm_call_logging(context: ChatContext, next_handler):
    msg_count = len(context.messages) if context.messages else 0
    log.info("LLM call starting: %d messages", msg_count)
    start = time.monotonic()
    try:
        await next_handler()
        elapsed = (time.monotonic() - start) * 1000
        result = context.result
        text = getattr(result, "text", None) or ""
        log.info("LLM call OK in %.0fms, response %d chars", elapsed, len(text))
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        log.error("LLM call FAILED after %.0fms: %s", elapsed, e)
        raise


# ---------------------------------------------------------------------------
# Function middleware — tool call logging with timing
# ---------------------------------------------------------------------------


@function_middleware
async def tool_call_logging(context: FunctionInvocationContext, next_handler):
    log.info("Tool call: %s(%s)", context.function.name, str(context.arguments)[:200])
    start = time.monotonic()
    try:
        await next_handler()
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        log.error("Tool %s FAILED after %.0fms: %s", context.function.name, elapsed, e)
        raise
    elapsed = (time.monotonic() - start) * 1000
    result_str = str(context.result) if context.result is not None else ""
    log.info("Tool %s returned %d chars in %.0fms", context.function.name, len(result_str), elapsed)


# ---------------------------------------------------------------------------
# Function middleware — cache tool results
# ---------------------------------------------------------------------------

_cache: dict[str, str] = {}


@function_middleware
async def caching(context: FunctionInvocationContext, next_handler):
    global _cache
    key = hashlib.md5(
        f"{context.function.name}:{json.dumps(context.arguments, sort_keys=True)}".encode()
    ).hexdigest()
    if key in _cache:
        log.debug("Cache hit: %s", context.function.name)
        context.result = _cache[key]
        return
    await next_handler()
    if context.result is not None:
        _cache[key] = context.result


# ---------------------------------------------------------------------------
# Function middleware — retry failed tool calls
# ---------------------------------------------------------------------------


@function_middleware
async def retry(context: FunctionInvocationContext, next_handler):
    for attempt in range(3):
        try:
            await next_handler()
            return
        except Exception as e:
            if attempt == 2:
                raise
            log.warning("Tool %s failed (attempt %d/3): %s", context.function.name, attempt + 1, e)
            await asyncio.sleep(2**attempt)
