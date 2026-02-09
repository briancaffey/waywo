"""Tests for video script generation (director)."""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.video_director import (
    generate_video_script,
    video_script_prompt,
    _parse_llm_json,
    _validate_script,
    VALID_STYLES,
    VALID_SEGMENT_TYPES,
    VALID_VISUAL_STYLES,
    VALID_TRANSITIONS,
)

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_PROJECT = {
    "title": "CodeScope",
    "short_description": "AI-powered code review assistant",
    "description": (
        "CodeScope is an AI-powered code review tool that analyzes pull requests "
        "for bugs, security issues, and style violations. It integrates with GitHub "
        "and GitLab, providing inline suggestions and a summary dashboard."
    ),
    "hashtags": ["ai", "devtools", "codereview", "github"],
}

SAMPLE_LLM_RESPONSE = json.dumps(
    {
        "video_title": "CodeScope: Your AI Code Reviewer",
        "video_style": "professional",
        "target_duration_seconds": 42,
        "segments": [
            {
                "segment_id": 1,
                "segment_type": "hook",
                "narration_text": "Your pull requests deserve better than a rubber stamp.",
                "scene_description": (
                    "A glowing magnifying glass hovering over streams of colorful "
                    "code on a deep navy background, light refracting through the lens"
                ),
                "visual_style": "cinematic",
                "transition": "fade",
            },
            {
                "segment_id": 2,
                "segment_type": "introduction",
                "narration_text": (
                    "Meet CodeScope, an AI assistant that reviews your code the way "
                    "a senior engineer would."
                ),
                "scene_description": (
                    "Abstract isometric 3D workspace with floating code blocks and "
                    "a friendly robot silhouette, soft purple and teal palette"
                ),
                "visual_style": "abstract",
                "transition": "cut",
            },
            {
                "segment_id": 3,
                "segment_type": "features",
                "narration_text": (
                    "It catches bugs, flags security holes, and suggests style fixes "
                    "right inside your pull request."
                ),
                "scene_description": (
                    "Three glowing shield icons in a row — red for bugs, yellow for "
                    "security, green for style — on a dark grid background"
                ),
                "visual_style": "vibrant",
                "transition": "slide_left",
            },
            {
                "segment_id": 4,
                "segment_type": "audience",
                "narration_text": (
                    "If you're shipping code on GitHub or GitLab, CodeScope has your back."
                ),
                "scene_description": (
                    "Connected nodes forming a branching tree structure, each node "
                    "a soft glowing orb, on a dark background with subtle grid lines"
                ),
                "visual_style": "minimal",
                "transition": "fade",
            },
            {
                "segment_id": 5,
                "segment_type": "closing",
                "narration_text": "Stop reviewing alone. Let CodeScope watch your six.",
                "scene_description": (
                    "A single bright blue star bursting with light rays on a deep "
                    "space background, particles scattering outward"
                ),
                "visual_style": "cinematic",
                "transition": "zoom_in",
            },
        ],
    }
)


# ---------------------------------------------------------------------------
# Prompt formatting tests
# ---------------------------------------------------------------------------


class TestVideoScriptPrompt:
    def test_prompt_includes_project_data(self):
        prompt = video_script_prompt(
            title="TestProject",
            short_description="A test project",
            description="A project for testing things.",
            hashtags=["python", "testing"],
        )

        assert "TestProject" in prompt
        assert "A test project" in prompt
        assert "A project for testing things." in prompt
        assert "python, testing" in prompt

    def test_prompt_includes_url_summaries(self):
        prompt = video_script_prompt(
            title="TestProject",
            short_description="A test project",
            description="A project for testing.",
            hashtags=["python"],
            url_summaries={
                "https://example.com": "Homepage with docs",
                "https://github.com/test": "Source code repo",
            },
        )

        assert "https://example.com" in prompt
        assert "Homepage with docs" in prompt
        assert "https://github.com/test" in prompt
        assert "Source code repo" in prompt
        assert "Linked pages:" in prompt

    def test_prompt_handles_empty_hashtags(self):
        prompt = video_script_prompt(
            title="TestProject",
            short_description="A test project",
            description="A project for testing.",
            hashtags=[],
        )

        assert "none" in prompt

    def test_prompt_handles_no_url_summaries(self):
        prompt = video_script_prompt(
            title="TestProject",
            short_description="A test project",
            description="A project for testing.",
            hashtags=["python"],
            url_summaries=None,
        )

        assert "Linked pages:" not in prompt

    def test_prompt_contains_json_schema(self):
        prompt = video_script_prompt(
            title="X",
            short_description="X",
            description="X",
            hashtags=[],
        )

        assert '"video_title"' in prompt
        assert '"segments"' in prompt
        assert '"narration_text"' in prompt
        assert '"scene_description"' in prompt

    def test_prompt_contains_flux_klein_guidance(self):
        prompt = video_script_prompt(
            title="X",
            short_description="X",
            description="X",
            hashtags=[],
        )

        # Prose, not keywords
        assert "flowing prose" in prompt.lower()
        assert "keyword" in prompt.lower()

        # Lighting is mandatory
        assert "LIGHTING IS MANDATORY" in prompt

        # Front-load subject
        assert "Front-load the subject" in prompt

        # Word count guidance
        assert "40-70 words" in prompt

        # Style and mood tags
        assert "Style:" in prompt
        assert "Mood:" in prompt

        # Textures and materials
        assert "textures" in prompt.lower()


# ---------------------------------------------------------------------------
# JSON parsing tests
# ---------------------------------------------------------------------------


class TestParseJson:
    def test_parse_plain_json(self):
        result = _parse_llm_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_with_code_fence(self):
        result = _parse_llm_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_parse_json_with_bare_code_fence(self):
        result = _parse_llm_json('```\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_parse_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_llm_json("not json at all")


# ---------------------------------------------------------------------------
# Script validation tests
# ---------------------------------------------------------------------------


class TestValidateScript:
    def test_valid_script_passes(self):
        script = json.loads(SAMPLE_LLM_RESPONSE)
        result = _validate_script(script)

        assert result["video_title"] == "CodeScope: Your AI Code Reviewer"
        assert result["video_style"] == "professional"
        assert len(result["segments"]) == 5

    def test_truncates_long_title(self):
        script = json.loads(SAMPLE_LLM_RESPONSE)
        script["video_title"] = "A" * 100
        result = _validate_script(script)
        assert len(result["video_title"]) == 60

    def test_defaults_missing_title(self):
        script = json.loads(SAMPLE_LLM_RESPONSE)
        script["video_title"] = ""
        result = _validate_script(script)
        assert result["video_title"] == "Untitled Video"

    def test_defaults_invalid_style(self):
        script = json.loads(SAMPLE_LLM_RESPONSE)
        script["video_style"] = "funky"
        result = _validate_script(script)
        assert result["video_style"] == "energetic"

    def test_clamps_duration(self):
        script = json.loads(SAMPLE_LLM_RESPONSE)
        script["target_duration_seconds"] = 999
        result = _validate_script(script)
        assert result["target_duration_seconds"] == 60

        script["target_duration_seconds"] = 5
        result = _validate_script(script)
        assert result["target_duration_seconds"] == 20

    def test_defaults_invalid_segment_type(self):
        script = json.loads(SAMPLE_LLM_RESPONSE)
        script["segments"][0]["segment_type"] = "random_type"
        result = _validate_script(script)
        assert result["segments"][0]["segment_type"] == "features"

    def test_defaults_invalid_visual_style(self):
        script = json.loads(SAMPLE_LLM_RESPONSE)
        script["segments"][0]["visual_style"] = "neon"
        result = _validate_script(script)
        assert result["segments"][0]["visual_style"] == "abstract"

    def test_defaults_invalid_transition(self):
        script = json.loads(SAMPLE_LLM_RESPONSE)
        script["segments"][0]["transition"] = "spin"
        result = _validate_script(script)
        assert result["segments"][0]["transition"] == "fade"

    def test_skips_empty_narration(self):
        script = json.loads(SAMPLE_LLM_RESPONSE)
        script["segments"][2]["narration_text"] = ""
        result = _validate_script(script)
        assert len(result["segments"]) == 4

    def test_defaults_empty_scene_description(self):
        script = json.loads(SAMPLE_LLM_RESPONSE)
        script["segments"][0]["scene_description"] = ""
        result = _validate_script(script)
        assert "geometric" in result["segments"][0]["scene_description"].lower()
        assert "Style:" in result["segments"][0]["scene_description"]
        assert "Mood:" in result["segments"][0]["scene_description"]

    def test_renumbers_segment_ids(self):
        script = json.loads(SAMPLE_LLM_RESPONSE)
        result = _validate_script(script)
        ids = [s["segment_id"] for s in result["segments"]]
        assert ids == [1, 2, 3, 4, 5]

    def test_raises_on_empty_segments(self):
        script = {"video_title": "Test", "segments": []}
        with pytest.raises(ValueError, match="at least one segment"):
            _validate_script(script)

    def test_raises_on_all_empty_narration(self):
        script = {
            "video_title": "Test",
            "segments": [{"narration_text": "", "scene_description": "test"}],
        }
        with pytest.raises(ValueError, match="No valid segments"):
            _validate_script(script)


# ---------------------------------------------------------------------------
# generate_video_script() integration tests (mocked LLM)
# ---------------------------------------------------------------------------


class TestGenerateVideoScript:
    @pytest.mark.asyncio
    async def test_successful_generation(self):
        mock_llm = MagicMock()
        mock_llm.acomplete = AsyncMock(return_value=SAMPLE_LLM_RESPONSE)

        result = await generate_video_script(
            llm=mock_llm,
            **SAMPLE_PROJECT,
        )

        assert result["video_title"] == "CodeScope: Your AI Code Reviewer"
        assert result["video_style"] == "professional"
        assert len(result["segments"]) == 5
        assert result["segments"][0]["segment_type"] == "hook"
        assert result["segments"][-1]["segment_type"] == "closing"

        # Verify LLM was called with a prompt containing project data
        call_args = mock_llm.acomplete.call_args
        prompt = call_args[0][0]
        assert "CodeScope" in prompt
        assert "AI-powered code review" in prompt

    @pytest.mark.asyncio
    async def test_generation_with_url_summaries(self):
        mock_llm = MagicMock()
        mock_llm.acomplete = AsyncMock(return_value=SAMPLE_LLM_RESPONSE)

        result = await generate_video_script(
            llm=mock_llm,
            url_summaries={"https://codescope.dev": "Official landing page"},
            **SAMPLE_PROJECT,
        )

        prompt = mock_llm.acomplete.call_args[0][0]
        assert "https://codescope.dev" in prompt
        assert "Official landing page" in prompt

    @pytest.mark.asyncio
    async def test_generation_with_code_fence_response(self):
        wrapped = f"```json\n{SAMPLE_LLM_RESPONSE}\n```"
        mock_llm = MagicMock()
        mock_llm.acomplete = AsyncMock(return_value=wrapped)

        result = await generate_video_script(
            llm=mock_llm,
            **SAMPLE_PROJECT,
        )

        assert result["video_title"] == "CodeScope: Your AI Code Reviewer"
        assert len(result["segments"]) == 5

    @pytest.mark.asyncio
    async def test_generation_raises_on_bad_json(self):
        mock_llm = MagicMock()
        mock_llm.acomplete = AsyncMock(return_value="This is not JSON at all")

        with pytest.raises(json.JSONDecodeError):
            await generate_video_script(
                llm=mock_llm,
                **SAMPLE_PROJECT,
            )

    @pytest.mark.asyncio
    async def test_generation_raises_on_empty_segments(self):
        bad_script = json.dumps(
            {"video_title": "Test", "video_style": "calm", "segments": []}
        )
        mock_llm = MagicMock()
        mock_llm.acomplete = AsyncMock(return_value=bad_script)

        with pytest.raises(ValueError, match="at least one segment"):
            await generate_video_script(
                llm=mock_llm,
                **SAMPLE_PROJECT,
            )

    @pytest.mark.asyncio
    async def test_generation_applies_defaults_for_bad_values(self):
        script = {
            "video_title": "",
            "video_style": "INVALID",
            "target_duration_seconds": 999,
            "segments": [
                {
                    "segment_type": "BAD_TYPE",
                    "narration_text": "Hello world.",
                    "scene_description": "A scene.",
                    "visual_style": "BAD_STYLE",
                    "transition": "BAD_TRANS",
                }
            ],
        }
        mock_llm = MagicMock()
        mock_llm.acomplete = AsyncMock(return_value=json.dumps(script))

        result = await generate_video_script(
            llm=mock_llm,
            **SAMPLE_PROJECT,
        )

        assert result["video_title"] == "Untitled Video"
        assert result["video_style"] == "energetic"
        assert result["target_duration_seconds"] == 60
        assert result["segments"][0]["segment_type"] == "features"
        assert result["segments"][0]["visual_style"] == "abstract"
        assert result["segments"][0]["transition"] == "fade"

    @pytest.mark.asyncio
    async def test_generation_llm_error_propagates(self):
        mock_llm = MagicMock()
        mock_llm.acomplete = AsyncMock(side_effect=RuntimeError("LLM down"))

        with pytest.raises(RuntimeError, match="LLM down"):
            await generate_video_script(
                llm=mock_llm,
                **SAMPLE_PROJECT,
            )
