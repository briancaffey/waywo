"""Core agent loop — async generator yielding AgentEvents.

Two modes selected by AGENT_TOOL_CALLING:
  True  → OpenAI-compatible structured tool calling (primary)
  False → Proactive RAG fallback (for vLLM without --enable-auto-tool-choice)
"""

import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator

from src.agent.events import AgentEvent, AgentEventType
from src.agent.tools import TOOL_SCHEMAS, get_tool
from src.llm_config import get_openai_client
from src.settings import AGENT_MAX_ITERATIONS, AGENT_TOOL_CALLING, LLM_MODEL_NAME, LLM_TEMPERATURE, LLM_MAX_TOKENS

logger = logging.getLogger(__name__)

# Regex to detect Hermes-format tool calls that leak into content
_HERMES_TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*<function=(\w+)>(.*?)</function>\s*</tool_call>",
    re.DOTALL,
)
_HERMES_PARAM_RE = re.compile(
    r"<parameter=(\w+)>\s*(.*?)\s*</parameter>",
    re.DOTALL,
)


def _extract_hermes_tool_calls(text: str) -> tuple[str, list[tuple[str, dict]]]:
    """Parse Hermes <tool_call> tags from text content.

    Returns (remaining_text, [(tool_name, arguments_dict), ...]).
    """
    calls: list[tuple[str, dict]] = []
    for m in _HERMES_TOOL_CALL_RE.finditer(text):
        fn_name = m.group(1)
        body = m.group(2)
        params: dict = {}
        for pm in _HERMES_PARAM_RE.finditer(body):
            key = pm.group(1)
            val = pm.group(2).strip()
            # Try to cast to int if it looks numeric
            try:
                val = int(val)
            except (ValueError, TypeError):
                pass
            params[key] = val
        calls.append((fn_name, params))

    remaining = _HERMES_TOOL_CALL_RE.sub("", text).strip()
    return remaining, calls


# Patterns that suggest the user is asking about projects (used by fallback)
_FACTUAL_KEYWORDS = {
    "project", "projects", "working on", "built", "building", "app",
    "tool", "tools", "startup", "show", "made", "create", "using",
    "framework", "language", "AI", "ml", "machine learning", "web",
    "api", "database", "what", "how many", "list", "find", "search",
    "any", "recommend", "suggest", "tell me about", "details",
}


def _is_factual_query(text: str) -> bool:
    """Heuristic: does the user message look like it needs RAG?"""
    lower = text.lower()
    return any(kw in lower for kw in _FACTUAL_KEYWORDS)


def _build_messages(
    user_message: str,
    history: list,
    system_prompt: str,
) -> list[dict]:
    """Build OpenAI-format message list from system prompt + history + user."""
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for turn in history:
        messages.append({"role": turn.role, "content": turn.text})
    messages.append({"role": "user", "content": user_message})
    return messages


def _dedup_projects(projects: list[dict]) -> list[dict]:
    """Deduplicate source projects by ID."""
    seen: set[int] = set()
    unique: list[dict] = []
    for p in projects:
        pid = p.get("id")
        if pid not in seen:
            seen.add(pid)
            unique.append(p)
    return unique


async def _execute_tool_call(
    tool_name: str, arguments: dict
) -> tuple[str, list[dict]]:
    """Execute a tool by name with parsed arguments, return (text, projects)."""
    tool = get_tool(tool_name)
    if tool is None:
        return f"Error: Unknown tool '{tool_name}'. Available: search_projects, get_project_details", []
    try:
        return await tool.execute(**arguments)
    except Exception as e:
        logger.error(f"Tool execution failed ({tool_name}): {e}")
        return f"Error executing {tool_name}: {e}", []


# ---------------------------------------------------------------------------
# Primary path: OpenAI tool calling
# ---------------------------------------------------------------------------


async def _run_tool_calling(
    user_message: str,
    history: list,
    system_prompt: str,
    max_iterations: int,
    stream_final_answer: bool,
) -> AsyncGenerator[AgentEvent, None]:
    """Agent loop using OpenAI-compatible tool calling."""
    client = get_openai_client()
    messages = _build_messages(user_message, history, system_prompt)
    all_source_projects: list[dict] = []
    agent_steps: list[dict] = []

    for iteration in range(1, max_iterations + 1):
        logger.info(f"Agent tool-calling iteration {iteration}/{max_iterations}")

        try:
            response = await client.chat.completions.create(
                model=LLM_MODEL_NAME,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
        except Exception as e:
            logger.error(f"Agent LLM call failed: {e}")
            yield AgentEvent(
                type=AgentEventType.ERROR,
                data={"error": str(e), "iteration": iteration},
            )
            yield AgentEvent(
                type=AgentEventType.ANSWER_DONE,
                data={
                    "full_text": "Sorry, I encountered an error processing your request.",
                    "source_projects": _dedup_projects(all_source_projects),
                    "agent_steps": agent_steps,
                },
            )
            return

        choice = response.choices[0]
        message = choice.message
        content_text = (message.content or "").strip()

        # Check for Hermes <tool_call> tags leaked into content
        remaining_text, hermes_calls = _extract_hermes_tool_calls(content_text)

        # Emit thinking for any non-tool-call content
        if remaining_text:
            yield AgentEvent(
                type=AgentEventType.THINKING,
                data={"thought": remaining_text, "iteration": iteration},
            )
            agent_steps.append({"type": "thought", "text": remaining_text})

        # ── Structured tool calls from the API ────────────────────────
        if message.tool_calls:
            messages.append(message.model_dump())

            for tc in message.tool_calls:
                fn = tc.function
                tool_name = fn.name
                try:
                    arguments = json.loads(fn.arguments)
                except json.JSONDecodeError:
                    arguments = {"query": fn.arguments}

                input_summary = json.dumps(arguments)[:200]
                yield AgentEvent(
                    type=AgentEventType.TOOL_CALL,
                    data={"tool": tool_name, "input": input_summary, "iteration": iteration},
                )
                agent_steps.append({"type": "tool_call", "tool": tool_name, "input": input_summary})

                observation, tool_projects = await _execute_tool_call(tool_name, arguments)
                all_source_projects.extend(tool_projects)

                yield AgentEvent(
                    type=AgentEventType.TOOL_RESULT,
                    data={
                        "tool": tool_name,
                        "projects_found": len(tool_projects),
                        "result_summary": observation[:200],
                        "iteration": iteration,
                    },
                )
                agent_steps.append({
                    "type": "tool_result",
                    "tool": tool_name,
                    "summary": observation[:200],
                    "projects_found": len(tool_projects),
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": observation,
                })

            continue

        # ── Hermes tool calls parsed from content text ────────────────
        if hermes_calls:
            logger.info(f"Parsed {len(hermes_calls)} Hermes tool call(s) from content")
            # Add a plain assistant message to history (without tool_calls)
            messages.append({"role": "assistant", "content": content_text})

            for tool_name, arguments in hermes_calls:
                input_summary = json.dumps(arguments)[:200]
                yield AgentEvent(
                    type=AgentEventType.TOOL_CALL,
                    data={"tool": tool_name, "input": input_summary, "iteration": iteration},
                )
                agent_steps.append({"type": "tool_call", "tool": tool_name, "input": input_summary})

                observation, tool_projects = await _execute_tool_call(tool_name, arguments)
                all_source_projects.extend(tool_projects)

                yield AgentEvent(
                    type=AgentEventType.TOOL_RESULT,
                    data={
                        "tool": tool_name,
                        "projects_found": len(tool_projects),
                        "result_summary": observation[:200],
                        "iteration": iteration,
                    },
                )
                agent_steps.append({
                    "type": "tool_result",
                    "tool": tool_name,
                    "summary": observation[:200],
                    "projects_found": len(tool_projects),
                })

                # Inject tool result as a user message (no tool_call_id for Hermes path)
                messages.append({
                    "role": "user",
                    "content": f"Tool result for {tool_name}:\n{observation}",
                })

            continue

        # ── No tool calls → final answer ──────────────────────────────
        final_text = content_text

        if stream_final_answer:
            yield AgentEvent(type=AgentEventType.ANSWER_START, data={})
            words = final_text.split(" ")
            for i, word in enumerate(words):
                token = word if i == 0 else " " + word
                yield AgentEvent(
                    type=AgentEventType.ANSWER_TOKEN,
                    data={"token": token},
                )
                await asyncio.sleep(0)

        yield AgentEvent(
            type=AgentEventType.ANSWER_DONE,
            data={
                "full_text": final_text,
                "source_projects": _dedup_projects(all_source_projects),
                "agent_steps": agent_steps,
            },
        )
        return

    # Max iterations reached
    logger.warning(f"Agent hit max iterations ({max_iterations})")
    yield AgentEvent(
        type=AgentEventType.MAX_ITERATIONS,
        data={"iterations": max_iterations},
    )
    yield AgentEvent(
        type=AgentEventType.ANSWER_DONE,
        data={
            "full_text": "I found some relevant information but ran out of processing steps. Here's what I gathered so far based on the search results.",
            "source_projects": _dedup_projects(all_source_projects),
            "agent_steps": agent_steps,
        },
    )


# ---------------------------------------------------------------------------
# Fallback path: proactive RAG (no tool calling needed from vLLM)
# ---------------------------------------------------------------------------


async def _run_proactive_rag(
    user_message: str,
    history: list,
    system_prompt: str,
    stream_final_answer: bool,
) -> AsyncGenerator[AgentEvent, None]:
    """Fallback: proactively call RAG for factual queries, skip for chat."""
    client = get_openai_client()
    all_source_projects: list[dict] = []
    agent_steps: list[dict] = []

    if _is_factual_query(user_message):
        # Proactively search
        yield AgentEvent(
            type=AgentEventType.THINKING,
            data={"thought": "Searching the project database...", "iteration": 1},
        )
        agent_steps.append({"type": "thought", "text": "Searching the project database..."})

        yield AgentEvent(
            type=AgentEventType.TOOL_CALL,
            data={"tool": "search_projects", "input": user_message, "iteration": 1},
        )
        agent_steps.append({"type": "tool_call", "tool": "search_projects", "input": user_message})

        observation, tool_projects = await _execute_tool_call(
            "search_projects", {"query": user_message}
        )
        all_source_projects.extend(tool_projects)

        yield AgentEvent(
            type=AgentEventType.TOOL_RESULT,
            data={
                "tool": "search_projects",
                "projects_found": len(tool_projects),
                "result_summary": observation[:200],
                "iteration": 1,
            },
        )
        agent_steps.append({
            "type": "tool_result",
            "tool": "search_projects",
            "summary": observation[:200],
            "projects_found": len(tool_projects),
        })

        # Build messages with RAG context injected as a system message
        messages = _build_messages(user_message, history, system_prompt)
        messages.insert(1, {
            "role": "system",
            "content": f"Here are relevant projects from the database. Use ONLY this data to answer:\n\n{observation}",
        })
    else:
        # Conversational — no RAG needed
        messages = _build_messages(user_message, history, system_prompt)

    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=messages,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        final_text = response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"Proactive RAG LLM call failed: {e}")
        yield AgentEvent(
            type=AgentEventType.ERROR,
            data={"error": str(e)},
        )
        final_text = "Sorry, I encountered an error processing your request."

    if stream_final_answer:
        yield AgentEvent(type=AgentEventType.ANSWER_START, data={})
        words = final_text.split(" ")
        for i, word in enumerate(words):
            token = word if i == 0 else " " + word
            yield AgentEvent(
                type=AgentEventType.ANSWER_TOKEN,
                data={"token": token},
            )
            await asyncio.sleep(0)

    yield AgentEvent(
        type=AgentEventType.ANSWER_DONE,
        data={
            "full_text": final_text,
            "source_projects": _dedup_projects(all_source_projects),
            "agent_steps": agent_steps,
        },
    )


# ---------------------------------------------------------------------------
# Public entry point (same signature as before)
# ---------------------------------------------------------------------------


async def run_agent(
    user_message: str,
    history: list,
    system_prompt_template: str,
    max_iterations: int | None = None,
    stream_final_answer: bool = True,
) -> AsyncGenerator[AgentEvent, None]:
    """Run the agent loop, yielding events as they occur.

    Args:
        user_message: The user's current message.
        history: List of turn objects with .role and .text attributes.
        system_prompt_template: System prompt (tool_descriptions placeholder ignored).
        max_iterations: Max tool-use iterations before forcing an answer.
        stream_final_answer: If True, yield word-by-word ANSWER_TOKEN events.

    Yields:
        AgentEvent instances as the agent thinks, acts, and answers.
    """
    if max_iterations is None:
        max_iterations = AGENT_MAX_ITERATIONS

    # Strip the old {tool_descriptions} placeholder if present
    system_prompt = system_prompt_template.replace("{tool_descriptions}", "").strip()

    if AGENT_TOOL_CALLING:
        logger.info("Agent: using OpenAI tool-calling path")
        async for event in _run_tool_calling(
            user_message, history, system_prompt, max_iterations, stream_final_answer
        ):
            yield event
    else:
        logger.info("Agent: using proactive RAG fallback path")
        async for event in _run_proactive_rag(
            user_message, history, system_prompt, stream_final_answer
        ):
            yield event
