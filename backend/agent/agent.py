"""Core AI Chat Agent — LLM reasoning loop with tool orchestration.

Implements a multi-turn function-calling agent that:
  1. Accepts user messages and conversation context
  2. Sends context + tool schemas to GPT-4o for reasoning
  3. Detects and executes tool calls autonomously
  4. Feeds tool results back into the LLM for synthesis
  5. Yields SSE events for real-time streaming to the client
  6. Extracts citations from tool results

The agent runs as an async generator, yielding typed SSE events that the
API layer can stream directly back to the client.

SSE Event Types:
  - thinking        → Agent is processing (show typing indicator)
  - tool_call       → Agent invoked a tool (show tool name + args)
  - tool_result     → Tool returned results (show status)
  - content         → Text chunk from the LLM (stream to chat bubble)
  - citation        → A source reference extracted from tool results
  - recommendation  → Actionable recommendation from analysis
  - done            → Agent finished response (finalize chat bubble)
  - error           → An error occurred (show error to user)
"""

import json
import logging
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from openai import AsyncOpenAI

from backend.agent.context import ConversationContext
from backend.agent.prompts import get_system_prompt
from backend.agent.tools import TOOL_SCHEMAS, execute_tool
from backend.ai.guardrails import MAX_CHAT_MESSAGE_LENGTH, GuardrailsService
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Constants ────────────────────────────────────────────────────────

MAX_TOOL_ROUNDS = 5  # Maximum tool-call-then-reason loops per turn
STREAM_MODEL = "gpt-4o"  # Use standard model for agent reasoning
TEMPERATURE = 0.3  # Low temperature for factual, consistent responses
MAX_RESPONSE_TOKENS = 2048  # Cap response length


# ── SSE Event Dataclass ──────────────────────────────────────────────


@dataclass
class SSEEvent:
    """A single Server-Sent Event emitted by the agent."""

    event: str  # Event type: thinking, tool_call, tool_result, content, citation, recommendation, done, error
    data: dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        """Serialize to SSE wire format."""
        payload = json.dumps(self.data, default=str)
        return f"event: {self.event}\ndata: {payload}\n\n"


# ── Citation Extractor ───────────────────────────────────────────────


def _extract_citations(
    tool_name: str, tool_result: dict[str, Any]
) -> list[dict[str, Any]]:
    """Extract citation objects from tool results.

    Returns a list of citation dicts with:
        - source_type (str): signal, search_result, recommendation, etc.
        - title (str): Human-readable title
        - signal_id (str | None): Signal UUID if applicable
        - confidence (float | None): Confidence score if available
        - snippet (str | None): Short excerpt
    """
    citations: list[dict[str, Any]] = []

    if tool_name == "search_signals":
        for signal in tool_result.get("signals", []):
            citations.append(
                {
                    "source_type": "signal",
                    "title": signal.get("title", "Unknown"),
                    "signal_id": signal.get("id"),
                    "confidence": signal.get("confidence"),
                    "snippet": signal.get("summary", "")[:200],
                }
            )

    elif tool_name == "deep_search":
        # Internal signal results (may include fused web results)
        for result in tool_result.get("results", []):
            is_web = result.get("is_live_web", False)
            url = result.get("source_url") or result.get("url")
            citations.append(
                {
                    "source_type": "web_result" if is_web else "search_result",
                    "title": result.get("title", "Unknown"),
                    "signal_id": None,
                    "confidence": result.get("confidence")
                    or result.get("relevance_score"),
                    "snippet": (result.get("summary") or result.get("snippet", ""))[
                        :200
                    ],
                    "source_url": url,
                    "url": url,
                    "source": result.get("source"),
                    "source_name": result.get("source"),
                    "is_live_web": is_web,
                }
            )
        # Dedicated web results from SerpApi
        for wr in tool_result.get("web_results", []):
            citations.append(
                {
                    "source_type": "web_result",
                    "title": wr.get("title", "Web Source"),
                    "signal_id": None,
                    "confidence": None,
                    "snippet": wr.get("snippet", "")[:200],
                    "source_url": wr.get("url"),
                    "url": wr.get("url"),
                    "source": wr.get("source"),
                    "source_name": wr.get("source"),
                    "is_live_web": True,
                }
            )

    elif tool_name == "synthesize_signal":
        if tool_result.get("signal_id"):
            citations.append(
                {
                    "source_type": "synthesized_signal",
                    "title": tool_result.get("title", "Synthesized signal"),
                    "signal_id": tool_result.get("signal_id"),
                    "confidence": tool_result.get("confidence"),
                    "snippet": tool_result.get("summary", "")[:200],
                }
            )

    elif tool_name == "get_analytics":
        if tool_result.get("analytics"):
            citations.append(
                {
                    "source_type": "analytics",
                    "title": f"Analytics: {tool_result.get('metric', 'overview')}",
                    "signal_id": None,
                    "confidence": None,
                    "snippet": json.dumps(tool_result["analytics"])[:200],
                }
            )

    elif tool_name == "get_recommendations":
        for rec in tool_result.get("recommendations", []):
            citations.append(
                {
                    "source_type": "recommendation",
                    "title": rec.get("title", "Recommendation"),
                    "signal_id": rec.get("signal_id"),
                    "confidence": rec.get("score"),
                    "snippet": rec.get("rationale", "")[:200],
                }
            )

    return citations


# ── Core Agent ───────────────────────────────────────────────────────


class ChatAgent:
    """Multi-turn function-calling AI agent.

    Usage:
        agent = ChatAgent(
            session_id=session_id,
            org_id=org_id,
            user_id=user_id,
            industry_code="fintech",
        )
        async for event in agent.run(user_message, db, redis):
            yield event.to_sse()
    """

    def __init__(
        self,
        session_id: UUID,
        org_id: UUID,
        user_id: UUID,
        industry_code: str | None = None,
        country: str | None = None,
    ):
        self.session_id = session_id
        self.org_id = org_id
        self.user_id = user_id
        self.industry_code = industry_code
        self.country = (
            country  # ISO 3166-1 alpha-3 (e.g. 'NGA') — from org.default_country
        )
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.guardrails = GuardrailsService()
        self.context_manager = ConversationContext()
        self._all_citations: list[dict[str, Any]] = []
        self._all_recommendations: list[dict[str, Any]] = []
        self._context_messages: list[dict[str, str]] = []
        self._context_metadata: dict[str, Any] = {}

    async def run(
        self,
        user_message: str,
        db: Any,  # AsyncSession — typed as Any to avoid circular imports
        redis: Any,  # Redis client
    ) -> AsyncGenerator[SSEEvent, None]:
        """Run the agent for one user turn.

        This is an async generator that yields SSE events as the agent
        reasons, calls tools, and generates its response.

        Args:
            user_message: The user's chat message.
            db: SQLAlchemy AsyncSession.
            redis: Redis client for context caching.

        Yields:
            SSEEvent objects representing agent activity.
        """
        start_time = time.time()

        # ── 1. Input validation ──────────────────────────────────────
        sanitized = self.guardrails.sanitize_input(
            user_message,
            max_length=MAX_CHAT_MESSAGE_LENGTH,
            context="chat",
        )
        if not sanitized.is_safe:
            yield SSEEvent(
                event="error",
                data={
                    "code": "input_blocked",
                    "message": "Your message was blocked by content safety filters.",
                    "detail": "; ".join(sanitized.warnings),
                },
            )
            return

        clean_message = sanitized.text

        # ── 2. Load/build conversation context ───────────────────────
        yield SSEEvent(event="thinking", data={"status": "loading_context"})

        cached = await self.context_manager.load(self.session_id)

        if cached:
            self._context_messages = cached.get("messages", [])
            self._context_metadata = cached.get("metadata", {})
        else:
            # Cache miss — try to rebuild from DB
            from backend.repositories.chat_session import ChatSessionRepository

            repo = ChatSessionRepository(db, self.org_id, self.user_id)
            db_messages = await repo.get_recent_messages(self.session_id)
            if db_messages:
                self._context_messages = await self.context_manager.build_from_db(
                    self.session_id, db_messages, self._context_metadata
                )

        # Append user message to context
        self._context_messages = await self.context_manager.append_message(
            self.session_id, "user", clean_message
        )

        # ── 3. Build messages array for LLM ──────────────────────────
        # Resolve org country if not set on agent
        country = self.country
        if not country:
            try:
                from backend.models.organization import Organization

                org = await db.get(Organization, self.org_id)
                if org:
                    country = org.default_country
            except Exception:
                pass  # Graceful fallback — no country context

        system_prompt = await get_system_prompt(
            db, country=country, industry_code=self.industry_code
        )
        messages = self._build_messages(system_prompt)

        # ── 4. Tool-calling reasoning loop ───────────────────────────
        yield SSEEvent(event="thinking", data={"status": "reasoning"})

        tool_rounds = 0
        final_content = ""

        while tool_rounds < MAX_TOOL_ROUNDS:
            tool_rounds += 1

            try:
                response = await self.client.chat.completions.create(
                    model=STREAM_MODEL,
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                    temperature=TEMPERATURE,
                    max_tokens=MAX_RESPONSE_TOKENS,
                    stream=True,
                )
            except Exception as e:
                logger.error(f"OpenAI API error in agent loop: {e}")
                yield SSEEvent(
                    event="error",
                    data={
                        "code": "llm_error",
                        "message": "Failed to get AI response. Please try again.",
                    },
                )
                return

            # ── 4a. Stream the response ──────────────────────────────
            assistant_content = ""
            tool_calls_accumulator: dict[int, dict[str, Any]] = {}
            finish_reason = None

            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                # Accumulate finish_reason
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason

                # Stream text content tokens
                if delta.content:
                    assistant_content += delta.content
                    yield SSEEvent(
                        event="content",
                        data={"text": delta.content},
                    )

                # Accumulate tool calls (they arrive in chunks)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_accumulator:
                            tool_calls_accumulator[idx] = {
                                "id": tc.id or "",
                                "name": "",
                                "arguments": "",
                            }
                        if tc.id:
                            tool_calls_accumulator[idx]["id"] = tc.id
                        if tc.function and tc.function.name:
                            tool_calls_accumulator[idx]["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            tool_calls_accumulator[idx][
                                "arguments"
                            ] += tc.function.arguments

            # ── 4b. Check if we should finish or call tools ──────────
            if finish_reason == "stop" or not tool_calls_accumulator:
                # LLM finished without tool calls — we have the final response
                final_content = assistant_content
                break

            # ── 4c. Execute tool calls ───────────────────────────────
            # Add assistant message with tool calls to context
            tool_calls_list = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"],
                    },
                }
                for tc in tool_calls_accumulator.values()
            ]

            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_content or None,
                    "tool_calls": tool_calls_list,
                }
            )

            # Execute each tool call
            for tc_data in tool_calls_accumulator.values():
                tool_name = tc_data["name"]
                tool_call_id = tc_data["id"]

                try:
                    tool_args = json.loads(tc_data["arguments"])
                except json.JSONDecodeError:
                    tool_args = {}

                # Emit tool_call event
                yield SSEEvent(
                    event="tool_call",
                    data={
                        "tool": tool_name,
                        "arguments": tool_args,
                    },
                )

                # Execute the tool
                try:
                    tool_result = await execute_tool(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        db=db,
                        org_id=self.org_id,
                        user_id=self.user_id,
                    )
                except Exception as e:
                    logger.error(f"Tool execution error ({tool_name}): {e}")
                    tool_result = {
                        "error": f"Tool '{tool_name}' failed: {str(e)}",
                        "status": "error",
                    }

                # Emit tool_result event
                yield SSEEvent(
                    event="tool_result",
                    data={
                        "tool": tool_name,
                        "status": "error" if "error" in tool_result else "success",
                        "summary": _summarize_tool_result(tool_name, tool_result),
                    },
                )

                # Extract citations from tool result
                citations = _extract_citations(tool_name, tool_result)
                self._all_citations.extend(citations)
                for citation in citations:
                    yield SSEEvent(event="citation", data=citation)

                # Extract recommendations if applicable
                if tool_name == "get_recommendations":
                    for rec in tool_result.get("recommendations", []):
                        self._all_recommendations.append(rec)
                        yield SSEEvent(event="recommendation", data=rec)

                # Add tool result to messages for LLM context
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps(tool_result, default=str),
                    }
                )

            # Continue the loop — LLM will process tool results and either
            # generate a final response or call more tools
            yield SSEEvent(event="thinking", data={"status": "processing_results"})

        # ── 5. Finalize ──────────────────────────────────────────────

        # If we hit max rounds without a clean finish, warn
        if tool_rounds >= MAX_TOOL_ROUNDS and not final_content:
            final_content = (
                "I've gathered the available information but reached my processing limit. "
                "Here's what I found so far — please ask a follow-up question if you need more detail."
            )
            yield SSEEvent(event="content", data={"text": final_content})

        # Save assistant response to context
        if final_content:
            await self.context_manager.append_message(
                self.session_id, "assistant", final_content
            )

        # Calculate timing
        elapsed = round(time.time() - start_time, 2)

        # Emit done event
        yield SSEEvent(
            event="done",
            data={
                "session_id": str(self.session_id),
                "total_citations": len(self._all_citations),
                "total_recommendations": len(self._all_recommendations),
                "tool_rounds": tool_rounds,
                "elapsed_seconds": elapsed,
            },
        )

    # ── Private Helpers ──────────────────────────────────────────────

    def _build_messages(self, system_prompt: str) -> list[dict[str, Any]]:
        """Build the messages array for the OpenAI API.

        Structure:
          [system, ...context_messages, user_message]
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]

        # Add conversation history from context
        for msg in self._context_messages:
            messages.append(
                {
                    "role": msg["role"],
                    "content": msg["content"],
                }
            )

        return messages


# ── Utility Functions ────────────────────────────────────────────────


def _summarize_tool_result(tool_name: str, result: dict[str, Any]) -> str:
    """Create a short human-readable summary of a tool result for SSE."""
    if "error" in result:
        return f"Error: {result['error']}"

    summaries = {
        "search_signals": lambda r: f"Found {r.get('count', 0)} signals",
        "deep_search": lambda r: (
            f"Found {len(r.get('results', []))} results"
            + (
                f" + {r.get('web_result_count', 0)} web results"
                if r.get("web_result_count")
                else ""
            )
        ),
        "synthesize_signal": lambda r: f"Created signal: {r.get('title', 'untitled')}",
        "get_analytics": lambda r: f"Retrieved {r.get('metric', 'analytics')} data",
        "get_recommendations": lambda r: f"Generated {len(r.get('recommendations', []))} recommendations",
        "browse_ontology": lambda r: f"Found {len(r.get('industries', r.get('contracts', [])))} items",
        "create_contract": lambda r: f"Created contract: {r.get('name', 'untitled')}",
    }

    summarizer = summaries.get(tool_name, lambda r: "Completed")
    try:
        return summarizer(result)
    except Exception:
        return "Completed"
