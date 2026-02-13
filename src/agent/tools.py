"""Agent tool definitions wrapping existing retrieval and DB functions."""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Coroutine

from src.db.projects import get_project
from src.rag.retrieve import smart_retrieve

logger = logging.getLogger(__name__)


@dataclass
class AgentTool:
    name: str
    description: str
    parameters: str  # Human-readable parameter description for the prompt
    execute: Callable[..., Coroutine[Any, Any, tuple[str, list[dict]]]]


async def _search_projects(query: str, top_k: int = 5) -> tuple[str, list[dict]]:
    """Search the project database using semantic retrieval.

    Returns (observation_text, source_projects_list).
    """
    rag = await smart_retrieve(query, similarity_threshold=0.0, top_k=top_k)

    if not rag.source_projects:
        return "No projects found matching that query.", []

    lines = [f"Found {len(rag.source_projects)} relevant projects:\n"]
    for i, p in enumerate(rag.source_projects, 1):
        tags = ", ".join(f"#{t}" for t in p.get("hashtags", []))
        lines.append(
            f"{i}. **{p['title']}** (ID: {p['id']})\n"
            f"   {p.get('short_description', '')}\n"
            f"   Tags: {tags}\n"
            f"   Idea: {p.get('idea_score', '?')}/10 | Complexity: {p.get('complexity_score', '?')}/10"
        )

    return "\n".join(lines), rag.source_projects


async def _get_project_details(project_id: int) -> tuple[str, list[dict]]:
    """Get full details for a specific project by ID.

    Returns (observation_text, source_projects_list).
    """
    project = get_project(project_id)
    if project is None:
        return f"No project found with ID {project_id}.", []

    tags = ", ".join(f"#{t}" for t in project.hashtags)
    urls = ", ".join(project.project_urls) if project.project_urls else "None"

    text = (
        f"**{project.title}** (ID: {project.id})\n"
        f"Description: {project.description}\n"
        f"Short description: {project.short_description}\n"
        f"Tags: {tags}\n"
        f"URLs: {urls}\n"
        f"Primary URL: {project.primary_url or 'None'}\n"
        f"Idea Score: {project.idea_score}/10 | Complexity Score: {project.complexity_score}/10\n"
        f"Source: {project.source or 'hn'}"
    )

    source = {
        "id": project.id,
        "title": project.title,
        "short_description": project.short_description,
        "similarity": 1.0,
        "hashtags": project.hashtags,
        "idea_score": project.idea_score,
        "complexity_score": project.complexity_score,
    }

    return text, [source]


# Tool registry
AGENT_TOOLS: list[AgentTool] = [
    AgentTool(
        name="search_projects",
        description="Search the Hacker News project database by semantic similarity. Use this to find projects related to a topic, technology, or concept.",
        parameters='query (str): The search query describing what projects to look for.\ntop_k (int, optional): Number of results to return. Default: 5.',
        execute=_search_projects,
    ),
    AgentTool(
        name="get_project_details",
        description="Get full details for a specific project by its ID. Use this when you need more information about a project that was already found by search.",
        parameters="project_id (int): The numeric ID of the project to retrieve.",
        execute=_get_project_details,
    ),
]


def get_tool(name: str) -> AgentTool | None:
    """Look up a tool by name."""
    for tool in AGENT_TOOLS:
        if tool.name == name:
            return tool
    return None


def format_tool_descriptions() -> str:
    """Format all tools into a text block for the system prompt."""
    parts = []
    for tool in AGENT_TOOLS:
        parts.append(
            f"Tool: {tool.name}\n"
            f"Description: {tool.description}\n"
            f"Parameters:\n{tool.parameters}"
        )
    return "\n\n".join(parts)


# OpenAI function-calling schemas (used by the tool-calling agent path)
TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_projects",
            "description": (
                "Search the Hacker News project database by semantic similarity. "
                "Use this to find projects related to a topic, technology, or concept."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query describing what projects to look for.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return. Default: 5.",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_project_details",
            "description": (
                "Get full details for a specific project by its ID. "
                "Use this when you need more information about a project found by search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "integer",
                        "description": "The numeric ID of the project to retrieve.",
                    },
                },
                "required": ["project_id"],
            },
        },
    },
]
