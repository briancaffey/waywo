"""
NeMo DataDesigner pipeline definition for synthetic project generation.

Defines the column pipeline that transforms tag seeds into full
WaywoProject records. See NDD_PLAN.md for the data flow diagram.
"""

import json
import logging
from collections import Counter

from pydantic import BaseModel, Field

from data_designer.config.column_configs import (
    ExpressionColumnConfig,
    LLMJudgeColumnConfig,
    LLMStructuredColumnConfig,
    LLMTextColumnConfig,
    SamplerColumnConfig,
    Score,
)
from data_designer.config.config_builder import DataDesignerConfigBuilder
from data_designer.config.models import ModelConfig
from data_designer.config.sampler_params import (
    CategorySamplerParams,
    SubcategorySamplerParams,
    UniformSamplerParams,
)

logger = logging.getLogger(__name__)

# Target audience personas for diversity in generation
TARGET_AUDIENCES = [
    "indie hackers",
    "enterprise developers",
    "data scientists",
    "students and learners",
    "open source contributors",
    "startup founders",
    "devops engineers",
    "frontend developers",
    "backend engineers",
    "mobile developers",
    "security researchers",
    "product managers",
    "hobbyist programmers",
    "creative technologists",
]


class ProjectMetadata(BaseModel):
    """Schema for the LLM structured extraction column."""

    title: str = Field(description="A concise, memorable project name (2-5 words)")
    short_description: str = Field(
        description="A brief tagline describing the project (5-10 words)"
    )
    description: str = Field(
        description="A clear 1-3 sentence description of what the project does and why it matters"
    )
    hashtags: list[str] = Field(
        description="3-5 lowercase hyphenated tags describing the project domain and tech"
    )


def build_tag_cooccurrence(
    projects: list,
) -> dict[str, list[tuple[str, int]]]:
    """Compute tag co-occurrence from existing projects.

    For each tag, find which other tags most commonly appear alongside it.

    Args:
        projects: List of WaywoProject objects (or anything with .hashtags list).

    Returns:
        Dict mapping each tag to a list of (co_tag, count) tuples,
        sorted by count descending.
    """
    cooccurrence: dict[str, Counter] = {}

    for project in projects:
        tags = project.hashtags if isinstance(project.hashtags, list) else []
        for tag in tags:
            if tag not in cooccurrence:
                cooccurrence[tag] = Counter()
            for other_tag in tags:
                if other_tag != tag:
                    cooccurrence[tag][other_tag] += 1

    result = {}
    for tag, counter in cooccurrence.items():
        result[tag] = counter.most_common()

    logger.info(
        f"Built tag co-occurrence map: {len(result)} tags, "
        f"avg {sum(len(v) for v in result.values()) / max(len(result), 1):.0f} co-tags each"
    )
    return result


def _build_subcategory_values(
    tag_cooccurrence: dict[str, list[tuple[str, int]]],
    seed_tags: list[str] | None,
    all_tags: list[str],
    top_n: int = 10,
) -> dict[str, list[str]]:
    """Build the subcategory mapping for each primary tag.

    For each possible primary tag value, picks the top co-occurring tags
    as possible secondary tags. Falls back to a general pool if a tag
    has no co-occurrence data.

    Returns:
        Dict mapping primary tag -> list of possible secondary tags.
    """
    # Determine which tags will be primary_tag values
    primary_tags = seed_tags if seed_tags else all_tags

    # General fallback pool: most common tags overall
    all_counts: Counter = Counter()
    for tag, cotags in tag_cooccurrence.items():
        for cotag, count in cotags:
            all_counts[cotag] += count
    fallback_tags = [t for t, _ in all_counts.most_common(top_n)]

    subcategory_map = {}
    for tag in primary_tags:
        if tag in tag_cooccurrence and tag_cooccurrence[tag]:
            cotags = [t for t, _ in tag_cooccurrence[tag][:top_n]]
            # Ensure we have at least 2 options
            if len(cotags) < 2:
                cotags = list(set(cotags + fallback_tags))[:top_n]
            subcategory_map[tag] = cotags
        else:
            # Tag not in co-occurrence data; use fallback minus itself
            subcategory_map[tag] = [t for t in fallback_tags if t != tag][:top_n]

    return subcategory_map


def build_pipeline_config(
    models: list[ModelConfig],
    seed_tags: list[str] | None = None,
    tag_cooccurrence: dict[str, list[tuple[str, int]]] | None = None,
    all_tags: list[str] | None = None,
) -> DataDesignerConfigBuilder:
    """Build the full DataDesigner pipeline configuration.

    Args:
        models: List of ModelConfig from build_ndd_models().
        seed_tags: User-provided seed tags (None for "surprise me" mode).
        tag_cooccurrence: Co-occurrence map from build_tag_cooccurrence().
        all_tags: Full tag vocabulary with frequency info. Used when
            seed_tags is None to weight the primary_tag sampler.

    Returns:
        Configured DataDesignerConfigBuilder ready for preview() or create().
    """
    tag_cooccurrence = tag_cooccurrence or {}
    all_tags = all_tags or []

    config = DataDesignerConfigBuilder(model_configs=models)

    # --- Column 1: primary_tag (SamplerColumn — CATEGORY) ---
    if seed_tags:
        primary_values = seed_tags
    elif all_tags:
        primary_values = all_tags
    else:
        primary_values = ["ai", "web", "devops", "saas", "open-source"]

    config.add_column(
        SamplerColumnConfig(
            name="primary_tag",
            sampler_type="category",
            params=CategorySamplerParams(values=primary_values),
        )
    )

    # --- Column 2: secondary_tags (SamplerColumn — SUBCATEGORY) ---
    subcategory_values = _build_subcategory_values(
        tag_cooccurrence, seed_tags, all_tags
    )

    # Only add subcategory if we have valid mappings
    if subcategory_values and all(
        len(v) > 0 for v in subcategory_values.values()
    ):
        config.add_column(
            SamplerColumnConfig(
                name="secondary_tags",
                sampler_type="subcategory",
                params=SubcategorySamplerParams(
                    category="primary_tag",
                    values=subcategory_values,
                ),
            )
        )
        secondary_ref = "{{ secondary_tags }}"
    else:
        # Fallback: no subcategory, just use primary tag
        secondary_ref = ""

    # --- Column 3: target_audience (SamplerColumn — CATEGORY) ---
    config.add_column(
        SamplerColumnConfig(
            name="target_audience",
            sampler_type="category",
            params=CategorySamplerParams(values=TARGET_AUDIENCES),
        )
    )

    # --- Column 4: target_complexity (SamplerColumn — UNIFORM 1-10) ---
    config.add_column(
        SamplerColumnConfig(
            name="target_complexity",
            sampler_type="uniform",
            params=UniformSamplerParams(low=1.0, high=10.0, decimal_places=0),
            convert_to="int",
        )
    )

    # --- Column 5: project_idea (LLMTextColumn) ---
    # When the user provides multiple seed tags, we want every generated idea
    # to incorporate ALL of them — not just the one picked by the sampler.
    if seed_tags and len(seed_tags) > 1:
        seed_tag_line = (
            f"REQUIRED themes (combine ALL of these): {', '.join(seed_tags)}\n"
            f"Lead technology/domain: {{{{ primary_tag }}}}"
        )
    else:
        seed_tag_line = "Primary technology/domain: {{ primary_tag }}"

    idea_prompt = f"""{seed_tag_line}
{f'Related technologies: {secondary_ref}' if secondary_ref else ''}
Target audience: {{{{ target_audience }}}}
Target complexity: {{{{ target_complexity }}}}/10

Generate a creative and specific software project idea that combines all of the themes above.

Write 2-3 paragraphs describing:
1. What the project does and the problem it solves
2. Key technical features and how it works
3. What makes it interesting or unique

Be specific and creative. Include concrete details about the implementation approach.
The project should be realistic and buildable by a small team or solo developer."""

    config.add_column(
        LLMTextColumnConfig(
            name="project_idea",
            prompt=idea_prompt,
            model_alias="waywo-creative",
            system_prompt="You are a creative software engineer who generates innovative but realistic project ideas. Focus on practical projects that solve real problems.",
        )
    )

    # --- Column 6: metadata (LLMStructuredColumn) ---
    config.add_column(
        LLMStructuredColumnConfig(
            name="metadata",
            prompt=f"""Extract structured metadata from this project idea.

Project idea:
{{{{ project_idea }}}}

Primary tag: {{{{ primary_tag }}}}
{f'All seed tags (MUST include all): {", ".join(seed_tags)}' if seed_tags and len(seed_tags) > 1 else ''}

Extract a concise title, a brief tagline, a clear description, and relevant hashtags.
For hashtags: use lowercase, hyphenated tags (e.g., "machine-learning", "web-dev").
Include the primary tag{' and all seed tags' if seed_tags and len(seed_tags) > 1 else ''} plus 2-4 additional relevant tags. Prefer existing common tags
over inventing new ones.""",
            model_alias="waywo-structured",
            output_format=ProjectMetadata,
        )
    )

    # --- Column 7: idea_quality (LLMJudgeColumn) ---
    config.add_column(
        LLMJudgeColumnConfig(
            name="idea_quality",
            prompt="""Evaluate this project idea:

Title: {{ metadata.title }}
Description: {{ metadata.description }}
Tags: {{ metadata.hashtags }}
Target complexity: {{ target_complexity }}/10""",
            model_alias="waywo-judge",
            scores=[
                Score(
                    name="idea_score",
                    description="How innovative, useful, and interesting is this project idea? Consider originality, potential impact, and whether it solves a real problem.",
                    options={
                        1: "Trivial or unoriginal — a basic tutorial project",
                        2: "Very common idea with no distinguishing features",
                        3: "Below average — exists in many forms already",
                        4: "Slightly below average — some merit but uninspired",
                        5: "Average — decent idea, moderate novelty",
                        6: "Above average — interesting angle or combination",
                        7: "Good — creative approach with clear value",
                        8: "Very good — novel and compelling idea",
                        9: "Excellent — highly innovative with strong potential",
                        10: "Exceptional — groundbreaking concept",
                    },
                ),
                Score(
                    name="complexity_score",
                    description="How technically complex is this project to build? Consider the breadth of technologies, system design challenges, and implementation difficulty.",
                    options={
                        1: "Trivial — a single script or basic CRUD app",
                        2: "Very simple — minimal moving parts",
                        3: "Simple — standard web app or CLI tool",
                        4: "Below moderate — some integration work needed",
                        5: "Moderate — multiple components, some complexity",
                        6: "Above moderate — significant architecture decisions",
                        7: "Complex — distributed systems or ML pipelines",
                        8: "Very complex — multiple services, advanced algorithms",
                        9: "Highly complex — cutting-edge tech, major engineering",
                        10: "Extremely complex — research-level difficulty",
                    },
                ),
            ],
        )
    )

    # --- Columns 8-11: Expression columns to flatten metadata ---
    config.add_column(
        ExpressionColumnConfig(
            name="title",
            expr="{{ metadata.title }}",
        )
    )
    config.add_column(
        ExpressionColumnConfig(
            name="short_description",
            expr="{{ metadata.short_description }}",
        )
    )
    config.add_column(
        ExpressionColumnConfig(
            name="description",
            expr="{{ metadata.description }}",
        )
    )
    config.add_column(
        ExpressionColumnConfig(
            name="hashtags",
            expr="{{ metadata.hashtags }}",
        )
    )

    logger.info(
        f"Built NDD pipeline: {config.num_columns_of_type('sampler')} samplers, "
        f"{config.num_columns_of_type('llm-text')} LLM text, "
        f"{config.num_columns_of_type('llm-structured')} structured, "
        f"{config.num_columns_of_type('llm-judge')} judge, "
        f"{config.num_columns_of_type('expression')} expression"
    )
    return config
