"""MAF middleware: function-level caching, retry, logging + agent-level logging."""
from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from agent_framework._middleware import (
    AgentContext,
    AgentMiddleware,
    FunctionInvocationContext,
    FunctionMiddleware,
)

logger = logging.getLogger(__name__)


class CachingMiddleware(FunctionMiddleware):
    """Cache function results keyed by function name + arguments."""

    def __init__(self) -> None:
        self.cache: dict[str, object] = {}

    async def process(
        self,
        context: FunctionInvocationContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        cache_key = f"{context.function.name}:{context.arguments}"
        if cache_key in self.cache:
            context.result = self.cache[cache_key]
            return
        await call_next()
        if context.result is not None:
            self.cache[cache_key] = context.result


class RetryMiddleware(FunctionMiddleware):
    """Retry failed function invocations up to max_retries times."""

    def __init__(self, max_retries: int = 2) -> None:
        self.max_retries = max_retries

    async def process(
        self,
        context: FunctionInvocationContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                await call_next()
                return
            except Exception as exc:
                last_exc = exc
                logger.warning("Tool %s attempt %d failed: %s", context.function.name, attempt, exc)
        if last_exc is not None:
            raise last_exc


class LoggingMiddleware(FunctionMiddleware):
    """Log function invocations with timing."""

    async def process(
        self,
        context: FunctionInvocationContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        start = time.perf_counter()
        logger.info("Calling tool %s", context.function.name)
        await call_next()
        elapsed = time.perf_counter() - start
        logger.info("Tool %s completed in %.2fs", context.function.name, elapsed)


class AgentLoggingMiddleware(AgentMiddleware):
    """Log agent invocations with timing."""

    async def process(
        self,
        context: AgentContext,
        call_next: Callable[[], Awaitable[None]],
    ) -> None:
        agent_name = getattr(context.agent, "name", "unknown")
        start = time.perf_counter()
        logger.info("Agent %s invoked", agent_name)
        await call_next()
        elapsed = time.perf_counter() - start
        logger.info("Agent %s completed in %.2fs", agent_name, elapsed)
