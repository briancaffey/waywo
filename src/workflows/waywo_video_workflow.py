"""LlamaIndex workflow for end-to-end video generation.

Takes a project ID and video ID, then:
1. Loads project data from the database
2. Generates a video script via LLM
3. Generates TTS audio for each segment
4. Transcribes audio with word-level timestamps
5. Generates images via InvokeAI for each segment
6. Assembles the final video with MoviePy
"""

import logging
import os
import random
import wave

from llama_index.core.workflow import (
    StartEvent,
    StopEvent,
    Workflow,
    step,
)

from src.clients.invokeai import generate_image
from src.clients.stt import transcribe_audio
from src.clients.subtitles import add_subtitles
from src.clients.tts import generate_speech, list_voices
from src.clients.video import assemble_video
from src.db.projects import get_project
from src.db.videos import (
    append_video_workflow_log,
    create_segments,
    update_segment_audio,
    update_segment_image,
    update_video_output,
    update_video_script,
    update_video_status,
)
from src.video_director import generate_video_script
from src.workflows.video_events import (
    AudioGeneratedEvent,
    AudioTranscribedEvent,
    ImagesGeneratedEvent,
    ProjectLoadedEvent,
    ScriptGeneratedEvent,
)

logger = logging.getLogger(__name__)


class WaywoVideoWorkflow(Workflow):
    """Workflow that generates a complete video from a project."""

    def __init__(
        self,
        *args,
        tts_url: str,
        stt_url: str,
        invokeai_url: str,
        media_dir: str,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.tts_url = tts_url
        self.stt_url = stt_url
        self.invokeai_url = invokeai_url
        self.media_dir = media_dir

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log(self, video_id: int, message: str) -> None:
        logger.info(message)
        append_video_workflow_log(video_id, message)

    def _video_dir(self, video_id: int) -> str:
        return os.path.join(self.media_dir, "videos", str(video_id))

    def _segment_dir(self, video_id: int, segment_index: int) -> str:
        return os.path.join(self._video_dir(video_id), "segments", str(segment_index))

    def _relative_path(self, absolute_path: str) -> str:
        """Convert an absolute media path to a path relative to media_dir.

        The frontend serves files via /media/{relative_path}, so DB records
        must store paths relative to MEDIA_DIR (e.g. "videos/1/output.mp4").
        """
        return os.path.relpath(absolute_path, self.media_dir)

    # ------------------------------------------------------------------
    # Step 1: Load project
    # ------------------------------------------------------------------

    @step
    async def start(self, ev: StartEvent) -> ProjectLoadedEvent:
        project_id = ev.project_id
        video_id = ev.video_id

        project = get_project(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")

        self._log(video_id, f"Loaded project {project_id}: {project.title}")

        return ProjectLoadedEvent(
            project_id=project_id,
            video_id=video_id,
            title=project.title,
            short_description=project.short_description,
            description=project.description,
            hashtags=project.hashtags,
            url_summaries=project.url_summaries,
        )

    # ------------------------------------------------------------------
    # Step 2: Generate script
    # ------------------------------------------------------------------

    @step
    async def generate_script(self, ev: ProjectLoadedEvent) -> ScriptGeneratedEvent:
        self._log(ev.video_id, "Generating video script via LLM")

        script = await generate_video_script(
            title=ev.title,
            short_description=ev.short_description,
            description=ev.description,
            hashtags=ev.hashtags,
            url_summaries=ev.url_summaries or None,
        )

        # Pick a random voice (non-fatal if list_voices fails)
        voice_name = None
        try:
            voices = await list_voices(tts_url=self.tts_url)
            if voices:
                voice_name = random.choice(voices).get("name")
        except Exception as e:
            self._log(
                ev.video_id,
                f"Could not list voices, using default: {e}",
            )

        # Persist script to DB
        update_video_script(
            video_id=ev.video_id,
            video_title=script["video_title"],
            video_style=script["video_style"],
            script_json=script,
            voice_name=voice_name,
        )

        # Create segment rows
        segments_data = []
        for i, seg in enumerate(script["segments"]):
            segments_data.append(
                {
                    "segment_index": i,
                    "segment_type": seg["segment_type"],
                    "narration_text": seg["narration_text"],
                    "scene_description": seg["scene_description"],
                    "image_prompt": seg.get("image_prompt", seg["scene_description"]),
                    "visual_style": seg.get("visual_style", "abstract"),
                    "transition": seg.get("transition", "fade"),
                }
            )
        segment_ids = create_segments(ev.video_id, segments_data)

        update_video_status(ev.video_id, "generating")

        self._log(
            ev.video_id,
            f"Script generated: {script['video_title']} "
            f"({len(segment_ids)} segments, voice={voice_name})",
        )

        return ScriptGeneratedEvent(
            project_id=ev.project_id,
            video_id=ev.video_id,
            title=ev.title,
            short_description=ev.short_description,
            description=ev.description,
            hashtags=ev.hashtags,
            url_summaries=ev.url_summaries,
            script=script,
            segment_ids=segment_ids,
            voice_name=voice_name,
        )

    # ------------------------------------------------------------------
    # Step 3: Generate audio
    # ------------------------------------------------------------------

    @step
    async def generate_audio(self, ev: ScriptGeneratedEvent) -> AudioGeneratedEvent:
        self._log(ev.video_id, "Generating TTS audio for all segments")

        audio_paths: list[str] = []
        audio_durations: list[float] = []

        for i, seg in enumerate(ev.script["segments"]):
            seg_dir = self._segment_dir(ev.video_id, i)
            os.makedirs(seg_dir, exist_ok=True)

            audio_bytes = await generate_speech(
                text=seg["narration_text"],
                voice=ev.voice_name,
                tts_url=self.tts_url,
            )

            audio_path = os.path.join(seg_dir, "audio.wav")
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)

            # Read duration via stdlib wave module
            with wave.open(audio_path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / float(rate)

            update_segment_audio(
                segment_id=ev.segment_ids[i],
                audio_path=self._relative_path(audio_path),
                audio_duration_seconds=duration,
            )

            audio_paths.append(audio_path)
            audio_durations.append(duration)

            self._log(
                ev.video_id,
                f"Segment {i} audio: {duration:.1f}s",
            )

        return AudioGeneratedEvent(
            project_id=ev.project_id,
            video_id=ev.video_id,
            title=ev.title,
            short_description=ev.short_description,
            description=ev.description,
            hashtags=ev.hashtags,
            url_summaries=ev.url_summaries,
            script=ev.script,
            segment_ids=ev.segment_ids,
            voice_name=ev.voice_name,
            audio_paths=audio_paths,
            audio_durations=audio_durations,
        )

    # ------------------------------------------------------------------
    # Step 4: Transcribe audio
    # ------------------------------------------------------------------

    @step
    async def transcribe_audio_step(
        self, ev: AudioGeneratedEvent
    ) -> AudioTranscribedEvent:
        self._log(ev.video_id, "Transcribing audio for all segments")

        transcriptions: list[dict] = []

        for i, audio_path in enumerate(ev.audio_paths):
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            result = await transcribe_audio(
                audio_bytes=audio_bytes,
                timestamps=True,
                stt_url=self.stt_url,
            )

            transcription = {
                "text": result.text,
                "words": (
                    [
                        {"word": w.word, "start": w.start, "end": w.end}
                        for w in result.words
                    ]
                    if result.words
                    else []
                ),
            }

            update_segment_audio(
                segment_id=ev.segment_ids[i],
                audio_path=self._relative_path(audio_path),
                audio_duration_seconds=ev.audio_durations[i],
                transcription_json=transcription,
            )

            transcriptions.append(transcription)

            self._log(
                ev.video_id,
                f"Segment {i} transcribed: {len(transcription.get('words', []))} words",
            )

        return AudioTranscribedEvent(
            project_id=ev.project_id,
            video_id=ev.video_id,
            title=ev.title,
            short_description=ev.short_description,
            description=ev.description,
            hashtags=ev.hashtags,
            url_summaries=ev.url_summaries,
            script=ev.script,
            segment_ids=ev.segment_ids,
            voice_name=ev.voice_name,
            audio_paths=ev.audio_paths,
            audio_durations=ev.audio_durations,
            transcriptions=transcriptions,
        )

    # ------------------------------------------------------------------
    # Step 5: Generate images
    # ------------------------------------------------------------------

    @step
    async def generate_images(self, ev: AudioTranscribedEvent) -> ImagesGeneratedEvent:
        self._log(ev.video_id, "Generating images for all segments")

        image_paths: list[str] = []
        image_names: list[str] = []

        for i, seg in enumerate(ev.script["segments"]):
            seg_dir = self._segment_dir(ev.video_id, i)
            os.makedirs(seg_dir, exist_ok=True)

            prompt = seg.get("image_prompt", seg["scene_description"])
            result = await generate_image(
                prompt=prompt,
                width=768,
                height=1360,
                invokeai_url=self.invokeai_url,
            )

            image_path = os.path.join(seg_dir, "image.png")
            with open(image_path, "wb") as f:
                f.write(result.image_bytes)

            update_segment_image(
                segment_id=ev.segment_ids[i],
                image_path=self._relative_path(image_path),
                image_name=result.image_name,
            )

            image_paths.append(image_path)
            image_names.append(result.image_name)

            self._log(
                ev.video_id,
                f"Segment {i} image: {result.image_name}",
            )

        return ImagesGeneratedEvent(
            project_id=ev.project_id,
            video_id=ev.video_id,
            title=ev.title,
            short_description=ev.short_description,
            description=ev.description,
            hashtags=ev.hashtags,
            url_summaries=ev.url_summaries,
            script=ev.script,
            segment_ids=ev.segment_ids,
            voice_name=ev.voice_name,
            audio_paths=ev.audio_paths,
            audio_durations=ev.audio_durations,
            transcriptions=ev.transcriptions,
            image_paths=image_paths,
            image_names=image_names,
        )

    # ------------------------------------------------------------------
    # Step 6: Assemble video
    # ------------------------------------------------------------------

    @step
    async def assemble_video_step(self, ev: ImagesGeneratedEvent) -> StopEvent:
        self._log(ev.video_id, "Assembling final video")

        video_dir = self._video_dir(ev.video_id)
        os.makedirs(video_dir, exist_ok=True)
        output_path = os.path.join(video_dir, "output.mp4")
        raw_path = os.path.join(video_dir, "output_raw.mp4")

        segments_for_assembly = []
        for i, seg in enumerate(ev.script["segments"]):
            segments_for_assembly.append(
                {
                    "image_path": ev.image_paths[i],
                    "audio_path": ev.audio_paths[i],
                    "audio_duration_seconds": ev.audio_durations[i],
                    "transition": seg.get("transition", "fade"),
                }
            )

        from src.settings import USE_KEN_BURNS, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH

        duration_seconds = assemble_video(
            segments=segments_for_assembly,
            output_path=raw_path,
            width=VIDEO_WIDTH,
            height=VIDEO_HEIGHT,
            fps=VIDEO_FPS,
            use_ken_burns=USE_KEN_BURNS,
        )

        # Add subtitles: extract audio from assembled video, transcribe in
        # one pass, then burn word-level animated subtitles via pycaps.
        try:
            self._log(ev.video_id, "Adding subtitles to video")
            await add_subtitles(
                video_path=raw_path,
                output_path=output_path,
                stt_url=self.stt_url,
            )
            # Clean up the intermediate file
            try:
                os.unlink(raw_path)
            except OSError:
                pass
            self._log(ev.video_id, "Subtitles added successfully")
        except Exception as e:
            self._log(ev.video_id, f"Subtitle generation failed (non-fatal): {e}")
            # Fall back to the video without subtitles
            os.rename(raw_path, output_path)

        # Use first segment image as thumbnail
        thumbnail_rel = None
        if ev.image_paths:
            first_img = ev.image_paths[0]
            thumb_path = os.path.join(video_dir, "thumbnail.jpg")
            try:
                from PIL import Image as PILImage

                with PILImage.open(first_img) as img:
                    img = img.convert("RGB")
                    img.thumbnail((480, 854))
                    img.save(thumb_path, "JPEG", quality=85)
                thumbnail_rel = self._relative_path(thumb_path)
                self._log(ev.video_id, "Thumbnail generated from first segment")
            except Exception as e:
                self._log(ev.video_id, f"Thumbnail generation failed (non-fatal): {e}")

        update_video_output(
            video_id=ev.video_id,
            video_path=self._relative_path(output_path),
            thumbnail_path=thumbnail_rel,
            duration_seconds=duration_seconds,
        )
        update_video_status(ev.video_id, "completed")

        self._log(
            ev.video_id,
            f"Video assembled: {output_path} ({duration_seconds:.1f}s)",
        )

        return StopEvent(
            result={
                "video_id": ev.video_id,
                "video_path": output_path,
                "duration_seconds": duration_seconds,
            }
        )
