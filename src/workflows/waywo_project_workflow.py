"""
LlamaIndex workflow for processing waywo comments into structured project data.

This workflow takes a comment and:
1. Extracts project(s) from the text (handling multi-project comments)
2. Validates each project (filters out non-projects)
3. Fetches URL content via Firecrawl
4. Generates metadata (title, description, tags)
5. Scores the project (idea score, complexity score)
6. Returns structured WaywoProject data
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional

from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)

from src.embedding_client import (
    EmbeddingError,
    create_embedding_text,
    get_single_embedding,
)
from src.firecrawl_client import extract_urls_from_text, scrape_urls
from src.llm_config import get_llm, get_llm_for_structured_output
from src.workflows.events import (
    CommentInputEvent,
    EmbeddingGeneratedEvent,
    ExtractedProjectEvent,
    MetadataGeneratedEvent,
    ProjectCompleteEvent,
    ScoredProjectEvent,
    URLsFetchedEvent,
    ValidatedProjectEvent,
)

logger = logging.getLogger(__name__)


class WaywoProjectWorkflow(Workflow):
    """
    Workflow for processing a waywo comment into structured project data.

    Usage:
        workflow = WaywoProjectWorkflow(timeout=120)
        result = await workflow.run(
            comment_id=12345,
            comment_text="I'm building an AI app...",
            comment_author="user123",
        )
    """

    def __init__(
        self,
        *args,
        firecrawl_url: str = "http://localhost:3002",
        embedding_url: str = "http://192.168.5.96:8000",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.firecrawl_url = firecrawl_url
        self.embedding_url = embedding_url
        self.llm = get_llm()
        self.llm_structured = get_llm_for_structured_output()

    async def _log(self, ctx: Context, emoji: str, message: str) -> None:
        """Add a log entry with timestamp and emoji."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {emoji} {message}"

        logs = await ctx.store.get("logs") or []
        logs.append(log_entry)
        await ctx.store.set("logs", logs)
        logger.info(log_entry)

    @step
    async def start(self, ctx: Context, ev: StartEvent) -> CommentInputEvent:
        """Initialize the workflow with comment data."""
        # Initialize context
        await ctx.store.set("logs", [])
        await ctx.store.set("projects", [])
        await ctx.store.set("total_projects", 1)
        await ctx.store.set("comment_id", ev.comment_id)

        await self._log(ctx, "🚀", f"Starting workflow for comment {ev.comment_id}")

        return CommentInputEvent(
            comment_id=ev.comment_id,
            comment_text=ev.comment_text,
            comment_author=ev.get("comment_author"),
            comment_time=ev.get("comment_time"),
            parent_post_id=ev.get("parent_post_id"),
        )

    @step
    async def extract_projects(self, ctx: Context, ev: CommentInputEvent) -> ExtractedProjectEvent:
        """
        Extract individual project(s) from the comment text.

        For multi-project comments, sends additional events via context.
        """
        await self._log(ctx, "🔍", "Extracting projects from comment")

        comment_text = ev.comment_text or ""

        # Quick check for deleted/removed comments
        if comment_text.strip() in ["[deleted]", "[removed]", ""]:
            await self._log(ctx, "❌", "Comment is deleted/removed")
            await ctx.store.set("total_projects", 1)
            return ExtractedProjectEvent(
                comment_id=ev.comment_id,
                project_index=0,
                total_projects=1,
                raw_text=comment_text,
                original_comment_text=comment_text,
            )

        # Use LLM to identify and split projects
        prompt = f"""Analyze this Hacker News comment and identify distinct projects or products being discussed.

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

        try:
            response = await self.llm.acomplete(prompt)
            response_text = str(response).strip()

            # Try to parse JSON
            # Handle cases where LLM wraps in markdown code blocks
            if response_text.startswith("```"):
                response_text = re.sub(r"```json?\n?", "", response_text)
                response_text = response_text.replace("```", "").strip()

            projects = json.loads(response_text)

            if not isinstance(projects, list) or len(projects) == 0:
                projects = [comment_text]

        except (json.JSONDecodeError, Exception) as e:
            await self._log(ctx, "⚠️", f"Failed to parse projects, using full text: {e}")
            projects = [comment_text]

        await self._log(ctx, "📊", f"Found {len(projects)} project(s) in comment")
        await ctx.store.set("total_projects", len(projects))

        # Send additional events for multi-project comments
        for i in range(1, len(projects)):
            ctx.send_event(
                ExtractedProjectEvent(
                    comment_id=ev.comment_id,
                    project_index=i,
                    total_projects=len(projects),
                    raw_text=projects[i],
                    original_comment_text=comment_text,
                )
            )

        # Return the first project
        return ExtractedProjectEvent(
            comment_id=ev.comment_id,
            project_index=0,
            total_projects=len(projects),
            raw_text=projects[0],
            original_comment_text=comment_text,
        )

    @step
    async def validate_project(self, ctx: Context, ev: ExtractedProjectEvent) -> ValidatedProjectEvent:
        """
        Validate whether the extracted text represents a valid project/product.

        Filters out:
        - Deleted/removed comments
        - Personal tasks ("cleaning my garage")
        - Study/learning activities ("studying C#")
        - General discussions without a concrete project
        """
        await self._log(ctx, "✓", f"Validating project {ev.project_index + 1}/{ev.total_projects}")

        raw_text = ev.raw_text.strip()

        # Quick checks for obvious non-projects
        if raw_text in ["[deleted]", "[removed]", ""]:
            return ValidatedProjectEvent(
                **ev.model_dump(),
                is_valid=False,
                invalid_reason="deleted_or_removed",
            )

        if len(raw_text) < 20:
            return ValidatedProjectEvent(
                **ev.model_dump(),
                is_valid=False,
                invalid_reason="text_too_short",
            )

        # Use LLM to validate
        prompt = f"""Analyze this text from a Hacker News "What are you working on?" thread.

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

        try:
            response = await self.llm_structured.acomplete(prompt)
            response_text = str(response).strip()

            # Handle markdown code blocks
            if response_text.startswith("```"):
                response_text = re.sub(r"```json?\n?", "", response_text)
                response_text = response_text.replace("```", "").strip()

            result = json.loads(response_text)
            is_valid = result.get("is_valid", False)
            reason = result.get("reason", "")

            if is_valid:
                await self._log(ctx, "✅", f"Project validated: {reason[:50]}...")
            else:
                await self._log(ctx, "❌", f"Project invalid: {reason}")

            return ValidatedProjectEvent(
                **ev.model_dump(),
                is_valid=is_valid,
                invalid_reason=None if is_valid else reason,
            )

        except Exception as e:
            await self._log(ctx, "⚠️", f"Validation error, assuming valid: {e}")
            return ValidatedProjectEvent(
                **ev.model_dump(),
                is_valid=True,
                invalid_reason=None,
            )

    @step
    async def fetch_urls(self, ctx: Context, ev: ValidatedProjectEvent) -> URLsFetchedEvent:
        """
        Extract URLs from the project text and fetch their content via Firecrawl.
        """
        await self._log(ctx, "🔗", f"Extracting URLs from project {ev.project_index + 1}")

        # Extract URLs using firecrawl_client (handles validation and deduplication)
        cleaned_urls = extract_urls_from_text(ev.raw_text)

        await self._log(ctx, "📋", f"Found {len(cleaned_urls)} valid URLs")

        url_contents: dict[str, str] = {}
        url_errors: dict[str, str] = {}

        # Only fetch if project is valid and we have URLs
        if ev.is_valid and cleaned_urls:
            # Use firecrawl_client with retry logic
            results = await scrape_urls(
                urls=cleaned_urls,
                max_urls=5,
                firecrawl_url=self.firecrawl_url,
            )

            for result in results:
                if result.success and result.content:
                    url_contents[result.url] = result.content
                    await self._log(
                        ctx, "✅", f"Fetched {len(result.content)} chars from {result.url[:40]}..."
                    )
                elif result.error:
                    url_errors[result.url] = result.error
                    await self._log(ctx, "⚠️", f"Failed: {result.url[:40]}: {result.error}")

        return URLsFetchedEvent(
            comment_id=ev.comment_id,
            project_index=ev.project_index,
            total_projects=ev.total_projects,
            raw_text=ev.raw_text,
            original_comment_text=ev.original_comment_text,
            is_valid=ev.is_valid,
            invalid_reason=ev.invalid_reason,
            urls=cleaned_urls,
            url_contents=url_contents,
            url_errors=url_errors,
        )

    @step
    async def generate_metadata(self, ctx: Context, ev: URLsFetchedEvent) -> MetadataGeneratedEvent:
        """
        Generate metadata: title, descriptions, hashtags, and URL summaries.
        """
        await self._log(ctx, "📝", f"Generating metadata for project {ev.project_index + 1}")

        # Default values for invalid projects
        if not ev.is_valid:
            return MetadataGeneratedEvent(
                **ev.model_dump(),
                title="[Invalid Project]",
                short_description="Not a valid project",
                description=ev.invalid_reason or "This comment does not describe a valid project.",
                hashtags=[],
                url_summaries={},
            )

        # Build context from URL content
        url_context = ""
        if ev.url_contents:
            url_context = "\n\nContent from linked URLs:\n"
            for url, content in ev.url_contents.items():
                # Truncate for prompt
                truncated = content[:2000] if len(content) > 2000 else content
                url_context += f"\n--- {url} ---\n{truncated}\n"

        prompt = f"""Analyze this project from a Hacker News "What are you working on?" thread and generate metadata.

Project text:
{ev.raw_text}
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

        try:
            response = await self.llm_structured.acomplete(prompt)
            response_text = str(response).strip()

            # Handle markdown code blocks
            if response_text.startswith("```"):
                response_text = re.sub(r"```json?\n?", "", response_text)
                response_text = response_text.replace("```", "").strip()

            result = json.loads(response_text)

            title = result.get("title", "Untitled Project")
            short_desc = result.get("short_description", "No description")
            description = result.get("description", ev.raw_text[:200])
            hashtags = result.get("hashtags", [])
            url_summaries = result.get("url_summaries", {})

            # Validate hashtags
            hashtags = [
                tag.lower().strip("#")
                for tag in hashtags
                if isinstance(tag, str) and len(tag) < 30
            ][:5]

            await self._log(ctx, "✅", f"Generated metadata: {title}")

            return MetadataGeneratedEvent(
                **ev.model_dump(),
                title=title,
                short_description=short_desc,
                description=description,
                hashtags=hashtags,
                url_summaries=url_summaries,
            )

        except Exception as e:
            await self._log(ctx, "⚠️", f"Metadata generation error: {e}")
            return MetadataGeneratedEvent(
                **ev.model_dump(),
                title="Untitled Project",
                short_description="Project from HN",
                description=ev.raw_text[:200],
                hashtags=[],
                url_summaries={},
            )

    @step
    async def score_project(self, ctx: Context, ev: MetadataGeneratedEvent) -> ScoredProjectEvent:
        """
        Score the project on idea quality and complexity.
        """
        await self._log(ctx, "📊", f"Scoring project {ev.project_index + 1}: {ev.title}")

        # Default scores for invalid projects
        if not ev.is_valid:
            return ScoredProjectEvent(
                **ev.model_dump(),
                idea_score=1,
                complexity_score=1,
            )

        prompt = f"""Rate this project on two dimensions. Be fair but critical.

Project: {ev.title}
Description: {ev.description}
Original text: {ev.raw_text[:500]}

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

        try:
            response = await self.llm_structured.acomplete(prompt)
            response_text = str(response).strip()

            if response_text.startswith("```"):
                response_text = re.sub(r"```json?\n?", "", response_text)
                response_text = response_text.replace("```", "").strip()

            result = json.loads(response_text)

            idea_score = max(1, min(10, int(result.get("idea_score", 5))))
            complexity_score = max(1, min(10, int(result.get("complexity_score", 5))))

            await self._log(
                ctx,
                "📈",
                f"Scores: idea={idea_score}, complexity={complexity_score}",
            )

            return ScoredProjectEvent(
                **ev.model_dump(),
                idea_score=idea_score,
                complexity_score=complexity_score,
            )

        except Exception as e:
            await self._log(ctx, "⚠️", f"Scoring error, using defaults: {e}")
            return ScoredProjectEvent(
                **ev.model_dump(),
                idea_score=5,
                complexity_score=5,
            )

    @step
    async def generate_embedding(
        self, ctx: Context, ev: ScoredProjectEvent
    ) -> EmbeddingGeneratedEvent:
        """
        Generate embedding for semantic search using the embedding service.
        Combines title + description + hashtags for richer semantic representation.
        """
        await self._log(ctx, "🧠", f"Generating embedding for project {ev.project_index + 1}")

        embedding: list[float] | None = None

        # Only generate embedding for valid projects
        if ev.is_valid:
            try:
                # Create combined text for embedding
                embedding_text = create_embedding_text(
                    title=ev.title,
                    description=ev.description,
                    hashtags=ev.hashtags,
                )

                # Call embedding service
                embedding = await get_single_embedding(
                    text=embedding_text,
                    embedding_url=self.embedding_url,
                )

                await self._log(
                    ctx,
                    "✅",
                    f"Generated embedding with {len(embedding)} dimensions",
                )

            except EmbeddingError as e:
                await self._log(ctx, "⚠️", f"Embedding generation failed: {e}")
                # Continue without embedding - it's optional
            except Exception as e:
                await self._log(ctx, "⚠️", f"Unexpected embedding error: {e}")
        else:
            await self._log(ctx, "⏭️", "Skipping embedding for invalid project")

        return EmbeddingGeneratedEvent(
            **ev.model_dump(),
            embedding=embedding,
        )

    @step
    async def finalize(self, ctx: Context, ev: EmbeddingGeneratedEvent) -> StopEvent | None:
        """
        Finalize the project and collect results.
        """
        logs = await ctx.store.get("logs") or []
        await self._log(ctx, "✨", f"Finalizing project: {ev.title}")

        project_data = {
            "comment_id": ev.comment_id,
            "project_index": ev.project_index,
            "total_projects": ev.total_projects,
            "is_valid": ev.is_valid,
            "invalid_reason": ev.invalid_reason,
            "title": ev.title,
            "short_description": ev.short_description,
            "description": ev.description,
            "hashtags": ev.hashtags,
            "urls": ev.urls,
            "url_summaries": ev.url_summaries,
            "idea_score": ev.idea_score,
            "complexity_score": ev.complexity_score,
            "embedding": ev.embedding,
            "workflow_logs": list(logs),
        }

        # Store project in context
        projects = await ctx.store.get("projects") or []
        projects.append(project_data)
        await ctx.store.set("projects", projects)

        total_projects = await ctx.store.get("total_projects") or 1

        # Check if all projects from this comment are processed
        if len(projects) >= total_projects:
            await self._log(ctx, "🎉", f"All {total_projects} project(s) processed")
            final_logs = await ctx.store.get("logs") or []
            comment_id = await ctx.store.get("comment_id")

            return StopEvent(
                result={
                    "comment_id": comment_id,
                    "total_projects": total_projects,
                    "projects": projects,
                    "logs": final_logs,
                }
            )

        # More projects to process, wait for them
        return None
