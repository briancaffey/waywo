# Content Safety Implementation Plan

Plan for integrating content safety into the Waywo agentic chatbot (text and voice).

## Goal

Keep conversations on track and focused by classifying user prompts and LLM responses before they reach the user. Block harmful content and enforce custom policies relevant to the Waywo use case.

## Architecture

```
User Input
  ↓
[1] Classify user prompt (content-safety model)
  ↓ harmful? → reject with canned response
  ↓ unharmful? → continue
Agent Execution (RAG + LLM)
  ↓
[2] Classify LLM response (content-safety model)
  ↓ harmful? → replace with canned response
  ↓ unharmful? → return to user
```

Both text chat and voice chat follow the same flow. The safety check is a single async HTTP call to the vLLM service at each gate.

## Steps

### 1. Create the content safety client

**File:** `src/clients/content_safety.py`

Follow the same pattern as existing clients (`embedding.py`, `rerank.py`, etc.):

- `httpx.AsyncClient` with configurable base URL and timeout
- `CONTENT_SAFETY_URL` setting from environment (default: `http://192.168.5.173:8085`)
- Two public functions:
  - `classify_prompt(user_text: str) -> bool` — returns `True` if harmful
  - `classify_exchange(user_text: str, assistant_text: str) -> bool` — returns `True` if response is harmful
- Use the `/v1/chat/completions` endpoint (OpenAI-compatible)
- Use `/no_think` mode for low latency in production
- Parse the response text for `harmful`/`unharmful` strings
- Add `check_content_safety_health()` for the admin health check dashboard
- Retry logic with exponential backoff (same as other clients)

### 2. Define the safety policy prompt

**File:** `src/clients/content_safety.py` (constant at top of file)

Start with a focused policy for the Waywo use case:

```
You are a classifier for analyzing interactions between humans and LLMs.
The AI assistant is a chatbot that helps users discover and learn about
software projects shared on Hacker News "What are you working on?" threads.

Determine if the user's request or the assistant's response is harmful.

The following are harmful:
- Violence, threats, harassment, or hate speech
- Sexual or explicit content
- Illegal activity or criminal planning
- Personal information disclosure
- Manipulation or social engineering
- Content unrelated to software projects, technology, or the assistant's purpose

The following are NOT harmful:
- Questions about software projects, programming, or technology
- Asking for project recommendations or comparisons
- Technical discussions, even about security tools or penetration testing
- Casual greetings or small talk that leads into on-topic conversation
```

This keeps the policy tight around the Waywo use case without being overly restrictive.

### 3. Integrate into text chat

**File:** `src/routes/chat.py`

At two points:

**Input gate** — after receiving the user message, before calling the agent:

```python
from src.clients.content_safety import classify_prompt

is_harmful = await classify_prompt(user_message)
if is_harmful:
    # Return a canned refusal instead of running the agent
    # Save the turn to DB with a flag indicating it was blocked
```

**Output gate** — after the agent produces a final answer, before returning to the user:

```python
from src.clients.content_safety import classify_exchange

is_harmful = await classify_exchange(user_message, assistant_response)
if is_harmful:
    # Replace the response with a canned safe message
```

For the streaming endpoint (`/message/stream`), collect the full response first, then classify before sending the final `ANSWER_DONE` event. Alternatively, stream tokens through but hold the ability to append a warning or retract if the full response classifies as harmful.

### 4. Integrate into voice chat

**File:** `src/routes/voice.py`

Same two gates, applied in the WebSocket handler:

**Input gate** — after STT transcription is received, before agent execution:

```python
is_harmful = await classify_prompt(transcribed_text)
if is_harmful:
    # Generate TTS of a canned refusal and send audio back
    # Skip agent execution entirely
```

**Output gate** — after agent response, before TTS generation:

```python
is_harmful = await classify_exchange(transcribed_text, agent_response)
if is_harmful:
    # Replace agent_response with canned message before TTS
```

This is simpler than text chat because voice responses are not streamed token-by-token — the full response is collected before TTS.

### 5. Add health check

**File:** `src/routes/admin.py`

Add `content_safety` to the service health check endpoint alongside the existing services:

```python
from src.clients.content_safety import check_content_safety_health
```

### 6. Add settings

**File:** `src/settings.py`

```python
CONTENT_SAFETY_URL = os.getenv("CONTENT_SAFETY_URL", "http://192.168.5.173:8085")
CONTENT_SAFETY_ENABLED = os.getenv("CONTENT_SAFETY_ENABLED", "true").lower() == "true"
CONTENT_SAFETY_TIMEOUT = int(os.getenv("CONTENT_SAFETY_TIMEOUT", "5"))
```

The `ENABLED` flag allows disabling safety checks in development without removing the code.

### 7. Add environment variable to Docker Compose

**File:** `docker-compose.yml`

Add to the `*common-env` anchor:

```yaml
CONTENT_SAFETY_URL: ${CONTENT_SAFETY_URL:-http://192.168.5.173:8085}
CONTENT_SAFETY_ENABLED: ${CONTENT_SAFETY_ENABLED:-true}
```

### 8. Write tests

**File:** `src/test/test_content_safety.py`

- Test prompt classification (harmful and unharmful cases)
- Test exchange classification (harmful response, unharmful response)
- Test that the client handles timeouts gracefully (fail open or fail closed — see design decision below)
- Test health check function
- Mock the vLLM API responses

### 9. Graceful degradation

If the content safety service is unavailable:

- **Fail open** — allow the request through without classification. Log a warning. This keeps the chatbot functional even if the safety service is down.
- Add a circuit breaker: after N consecutive failures, stop calling the safety service for a cooldown period to avoid adding latency to every request.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Fail open vs. fail closed | **Fail open** | Waywo is a project discovery tool, not a high-risk application. Availability matters more than blocking every edge case. |
| Reasoning mode | **Off (`/no_think`)** | Latency is critical, especially for voice. Use reasoning mode only for audit logging or debugging. |
| Where to classify | **Both input and output** | Input gate catches prompt injection and off-topic requests early. Output gate catches cases where the LLM produces harmful content despite a benign prompt. |
| Streaming handling | **Collect-then-classify** | For text streaming, buffer the full response before sending `ANSWER_DONE`. This adds slight latency but avoids sending harmful content that gets retracted. |
| Policy location | **In code** | Start with a hardcoded policy string. Move to a configurable file or database later if needed. |

## File Summary

| File | Action |
|------|--------|
| `src/clients/content_safety.py` | Create — async client for vLLM content safety API |
| `src/settings.py` | Edit — add `CONTENT_SAFETY_URL`, `CONTENT_SAFETY_ENABLED`, `CONTENT_SAFETY_TIMEOUT` |
| `src/routes/chat.py` | Edit — add input/output safety gates |
| `src/routes/voice.py` | Edit — add input/output safety gates |
| `src/routes/admin.py` | Edit — add content safety health check |
| `src/test/test_content_safety.py` | Create — client and integration tests |
| `docker-compose.yml` | Edit — add env vars to common anchor |

## Future Considerations

- **Logging and auditing**: Log all blocked requests with the classification result for review
- **Admin dashboard**: Surface blocked request counts and trends in the admin UI
- **Per-category classification**: Use the full Nemotron taxonomy (S1-S22) for finer-grained blocking
- **Reasoning mode for audits**: Periodically run a sample of requests through `/think` mode and log the reasoning traces
- **Topic-following enforcement**: Use the model's topic-following capability to ensure conversations stay focused on software projects
- **Rate limiting**: Combine content safety with rate limiting to catch abuse patterns
