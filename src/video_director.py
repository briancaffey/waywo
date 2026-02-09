"""
Video script generation prompt and director function.

The "director" takes project data and uses an LLM to generate a segmented
video script. Each segment contains narration text (for TTS) and a scene
description (for image generation via FLUX).
"""

import json
import logging
import re

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

VIDEO_SCRIPT_TEMPLATE = """You are a presenter introducing a tech project to a smart, tech-savvy audience. Your job is to clearly explain what this project does, why it's interesting, and who it's for. Each video will be narrated by a text-to-speech engine and illustrated with AI-generated images.

PROJECT:
Title: {title}
Summary: {short_description}
Description: {description}
Tags: {hashtags}
{url_context}
INSTRUCTIONS:

Pick a video style that fits this project:
- "energetic" — fast cuts, bold claims, excitement. Best for novel or consumer-facing projects.
- "calm" — measured pace, thoughtful tone. Best for developer tools, libraries, or technical infrastructure.
- "professional" — polished, confident, authoritative. Best for B2B, enterprise, or data-heavy projects.
- "playful" — light, fun, surprising. Best for games, creative tools, or quirky side projects.

Write 4-6 segments. The total narration MUST be between 80 and 150 words so the video runs 30-60 seconds.

SEGMENT TYPES (use each at most once, in this order):
1. "hook" — REQUIRED. One sentence that leads with the project's core value proposition or most striking capability. Be specific and direct — tell the viewer what this project actually does. Do NOT start with "Have you ever", "Imagine", "What if", or "In a world". Do NOT use vague creative hooks like metaphors, rhetorical questions, or dramatic stats.
2. "introduction" — REQUIRED. Name the project and explain what it is in plain terms. 1-2 sentences.
3. "features" — Highlight 1-3 specific, concrete capabilities. Describe what each feature does, not how it makes the user feel.
4. "audience" — Who is this for and what problem does it solve for them?
5. "closing" — REQUIRED. End with a concise call to action or summary of why this project matters. One sentence.

NARRATION RULES:
- Write for the SPOKEN word. Use contractions, short sentences, natural rhythm.
- Never use markdown, bullet points, or formatting — pure speech.
- Mention the project name at least once.
- Be direct and informative. State what things do, not how they feel.
- Avoid clichés: "game-changer", "revolutionary", "next-level", "takes X to the next level", "the future of", "reimagining".
- Avoid vague praise: "elegant", "seamless", "powerful", "beautiful". Use specific descriptions instead.
- Each segment: 1-3 sentences, 15-35 words.

SCENE DESCRIPTION RULES:
Each scene_description will be used verbatim as a FLUX 2 Klein image generation prompt. FLUX Klein does NOT auto-enhance prompts — what you write is exactly what you get. Write each scene as flowing prose, like a novelist describing a painting. NEVER use comma-separated keyword lists.

CRITICAL: Each scene must visually relate to the actual project content — the domain, technology, or what's being built. Think about what the project does and create images that conceptually represent that subject matter. For example:
- A code editor project → an artful arrangement of mechanical typewriter keys or precision instruments
- A weather app → dramatic cloudscapes, atmospheric phenomena, meteorological instruments
- A music tool → sculptural audio waveforms, resonating strings, analog dials
- A database tool → crystalline storage structures, organized mineral formations, archival shelves

The image should connect to what's being narrated in that specific segment.

Structure: Subject first → Setting → Details (textures, materials) → Lighting → Atmosphere.

Front-load the subject. The most important visual element MUST come first. Do not bury it in atmospheric description.

LIGHTING IS MANDATORY in every scene. Describe:
- Source: natural, artificial, ambient, emanating from objects
- Quality: soft, harsh, diffused, direct, dappled
- Direction: side-lit, backlit, overhead, rim-lit, from below
- Temperature: warm golden, cool blue, neutral white, amber
- Interaction: how light catches surfaces, casts shadows, creates reflections

Include textures and material qualities: brushed metal, frosted glass, weathered wood, liquid mercury, woven fabric, cracked stone. Sensory details make scenes tangible.

Each scene description must be 40-70 words. Shorter prompts produce vague results with Klein.

End each scene description with style and mood tags in this format: "Style: [aesthetic]. Mood: [emotion, emotion]."

NO text, words, logos, UI screenshots, or realistic human faces.
Each scene must be visually DISTINCT — vary subjects, color palettes, lighting setups, and materials across segments.

VISUAL STYLE (per segment):
- "abstract" — geometric shapes, patterns, gradients
- "cinematic" — dramatic lighting, depth of field, moody
- "minimal" — clean lines, whitespace, simple forms
- "vibrant" — bold saturated colors, high energy

TRANSITIONS (per segment):
- "fade" — smooth dissolve (good for calm/professional)
- "cut" — hard cut (good for energetic/punchy)
- "slide_left" — directional wipe (good for progression/features)
- "zoom_in" — zoom transition (good for reveals/closings)

Return ONLY valid JSON, no other text:
{{
  "video_title": "Short catchy title under 60 characters",
  "video_style": "energetic | calm | professional | playful",
  "target_duration_seconds": 45,
  "segments": [
    {{
      "segment_id": 1,
      "segment_type": "hook",
      "narration_text": "Spoken narration here...",
      "scene_description": "A mechanical compass resting on a weathered topographic map, its brass needle catching warm side-light from the left. Fine engraved gridlines and elevation contours spread beneath it, with soft shadows pooling in the paper's creases. Style: cinematic still life. Mood: precision, exploration.",
      "visual_style": "abstract | cinematic | minimal | vibrant",
      "transition": "fade | cut | slide_left | zoom_in"
    }}
  ]
}}"""


def video_script_prompt(
    title: str,
    short_description: str,
    description: str,
    hashtags: list[str],
    url_summaries: dict[str, str] | None = None,
) -> str:
    """Format the video script prompt with project data."""
    hashtag_str = ", ".join(hashtags) if hashtags else "none"

    url_context = ""
    if url_summaries:
        url_lines = []
        for url, summary in url_summaries.items():
            url_lines.append(f"  {url}: {summary}")
        url_context = "Linked pages:\n" + "\n".join(url_lines)

    return VIDEO_SCRIPT_TEMPLATE.format(
        title=title,
        short_description=short_description,
        description=description,
        hashtags=hashtag_str,
        url_context=url_context,
    )


# ---------------------------------------------------------------------------
# Director function
# ---------------------------------------------------------------------------

# Valid values for validation
VALID_STYLES = {"energetic", "calm", "professional", "playful"}
VALID_SEGMENT_TYPES = {"hook", "introduction", "features", "audience", "closing"}
VALID_VISUAL_STYLES = {"abstract", "cinematic", "minimal", "vibrant"}
VALID_TRANSITIONS = {"fade", "cut", "slide_left", "zoom_in"}


def _parse_llm_json(response_text: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = response_text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        text = re.sub(r"```json?\n?", "", text)
        text = text.replace("```", "").strip()

    return json.loads(text)


def _validate_script(script: dict) -> dict:
    """Validate and normalize a parsed video script, applying sensible defaults."""
    # Top-level fields
    if not isinstance(script.get("video_title"), str) or not script["video_title"]:
        script["video_title"] = "Untitled Video"

    script["video_title"] = script["video_title"][:60]

    if script.get("video_style") not in VALID_STYLES:
        script["video_style"] = "energetic"

    if not isinstance(script.get("target_duration_seconds"), (int, float)):
        script["target_duration_seconds"] = 45
    script["target_duration_seconds"] = max(
        20, min(60, int(script["target_duration_seconds"]))
    )

    # Segments
    segments = script.get("segments")
    if not isinstance(segments, list) or len(segments) == 0:
        raise ValueError("Script must contain at least one segment")

    validated = []
    for i, seg in enumerate(segments):
        if not isinstance(seg, dict):
            continue

        validated_seg = {
            "segment_id": i + 1,
            "segment_type": (
                seg.get("segment_type", "features")
                if seg.get("segment_type") in VALID_SEGMENT_TYPES
                else "features"
            ),
            "narration_text": str(seg.get("narration_text", "")).strip(),
            "scene_description": str(seg.get("scene_description", "")).strip(),
            "visual_style": (
                seg.get("visual_style", "abstract")
                if seg.get("visual_style") in VALID_VISUAL_STYLES
                else "abstract"
            ),
            "transition": (
                seg.get("transition", "fade")
                if seg.get("transition") in VALID_TRANSITIONS
                else "fade"
            ),
        }

        # Skip segments with empty narration
        if not validated_seg["narration_text"]:
            continue

        # Default scene description if missing
        if not validated_seg["scene_description"]:
            validated_seg["scene_description"] = (
                "Luminous geometric shapes drift through a deep indigo void, "
                "their faceted surfaces catching soft directional light from "
                "the upper right. Faint prismatic reflections scatter across "
                "a smooth dark ground plane below. "
                "Style: abstract digital art. Mood: contemplative, futuristic."
            )

        validated.append(validated_seg)

    if len(validated) == 0:
        raise ValueError("No valid segments with narration text found")

    script["segments"] = validated
    return script


async def generate_video_script(
    title: str,
    short_description: str,
    description: str,
    hashtags: list[str],
    url_summaries: dict[str, str] | None = None,
    llm=None,
) -> dict:
    """
    Generate a video script for a project using the LLM.

    Args:
        title: Project title.
        short_description: Brief 5-10 word description.
        description: Full project description (1-5 sentences).
        hashtags: Project tags.
        url_summaries: Optional URL -> summary mapping for linked pages.
        llm: Optional LLM instance (uses creative config by default).

    Returns:
        Validated script dict with video_title, video_style,
        target_duration_seconds, and segments list.

    Raises:
        ValueError: If the LLM response cannot be parsed or validated.
    """
    if llm is None:
        from src.llm_config import get_llm_for_creative_output

        llm = get_llm_for_creative_output()

    prompt = video_script_prompt(
        title=title,
        short_description=short_description,
        description=description,
        hashtags=hashtags,
        url_summaries=url_summaries,
    )

    logger.info(f"🎬 Generating video script for: {title}")

    response = await llm.acomplete(prompt)
    response_text = str(response).strip()

    logger.debug(f"LLM response length: {len(response_text)} chars")

    script = _parse_llm_json(response_text)
    script = _validate_script(script)

    total_words = sum(
        len(seg["narration_text"].split()) for seg in script["segments"]
    )
    logger.info(
        f"🎬 Script generated: {script['video_title']} "
        f"({len(script['segments'])} segments, {total_words} words, "
        f"style={script['video_style']})"
    )

    return script
