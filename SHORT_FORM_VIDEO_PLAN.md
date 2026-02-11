# Short-Form Video Generation Plan

Generate narrated short-form videos that introduce waywo projects. Each video combines
LLM-generated scripts, TTS narration, AI-generated visuals, word-level subtitles,
stitched together into vertical video for a TikTok-style feed.

## Architecture

```
Project Data
    │
    ▼
┌──────────┐   ┌──────────┐   ┌───────────┐   ┌───────────┐
│ Generate  │──▶│ Generate │──▶│ Transcribe│──▶│ Generate  │
│  Script   │   │  Audio   │   │   (STT)   │   │  Images   │
│  (LLM)    │   │  (TTS)   │   │           │   │(InvokeAI) │
└──────────┘   └──────────┘   └───────────┘   └───────────┘
                                                     │
               ┌──────────┐   ┌───────────┐         │
               │   Add    │◀──│ Assemble  │◀────────┘
               │ Subtitles│   │   Video   │
               │          │   │ (MoviePy) │
               └──────────┘   └───────────┘
                    │
                    ▼
              Final MP4 (9:16)
```

TTS and STT run first because MoviePy needs audio durations to set each image frame's length.

---

## Milestones

### Milestone 1: InvokeAI Image Generation Client ✅

Built `src/clients/invokeai.py` with FLUX 2 Klein model graph support.

**What was built:**
- `generate_image()` — text-to-image via graph-based queue (enqueue -> poll -> download)
- `generate_image_with_reference()` — reference-image-guided generation (FLUX Kontext conditioning)
- `upload_image()` — upload reference images to InvokeAI
- `check_invokeai_health()` — service health check
- Graph templates for both txt2img and ref-img pipelines
- Async httpx, retry with exponential backoff, `InvokeAIError`
- Full test coverage (6 tests) and walkthrough notebook (`notebooks/invokeai.ipynb`)
- Settings: `INVOKEAI_URL` in settings.py, .env.example, docker-compose.yml
- Admin health check on `/api/admin/services-health`

**Key details:**
- Board ID: `d5f9e3ae-df06-451f-b538-4bb58a6cc43e`
- Default URL: `http://192.168.5.173:9090`
- API flow: `POST enqueue_batch` -> poll batch status -> extract image name -> `GET /api/v1/images/i/{name}/full`

---

### Milestone 2: TTS & STT Clients + MoviePy Foundation ✅

Built TTS and STT clients, added moviepy + ffmpeg to the project.

**What was built:**

`src/clients/tts.py` — NVIDIA Magpie NIM text-to-speech:
- `generate_speech(text, language, voice, sample_rate_hz)` → WAV bytes
- `list_voices()` → available voices from service
- `check_tts_health()` — health check via `/v1/audio/list_voices`
- API: `POST /v1/audio/synthesize` with multipart form-data
- Default URL: `http://192.168.6.3:9000`

`src/clients/stt.py` — Nemotron Speech Streaming speech-to-text:
- `transcribe_audio(audio_bytes, timestamps)` → `TranscriptionResult`
- `check_stt_health()` — health check via `/health`
- Dataclasses: `WordTimestamp(word, start, end)`, `TranscriptionResult(text, words)`
- API: `POST /transcribe?timestamps=true` with file upload
- Default URL: `http://192.168.5.96:8001`

Dependencies and infrastructure:
- `moviepy>=2.2.1` added to pyproject.toml
- `ffmpeg` added to Dockerfile apt-get
- `TTS_URL` and `STT_URL` in settings.py, .env.example, docker-compose.yml
- TTS and STT added to admin health checks (`/api/admin/services-health`)
- 12 new tests (6 TTS + 6 STT), all passing
- Walkthrough notebooks: `notebooks/tts.ipynb`, `notebooks/stt.ipynb`

---

### Milestone 3: LLM Script Generation (Director) ✅

Single LLM call generates a segmented video script from project data.

**What was built:**

`src/video_director.py` — prompt template + script generation:
- `video_script_prompt()` — formats project data into an optimized prompt
- `generate_video_script()` — async: calls LLM, parses JSON, validates/normalizes output
- `_parse_llm_json()` — handles markdown code fences in LLM responses
- `_validate_script()` — applies sensible defaults, clamps duration, renumbers segments

`src/llm_config.py` — added `get_llm_for_creative_output()` (temperature=0.8 for variety)

**Output schema:**
```json
{
  "video_title": "Short catchy title under 60 chars",
  "video_style": "energetic | calm | professional | playful",
  "target_duration_seconds": 45,
  "segments": [
    {
      "segment_id": 1,
      "segment_type": "hook | introduction | features | audience | closing",
      "narration_text": "Spoken narration here...",
      "scene_description": "Detailed visual art direction for FLUX...",
      "visual_style": "abstract | cinematic | minimal | vibrant",
      "transition": "fade | cut | slide_left | zoom_in"
    }
  ]
}
```

29 new tests (5 prompt, 4 JSON parsing, 13 validation, 7 generation).

---

### Milestone 4: Video & Segment Data Models ✅

Built granular data models for video components, enabling editing and regeneration of individual parts.

**What was built:**

`src/db/models.py` — two new SQLAlchemy models:

`WaywoVideoDB` (parent):
- Auto-incrementing `version` per project (old videos preserved for comparison)
- Script metadata: `video_title`, `video_style`, `script_json`, `voice_name`
- Status tracking: `pending` → `script_generated` → `generating` → `completed` / `failed`
- Output: `video_path`, `thumbnail_path`, `duration_seconds`, `width`, `height`
- User interaction: `view_count`, `is_favorited`
- Cascade delete to segments

`WaywoVideoSegmentDB` (child):
- `narration_text` (editable) — editing clears audio + transcription for regeneration
- `scene_description` (preserved original from LLM) + `image_prompt` (editable copy)
- `audio_path`, `audio_duration_seconds`, `transcription_json` (word timestamps)
- `image_path`, `image_name` (InvokeAI reference)
- Independent status: `pending` → `audio_generated` → `image_generated` → `complete`

`src/models.py` — Pydantic models: `WaywoVideo`, `WaywoVideoSegment`

`src/db/videos.py` — 21 operations for videos and segments.

Re-exported via `src/db/client.py`. Tables auto-created by `init_db()`.
20 new tests covering all operations.

---

### Milestone 5: Video Assembly (MoviePy) ✅

Stitches AI-generated images and TTS audio into an MP4 video with Ken Burns effects and transitions.

**What was built:**

`src/clients/video.py` — MoviePy 2.x video assembly:
- `assemble_video(segments, output_path, width, height, fps, transition_duration)` → total duration
- Ken Burns effect: 4 motion presets (zoom_in, zoom_out, pan_left, pan_right) via custom `VideoClip(frame_function=...)`
- Transitions: fade (CrossFadeIn), cut (no overlap), slide_left (SlideIn), zoom_in (CrossFadeIn)
- Manual compositing via `CompositeVideoClip` with staggered `.with_start()` offsets
- Audio fade in/out at video start/end for polish
- Output: H.264/AAC MP4 at configurable resolution (default 1080x1920 9:16, 30fps)
- `VideoAssemblyError` exception class

11 new tests with synthetic fixtures (solid-color PNGs + silent WAVs).
Walkthrough notebook: `notebooks/video_assembly.ipynb`. 189 total suite tests passing.

---

### Milestone 6: Video Generation Workflow ⬅️ NEXT

Wire the pipeline into a Celery task + LlamaIndex Workflow. A single Celery task triggers the workflow; one video generates at a time (InvokeAI is GPU-bound).

**Celery task** — `generate_video_task(project_id)`:
- Creates a `WaywoVideoDB` record with status `pending`
- Launches the LlamaIndex workflow
- Updates DB status as each step completes
- On failure: sets status to `failed`, logs error

**LlamaIndex Workflow — `WaywoVideoWorkflow`:**
1. Load project data from DB
2. Generate script (LLM via `generate_video_script()`)
3. Save script to DB, create segment records
4. Pick a random neutral/happy EN-US voice from TTS
5. For each segment: generate audio (TTS) → get WAV bytes + duration
6. For each segment: transcribe audio (STT) → get word timestamps
7. For each segment: generate image (InvokeAI) → save to disk
8. Assemble video (MoviePy `assemble_video()`)
9. Save final MP4 path + duration to DB, set status `completed`

**Files to create:**
- `src/workflows/video_events.py` — workflow event definitions
- `src/workflows/waywo_video_workflow.py` — main workflow
- `src/tasks/video.py` — Celery task that triggers the workflow

---

### Milestone 7: API Routes

Backend endpoints for triggering generation, serving videos, and editing segments.

**Video endpoints:**
```
POST /api/videos/generate/{project_id}  — trigger generation (Celery task)
GET  /api/videos/{video_id}             — video metadata + segments
GET  /api/videos/{video_id}/status      — check generation progress
GET  /api/videos/{video_id}/stream      — stream MP4 (range requests)
GET  /api/videos/{video_id}/thumbnail   — thumbnail image
GET  /api/videos/feed                   — paginated feed (completed videos)
POST /api/videos/{video_id}/favorite    — toggle favorite
POST /api/videos/{video_id}/view        — increment view count
GET  /api/projects/{project_id}/videos  — all versions for a project
POST /api/videos/{video_id}/reassemble  — re-stitch from current segments
```

**Segment endpoints:**
```
GET    /api/videos/{video_id}/segments                                  — list segments
GET    /api/videos/{video_id}/segments/{segment_id}                     — single segment
PATCH  /api/videos/{video_id}/segments/{segment_id}                     — edit narration/image_prompt
POST   /api/videos/{video_id}/segments/{segment_id}/regenerate-audio    — re-run TTS + STT
POST   /api/videos/{video_id}/segments/{segment_id}/regenerate-image    — re-run InvokeAI
GET    /api/videos/{video_id}/segments/{segment_id}/audio               — stream segment WAV
GET    /api/videos/{video_id}/segments/{segment_id}/image               — serve segment image
```

**Files to create:**
- `src/routes/videos.py`
- Register in `src/main.py`

---

### Milestone 8: Frontend — Video Generation & Feed UI

Full frontend for triggering video generation, monitoring progress, and browsing/watching videos.

**Components:**
- `VideoPlayer.vue` — HTML5 video with custom controls, Intersection Observer autoplay
- `VideoFeedCard.vue` — single video card with project info overlay
- `VideoFeedScroller.vue` — virtual scroll container
- `VideoGenerateButton.vue` — trigger + progress indicator on project detail page
- `VideoSegmentEditor.vue` — edit narration/image prompts, regenerate individual segments

**Pages:**
- `pages/videos.vue` — full-viewport TikTok-style vertical feed
- Update `pages/projects/[id].vue` — add video section + generation trigger + segment editor

**Types:**
- Add `WaywoVideo`, `WaywoVideoSegment`, `VideoFeedItem` to `types/models.ts`

---

### Milestone 9: Subtitle Overlay (pycaps) ✅

Added word-level animated subtitle captions to assembled videos using pycaps.

**What was built:**

`src/clients/subtitles.py` — subtitle overlay pipeline:
- `add_subtitles(video_path, output_path, stt_url)` — async entry point
- One-pass approach: extracts audio from the assembled video via ffmpeg, transcribes the
  full audio in a single STT call, then burns subtitles via pycaps — no per-segment offset
  calculations needed
- `transcription_to_whisper_json(result, pause_threshold)` — converts `TranscriptionResult`
  to pycaps whisper_json format, splitting on speech pauses (aligns naturally with the 0.3s
  silence gaps between narration segments)
- `extract_audio_to_wav()` — ffmpeg audio extraction (16-kHz mono PCM for STT)
- `_run_pycaps_pipeline()` — loads the `minimalist` template (bottom-center, 2-line max,
  char-limit splitter, fade animations) with custom CSS overlay (white text, gold highlight
  for current word, bold sans-serif with drop shadow)
- Synchronous pycaps render offloaded to thread pool via `run_in_executor`
- `SubtitleError` exception class

Workflow integration (`src/workflows/waywo_video_workflow.py`):
- Assembly step writes to `output_raw.mp4`, then `add_subtitles` renders to `output.mp4`
- Graceful fallback: if subtitles fail, the raw video is renamed to `output.mp4` and the
  pipeline continues — subtitle failure is non-fatal

Dependencies:
- `pycaps` added to `pyproject.toml` (git install from `francozanardi/pycaps`)
- `git` added to Dockerfile apt-get (required for git-based pip install)
- Chromium already installed via `playwright install --with-deps chromium`

14 new tests (8 whisper_json conversion, 4 add_subtitles, 2 workflow integration).
35 total video tests passing.

---

## Current Environment Variables

| Variable | Default | Status |
|---|---|---|
| `INVOKEAI_URL` | `http://192.168.5.173:9090` | ✅ Configured |
| `TTS_URL` | `http://192.168.6.3:9000` | ✅ Configured |
| `STT_URL` | `http://192.168.5.96:8001` | ✅ Configured |

Future additions:

| Variable | Default | Purpose |
|---|---|---|
| `VIDEO_WIDTH` | `1080` | Video width |
| `VIDEO_HEIGHT` | `1920` | Video height |
| `VIDEO_FPS` | `30` | Frames per second |
| `VIDEO_MAX_DURATION` | `60` | Max video duration in seconds |

---

## Decisions Made

- **Subtitles** — pycaps (deferred to Milestone 9, not blocking core pipeline)
- **Voice selection** — Random neutral/happy EN-US voice per video
- **Concurrent generation** — One video at a time (InvokeAI is GPU-heavy), enforced via Celery
- **Video storage** — Local media directory (same pattern as images/audio)
- **Regeneration** — Keep old videos (version tracking per project for comparison)
