# A simple implementation of the Multi-Agent Knowledge Coordination Challenge
# This script defines minimal agent behaviors and a run_swarm function
# that coordinates them to answer a task.

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Callable, Any, Optional

# [REFACTOR] Standard library imports for new logic
import argparse
import json
import logging
import os
import re
from pathlib import Path
from typing import List
import asyncio

# [REFACTOR] FastAPI imports for new logic
import uuid
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

import uvicorn

# --- App Modules ---
from config.settings import settings # Centralized settings
from main_agent import MainAgent
from agents.utils.email_integration import send_sms
from midjourney_integration.client import (
    MidjourneyClient, 
    poll_until_complete, 
    MidjourneyError,
    upload_to_gcs_and_get_public_url,
    verify_image_is_public,
)

# --- Placeholder Agent Logic (from original main.py) ---
@dataclass
class AgentContext:
    name: str
    persona: str
AgentFn = Callable[[str, Dict[str, Any]], str]
def task_planner(task: str, state: Dict[str, Any]) -> str:
    state.setdefault("log", []).append({"agent": "TaskPlanner", "action": "Delegated task to Researcher"})
    state["current_task"] = task
    return task
def researcher(task: str, state: Dict[str, Any]) -> str:
    facts = ["Fact 1", "Fact 2", "Fact 3"]
    state["facts"] = facts
    state.setdefault("log", []).append({"agent": "Researcher", "output": facts})
    return " ".join(facts)
def analyst(_: str, state: Dict[str, Any]) -> str:
    pros = ["Pro 1", "Pro 2"]
    cons = ["Con 1", "Con 2"]
    state["pros"] = pros
    state["cons"] = cons
    state.setdefault("log", []).append({"agent": "Analyst", "pros": pros, "cons": cons})
    return "analysis complete"
def summarizer(_: str, state: Dict[str, Any]) -> str:
    summary = "This is a summary."
    state["summary"] = summary
    state.setdefault("log", []).append({"agent": "Summarizer", "summary": summary})
    return summary
def auditor(_: str, state: Dict[str, Any]) -> str:
    result = {"summary": state.get("summary", ""), "log": state.get("log", [])}
    state["result"] = result
    state.setdefault("log", []).append({"agent": "Auditor", "action": "Compiled final report"})
    return "audit complete"
AGENT_FUNCS: Dict[str, AgentFn] = {"TaskPlanner": task_planner, "Researcher": researcher, "Analyst": analyst, "Summarizer": summarizer, "Auditor": auditor}
def run_swarm(task: str, agents: List[str], personas: Dict[str, str]) -> Dict[str, Any]:
    state: Dict[str, Any] = {}
    message = task
    for agent_name in agents:
        fn = AGENT_FUNCS.get(agent_name)
        if fn: message = fn(message, state)
    return state.get("result", {})
AGENT_PERSONAS = {"TaskPlanner": "Planner", "Researcher": "Researcher", "Analyst": "Analyst", "Summarizer": "Summarizer", "Auditor": "Auditor"}
TASK = "Placeholder task"
agents = list(AGENT_PERSONAS.keys())
# --- End Placeholder Agent Logic ---


# ------------------------------------------------------------
# Security
# ------------------------------------------------------------
_TOKEN = os.getenv("SEMANT_API_TOKEN")
_http_bearer = HTTPBearer(auto_error=False)

async def _require_token(credentials: HTTPAuthorizationCredentials = Depends(_http_bearer)):
    # Only enforce authentication if a token is configured
    if _TOKEN:
        if credentials is None:
            raise HTTPException(status_code=401, detail="Missing authorization token")
        if credentials.credentials != _TOKEN:
            raise HTTPException(status_code=401, detail="Invalid authorization token")

# ------------------------------------------------------------------
# FastAPI setup
# ------------------------------------------------------------------
app = FastAPI(title="Semant Main Agent API (Unified)")
app.mount("/static", StaticFiles(directory="static"), name="static")
# [REFACTOR] Mount jobs directory for image access
JOBS_DIR = Path("midjourney_integration/jobs")
JOBS_DIR.mkdir(exist_ok=True)
app.mount("/jobs", StaticFiles(directory=JOBS_DIR), name="jobs")
# Mount uploads directory for image prompts
UPLOADS_DIR = Path("midjourney_integration/uploads")
UPLOADS_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


# ------------------------------------------------------------
# Midjourney prompt sanitization helpers (additive, non-destructive)
# ------------------------------------------------------------
_MJ_FLAG_PATTERNS = {
    "ar": re.compile(r"\s--ar\s+\S+", re.IGNORECASE),
    "stylize": re.compile(r"\s--s\s+\S+", re.IGNORECASE),
    "cref": re.compile(r"\s--cref\s+\S+", re.IGNORECASE),
    "cw": re.compile(r"\s--cw\s+\S+", re.IGNORECASE),
    # Additional flags that can trigger GoAPI prompt parser for v7
    "sref": re.compile(r"\s--sref\s+\S+", re.IGNORECASE),
    "sw": re.compile(r"\s--sw\s+\S+", re.IGNORECASE),
    "iw": re.compile(r"\s--iw\s+\S+", re.IGNORECASE),
    "seed": re.compile(r"\s--seed\s+\S+", re.IGNORECASE),
    "chaos": re.compile(r"\s--c\s+\S+", re.IGNORECASE),
    "weird": re.compile(r"\s--w\s+\S+", re.IGNORECASE),
    "tile": re.compile(r"\s--tile\b", re.IGNORECASE),
    "style_raw": re.compile(r"\s--style\s+raw\b", re.IGNORECASE),
    # Remove inline version flags; version is passed via payload separately
    "version": re.compile(r"\s--v\s+\S+", re.IGNORECASE),
    # Remove inline niji flags as version as well
    "niji": re.compile(r"\s--niji\s+\S+", re.IGNORECASE),
}

def _ensure_space_before_flags(text: str) -> str:
    """Ensure a space exists before any --flag (GoAPI can enforce this)."""
    try:
        return re.sub(r"([^\s])(--\w+)", r"\1 \2", text)
    except Exception:
        return text

def _sanitize_mj_prompt(raw_prompt: str, *, remove_ar: bool, v7: bool) -> str:
    """
    Additive normalizer for Midjourney prompts.
    - Removes --ar when aspect_ratio is provided separately
    - For v7, removes unsupported or problematic flags like --s, --cref, --cw
    - Ensures a space exists before any --flag
    Does not delete user text; only trims problematic flag segments.
    """
    prompt = raw_prompt or ""
    try:
        # Normalize unicode dashes to prevent GoAPI parser confusion (em/en/minus)
        prompt = (
            prompt.replace("\u2014", " - ")  # em dash —
                  .replace("\u2013", " - ")  # en dash –
                  .replace("\u2212", "-")    # minus sign −
        )
        if remove_ar:
            prompt = _MJ_FLAG_PATTERNS["ar"].sub("", prompt)
        # Always strip inline version flags; we pass model_version explicitly.
        prompt = _MJ_FLAG_PATTERNS["version"].sub("", prompt)
        prompt = _MJ_FLAG_PATTERNS["niji"].sub("", prompt)
        if v7:
            prompt = _MJ_FLAG_PATTERNS["stylize"].sub("", prompt)
            prompt = _MJ_FLAG_PATTERNS["cref"].sub("", prompt)
            prompt = _MJ_FLAG_PATTERNS["cw"].sub("", prompt)
            prompt = _MJ_FLAG_PATTERNS["sref"].sub("", prompt)
            prompt = _MJ_FLAG_PATTERNS["sw"].sub("", prompt)
            prompt = _MJ_FLAG_PATTERNS["iw"].sub("", prompt)
            prompt = _MJ_FLAG_PATTERNS["seed"].sub("", prompt)
            prompt = _MJ_FLAG_PATTERNS["chaos"].sub("", prompt)
            prompt = _MJ_FLAG_PATTERNS["weird"].sub("", prompt)
            prompt = _MJ_FLAG_PATTERNS["tile"].sub("", prompt)
            prompt = _MJ_FLAG_PATTERNS["style_raw"].sub("", prompt)
            # For negative prompts, remove the segment until the next flag or end of string
            prompt = re.sub(r"\s--no\s+.*?(?=(\s--|$))", " ", prompt, flags=re.IGNORECASE)
        prompt = _ensure_space_before_flags(prompt)
        # collapse multiple spaces
        prompt = re.sub(r"\s{2,}", " ", prompt).strip()
    except Exception:
        # Fail open: return the original prompt if anything goes wrong
        return raw_prompt
    return prompt


from agents.core.agentic_prompt_agent import AgenticPromptAgent
from agents.core.message_types import AgentMessage

_logger = logging.getLogger(__name__)
_main_agent = MainAgent()
# [REFACTOR] Initialize the single, reusable Midjourney client
_midjourney_client = MidjourneyClient()

# Configure and initialize the AgenticPromptAgent for prompt refinement
_prompt_refinement_template = {
    "role": "You are an expert Midjourney prompt engineer.",
    "objective": "Refine the following user-provided prompt to be more descriptive and evocative, suitable for generating high-quality images. The refined prompt should be a single, coherent paragraph. User's original prompt: {user_prompt}",
    "approach": "Analyze the user's core concept and expand upon it with creative details, camera angles, lighting, and artistic styles. Do not ask questions; provide a direct, refined prompt.",
}
_prompt_agent = AgenticPromptAgent(
    agent_id="prompt_refiner",
    config={"prompt_templates": {"midjourney_refinement": _prompt_refinement_template}},
)
# We must manually initialize the agent
@app.on_event("startup")
async def startup_event():
    await _prompt_agent.initialize()

# --- ADDED: optional multi-agent prompt refinement registry (no deletions) ---
try:
    from agents.core.agent_registry import AgentRegistry
    from agents.domain.planner_agent import PlannerAgent
    from agents.domain.logo_analysis_agent import LogoAnalysisAgent
    from agents.domain.aesthetics_agent import AestheticsAgent
    from agents.domain.color_palette_agent import ColorPaletteAgent
    from agents.domain.composition_agent import CompositionAgent
    from agents.domain.prompt_synthesis_agent import PromptSynthesisAgent
    from agents.domain.prompt_critic_agent import PromptCriticAgent
    from agents.domain.prompt_judge_agent import PromptJudgeAgent
    from agents.core.capability_types import CapabilityType
    _MA_IMPORTS_OK = True
except Exception as _e:
    _MA_IMPORTS_OK = False
    _logger.info("Multi-agent refinement modules not loaded: %s", _e)

_refine_registry = None  # type: ignore[var-annotated]
_planner = None          # type: ignore[var-annotated]

@app.on_event("startup")
async def startup_multi_agent_refiner():
    """ADDED: Initialize multi-agent refinement (tolerates missing deps)."""
    global _refine_registry, _planner
    if not _MA_IMPORTS_OK:
        return
    try:
        _refine_registry = AgentRegistry(disable_auto_discovery=True)
        await _refine_registry.initialize()
        agents_to_register = [
            PlannerAgent("planner", _refine_registry),
            LogoAnalysisAgent("logo_analyzer", capabilities={CapabilityType.LOGO_ANALYSIS}),
            AestheticsAgent("aesthetics_analyzer", capabilities={CapabilityType.AESTHETICS_ANALYSIS}),
            ColorPaletteAgent("color_palette_analyzer", capabilities={CapabilityType.COLOR_PALETTE_ANALYSIS}),
            CompositionAgent("composition_analyzer", capabilities={CapabilityType.COMPOSITION_ANALYSIS}),
            PromptSynthesisAgent("synthesis_agent", capabilities={CapabilityType.PROMPT_SYNTHESIS}),
            PromptCriticAgent("critic_agent", capabilities={CapabilityType.PROMPT_CRITIQUE}),
            PromptJudgeAgent("judge_agent", capabilities={CapabilityType.PROMPT_JUDGMENT}),
        ]
        for ag in agents_to_register:
            await _refine_registry.register_agent(ag)
        _planner = await _refine_registry.get_agent("planner")
        _logger.info("Multi-agent refinement planner initialized")
    except Exception as e:
        _logger.warning("Multi-agent refinement not available: %s", e)


# --------------------- Pydantic request models --------------------
class InvestigateRequest(BaseModel):
    topic: str
class TraverseRequest(BaseModel):
    start_node: str
    max_depth: int = 2
class FeedbackRequest(BaseModel):
    feedback: str
class ChatRequest(BaseModel):
    message: str
    history: List[str] = []
class MidjourneyImagineRequest(BaseModel):
    prompt: str
    aspect_ratio: str = "1:1"
    process_mode: str = "relax"
class MidjourneyActionRequest(BaseModel):
    action: str
    origin_task_id: str

class MidjourneySeedRequest(BaseModel):
    origin_task_id: str

class RefinePromptRequest(BaseModel):
    prompt: str



# ---------------------------- Midjourney Background Worker ---------------------------

def _save_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    """Helper to write JSON safely."""
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(path)

async def poll_and_store_task(task_id: str):
    """
    [REFACTOR] This is the new background worker function.
    It polls for task completion and then saves the results.
    """
    _logger.info("Starting background poll for task_id: %s", task_id)
    try:
        final_payload = await poll_until_complete(client=_midjourney_client, task_id=task_id)
        
        task_dir = JOBS_DIR / task_id
        task_dir.mkdir(exist_ok=True)
        
        # Store metadata
        meta_file = task_dir / "metadata.json"
        _save_json_atomic(meta_file, final_payload)
        _logger.info("Stored final metadata for task %s", task_id)

        # Download image
        image_url = final_payload.get("output", {}).get("image_url")
        if image_url:
            image_path = task_dir / "original.png"
            await _midjourney_client.download_image(image_url, str(image_path))
            _logger.info("Downloaded final image for task %s", task_id)

    except Exception as e:
        _logger.error("Background polling for task %s failed: %s", task_id, e, exc_info=True)
        # Optionally, store error state in the metadata file
        error_payload = {"task_id": task_id, "status": "failed", "error": str(e)}
        _save_json_atomic(JOBS_DIR / task_id / "metadata.json", error_payload)


@app.post("/api/upload-image")
async def api_upload_image(image_file: UploadFile = File(...)):
    """
    Handles a single image upload and returns its public GCS URL.
    This is used for the --cref and --sref workflows.
    """
    try:
        if not image_file.filename:
            raise HTTPException(status_code=400, detail="Image file must have a name.")

        # Create a unique local path
        ext = Path(image_file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{ext}"
        local_save_path = UPLOADS_DIR / unique_filename

        # Save the file locally first
        with open(local_save_path, "wb") as f:
            f.write(await image_file.read())
        _logger.info("Image for referencing saved locally to %s", local_save_path)

        # Upload to GCS and get the public URL
        public_url = upload_to_gcs_and_get_public_url(
            local_save_path, unique_filename
        )
        
        # Verify it's accessible before returning
        await verify_image_is_public(public_url)
        
        return {"url": public_url}

    except Exception as e:
        _logger.error("/api/upload-image error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



# ---------------------------- API Endpoints ---------------------------

# --- Standard Agent Endpoints ---
@app.post("/investigate")
async def api_investigate(request: InvestigateRequest):
    return await _main_agent.handle_investigate(request.topic)
@app.post("/traverse")
async def api_traverse(request: TraverseRequest):
    return await _main_agent.handle_traverse(request.start_node, request.max_depth)
@app.post("/feedback")
def api_feedback(request: FeedbackRequest):
    return _main_agent.handle_feedback(request.feedback)
@app.post("/chat")
async def api_chat(request: ChatRequest):
    return await _main_agent.handle_chat(request.message, request.history)

# --- Midjourney Endpoints (Refactored) ---



@app.post("/api/midjourney/imagine")
async def api_midjourney_imagine(
    background_tasks: BackgroundTasks,
    prompt: str = Form(...),
    aspect_ratio: str = Form("1:1"),
    process_mode: str = Form("relax"),
    version: str | None = Form(None),
    image_files: List[UploadFile] = File([]),
):
    """
    Submit a new Midjourney task, handling an optional image upload.
    This endpoint now manages the entire GCS upload and prompt creation process.
    """
    try:
        final_prompt = prompt
        public_urls = []

        # 1. Handle image uploads if any are provided
        if image_files:
            _logger.info("Received %d image(s) for prompt.", len(image_files))
            for image_file in image_files:
                if not image_file.filename:
                    continue  # Skip files without a name

                # Create a unique local path
                ext = Path(image_file.filename).suffix
                unique_filename = f"{uuid.uuid4()}{ext}"
                local_save_path = UPLOADS_DIR / unique_filename

                # Save the file locally
                with open(local_save_path, "wb") as f:
                    f.write(await image_file.read())
                _logger.info("Image saved locally to %s", local_save_path)

                # Upload to GCS and get the public URL
                public_url = upload_to_gcs_and_get_public_url(
                    local_save_path, unique_filename
                )
                public_urls.append(public_url)
            
            # Prepend the public URLs to the prompt and verify them
            if public_urls:
                # Verify all images are public before continuing
                verification_tasks = [verify_image_is_public(url) for url in public_urls]
                await asyncio.gather(*verification_tasks)

                # Replace placeholders in the prompt with the real URLs
                for url in public_urls:
                    final_prompt = final_prompt.replace("URL_PLACEHOLDER", url, 1)

        
        # Extract --oref URL and --ow weight from the raw prompt BEFORE sanitization
        oref_match = re.search(r"--oref\s+(\S+)", final_prompt, re.IGNORECASE)
        ow_match = re.search(r"--ow\s+(\d+)", final_prompt, re.IGNORECASE)
        oref_url: Optional[str] = oref_match.group(1) if oref_match else None
        oref_weight: Optional[int] = int(ow_match.group(1)) if ow_match else None

        # Remove --oref <url> and --ow <int> segments from the prompt to avoid GoAPI parser errors
        if oref_match:
            final_prompt = re.sub(r"\s--oref\s+\S+", "", final_prompt, flags=re.IGNORECASE)
        if ow_match:
            final_prompt = re.sub(r"\s--ow\s+\d+", "", final_prompt, flags=re.IGNORECASE)

        # Extract aspect ratio from the raw prompt BEFORE sanitization (so we don't lose it)
        ar_match_pre = re.search(r'--ar\s+(\S+)', final_prompt)

        # Determine model_version: prefer explicit form field, else detect from prompt
        model_version: Optional[str] = (version.strip() if version else None)
        if not model_version:
            version_match = re.search(r"--v\s+(7|6|5\.2)|\bniji\s+6\b", final_prompt, re.IGNORECASE)
            if version_match:
                if version_match.group(1) in {"7", "6", "5.2"}:
                    model_version = f"v{version_match.group(1)}"
                elif re.search(r"niji\s+6", final_prompt, re.IGNORECASE):
                    model_version = "niji 6"

        # Force/upgrade to v7 if --oref/--ow were detected and version is not already v7/niji 6
        if (oref_url or (oref_weight is not None)) and model_version not in {"v7", "niji 6"}:
            model_version = "v7"
            _logger.info("Model_version set to v7 due to presence of --oref/--ow flags")

        is_v7 = (model_version == "v7") or ("--v 7" in final_prompt)
        final_prompt = _sanitize_mj_prompt(
            final_prompt,
            remove_ar=True,  # aspect_ratio is provided via field
            v7=is_v7,
        )

        _logger.info("Submitting imagine task with final prompt: '%s'", final_prompt)

        # Prefer aspect ratio detected pre-sanitize; otherwise fall back to provided form field
        aspect_ratio_to_pass = ar_match_pre.group(1) if ar_match_pre else (aspect_ratio or "1:1")
        # Validate AR format: must be like "1:1" or "7:4"
        if not re.match(r"^\d{1,2}:\d{1,2}$", aspect_ratio_to_pass):
            _logger.info("Normalizing invalid aspect_ratio '%s' to '1:1' to satisfy GoAPI", aspect_ratio_to_pass)
            aspect_ratio_to_pass = "1:1"

        # 2. Submit the task to Midjourney
        response = await _midjourney_client.submit_imagine(
            prompt=final_prompt,
            aspect_ratio=aspect_ratio_to_pass,
            process_mode=process_mode,
            oref_url=oref_url,
            oref_weight=oref_weight,
            model_version=model_version,
        )
        task_id = response.get("data", response).get("task_id")
        if not task_id:
            raise MidjourneyError(f"Could not get task_id from response: {response}")

        # 3. Store initial metadata and start background polling
        task_dir = JOBS_DIR / task_id
        task_dir.mkdir(exist_ok=True)
        _save_json_atomic(task_dir / "metadata.json", response.get("data", response))

        background_tasks.add_task(poll_and_store_task, task_id)
        
        _logger.info("Task %s submitted for prompt: %s", task_id, final_prompt)
        return {"task_id": task_id, "status": "submitted"}
        
    except Exception as e:
        _logger.error("/api/midjourney/imagine error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/midjourney/action")
async def api_midjourney_action(request: MidjourneyActionRequest, background_tasks: BackgroundTasks):
    """Perform an action (upscale, variation, reroll) on a completed task."""
    try:
        response = await _midjourney_client.submit_action(
            origin_task_id=request.origin_task_id,
            action=request.action,
        )
        
        task_id = response.get("data", response).get("task_id")
        if not task_id:
            raise MidjourneyError(f"Could not get new task_id from action response: {response}")

        # Store initial metadata for the new task
        task_dir = JOBS_DIR / task_id
        task_dir.mkdir(exist_ok=True)
        _save_json_atomic(task_dir / "metadata.json", response.get("data", response))

        # Start a background poller for the new task
        background_tasks.add_task(poll_and_store_task, task_id)
        
        _logger.info("Action '%s' for task %s submitted as new task %s.", request.action, request.origin_task_id, task_id)
        return {"task_id": task_id, "status": "submitted"}

    except Exception as e:
        _logger.error("/api/midjourney/action error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/midjourney/describe")
async def api_midjourney_describe(image_file: UploadFile = File(...)):
    """
    Submit a new Midjourney describe task.
    This endpoint handles the GCS upload, verification, and polling.
    """
    try:
        if not image_file.filename:
            raise HTTPException(status_code=400, detail="Image file must have a name.")

        # 1. Upload and verify the image
        ext = Path(image_file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{ext}"
        local_save_path = UPLOADS_DIR / unique_filename
        
        with open(local_save_path, "wb") as f:
            f.write(await image_file.read())
        _logger.info("Image for describe saved locally to %s", local_save_path)
        
        public_url = upload_to_gcs_and_get_public_url(local_save_path, unique_filename)
        await verify_image_is_public(public_url)

        # 2. Submit the describe task
        response = await _midjourney_client.submit_describe(public_url)
        task_id = response.get("data", response).get("task_id")
        if not task_id:
            raise MidjourneyError(f"Could not get task_id from describe response: {response}")

        # 3. Poll for the result directly, as describe is usually fast
        final_payload = await poll_until_complete(client=_midjourney_client, task_id=task_id)
        
        # The description is in the 'description' field of the output
        description = final_payload.get("output", {}).get("description")
        if not description:
            raise MidjourneyError("Describe task finished but no description was found.")

        # Descriptions are returned as a single string, separated by "--".
        prompts = [p.strip() for p in description.split("--") if p.strip()]

        return {"prompts": prompts}

    except Exception as e:
        _logger.error("/api/midjourney/describe error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- ADDED: URL-based describe endpoint (does not replace existing) ---
@app.post("/api/midjourney/describe-url")
async def api_midjourney_describe_url(image_url: str = Form(...)):
    """ADDED endpoint to describe an already-public image URL.
    Leaves the original file-upload describe endpoint intact.
    """
    try:
        await verify_image_is_public(image_url)
        response = await _midjourney_client.submit_describe(image_url)
        task_id = response.get("data", response).get("task_id")
        if not task_id:
            raise MidjourneyError(f"Could not get task_id from describe response: {response}")
        final_payload = await poll_until_complete(client=_midjourney_client, task_id=task_id)
        description = final_payload.get("output", {}).get("description")
        if not description:
            raise MidjourneyError("Describe task finished but no description was found.")
        prompts = [p.strip() for p in description.split("--") if p.strip()]
        return {"prompts": prompts}
    except Exception as e:
        _logger.error("/api/midjourney/describe-url error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/midjourney/seed")
async def api_midjourney_seed(request: MidjourneySeedRequest):
    """
    Retrieve the seed for a completed Midjourney task.
    """
    try:
        response = await _midjourney_client.submit_seed(request.origin_task_id)
        task_id = response.get("data", response).get("task_id")
        if not task_id:
            raise MidjourneyError(f"Could not get task_id from seed response: {response}")

        final_payload = await poll_until_complete(client=_midjourney_client, task_id=task_id)
        
        seed = final_payload.get("output", {}).get("seed")
        if not seed:
            raise MidjourneyError("Seed task finished but no seed was found.")

        return {"seed": seed}

    except Exception as e:
        _logger.error("/api/midjourney/seed error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/midjourney/blend")
async def api_midjourney_blend(
    background_tasks: BackgroundTasks,
    dimension: str = Form(...),
    image_files: List[UploadFile] = File([]),
    image_urls: Optional[str] = Form(None),
):
    """
    Submit a new Midjourney blend task.
    """
    try:
        public_urls: List[str] = []

        # Path A: Prefer URL-based blend if provided to avoid browser CORS issues
        if image_urls:
            try:
                # Accept JSON array or comma-separated string
                if image_urls.strip().startswith("["):
                    public_urls = json.loads(image_urls)
                else:
                    public_urls = [u.strip() for u in image_urls.split(",") if u.strip()]
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid image_urls format. Provide JSON array or comma-separated URLs.")

        # Path B: Fallback to file-upload based blend (existing behavior)
        if not public_urls:
            if not (2 <= len(image_files) <= 5):
                raise HTTPException(status_code=400, detail="Blend requires 2 to 5 images.")

            for image_file in image_files:
                if not image_file.filename:
                    continue
                ext = Path(image_file.filename).suffix
                unique_filename = f"{uuid.uuid4()}{ext}"
                local_save_path = UPLOADS_DIR / unique_filename
                with open(local_save_path, "wb") as f:
                    f.write(await image_file.read())
                public_url = upload_to_gcs_and_get_public_url(local_save_path, unique_filename)
                public_urls.append(public_url)

        if not (2 <= len(public_urls) <= 5):
            raise HTTPException(status_code=400, detail="Blend requires 2 to 5 images.")

        # Verify the URLs are publicly reachable
        verification_tasks = [verify_image_is_public(url) for url in public_urls]
        await asyncio.gather(*verification_tasks)

        response = await _midjourney_client.submit_blend(public_urls, dimension)
        task_id = response.get("data", response).get("task_id")
        if not task_id:
            raise MidjourneyError(f"Could not get task_id from blend response: {response}")

        task_dir = JOBS_DIR / task_id
        task_dir.mkdir(exist_ok=True)
        _save_json_atomic(task_dir / "metadata.json", response.get("data", response))

        background_tasks.add_task(poll_and_store_task, task_id)

        return {"task_id": task_id, "status": "submitted"}

    except Exception as e:
        _logger.error("/api/midjourney/blend error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/midjourney/refine-prompt")
async def api_midjourney_refine_prompt(request: RefinePromptRequest):
    """
    Refine a user's prompt using the AgenticPromptAgent.
    """
    try:
        message = AgentMessage(
            sender_id="api",
            recipient_id="prompt_refiner",
            message_type="prompt_request",
            content={
                "prompt_type": "midjourney_refinement",
                "context": {"user_prompt": request.prompt},
                "objective": "Refine the user's prompt.",
            },
        )
        # BaseAgent exposes `process_message` as the unified async API.
        # Older code referenced `handle_message`, which doesn't exist.
        response_message = await _prompt_agent.process_message(message)
        refined_prompt = response_message.content.get("prompt", {}).get("objective", "")
        # The template returns a full sentence, so we extract the part after the colon
        final_prompt = refined_prompt.split("User's original prompt:")[-1].strip()
        return {"refined_prompt": final_prompt}
    except Exception as e:
        _logger.error("/api/midjourney/refine-prompt error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- ADDED: Multi-agent refinement endpoint (keeps original endpoint) ---
@app.post("/api/midjourney/refine-prompt-workflow")
async def api_midjourney_refine_prompt_workflow(request: RefinePromptRequest):
    """Run the multi-agent Planner workflow to refine prompts.
    Returns { refined_prompt, transcript }.
    """
    try:
        if _planner is None:
            raise HTTPException(status_code=503, detail="Multi-agent refiner not available")

        transcript: List[str] = []

        async def on_stream(text: str):
            transcript.append(text)

        msg = AgentMessage(
            sender_id="api",
            recipient_id="planner",
            content={
                "prompt": request.prompt,
                "image_urls": [],
                "streaming_callback": on_stream,
            },
            message_type="refine_request",
        )
        result = await _planner.process_message(msg)
        final_prompt = result.content.get("final_prompt") or request.prompt
        return {"refined_prompt": final_prompt, "transcript": transcript}
    except Exception as e:
        _logger.error("/api/midjourney/refine-prompt-workflow error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/midjourney/jobs")
async def api_midjourney_list_jobs():
    """List all Midjourney jobs by reading the stored metadata."""
    jobs = []
    if not JOBS_DIR.exists():
        return []
    
    for task_dir in sorted(JOBS_DIR.iterdir(), key=os.path.getmtime, reverse=True):
        if task_dir.is_dir():
            meta_file = task_dir / "metadata.json"
            if meta_file.exists():
                try:
                    jobs.append(json.loads(meta_file.read_text()))
                except json.JSONDecodeError:
                    _logger.warning(f"Could not parse metadata for job: {task_dir.name}")
    return jobs

@app.get("/api/midjourney/jobs/{task_id}")
async def api_midjourney_get_job(task_id: str):
    """Get the status of a specific Midjourney job."""
    meta_file = JOBS_DIR / task_id / "metadata.json"
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(meta_file.read_text())


@app.post("/api/midjourney/split-grid/{task_id}")
async def api_midjourney_split_grid(task_id: str):
    """
    Takes a completed task, splits the image grid, and updates the metadata.
    """
    try:
        task_dir = JOBS_DIR / task_id
        meta_file = task_dir / "metadata.json"
        image_file = task_dir / "original.png"

        if not meta_file.exists() or not image_file.exists():
            raise HTTPException(status_code=404, detail="Completed job not found.")

        # Load metadata
        metadata = json.loads(meta_file.read_text())
        if metadata.get("status") not in ["completed", "finished"]:
             raise HTTPException(status_code=400, detail="Job is not yet complete.")

        # Perform the split and upload
        from midjourney_integration.client import split_grid_and_upload
        bucket_name = settings.GCS_BUCKET_NAME
        if not bucket_name:
            raise HTTPException(status_code=500, detail="GCS_BUCKET_NAME not configured.")
        
        quadrant_urls = await split_grid_and_upload(task_id, image_file, bucket_name)

        # Update and save metadata
        metadata["quadrant_image_urls"] = quadrant_urls
        _save_json_atomic(meta_file, metadata)

        _logger.info("Grid split and metadata updated for task %s.", task_id)
        return {"status": "success", "quadrant_image_urls": quadrant_urls}

    except Exception as e:
        _logger.error("/api/midjourney/split-grid error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



# --- Other Endpoints ---
@app.get("/artifacts")
def api_list_artifacts():
    return [{"artifact_id": a.artifact_id, "content": a.content, "author": a.author, "timestamp": a.timestamp} for a in _main_agent.artifacts]
@app.get("/diary/{agent_id}")
async def api_get_diary(agent_id: str, _=Depends(_require_token)):
    from agents.core.base_agent import BaseAgent
    agent = BaseAgent._GLOBAL_AGENTS.get(agent_id)
    if not agent: raise HTTPException(status_code=404, detail="Agent not found")
    return agent.read_diary()
@app.get("/diary/{agent_id}/triples")
async def api_get_diary_triples(agent_id: str, _=Depends(_require_token)):
    from agents.core.base_agent import BaseAgent
    agent = BaseAgent._GLOBAL_AGENTS.get(agent_id)
    if not agent: raise HTTPException(status_code=404, detail="Agent not found")
    sparql = f"SELECT ?s ?p ?o WHERE {{ <http://example.org/agent/{agent_id}> ?p ?o . }}"
    return await agent.query_knowledge_graph({"sparql": sparql})

# ------------------------------------------------------------------
# Entry-point wrapper
# ------------------------------------------------------------------
def _run_cli_demo() -> None:
    result = run_swarm(task=TASK, agents=agents, personas=AGENT_PERSONAS)
    print(json.dumps(result, indent=2))

def _main():
    parser = argparse.ArgumentParser(description="Semant unified entry-point")
    parser.add_argument("--cli", action="store_true", help="Run CLI swarm demo and exit")
    parser.add_argument("--host", default=os.getenv("SEMANT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("SEMANT_PORT", 8000)))
    args = parser.parse_args()

    if args.cli:
        _run_cli_demo()
    else:
        uvicorn.run("main:app", host=args.host, port=args.port, reload=True)

if __name__ == "__main__":
    _main()
