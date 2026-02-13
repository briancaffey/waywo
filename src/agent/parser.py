"""Parse ReAct-style LLM output into structured results."""

import json
import re
from dataclasses import dataclass


@dataclass
class ParsedAction:
    thought: str
    action: str
    action_input: str


@dataclass
class ParsedFinalAnswer:
    thought: str
    answer: str


@dataclass
class ParseError:
    raw_text: str
    error: str


ParseResult = ParsedAction | ParsedFinalAnswer | ParseError


def parse_react_output(text: str) -> ParseResult:
    """Parse LLM text output into a structured ReAct result.

    Expected formats:
        Thought: <reasoning>
        Action: <tool_name>
        Action Input: <json or text>

    Or:
        Thought: <reasoning>
        Final Answer: <response text>
    """
    text = text.strip()

    # Extract thought
    thought = ""
    thought_match = re.search(
        r"Thought:\s*(.*?)(?=\n(?:Action:|Final Answer:)|$)",
        text,
        re.DOTALL,
    )
    if thought_match:
        thought = thought_match.group(1).strip()

    # Check for Final Answer
    final_match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL)
    if final_match:
        answer = final_match.group(1).strip()
        return ParsedFinalAnswer(thought=thought, answer=answer)

    # Check for Action + Action Input
    action_match = re.search(r"Action:\s*(\S+)", text)
    input_match = re.search(r"Action Input:\s*(.*?)(?=\n(?:Thought:|Action:|Final Answer:)|$)", text, re.DOTALL)

    if action_match:
        action = action_match.group(1).strip()
        action_input = input_match.group(1).strip() if input_match else ""
        return ParsedAction(
            thought=thought,
            action=action,
            action_input=action_input,
        )

    # Graceful degradation: treat unparseable text as final answer,
    # but log a warning since the model didn't follow the format
    if len(text) > 20:
        import logging
        logging.getLogger(__name__).warning(
            f"Agent output missing Thought:/Action:/Final Answer: labels, "
            f"treating as raw answer. First 100 chars: {text[:100]!r}"
        )
        return ParsedFinalAnswer(thought="", answer=text)

    return ParseError(raw_text=text, error="Could not parse ReAct output")


def parse_action_input(action_input: str, tool_name: str) -> dict:
    """Parse action input string into keyword arguments for a tool.

    Handles both JSON objects and plain strings.
    """
    action_input = action_input.strip()

    # Try JSON parsing first
    if action_input.startswith("{"):
        try:
            return json.loads(action_input)
        except json.JSONDecodeError:
            pass

    # For search_projects: treat as query string
    if tool_name == "search_projects":
        # Strip quotes if present
        query = action_input.strip("\"'")
        return {"query": query}

    # For get_project_details: extract integer
    if tool_name == "get_project_details":
        # Try to extract a number
        num_match = re.search(r"\d+", action_input)
        if num_match:
            return {"project_id": int(num_match.group())}

    return {"query": action_input}
