import asyncio
import io
import logging
import os
import re
import shutil
import wave
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.db import (
    init_db,
    list_projects,
    get_project,
    create_project,
    update_project,
    delete_project,
    get_project_audio_paths,
    list_segments,
    get_segment,
    create_segment,
    update_segment,
    delete_segment,
    delete_all_segments,
    reorder_segments,
    import_script,
    create_variant,
    get_variant,
    list_variants,
    delete_variant,
    list_voice_samples,
    get_voice_sample,
    create_voice_sample,
    delete_voice_sample,
)
from app.services.sanitize import sanitize_text

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")
VOICE_SAMPLES_DIR = os.path.join(OUTPUT_DIR, "voice_samples")

# Only one generation at a time
generation_lock = asyncio.Lock()
generation_status: dict = {"active": False, "segment_id": None, "message": ""}


async def _seed_default_voice_sample():
    """Seed Alice as default voice sample if no samples exist."""
    samples = await list_voice_samples()
    if samples:
        return
    alice_wav = os.path.join("sample", "Alice.wav")
    alice_txt = os.path.join("sample", "text.txt")
    if not os.path.exists(alice_wav):
        return
    transcript = ""
    if os.path.exists(alice_txt):
        with open(alice_txt) as f:
            transcript = f.read().strip()
    # Copy to voice_samples dir
    os.makedirs(VOICE_SAMPLES_DIR, exist_ok=True)
    dest = os.path.join(VOICE_SAMPLES_DIR, "Alice.wav")
    if not os.path.exists(dest):
        shutil.copy2(alice_wav, dest)
    await create_voice_sample("Alice", dest, transcript)
    logger.info("Seeded default voice sample: Alice")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(VOICE_SAMPLES_DIR, exist_ok=True)
    await _seed_default_voice_sample()
    yield


app = FastAPI(title="Narration", lifespan=lifespan)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# --- Pydantic models ---

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

class SegmentCreate(BaseModel):
    text: str
    position: int | None = None
    service: str = "dia"
    voice_sample_id: int | None = None
    magpie_voice: str | None = None

class SegmentUpdate(BaseModel):
    text: str | None = None
    position: int | None = None
    service: str | None = None
    voice_sample_id: int | None = None
    magpie_voice: str | None = None

class ReorderItem(BaseModel):
    id: int
    position: int

class ReorderRequest(BaseModel):
    ordering: list[ReorderItem]

class ImportRequest(BaseModel):
    text: str
    service: str = "dia"

class RegenerateRequest(BaseModel):
    text: str | None = None


# --- Routes ---

@app.get("/")
async def index():
    return FileResponse(str(static_dir / "index.html"))


# --- Projects ---

@app.get("/api/projects")
async def api_list_projects():
    return await list_projects()

@app.post("/api/projects", status_code=201)
async def api_create_project(body: ProjectCreate):
    return await create_project(body.name, body.description)

@app.get("/api/projects/{project_id}")
async def api_get_project(project_id: int):
    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found")
    return proj

@app.put("/api/projects/{project_id}")
async def api_update_project(project_id: int, body: ProjectUpdate):
    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found")
    kwargs = {}
    if body.name is not None:
        kwargs["name"] = body.name
    if body.description is not None:
        kwargs["description"] = body.description
    return await update_project(project_id, **kwargs)

@app.delete("/api/projects/{project_id}")
async def api_delete_project(project_id: int):
    # Delete audio files first
    paths = await get_project_audio_paths(project_id)
    for p in paths:
        if p and os.path.exists(p):
            os.remove(p)
    # Remove project output dir
    proj_dir = os.path.join(OUTPUT_DIR, str(project_id))
    if os.path.isdir(proj_dir):
        shutil.rmtree(proj_dir)
    ok = await delete_project(project_id)
    if not ok:
        raise HTTPException(404, "Project not found")
    return {"ok": True}


# --- Segments (scoped to project) ---

@app.get("/api/projects/{project_id}/segments")
async def api_list_segments(project_id: int):
    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found")
    return await list_segments(project_id)

@app.post("/api/projects/{project_id}/segments", status_code=201)
async def api_create_segment(project_id: int, body: SegmentCreate):
    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found")
    sanitized = sanitize_text(body.text)
    position = body.position
    if position is None:
        segments = await list_segments(project_id)
        position = len(segments) + 1
    return await create_segment(project_id, body.text, sanitized, position, body.service, body.voice_sample_id, body.magpie_voice)

@app.put("/api/segments/{segment_id}")
async def api_update_segment(segment_id: int, body: SegmentUpdate):
    seg = await get_segment(segment_id)
    if not seg:
        raise HTTPException(404, "Segment not found")
    kwargs = {}
    if body.text is not None:
        kwargs["text"] = body.text
        kwargs["sanitized_text"] = sanitize_text(body.text)
        kwargs["status"] = "pending"
        kwargs["audio_path"] = None
        kwargs["duration_seconds"] = None
    if body.position is not None:
        kwargs["position"] = body.position
    if body.service is not None:
        kwargs["service"] = body.service
    if body.voice_sample_id is not None:
        kwargs["voice_sample_id"] = body.voice_sample_id if body.voice_sample_id > 0 else None
    if body.magpie_voice is not None:
        kwargs["magpie_voice"] = body.magpie_voice if body.magpie_voice else None
    return await update_segment(segment_id, **kwargs)

@app.delete("/api/segments/{segment_id}")
async def api_delete_segment(segment_id: int):
    seg = await get_segment(segment_id)
    if seg and seg["audio_path"] and os.path.exists(seg["audio_path"]):
        os.remove(seg["audio_path"])
    ok = await delete_segment(segment_id)
    if not ok:
        raise HTTPException(404, "Segment not found")
    return {"ok": True}

@app.post("/api/segments/reorder")
async def api_reorder_segments(body: ReorderRequest):
    await reorder_segments([item.model_dump() for item in body.ordering])
    # Return segments for the project of the first item
    if body.ordering:
        seg = await get_segment(body.ordering[0].id)
        if seg:
            return await list_segments(seg["project_id"])
    return []

@app.post("/api/projects/{project_id}/segments/import")
async def api_import_segments(project_id: int, body: ImportRequest):
    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found")
    lines = [line.strip() for line in body.text.splitlines() if line.strip()]
    if not lines:
        raise HTTPException(400, "No lines to import")
    return await import_script(project_id, lines, body.service)

@app.delete("/api/projects/{project_id}/segments")
async def api_delete_all_segments(project_id: int):
    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found")
    # Delete audio files
    paths = await get_project_audio_paths(project_id)
    for p in paths:
        if p and os.path.exists(p):
            os.remove(p)
    count = await delete_all_segments(project_id)
    return {"ok": True, "deleted": count}

@app.get("/api/segments/{segment_id}/audio")
async def api_get_audio(segment_id: int):
    seg = await get_segment(segment_id)
    if not seg:
        raise HTTPException(404, "Segment not found")
    if not seg["audio_path"] or not os.path.exists(seg["audio_path"]):
        raise HTTPException(404, "Audio not generated yet")
    return FileResponse(seg["audio_path"], media_type="audio/wav")

@app.get("/api/voices")
async def api_list_voices():
    from app.services.magpie import list_voices
    try:
        voices = await list_voices()
        return {"voices": voices}
    except Exception as e:
        raise HTTPException(502, f"Failed to fetch voices: {e}")


# --- Voice Samples ---

@app.get("/api/voice-samples")
async def api_list_voice_samples():
    return await list_voice_samples()

@app.post("/api/voice-samples", status_code=201)
async def api_create_voice_sample(
    name: str = Form(...),
    transcript: str = Form(""),
    audio: UploadFile = File(...),
):
    if not audio.filename.lower().endswith(".wav"):
        raise HTTPException(400, "Only WAV files are supported")
    os.makedirs(VOICE_SAMPLES_DIR, exist_ok=True)
    # Save with unique name to avoid collisions
    safe_name = re.sub(r"[^\w\-.]", "_", audio.filename)
    dest = os.path.join(VOICE_SAMPLES_DIR, f"{name.replace(' ', '_').lower()}_{safe_name}")
    content = await audio.read()
    with open(dest, "wb") as f:
        f.write(content)
    return await create_voice_sample(name, dest, transcript)

@app.get("/api/voice-samples/{sample_id}")
async def api_get_voice_sample(sample_id: int):
    vs = await get_voice_sample(sample_id)
    if not vs:
        raise HTTPException(404, "Voice sample not found")
    return vs

@app.get("/api/voice-samples/{sample_id}/audio")
async def api_get_voice_sample_audio(sample_id: int):
    vs = await get_voice_sample(sample_id)
    if not vs:
        raise HTTPException(404, "Voice sample not found")
    if not vs["audio_path"] or not os.path.exists(vs["audio_path"]):
        raise HTTPException(404, "Voice sample audio not found")
    return FileResponse(vs["audio_path"], media_type="audio/wav")

@app.delete("/api/voice-samples/{sample_id}")
async def api_delete_voice_sample(sample_id: int):
    vs = await get_voice_sample(sample_id)
    if not vs:
        raise HTTPException(404, "Voice sample not found")
    if vs["audio_path"] and os.path.exists(vs["audio_path"]):
        os.remove(vs["audio_path"])
    ok = await delete_voice_sample(sample_id)
    if not ok:
        raise HTTPException(404, "Voice sample not found")
    return {"ok": True}


# --- Generation ---

def _make_output_filename(position: int, text: str, variant_num: int = 0) -> str:
    clean = re.sub(r"\[S\d+\]\s*", "", text)
    words = clean.split()[:5]
    name = "_".join(words)
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name).lower()[:50]
    suffix = f"_v{variant_num}" if variant_num > 0 else ""
    return f"{position:03d}_{name}{suffix}.wav"


async def _generate_segment(segment_id: int, text_override: str | None = None):
    """Generate audio for a single segment. Caller must hold generation_lock."""
    from app.services.dia import generate as dia_generate
    from app.services.dia import get_wav_duration

    seg = await get_segment(segment_id)
    if not seg:
        raise HTTPException(404, "Segment not found")

    generation_status["active"] = True
    generation_status["segment_id"] = segment_id
    generation_status["message"] = f"Generating segment {seg['position']}..."

    await update_segment(segment_id, status="generating")

    if text_override:
        gen_text = sanitize_text(text_override)
        raw_text = text_override
    else:
        gen_text = seg["sanitized_text"]
        raw_text = seg["text"]

    existing_variants = await list_variants(segment_id)
    variant_num = len(existing_variants)

    # Output into project subdirectory
    proj_dir = os.path.join(OUTPUT_DIR, str(seg["project_id"]))
    os.makedirs(proj_dir, exist_ok=True)
    filename = _make_output_filename(seg["position"], raw_text, variant_num)
    output_path = os.path.join(proj_dir, filename)

    try:
        if seg["service"] == "dia":
            # Look up voice sample for custom reference audio/text
            dia_kwargs = {}
            if seg.get("voice_sample_id"):
                vs = await get_voice_sample(seg["voice_sample_id"])
                if vs:
                    dia_kwargs["reference_audio_path"] = vs["audio_path"]
                    if vs["transcript"]:
                        dia_kwargs["reference_text_override"] = vs["transcript"]
            await dia_generate(gen_text, output_path, **dia_kwargs)
        elif seg["service"] == "magpie":
            from app.services.magpie import generate as magpie_generate
            magpie_voice = seg.get("magpie_voice") or None
            await magpie_generate(gen_text, output_path, voice=magpie_voice)
        else:
            raise RuntimeError(f"Unknown service: {seg['service']}")

        duration = get_wav_duration(output_path)

        variant = await create_variant(
            segment_id=segment_id,
            text=raw_text,
            sanitized_text=gen_text,
            service=seg["service"],
            audio_path=output_path,
            duration_seconds=round(duration, 2),
        )

        await update_segment(
            segment_id,
            status="done",
            audio_path=output_path,
            duration_seconds=round(duration, 2),
            error_message=None,
            selected_variant_id=variant["id"],
        )
        logger.info(f"Segment {segment_id} done: {duration:.1f}s (variant {variant['id']})")
    except Exception as e:
        logger.error(f"Segment {segment_id} failed: {e}")
        await update_segment(segment_id, status="error", error_message=str(e))
        raise
    finally:
        generation_status["active"] = False
        generation_status["segment_id"] = None
        generation_status["message"] = ""


@app.post("/api/segments/{segment_id}/generate")
async def api_generate_segment(segment_id: int):
    seg = await get_segment(segment_id)
    if not seg:
        raise HTTPException(404, "Segment not found")
    if generation_lock.locked():
        raise HTTPException(409, "A generation is already in progress")
    async with generation_lock:
        try:
            await _generate_segment(segment_id)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Generation failed: {e}")
    return await get_segment(segment_id)


@app.post("/api/projects/{project_id}/generate/all")
async def api_generate_all(project_id: int):
    if generation_lock.locked():
        raise HTTPException(409, "A generation is already in progress")
    segments = await list_segments(project_id)
    pending = [s for s in segments if s["status"] != "done"]
    if not pending:
        return {"message": "All segments already generated", "generated": 0}
    results = {"generated": 0, "failed": 0, "errors": []}
    async with generation_lock:
        for i, seg in enumerate(pending):
            generation_status["message"] = f"Generating segment {i + 1} of {len(pending)}..."
            try:
                await _generate_segment(seg["id"])
                results["generated"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"id": seg["id"], "error": str(e)})
    return results


@app.get("/api/status")
async def api_status():
    return generation_status


@app.get("/api/projects/{project_id}/export")
async def api_export(project_id: int):
    segments = await list_segments(project_id)
    done = [s for s in segments if s["status"] == "done" and s["audio_path"] and os.path.exists(s["audio_path"])]
    if not done:
        raise HTTPException(400, "No audio segments to export")
    buf = io.BytesIO()
    params_set = False
    with wave.open(buf, "wb") as out_wav:
        for seg in done:
            with wave.open(seg["audio_path"], "rb") as in_wav:
                if not params_set:
                    out_wav.setparams(in_wav.getparams())
                    params_set = True
                out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))
    buf.seek(0)
    proj = await get_project(project_id)
    filename = f"narration_{proj['name'].replace(' ', '_').lower()}.wav" if proj else "narration_export.wav"
    return StreamingResponse(
        buf,
        media_type="audio/wav",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# --- Variants ---

@app.post("/api/segments/{segment_id}/regenerate")
async def api_regenerate_segment(segment_id: int, body: RegenerateRequest | None = None):
    seg = await get_segment(segment_id)
    if not seg:
        raise HTTPException(404, "Segment not found")
    if generation_lock.locked():
        raise HTTPException(409, "A generation is already in progress")
    text_override = body.text if body else None
    async with generation_lock:
        try:
            await _generate_segment(segment_id, text_override=text_override)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Generation failed: {e}")
    seg = await get_segment(segment_id)
    seg["variants"] = await list_variants(segment_id)
    return seg

@app.get("/api/segments/{segment_id}/variants")
async def api_list_variants(segment_id: int):
    seg = await get_segment(segment_id)
    if not seg:
        raise HTTPException(404, "Segment not found")
    return await list_variants(segment_id)

@app.post("/api/segments/{segment_id}/variants/{variant_id}/select")
async def api_select_variant(segment_id: int, variant_id: int):
    seg = await get_segment(segment_id)
    if not seg:
        raise HTTPException(404, "Segment not found")
    variant = await get_variant(variant_id)
    if not variant or variant["segment_id"] != segment_id:
        raise HTTPException(404, "Variant not found for this segment")
    await update_segment(
        segment_id,
        status="done",
        audio_path=variant["audio_path"],
        duration_seconds=variant["duration_seconds"],
        selected_variant_id=variant_id,
    )
    return await get_segment(segment_id)

@app.get("/api/variants/{variant_id}/audio")
async def api_get_variant_audio(variant_id: int):
    variant = await get_variant(variant_id)
    if not variant:
        raise HTTPException(404, "Variant not found")
    if not variant["audio_path"] or not os.path.exists(variant["audio_path"]):
        raise HTTPException(404, "Variant audio not found")
    return FileResponse(variant["audio_path"], media_type="audio/wav")

@app.delete("/api/variants/{variant_id}")
async def api_delete_variant(variant_id: int):
    variant = await get_variant(variant_id)
    if not variant:
        raise HTTPException(404, "Variant not found")
    seg = await get_segment(variant["segment_id"])
    if seg and seg.get("selected_variant_id") == variant_id:
        others = [v for v in await list_variants(variant["segment_id"]) if v["id"] != variant_id]
        if others:
            best = others[0]
            await update_segment(
                variant["segment_id"],
                audio_path=best["audio_path"],
                duration_seconds=best["duration_seconds"],
                selected_variant_id=best["id"],
            )
        else:
            await update_segment(
                variant["segment_id"],
                status="pending",
                audio_path=None,
                duration_seconds=None,
                selected_variant_id=None,
            )
    if variant["audio_path"] and os.path.exists(variant["audio_path"]):
        os.remove(variant["audio_path"])
    await delete_variant(variant_id)
    return {"ok": True}
