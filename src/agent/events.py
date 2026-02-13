"""Agent event types yielded by the ReAct loop."""

from dataclasses import dataclass, field
from enum import Enum


class AgentEventType(str, Enum):
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ANSWER_START = "answer_start"
    ANSWER_TOKEN = "answer_token"
    ANSWER_DONE = "answer_done"
    ERROR = "error"
    MAX_ITERATIONS = "max_iterations"


@dataclass
class AgentEvent:
    type: AgentEventType
    data: dict = field(default_factory=dict)
