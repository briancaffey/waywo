# Speech-to-Speech Voice Agent

A voice-to-voice chat experience where users converse with an LLM using only speech. Text display is optional. Built iteratively with debuggability as a first-class concern.

---

## Architecture Overview

### Data Flow (Single Turn)

```
[Browser Mic] → PCM 16-bit 16kHz mono
       ↓ (binary WS frames)
[Backend WS: /ws/voice-chat] → forwards PCM chunks
       ↓ (binary WS frames)
[STT Service WS: /ws/transcribe] → partial + final transcription
       ↓ (JSON back to backend)
[Backend] → sends transcription + conversation history to LLM
       ↓ (streaming tokens via astream_chat)
[Backend] → buffers tokens, splits on sentence boundaries
       ↓ (each completed sentence)
[TTS Service: POST /v1/audio/synthesize] → WAV audio bytes
       ↓ (binary WS frames back to client)
[Browser] → plays WAV audio chunks sequentially via Web Audio API
```

### WebSocket Protocol (Frontend ↔ Backend)

Single WebSocket connection at `/ws/voice-chat?thread_id=<uuid>`.

**Client → Server (text frames = JSON, binary frames = PCM audio):**

| Message | Description |
|---------|-------------|
| `{"type": "start_listening"}` | User pressed talk button, audio chunks will follow |
| Binary frames | Raw PCM audio data (16-bit signed LE, 16kHz, mono) |
| `{"type": "stop_listening"}` | User stopped talking, finalize transcription |
| `{"type": "cancel"}` | Cancel current operation (stop LLM/TTS mid-generation) |
| `{"type": "set_voice", "voice": "..."}` | Change TTS voice for this session |

**Server → Client (text frames = JSON, binary frames = WAV audio):**

| Message | Description |
|---------|-------------|
| `{"type": "state", "state": "...", "thread_id": "..."}` | State machine transition (idle, listening, processing, speaking). Initial message includes `thread_id`. |
| `{"type": "stt_partial", "text": "..."}` | Real-time partial transcription from STT |
| `{"type": "stt_final", "text": "..."}` | Final transcription of user utterance |
| `{"type": "llm_token", "token": "...", "text": "..."}` | Streaming LLM token + accumulated text so far |
| `{"type": "llm_complete", "text": "..."}` | Full LLM response text |
| `{"type": "tts_sentence", "index": N, "text": "..."}` | TTS starting for sentence N |
| Binary frame | WAV audio for the most recently announced sentence |
| `{"type": "turn_complete"}` | Agent finished speaking, ready for next user turn |
| `{"type": "error", "message": "..."}` | Error occurred |
| `{"type": "debug", ...}` | Debug event (see Debug Events section) |

### State Machine (Per Connection)

```
IDLE → (start_listening) → LISTENING → (stop_listening) → PROCESSING → SPEAKING → IDLE
                                                              ↑              |
                                                              |   (turn_complete)
                                                              +──────────────+

Any state → (error) → IDLE
Any state → (cancel) → IDLE
```

### Debug Events

All debug events are sent as `{"type": "debug", "category": "...", "event": "...", "data": {...}, "ts": "ISO8601"}`.

Categories and events:
- **stt**: `ws_connected`, `chunks_forwarded` (every 10th), `partial`, `final`, `end_sent`, `ws_closed`, `empty_result`, `error`, `timeout`
- **llm**: `request_started`, `response_complete`, `empty_response`, `error`
- **tts**: `voice_changed`, `request_started`, `audio_received`, `error`
- **audio**: `sent_to_client`
- **ws**: `connected`, `turn_error`, `saving_turns`, `turns_saved`
- **state**: `transition` (to, with timing data on idle transition)

---

## Database Schema

### `voice_threads`

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT (UUID) | Primary key |
| title | TEXT | Auto-generated from first user message, editable |
| system_prompt | TEXT | Optional custom system prompt for this thread |
| created_at | DATETIME | UTC |
| updated_at | DATETIME | UTC, auto-updates |

### `voice_turns`

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key, auto-increment |
| thread_id | TEXT (UUID) | FK → voice_threads.id, CASCADE delete |
| role | VARCHAR(20) | "user" or "assistant" |
| text | TEXT | Transcribed user text or LLM response text |
| audio_duration_seconds | FLOAT | Duration of audio (recorded or generated) |
| tts_voice | VARCHAR(200) | Voice used for TTS (assistant turns only) |
| stt_raw_json | TEXT | Raw STT response JSON for debugging (user turns only) |
| token_count | INTEGER | LLM token count (assistant turns only) |
| llm_duration_ms | INTEGER | LLM generation time in ms (assistant turns only) |
| tts_duration_ms | INTEGER | TTS generation time in ms (assistant turns only) |
| stt_duration_ms | INTEGER | STT processing time in ms (user turns only) |
| created_at | DATETIME | UTC |

Indexes: `(thread_id, created_at)`, `(thread_id)`

---

## Milestones

### Milestone 1: Backend WebSocket + End-to-End Voice Round-Trip ✅

**Goal:** Prove the full audio pipeline works — speak into mic, hear LLM response spoken back. Minimal UI, no DB, no debug panel yet.

**Backend:**
- [x] New file `src/routes/voice.py` with FastAPI WebSocket endpoint at `/ws/voice-chat`
- [x] WebSocket handler implements the state machine (idle → listening → processing → speaking)
- [x] On `start_listening`: open a WebSocket connection to STT service (`{STT_URL}/ws/transcribe`)
- [x] Forward incoming binary PCM frames from client to STT WebSocket
- [x] Receive partial transcriptions from STT, forward as `stt_partial` to client
- [x] On `stop_listening`: send "END" to STT WebSocket, receive final transcription
- [x] Send final transcription to LLM via `get_llm().achat()` with a voice-friendly system prompt
- [x] Wait for full LLM response (no sentence pipelining yet — that's Milestone 3)
- [x] Send full response to TTS service, get WAV audio bytes back
- [x] Send WAV audio to client as binary frame
- [x] Send `turn_complete` when done
- [x] Register router in `src/main.py`
- [x] Add `STT_WS_URL` to `src/settings.py` (derived from STT_URL: `ws://` + host + `/ws/transcribe`)

**Frontend:**
- [x] New page `frontend/app/pages/voice.vue`
- [x] `useVoiceChat` composable (`frontend/app/composables/useVoiceChat.ts`):
  - WebSocket connection management (connect, disconnect)
  - `AudioWorklet` to capture PCM 16-bit 16kHz mono from mic (inline AudioWorkletProcessor, downsamples from 48kHz)
  - Send binary PCM chunks over WebSocket while recording
  - Parse incoming JSON text frames and binary audio frames
  - Play received WAV audio using `AudioContext` / `decodeAudioData()`
  - Expose reactive state: `connectionState`, `voiceState`, `partialTranscription`, `finalTranscription`, `llmResponse`, `errorMessage`
- [x] Basic UI:
  - Large circular button — hold to talk (press/release interaction)
  - Pulsing animation when `listening`
  - Spinner animation when `processing`
  - Pulse animation when `speaking`
  - Show partial transcription text while listening
  - Show response text when speaking

---

### Milestone 2: Debug Side Panel + Event System ✅

**Goal:** Full visibility into every backend event, timing, and data flow in a clean collapsible UI.

**Backend:**
- [x] Add debug event emission throughout the voice WebSocket handler
- [x] Every significant action sends a `{"type": "debug", ...}` event to the client
- [x] Include timing data: timestamps for STT connect/close, LLM start/end, TTS start/end
- [x] Include data: STT partial texts, LLM response preview, TTS audio sizes, error details

**Frontend:**
- [x] `useDebugPanel` composable (`frontend/app/composables/useDebugPanel.ts`):
  - Collects all debug events into a reactive array
  - Color-coded by category (stt=blue, llm=purple, tts=green, audio=orange, ws=gray, state=yellow)
  - Computes timing summaries (STT, LLM, TTS, total round-trip ms)
  - Max buffer size (500 events) with auto-trim
- [x] `VoiceDebugPanel.vue` component:
  - Right-side collapsible panel (slide in/out), toggle button in controls bar
  - Metrics bar with STT/LLM/TTS/Total ms display
  - Category filter pills to toggle event visibility
  - Scrollable event timeline with auto-scroll
  - Clear button to reset events
- [x] Integrated debug panel into `voice.vue` page layout

**Additional features implemented:**
- [x] TTS voice selection dropdown (grouped by language, fetched from `GET /api/voice/voices`)
- [x] `set_voice` WebSocket message type for changing voice mid-session
- [x] Text display toggle button
- [x] Consistent page header matching other pages (centered hero with icon)

---

### Milestone 3: LLM Streaming + Sentence-Level TTS Pipelining

**Goal:** Dramatically reduce time-to-first-audio by streaming the LLM response and sending each sentence to TTS as soon as it's complete.

**Backend:**
- [ ] Refactor LLM call to use `astream_chat()` for token-by-token streaming
- [ ] Implement sentence boundary detection:
  - Buffer tokens into accumulated text
  - Detect sentence endings: `.!?` followed by space or end-of-stream
  - Handle edge cases: abbreviations (Mr. Dr. etc.), ellipsis (...), URLs, numbers (3.14)
  - Send `llm_token` events to client for each token
  - When sentence boundary detected, send `tts_sentence` event + dispatch TTS request
- [ ] Run TTS requests concurrently with continued LLM streaming using `asyncio.create_task()`
- [ ] Send WAV audio binary frames to client as each TTS completes, **in sentence order**
  - If sentence 2 finishes TTS before sentence 1, hold it and send in order
- [ ] Send `llm_complete` when LLM finishes, then remaining TTS audio, then `turn_complete`
- [ ] Emit debug events for: each sentence boundary, TTS request start/complete per sentence, audio send order

**Frontend:**
- [ ] Audio playback queue in `useVoiceChat`:
  - Maintain ordered queue of WAV audio buffers
  - Play sequentially: when one finishes, start the next
  - Handle gap between audio chunks smoothly (crossfade or tight scheduling via AudioContext timing)
- [ ] Update UI to show LLM response text streaming in while audio plays
- [ ] Debug panel shows sentence-level TTS pipeline activity

**Verification:**
- First audio should start playing while LLM is still generating later sentences
- Debug panel shows overlapping LLM streaming + TTS generation
- Time-to-first-audio should be noticeably faster than Milestone 1
- All sentences play in correct order without gaps or overlaps

---

### Milestone 4: Database Persistence + Thread Management ✅

**Goal:** Persistent conversation threads with full CRUD, history loading, and conversation context for the LLM.

**Backend:**
- [x] New SQLAlchemy models in `src/db/models.py`: `VoiceThreadDB`, `VoiceTurnDB`
- [x] New DB module `src/db/voice.py` with CRUD operations:
  - `create_thread(title?)` → thread
  - `get_thread(thread_id, include_turns?)` → thread with optional turns
  - `list_threads(limit, offset)` → threads sorted by updated_at desc
  - `update_thread(thread_id, title)` → updated thread
  - `delete_thread(thread_id)` → cascade deletes turns
  - `search_threads(query, limit)` → threads matching title search
  - `get_thread_count()` → total thread count
  - `create_turn(thread_id, role, text, ...)` → turn (also bumps thread's updated_at)
  - `get_turns(thread_id, limit?)` → turns for thread
- [x] Re-export from `src/db/client.py`
- [x] New models registered in `src/db/database.py` `init_db()`
- [x] Pydantic models `VoiceTurn` and `VoiceThread` added to `src/models.py`
- [x] REST API endpoints in `src/routes/voice.py`:
  - `GET /api/voice/threads` — list threads (with optional `q` search param)
  - `POST /api/voice/threads` — create thread
  - `GET /api/voice/threads/{id}` — get thread with turns
  - `PUT /api/voice/threads/{id}` — rename thread
  - `DELETE /api/voice/threads/{id}` — delete thread
- [x] WebSocket handler changes:
  - Accept `thread_id` query param (creates new thread if absent)
  - Load conversation history (last 20 turns) and include as LLM chat context
  - Save user + assistant turns to DB after each completed round-trip
  - Auto-title: after first user message, async LLM call generates a short thread title
  - Emit debug events for DB operations (`saving_turns`, `turns_saved`)
  - Save timing metadata (stt_duration_ms, llm_duration_ms, tts_duration_ms)

**Frontend:**
- [x] `useVoiceThreads` composable (`frontend/app/composables/useVoiceThreads.ts`):
  - Fetch thread list, create, rename, delete threads via REST API
  - Active thread state tracking
  - Thread title refresh (picks up auto-generated titles)
- [x] `VoiceThreadSidebar.vue` component:
  - Left-side collapsible panel
  - List of threads sorted by most recent, showing title + relative timestamp
  - "New conversation" button
  - Click thread to switch to it
  - Delete button per thread (visible on hover)
- [x] Updated `useVoiceChat` composable:
  - `connect(threadId?)` accepts thread ID for resuming conversations
  - `messages` reactive array accumulates turns from WS events
  - `loadThreadHistory(id)` loads prior turns when switching threads
  - `threadId` exposed as reactive state
- [x] Updated `voice.vue` layout:
  - Thread sidebar toggle in controls bar
  - Conversation history in scrollable card with auto-scroll
  - Thread switching (disconnect → load history → reconnect)
  - Periodic title refresh to pick up auto-generated titles
- [x] TypeScript types for `VoiceThread`, `VoiceTurnRecord` in `types/voice.ts`

---

### Milestone 5: Polish, Error Handling, and UX

**Goal:** Production-quality voice experience with robust error handling and smooth UX.

**Backend:**
- [ ] Graceful error handling for all failure modes:
  - STT WebSocket connection failure → retry once, then error to client
  - STT transcription returns empty → inform client, return to idle
  - LLM timeout or error → error event, return to idle
  - TTS failure for a sentence → skip that sentence's audio, continue with next
  - Client disconnect mid-turn → clean up STT WS, cancel LLM/TTS tasks
- [ ] Cancel support: on `cancel` message, abort in-flight LLM generation and TTS requests
- [ ] Connection health: periodic ping/pong, detect stale connections

**Frontend:**
- [ ] Audio level visualization: real-time mic level indicator (ring around talk button)
- [ ] Push-to-talk vs click-to-toggle modes
- [ ] Keyboard shortcut: spacebar to talk (when input not focused)
- [ ] Error states with helpful messages ("Could not connect to speech service", "Mic permission denied", etc.)
- [ ] Mic permission handling: request on first use, show instructions if denied
- [ ] Reconnection: auto-reconnect WebSocket on disconnect with exponential backoff
- [ ] Mobile responsive layout
- [ ] Loading states for thread operations (create, delete, rename)
- [ ] Toast notifications for errors and success actions

**Verification:**
- Kill STT service mid-conversation → see error message, can start new turn
- Toggle text on/off while conversation is happening
- Audio level ring responds to mic input
- Works on mobile browser
- Spacebar triggers talk mode

---

## File Map

```
backend/
  src/
    routes/voice.py           # WebSocket + REST endpoints for voice chat
    db/voice.py               # Voice thread & turn DB operations
    db/models.py              # + VoiceThreadDB, VoiceTurnDB models (edit)
    db/client.py              # + re-export voice operations (edit)
    db/database.py            # + voice models in init_db() (edit)
    models.py                 # + VoiceTurn, VoiceThread Pydantic models (edit)
    settings.py               # + STT_WS_URL setting (edit)
    main.py                   # + include voice router (edit)

frontend/
  app/
    pages/voice.vue                          # Voice Mode page
    composables/useVoiceChat.ts              # WebSocket, audio capture, playback, thread support
    composables/useDebugPanel.ts             # Debug event collection and filtering
    composables/useVoiceThreads.ts           # Thread CRUD and state management
    components/voice/Button.vue              # Main talk button with animations (VoiceButton)
    components/voice/DebugPanel.vue          # Right-side debug panel (VoiceDebugPanel)
    components/voice/ThreadSidebar.vue       # Left-side thread list (VoiceThreadSidebar)
    types/voice.ts                           # TypeScript types for voice events, threads, turns
```

## Technical Notes

### Audio Capture (Browser → Backend)

Uses an inline `AudioWorkletProcessor` to capture raw Float32 samples from the mic, downsample from 48kHz to 16kHz, convert Float32 [-1, 1] to Int16 [-32768, 32767], and post as binary WebSocket frames in ~4096-sample chunks (~256ms at 16kHz).

### STT WebSocket Proxy

The backend proxies between the client WS and the STT service WS because:
- The STT service is on an internal network, not directly accessible from browser
- The backend can add logging, error handling, and debug events
- Future: backend can do VAD or pre-processing before forwarding

### TTS Audio Format

TTS service returns WAV (LINEAR_PCM) at 22050Hz. The browser's `AudioContext.decodeAudioData()` handles WAV natively, no conversion needed.

### TTS Voice Selection

Voices are fetched from `GET /v1/audio/list_voices` on the TTS service. The response format is `{"lang-codes": {"voices": [...]}}` where voice names follow the pattern `Magpie-Multilingual.LANG.Speaker.Emotion`. The backend parses this into structured `{id, language, speaker, emotion, label}` objects. The selected voice is sent via the `set_voice` WebSocket message and persisted per-session.

### LLM Conversation Context

For each turn, the last 20 turns are loaded from the DB and sent as chat messages:
```python
messages = [
    ChatMessage(role="system", content=VOICE_SYSTEM_PROMPT),
    ChatMessage(role="user", content=turn_1_text),
    ChatMessage(role="assistant", content=turn_1_response),
    ...
    ChatMessage(role="user", content=current_transcription),
]
```

The system prompt instructs the LLM to give concise, spoken-word-friendly responses (no markdown, no code blocks, short paragraphs).

### Thread Auto-Titling

After the first user turn in a new thread (title is still "New conversation"), the backend fires an async LLM call to generate a 3-6 word title from the user's message. This runs in the background via `asyncio.create_task()` and doesn't block the voice round-trip. The frontend periodically refreshes the thread title to pick up the auto-generated name.

### Sentence Boundary Detection (Planned — Milestone 3)

Simple regex-based approach with common abbreviation handling:
```python
import re
ABBREVIATIONS = {"mr", "mrs", "dr", "ms", "prof", "sr", "jr", "vs", "etc", "inc", "ltd"}
SENTENCE_END = re.compile(r'([.!?])\s+')
```

Split on `.!?` followed by whitespace, but not after known abbreviations. Also flush remaining text when LLM stream ends.
