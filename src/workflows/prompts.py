"""
Centralized prompt templates for all workflow steps.

Each prompt is defined as a function that accepts the dynamic inputs and returns
the formatted string. The WORKFLOW_STEPS registry makes every step and its
prompt inspectable via the API.
"""


# ---------------------------------------------------------------------------
# 1. Project Extraction
# ---------------------------------------------------------------------------
EXTRACT_PROJECTS_TEMPLATE = """Analyze this Hacker News comment and identify distinct projects or products being discussed.

Comment:
{comment_text}

Instructions:
1. If the comment describes ONE project/product, return a JSON array with one element containing the full text.
2. If the comment lists MULTIPLE distinct projects (e.g., "Project A: ..., Project B: ..."), split them and return each as a separate element.
3. Each element should contain enough context to understand the project independently.
4. If it's not about any project/product (e.g., just a question, greeting, or off-topic), return a single element with the original text.

Return ONLY a valid JSON array of strings, nothing else. Example:
["First project description...", "Second project description..."]

If there's only one project or it's not a project at all:
["The complete text..."]"""


def extract_projects_prompt(comment_text: str) -> str:
    return EXTRACT_PROJECTS_TEMPLATE.format(comment_text=comment_text)


# ---------------------------------------------------------------------------
# 2. Project Validation
# ---------------------------------------------------------------------------
VALIDATE_PROJECT_TEMPLATE = """Analyze this text from a Hacker News "What are you working on?" thread.

Text:
{raw_text}

Determine if this describes a VALID PROJECT or PRODUCT.

A VALID project is:
- A software application, website, tool, or service being built
- A hardware product or physical invention
- A creative work (game, book, course, art project) with tangible output
- An open source library or framework
- A startup or business venture
- A technical craft or specialized skill project

NOT valid (should be filtered):
- Personal life activities ("cleaning garage", "moving house")
- General learning/studying without building something ("studying Python", "reading about ML")
- Just asking questions or making comments
- Job hunting or career discussions
- Vague statements without concrete deliverables

Return a JSON object with exactly these fields:
{{
  "is_valid": true/false,
  "reason": "brief explanation"
}}

Return ONLY the JSON, nothing else."""


def validate_project_prompt(raw_text: str) -> str:
    return VALIDATE_PROJECT_TEMPLATE.format(raw_text=raw_text)


# ---------------------------------------------------------------------------
# 3. Metadata Generation
# ---------------------------------------------------------------------------
GENERATE_METADATA_TEMPLATE = """Analyze this project from a Hacker News "What are you working on?" thread and generate metadata.

Project text:
{raw_text}
{url_context}

Generate the following metadata as a JSON object:

1. "title": The project/product name. If not explicitly stated, create a concise descriptive title (3-7 words).

2. "short_description": A very brief description in 5-10 words that captures what it is.

3. "description": A 1-2 sentence description explaining what the project is and what it does. Start with the type of thing it is.

4. "hashtags": An array of 3-5 single-word tags or common acronyms (lowercase) that describe the project. Examples: ["ai", "python", "productivity", "saas", "opensource"]

5. "url_summaries": An object mapping each URL to a brief (1-2 sentence) summary of what that page contains. Only include URLs that were successfully fetched.

Return ONLY valid JSON matching this structure:
{{
  "title": "Project Name",
  "short_description": "Brief 5-10 word description",
  "description": "One or two sentences describing the project.",
  "hashtags": ["tag1", "tag2", "tag3"],
  "url_summaries": {{"https://example.com": "Summary of the page content"}}
}}"""


def generate_metadata_prompt(raw_text: str, url_context: str) -> str:
    return GENERATE_METADATA_TEMPLATE.format(raw_text=raw_text, url_context=url_context)


# ---------------------------------------------------------------------------
# 4. Project Scoring
# ---------------------------------------------------------------------------
SCORE_PROJECT_TEMPLATE = """Rate this project on two dimensions. Be fair but critical.

Project: {title}
Description: {description}
Original text: {raw_text}

Rate from 1-10 on:

1. **Idea Score** (how good/promising is the idea):
   - 1-2: Very weak idea, no clear value proposition
   - 3-4: Basic idea, nothing particularly novel or useful
   - 5-6: Decent idea with some merit, addresses a real need
   - 7-8: Good idea with clear value, interesting approach
   - 9-10: Excellent idea, innovative, strong market potential

Consider: Market need, uniqueness, potential impact, target audience clarity

2. **Complexity Score** (technical/implementation complexity):
   - 1-2: Very simple, could be built in a day
   - 3-4: Simple project, basic features
   - 5-6: Moderate complexity, multiple components
   - 7-8: Complex project, significant engineering
   - 9-10: Highly complex, cutting-edge technology

Consider: Technical stack, features mentioned, scale, integrations

Return ONLY a JSON object:
{{
  "idea_score": <number 1-10>,
  "complexity_score": <number 1-10>,
  "idea_reasoning": "brief explanation",
  "complexity_reasoning": "brief explanation"
}}"""


def score_project_prompt(title: str, description: str, raw_text: str) -> str:
    return SCORE_PROJECT_TEMPLATE.format(
        title=title, description=description, raw_text=raw_text
    )


# ---------------------------------------------------------------------------
# 5. Chatbot System Prompt
# ---------------------------------------------------------------------------
CHATBOT_SYSTEM_PROMPT = """You are an AI assistant that helps users explore projects from Hacker News "What are you working on?" threads.

You have access to a database of projects that people have shared. When answering questions:

1. Base your answers on the provided project context
2. If relevant projects are found, mention specific projects by name
3. Include relevant details like descriptions, tags, and scores when helpful
4. If no relevant projects are found, say so honestly
5. Be helpful and conversational

The projects come from monthly "What are you working on?" threads on Hacker News where developers share what they're building."""


# ---------------------------------------------------------------------------
# 6. Chatbot Response Generation
# ---------------------------------------------------------------------------
CHATBOT_RESPONSE_TEMPLATE = """{system_prompt}

Context from project database:
{context}

User question: {query}

Please provide a helpful response based on the project context above."""


def chatbot_response_prompt(query: str, context: str) -> str:
    return CHATBOT_RESPONSE_TEMPLATE.format(
        system_prompt=CHATBOT_SYSTEM_PROMPT, context=context, query=query
    )


# ---------------------------------------------------------------------------
# Workflow Steps Registry
# ---------------------------------------------------------------------------
WORKFLOW_STEPS = [
    {
        "step": 1,
        "name": "extract_projects",
        "title": "Extract Projects",
        "description": "Identify and split multiple projects from a single HN comment.",
        "workflow": "WaywoProjectWorkflow",
        "input_event": "CommentInputEvent",
        "output_event": "ExtractedProjectEvent",
        "prompt_template": EXTRACT_PROJECTS_TEMPLATE,
        "template_variables": ["comment_text"],
    },
    {
        "step": 2,
        "name": "validate_project",
        "title": "Validate Project",
        "description": "Determine whether extracted text describes a real project or should be filtered out.",
        "workflow": "WaywoProjectWorkflow",
        "input_event": "ExtractedProjectEvent",
        "output_event": "ValidatedProjectEvent",
        "prompt_template": VALIDATE_PROJECT_TEMPLATE,
        "template_variables": ["raw_text"],
    },
    {
        "step": 3,
        "name": "fetch_urls",
        "title": "Fetch URLs",
        "description": "Extract URLs from text and scrape their content via Firecrawl. No LLM prompt — pure URL fetching.",
        "workflow": "WaywoProjectWorkflow",
        "input_event": "ValidatedProjectEvent",
        "output_event": "URLsFetchedEvent",
        "prompt_template": None,
        "template_variables": [],
    },
    {
        "step": 4,
        "name": "generate_metadata",
        "title": "Generate Metadata",
        "description": "Generate title, short description, full description, hashtags, and URL summaries.",
        "workflow": "WaywoProjectWorkflow",
        "input_event": "URLsFetchedEvent",
        "output_event": "MetadataGeneratedEvent",
        "prompt_template": GENERATE_METADATA_TEMPLATE,
        "template_variables": ["raw_text", "url_context"],
    },
    {
        "step": 5,
        "name": "score_project",
        "title": "Score Project",
        "description": "Rate the project on idea quality (1-10) and implementation complexity (1-10).",
        "workflow": "WaywoProjectWorkflow",
        "input_event": "MetadataGeneratedEvent",
        "output_event": "ScoredProjectEvent",
        "prompt_template": SCORE_PROJECT_TEMPLATE,
        "template_variables": ["title", "description", "raw_text"],
    },
    {
        "step": 6,
        "name": "generate_embedding",
        "title": "Generate Embedding",
        "description": "Create a vector embedding for semantic search. No LLM prompt — calls the embedding service.",
        "workflow": "WaywoProjectWorkflow",
        "input_event": "ScoredProjectEvent",
        "output_event": "EmbeddingGeneratedEvent",
        "prompt_template": None,
        "template_variables": [],
    },
    {
        "step": 7,
        "name": "finalize",
        "title": "Finalize",
        "description": "Collect all results and mark the comment as processed.",
        "workflow": "WaywoProjectWorkflow",
        "input_event": "EmbeddingGeneratedEvent",
        "output_event": "StopEvent",
        "prompt_template": None,
        "template_variables": [],
    },
    {
        "step": 8,
        "name": "chatbot_response",
        "title": "Chatbot Response (RAG)",
        "description": "Generate a conversational response using retrieved project context.",
        "workflow": "WaywoChatbotWorkflow",
        "input_event": "user query + retrieved projects",
        "output_event": "ChatbotResult",
        "prompt_template": CHATBOT_RESPONSE_TEMPLATE,
        "template_variables": ["system_prompt", "context", "query"],
    },
]
