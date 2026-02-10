"""LlamaIndex workflow events for video generation.

Events carry accumulated data between workflow steps using the
same pattern as the project workflow events in events.py.
"""

from llama_index.core.workflow import Event


class ProjectLoadedEvent(Event):
    """Emitted after loading the project from the database."""

    project_id: int
    video_id: int
    title: str
    short_description: str
    description: str
    hashtags: list[str]
    url_summaries: dict[str, str]


class ScriptGeneratedEvent(Event):
    """Emitted after LLM script generation and DB persistence."""

    project_id: int
    video_id: int
    title: str
    short_description: str
    description: str
    hashtags: list[str]
    url_summaries: dict[str, str]

    # Script data
    script: dict
    segment_ids: list[int]
    voice_name: str | None


class AudioGeneratedEvent(Event):
    """Emitted after TTS audio generation for all segments."""

    project_id: int
    video_id: int
    title: str
    short_description: str
    description: str
    hashtags: list[str]
    url_summaries: dict[str, str]
    script: dict
    segment_ids: list[int]
    voice_name: str | None

    # Audio data (parallel arrays indexed by segment position)
    audio_paths: list[str]
    audio_durations: list[float]


class AudioTranscribedEvent(Event):
    """Emitted after STT transcription for all segments."""

    project_id: int
    video_id: int
    title: str
    short_description: str
    description: str
    hashtags: list[str]
    url_summaries: dict[str, str]
    script: dict
    segment_ids: list[int]
    voice_name: str | None
    audio_paths: list[str]
    audio_durations: list[float]

    # Transcription data (parallel array)
    transcriptions: list[dict]


class ImagesGeneratedEvent(Event):
    """Emitted after InvokeAI image generation for all segments."""

    project_id: int
    video_id: int
    title: str
    short_description: str
    description: str
    hashtags: list[str]
    url_summaries: dict[str, str]
    script: dict
    segment_ids: list[int]
    voice_name: str | None
    audio_paths: list[str]
    audio_durations: list[float]
    transcriptions: list[dict]

    # Image data (parallel arrays)
    image_paths: list[str]
    image_names: list[str]
