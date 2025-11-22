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
import mimetypes
import os
import re
from pathlib import Path
from typing import List
import random
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent

# [REFACTOR] FastAPI imports for new logic
import uuid
import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response

import uvicorn

# --- App Modules ---
from config.settings import settings # Centralized settings
from main_agent import MainAgent
from agents.utils.email_integration import send_sms
import os
from midjourney_integration.client import (
    MidjourneyClient, 
    poll_until_complete, 
    MidjourneyError,
    upload_to_gcs_and_get_public_url,
    verify_image_is_public,
)
from semant.agent_tools.midjourney.workflows import imagine_then_mirror
from semant.agent_tools.midjourney import REGISTRY
from semant.agent_tools.midjourney.workflows import generate_themed_portraits
from semant.agent_tools.midjourney.kg_logging import KGLogger, set_global_kg
from kg.models.graph_manager import KnowledgeGraphManager
from kg.models.remote_graph_manager import RemoteKnowledgeGraphManager
from midjourney_integration.persona_batch_generator import PersonaBatchGenerator, create_batch_generator
from midjourney_integration.image_cache import ImageCache, initialize_cache, get_cache
from midjourney_integration.refinement_history import get_refinement_history
from kg.services.image_embedding_service import (
    ImageEmbeddingService,
    generate_stable_point_id,
    generate_legacy_point_id,
)
try:
    from google.cloud import storage as gcs_storage
except ImportError:  # pragma: no cover - optional dependency
    gcs_storage = None  # type: ignore[assignment]

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
app = FastAPI(
    title="Semant Multi-Agent System API",
    description="""
    # Semant Multi-Agent System API

    A comprehensive API for managing multi-agent systems with knowledge graph integration.

    ## Features

    - **Agent Management**: Register, discover, and orchestrate agents
    - **Knowledge Graph**: Query and update semantic data
    - **Midjourney Integration**: AI-powered image generation and refinement
    - **Workflow Orchestration**: Execute complex multi-agent workflows
    - **Health Monitoring**: Real-time system health and metrics

    ## Getting Started

    1. **Health Check**: `GET /api/health` - Verify system status
    2. **API Documentation**: `GET /docs` - Interactive API docs
    3. **Metrics**: `GET /api/metrics` - System performance metrics

    ## Key Endpoints

    ### Agent Operations
    - `POST /investigate` - Start investigation workflow
    - `POST /chat` - Interactive agent chat
    - `POST /traverse` - Knowledge graph traversal

    ### Midjourney Integration
    - `POST /api/midjourney/imagine` - Generate images
    - `POST /api/midjourney/refine-prompt` - AI prompt refinement
    - `GET /api/midjourney/refine-history/{session_id}` - Refinement history

    ### Knowledge Graph
    - `GET /api/kg/query` - SPARQL queries
    - `POST /api/kg/update` - Update graph data

    ### System Management
    - `GET /api/health` - Health check
    - `GET /api/metrics` - Performance metrics
    - `GET /static/monitoring.html` - Monitoring dashboard
    - `GET /static/documentation.html` - Complete documentation center

    ## Authentication

    Currently no authentication required for development/demo purposes.
    Add authentication headers for production deployment.

    ## Support

    For issues and questions:
    - Check `/api/health` for system status
    - View `/docs` for detailed API documentation
    - Monitor system via `/static/monitoring.html`
    """,
    version="1.0.0",
    contact={
        "name": "Semant Development Team",
        "url": "https://github.com/semant-ai",
        "email": "support@semant.ai"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware to allow browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your actual frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/favicon.ico", StaticFiles(directory="static"), name="favicon")
# [REFACTOR] Mount jobs directory for image access
JOBS_DIR = Path("midjourney_integration/jobs")
JOBS_DIR.mkdir(exist_ok=True)
app.mount("/jobs", StaticFiles(directory=JOBS_DIR), name="jobs")
# Mount uploads directory for image prompts
UPLOADS_DIR = Path("midjourney_integration/uploads")
UPLOADS_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/books", StaticFiles(directory="generated_books"), name="books")

# Shared constants for image indexing
IMAGE_INDEX_MAX_FILE_SIZE = 12 * 1024 * 1024  # 12 MB limit to prevent runaway uploads
_ALLOWED_IMAGE_TYPES = {"input", "output", "reference"}
SCHEMA_NS = "http://schema.org/"
KG_NS = "http://example.org/kg#"
BOOK_NS = "http://example.org/childrens-book#"


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

# ---------------------------- SMS Notification Helper ---------------------------

def get_user_phone_number() -> Optional[str]:
    """Get user phone number from environment variable."""
    return os.getenv("USER_PHONE_NUMBER") or os.getenv("NOTIFICATION_PHONE_NUMBER")

async def send_agent_sms(message: str, force: bool = False) -> bool:
    """
    Send SMS notification to user from agents.
    
    Args:
        message: The message to send
        force: Force send even if phone number not configured (default: False)
    
    Returns:
        True if SMS was sent, False otherwise
    """
    phone_number = get_user_phone_number()
    if not phone_number:
        if force:
            _logger.warning("SMS notification requested but USER_PHONE_NUMBER not configured")
        return False
    
    try:
        result = send_sms(recipient_id=phone_number, body=message, force_real=True)
        if result.get("status") == "sent_real":
            _logger.info(f"SMS notification sent to {phone_number}")
            return True
        else:
            _logger.warning(f"SMS notification failed: {result.get('status')}")
            return False
    except Exception as e:
        _logger.error(f"Failed to send SMS notification: {e}", exc_info=True)
        return False

# [REFACTOR] Initialize the single, reusable Midjourney client
_midjourney_client = MidjourneyClient()

# Shared KG utilities for uploads and queries
# Configure KG: prefer remote SPARQL store if enabled via settings
if getattr(settings, "KG_REMOTE_ENABLED", False) and settings.KG_SPARQL_QUERY_ENDPOINT:
    _kg_manager = RemoteKnowledgeGraphManager(
        query_endpoint=settings.KG_SPARQL_QUERY_ENDPOINT,
        update_endpoint=settings.KG_SPARQL_UPDATE_ENDPOINT or settings.KG_SPARQL_QUERY_ENDPOINT,
        verify_ssl=bool(getattr(settings, "KG_VERIFY_SSL", True)),
    )
    _logger.info("KG configured to use Remote SPARQL endpoint: %s", settings.KG_SPARQL_QUERY_ENDPOINT)
else:
    # Use persistent RDF storage instead of in-memory
    _kg_manager = KnowledgeGraphManager(persistent_storage=True)

set_global_kg(_kg_manager)
_kg_logger_uploads = KGLogger(kg=_kg_manager, agent_id="agent/API")

# Initialize Image Embedding Service for similarity search
try:
    _image_embedding_service = ImageEmbeddingService(
        qdrant_host=os.getenv("QDRANT_HOST", "localhost"),
        qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
    )
    _logger.info("ImageEmbeddingService initialized")
except Exception as e:
    _logger.warning("ImageEmbeddingService initialization failed: %s", e)
    _image_embedding_service = None

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
# We will initialize/shutdown via FastAPI lifespan

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

# FastAPI lifespan replaces deprecated startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await _prompt_agent.initialize()
    except Exception as e:
        _logger.warning("Prompt agent init failed: %s", e)

    # Ensure KG is initialized early
    try:
        await _kg_manager.initialize()
        _logger.info("Knowledge Graph initialized (%s)", _kg_manager.__class__.__name__)
    except Exception as e:
        _logger.warning("KG init failed: %s", e)

    # Initialize image cache for Midjourney
    try:
        cache = await initialize_cache(
            cache_dir=".cache/midjourney",
            ttl_hours=24,
            max_cache_size_mb=500,
            redis_url=os.getenv("REDIS_URL")  # Optional Redis support
        )
        _logger.info("Image cache initialized: %s", await cache.get_stats())
    except Exception as e:
        _logger.warning("Image cache init failed: %s", e)

    # Optional: Rehydrate KG from existing jobs so Trace works after restarts
    try:
        from semant.agent_tools.midjourney.kg_logging import MJ_NS, CORE_NS
        if JOBS_DIR.exists():
            count_tasks = 0
            count_calls = 0
            for task_dir in JOBS_DIR.iterdir():
                if not task_dir.is_dir():
                    continue
                meta = task_dir / "metadata.json"
                if not meta.exists():
                    continue
                try:
                    data = json.loads(meta.read_text())
                except Exception:
                    continue
                task_id = str(data.get("task_id") or task_dir.name)
                if not task_id:
                    continue
                task_uri = f"{MJ_NS}Task/{task_id}"
                await _kg_manager.add_triple(task_uri, f"{CORE_NS}type", f"{MJ_NS}Task")
                count_tasks += 1

                # Synthesize an import ToolCall with media links for visibility
                try:
                    media_links = []
                    img_url = (data.get("output") or {}).get("image_url")
                    if isinstance(img_url, str) and img_url:
                        media_links.append(img_url)
                    if (task_dir / "original.png").exists():
                        media_links.append(f"/jobs/{task_id}/original.png")

                    await _kg_logger_uploads.log_tool_call(
                        tool_name="mj.import_job",
                        inputs={"source": "rehydration", "task_id": task_id},
                        outputs=data,
                        goapi_task={"task_id": task_id},
                        images=media_links or None,
                    )
                    count_calls += 1
                except Exception:
                    pass

            if count_tasks:
                _logger.info(
                    "KG rehydration: ensured %d Task node(s), %d synthesized ToolCall(s)",
                    count_tasks,
                    count_calls,
                )
    except Exception as e:
        _logger.warning("KG rehydration skipped: %s", e)

    if _MA_IMPORTS_OK:
        global _refine_registry, _planner
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
            # Ensure _planner is not a mock
            if _planner and hasattr(_planner, '__class__') and 'Mock' in _planner.__class__.__name__:
                _logger.warning("Planner initialization returned a Mock object, resetting to None")
                _planner = None
            else:
                _logger.info("Multi-agent refinement planner initialized")
        except Exception as e:
            _logger.warning("Multi-agent refinement not available: %s", e)
            _planner = None  # Explicitly set to None on failure

    # Yield control to application
    try:
        yield
    finally:
        # Shutdown
        try:
            if _refine_registry is not None:
                await _refine_registry.shutdown()
        except Exception as e:
            _logger.warning("Multi-agent registry shutdown error: %s", e)
        try:
            await _prompt_agent.shutdown()
        except Exception:
            pass

# Attach lifespan context to the app without moving app creation
app.router.lifespan_context = lifespan


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
class MidjourneyImagineAndMirrorResponse(BaseModel):
    task_id: str | None = None
    image_url: str | None = None
    gcs_url: str | None = None
    error: str | None = None
class MidjourneyActionRequest(BaseModel):
    action: str
    origin_task_id: str

class MidjourneySeedRequest(BaseModel):
    origin_task_id: str
class MidjourneyPanRequest(BaseModel):
    origin_task_id: str
    direction: str
class MidjourneyOutpaintRequest(BaseModel):
    image_url: str
    prompt: str | None = None
class MidjourneyVariationRequest(BaseModel):
    origin_task_id: str
    index: int
class MidjourneyCancelRequest(BaseModel):
    task_id: str

class RefinePromptRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None

class ThemedPortraitsRequest(BaseModel):
    theme: str
    face_image_urls: list[str]
    count: int = 10
    version: str = "v7"
    aspect_ratio: str | None = None
    process_mode: str | None = None
    cw: int | None = None
    ow: int | None = None

class ThemedSetRequest(BaseModel):
    theme: str
    face_image_urls: list[str]
    count: int = 10
    version: str = "v7"
    aspect_ratio: str | None = None
    process_mode: str | None = None
    cw: int | None = None
    ow: int | None = None
    extra_params: str | None = None



# ---------------------------- Themed Prompt Generator ---------------------------
def _generate_theme_aware_prompt(theme: str) -> str:
    """
    Generate a single cinematic portrait prompt aligned to the user's theme,
    using randomized role/setting/action/mood/lighting to create diversity.
    """
    theme_lower = (theme or "").lower()

    is_superhero = any(k in theme_lower for k in ["marvel", "superhero", "super hero", "avenger", "comic"])  # noqa: E501
    is_fantasy = any(k in theme_lower for k in ["lord of the rings", "lotr", "middle-earth", "fantasy", "medieval"])  # noqa: E501

    if is_superhero:
        roles = [
            "masked vigilante",
            "tech-powered hero",
            "super soldier",
            "web-slinging guardian",
            "cosmic defender",
            "mystic sorcerer",
            "armored innovator",
            "agile spy",
            "gamma titan",
            "thunder channeler",
        ]
        settings = [
            "neon-lit city rooftop at night",
            "futuristic lab with holographic displays",
            "rainy alley with neon signage",
            "battle-scarred urban street",
            "helipad at sunset over skyline",
            "press conference with flash bulbs",
            "cosmic portal shimmering in the sky",
            "high-tech command center",
            "skyscraper ledge above traffic trails",
            "suspension bridge under storm clouds",
        ]
        actions = [
            "leaping between skyscrapers",
            "charging repulsors",
            "summoning energy shield",
            "casting arcane sigil",
            "swinging on webline",
            "landing superhero pose",
            "deflecting debris mid-air",
            "activating stealth suit",
            "channeling lightning",
            "lifting a crushed car",
        ]
    elif is_fantasy:
        roles = [
            "seasoned scout",
            "royal captain",
            "artisan smith",
            "learned scholar",
            "swift rider",
            "poised sentry",
            "seafaring mariner",
            "diplomatic emissary",
            "master archer",
            "quiet tracker",
        ]
        settings = [
            "mountain ridge at blue hour with low cloud",
            "stone courtyard at golden hour",
            "windy grasslands under a storm front",
            "lantern-lit archive at dusk",
            "starlit forest canopy with luminous leaves",
            "sea wall at dawn spray",
            "foggy riverbank at early morning",
            "desert pavilion with patterned silk",
            "ancient library bathed in amber light",
            "rain-specked city balcony at twilight",
        ]
        actions = [
            "scanning the horizon with wind-tossed cloak",
            "lifting a helm under the arm",
            "gripping a banner as mist rises",
            "studying a weathered map",
            "nocking an arrow",
            "lowering a leaf-shaped blade",
            "presenting a sealed scroll",
            "turning a vellum page",
        ]
    else:
        roles = [
            "street photographer",
            "athletic runner",
            "studio model",
            "concert guitarist",
            "chef de cuisine",
            "race driver",
            "fashion stylist",
            "science researcher",
            "urban explorer",
            "art director",
        ]
        settings = [
            "downtown crosswalk at golden hour",
            "modern studio with seamless backdrop",
            "industrial warehouse with skylights",
            "underground station with motion blur",
            "coastal boardwalk at sunrise",
            "glass atrium with natural light",
            "city rooftop garden at twilight",
            "gallery space with spotlights",
            "rainy street with reflections",
            "vintage diner neon at night",
        ]
        actions = [
            "adjusting a leather glove",
            "tying running shoes",
            "framing a shot with hands",
            "tuning a guitar on stage",
            "plating a dish with tweezers",
            "tightening a racing helmet",
            "pinning a fabric swatch",
            "holding a clipboard with notes",
            "peering over a city map",
            "gesturing toward a moodboard",
        ]

    compositions = [
        "medium close-up, 85mm lens, slightly low-angle, rule of thirds",
        "three-quarter portrait, 50mm lens, eye-level, centered symmetry",
        "half-body, 70mm lens, over-shoulder framing with leading lines",
        "tight portrait, 135mm lens, eye-level, negative space to the right",
        "medium portrait, 105mm lens, slight high-angle, balanced asymmetry",
        "close portrait, 50mm lens, eye-level, diagonal stacks",
        "medium close-up, 35mm lens, low-angle, foreground depth",
        "medium portrait, 90mm lens, low-angle, foreground depth",
    ]
    lightings = [
        "cool rim light from the left with faint fog glow",
        "warm key light with soft bounce fill",
        "dramatic cross-light with storm backlight",
        "soft ambient with dappled foliage highlights",
        "cool dawn key with specular highlights",
        "overcast softbox look with gentle wrap",
        "hard sidelight with crisp shadow falloff",
        "neon accent lights with contrasting gels",
    ]
    moods = [
        ("stoic", "steel-blue and slate"),
        ("noble", "ivory and gold"),
        ("dynamic", "electric blue and crimson"),
        ("brooding", "charcoal and cobalt"),
        ("uplifting", "sunset orange and teal"),
        ("resolute", "ocean blue and slate"),
        ("vigilant", "graphite and amber"),
        ("dignified", "crimson and sand"),
    ]
    details_pool = [
        "subtle film grain",
        "shallow depth of field",
        "sharp eye catchlight",
        "micro-contrast on skin texture",
        "cinematic color grade",
        "raindrops and reflections",
        "glowing particles",
        "specular highlights",
        "motion blur streaks",
        "atmospheric haze",
        "bokeh orbs",
        "fine fabric texture",
    ]

    role = random.choice(roles)
    setting = random.choice(settings)
    composition = random.choice(compositions)
    lighting = random.choice(lightings)
    mood, palette = random.choice(moods)
    action = random.choice(actions)
    details = ", ".join(random.sample(details_pool, k=3))

    return (
        f"{theme} cinematic portrait; "
        f"subject: {role}, keep the referenced face as the protagonist; "
        f"setting: {setting}; "
        f"composition: {composition}; "
        f"lighting: {lighting}; "
        f"mood/color: {mood}, {palette}; "
        f"style: photographic realism; "
        f"action: {action}; "
        f"details: {details}; no text, no watermark"
    )

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
        final_payload = await poll_until_complete(client=_midjourney_client, task_id=task_id, kg_manager=_kg_manager)
        
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

        # Persist completion in KG with links to images for long-term traceability
        try:
            media_links = []
            if isinstance(image_url, str) and image_url:
                media_links.append(image_url)
            if (task_dir / "original.png").exists():
                media_links.append(f"/jobs/{task_id}/original.png")
            await _kg_logger_uploads.log_tool_call(
                tool_name="mj.complete",
                inputs={"task_id": task_id},
                outputs=final_payload,
                goapi_task=final_payload,
                images=media_links or None,
            )
        except Exception as e:
            _logger.warning("KG logging (complete) failed for %s: %s", task_id, e)

        # Send SMS notification on task completion
        try:
            prompt = final_payload.get("input", {}).get("prompt", "Unknown prompt")
            status = final_payload.get("status", "completed")
            message = f"✅ Task {task_id[:8]}... completed! Status: {status}"
            if image_url:
                message += f" Image ready: {image_url[:50]}..."
            await send_agent_sms(message)
        except Exception as e:
            _logger.warning("SMS notification (complete) failed for %s: %s", task_id, e)

    except Exception as e:
        _logger.error("Background polling for task %s failed: %s", task_id, e, exc_info=True)
        # Optionally, store error state in the metadata file
        error_payload = {"task_id": task_id, "status": "failed", "error": str(e)}
        _save_json_atomic(JOBS_DIR / task_id / "metadata.json", error_payload)
        
        # Send SMS notification on task failure
        try:
            message = f"❌ Task {task_id[:8]}... failed: {str(e)[:100]}"
            await send_agent_sms(message)
        except Exception as sms_err:
            _logger.warning("SMS notification (error) failed for %s: %s", task_id, sms_err)


@app.post("/api/upload-image")
async def api_upload_image(image_file: UploadFile = File(...)):
    """
    Handles a single image upload and returns its public GCS URL.
    This is used for the --cref and --sref workflows.

    OPTIMIZED: Uploads directly from memory without local file write or verification.
    """
    try:
        if not image_file.filename:
            raise HTTPException(status_code=400, detail="Image file must have a name.")

        # Create a unique filename
        ext = Path(image_file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{ext}"

        # Read file content into memory
        file_content = await image_file.read()
        _logger.info("Read %d bytes for upload: %s", len(file_content), image_file.filename)

        # Upload directly to GCS from memory (no local file write)
        public_url = upload_to_gcs_and_get_public_url(
            file_content, unique_filename, image_file.content_type
        )

        # Log the upload into the knowledge graph as a ToolCall with associated media
        try:
            await _kg_logger_uploads.log_tool_call(
                tool_name="mj.upload_image",
                inputs={
                    "filename": image_file.filename,
                    "content_type": image_file.content_type,
                },
                outputs={"url": public_url},
                images=[public_url],
            )
        except Exception as e:
            _logger.warning("KG logging for upload failed: %s", e)

        return {"url": public_url}

    except Exception as e:
        _logger.error("/api/upload-image error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _convert_gcs_url_to_public(gcs_url: str) -> str:
    """
    Convert a gs:// URL to a public HTTP URL.
    
    Args:
        gcs_url: GCS URL in format gs://bucket/path or file://path
        
    Returns:
        Public HTTP URL or original URL if conversion not possible
    """
    if not gcs_url:
        return gcs_url
    
    # Convert gs://bucket/path to https://storage.googleapis.com/bucket/path
    if gcs_url.startswith("gs://"):
        path = gcs_url[5:]  # Remove "gs://" prefix
        return f"https://storage.googleapis.com/{path}"
    
    # Handle file:// URLs (for local development)
    if gcs_url.startswith("file://"):
        # For local files, we'd need to serve them via a static endpoint
        # For now, return as-is or convert to a relative path
        file_path = gcs_url[7:]  # Remove "file://" prefix
        # If it's in a known directory, we could serve it statically
        # For now, return original
        return gcs_url
    
    # Already an HTTP URL or unknown format
    return gcs_url


def _normalize_image_type(image_type: Optional[str]) -> str:
    """Normalize image_type values to the supported vocabulary."""
    if not image_type:
        return "output"
    lower = image_type.strip().lower()
    return lower if lower in _ALLOWED_IMAGE_TYPES else "output"


async def _store_indexed_image_in_kg(
    image_uri: str,
    filename: str,
    gcs_url: str,
    image_type: str,
    description: str,
    file_size: int,
    embedding_dimension: int,
) -> None:
    """Persist minimal metadata for indexed images into the KG."""
    if not _kg_manager:
        return

    created_at = datetime.utcnow().isoformat()
    rdf_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    image_class = f"{BOOK_NS}{'InputImage' if image_type == 'input' else 'OutputImage'}"

    triples = [
        (image_uri, rdf_type, f"{SCHEMA_NS}ImageObject"),
        (image_uri, rdf_type, image_class),
        (image_uri, f"{SCHEMA_NS}name", filename),
        (image_uri, f"{SCHEMA_NS}contentUrl", gcs_url),
        (image_uri, f"{SCHEMA_NS}description", description),
        (image_uri, f"{SCHEMA_NS}contentSize", str(file_size)),
        (image_uri, f"{SCHEMA_NS}dateCreated", created_at),
        (image_uri, f"{KG_NS}imageType", image_type),
        (image_uri, f"{KG_NS}hasEmbedding", "true"),
        (image_uri, f"{KG_NS}embeddingDimension", str(embedding_dimension)),
        (image_uri, f"{KG_NS}embeddingStorage", "qdrant"),
    ]

    for subj, pred, obj in triples:
        try:
            await _kg_manager.add_triple(subj, pred, obj)
        except Exception as exc:
            _logger.warning("KG write failed for %s (%s -> %s): %s", subj, pred, obj, exc)


@app.post("/api/images/index")
async def api_index_image(
    image_file: UploadFile = File(...),
    image_type: str = Form("output"),
    source_uri: Optional[str] = Form(None),
    description_override: Optional[str] = Form(None),
    metadata_json: Optional[str] = Form(None),
    store_in_kg: bool = Form(False),
    verify_public: bool = Form(False),
):
    """
    Index a new image into Qdrant (and optionally the Knowledge Graph).

    Uploads the provided image to GCS, generates an embedding, and stores
    the resulting vector in the configured Qdrant collection.
    """
    if not _image_embedding_service:
        raise HTTPException(
            status_code=503,
            detail="Image embedding service not available. Check Qdrant connection.",
        )
    if not settings.GCS_BUCKET_NAME:
        raise HTTPException(
            status_code=500,
            detail="GCS bucket is not configured. Set GCS_BUCKET_NAME in settings.",
        )
    if not image_file.filename:
        raise HTTPException(status_code=400, detail="Image file must include a filename.")

    file_bytes = await image_file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Image file is empty.")
    if len(file_bytes) > IMAGE_INDEX_MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Image file exceeds {IMAGE_INDEX_MAX_FILE_SIZE // (1024 * 1024)} MB limit.",
        )

    extension = Path(image_file.filename).suffix or ".png"
    temp_path = UPLOADS_DIR / f"index_{uuid.uuid4()}{extension}"
    with open(temp_path, "wb") as tmp:
        tmp.write(file_bytes)

    normalized_type = _normalize_image_type(image_type)
    destination_blob = f"indexed/{uuid.uuid4()}{extension}"
    content_type = image_file.content_type or "image/png"

    try:
        embedding, auto_description = await _image_embedding_service.embed_image(temp_path)
        # Use description_override if provided and non-empty, otherwise use auto-generated description
        description = (
            description_override.strip() 
            if description_override and description_override.strip() 
            else auto_description
        )

        public_url = upload_to_gcs_and_get_public_url(temp_path, destination_blob, content_type)
        gcs_url = f"gs://{settings.GCS_BUCKET_NAME}/{destination_blob}"

        if verify_public:
            try:
                await verify_image_is_public(public_url)
            except Exception as exc:
                _logger.warning("Public verification failed for %s: %s", public_url, exc)

        metadata: Dict[str, Any] = {
            "filename": image_file.filename,
            "image_type": normalized_type,
            "gcs_url": gcs_url,
            "public_url": public_url,
            "description": description,
            "file_size": len(file_bytes),
        }

        if metadata_json and metadata_json.strip():
            try:
                extra = json.loads(metadata_json)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=400, detail=f"metadata_json must be valid JSON: {exc}") from exc
            if not isinstance(extra, dict):
                raise HTTPException(status_code=400, detail="metadata_json must be a JSON object.")
            metadata.update(extra)

        image_uri = source_uri.strip() if source_uri and source_uri.strip() else f"http://example.org/image/{uuid.uuid4()}"

        _image_embedding_service.store_embedding(
            image_uri=image_uri,
            embedding=embedding,
            metadata=metadata,
        )

        if store_in_kg:
            await _store_indexed_image_in_kg(
                image_uri=image_uri,
                filename=image_file.filename,
                gcs_url=gcs_url,
                image_type=normalized_type,
                description=description,
                file_size=len(file_bytes),
                embedding_dimension=len(embedding),
            )

        try:
            await _kg_logger_uploads.log_tool_call(
                tool_name="images.index",
                inputs={
                    "filename": image_file.filename,
                    "image_type": normalized_type,
                    "store_in_kg": store_in_kg,
                },
                outputs={
                    "image_uri": image_uri,
                    "gcs_url": gcs_url,
                    "public_url": public_url,
                },
                images=[public_url],
            )
        except Exception as exc:
            _logger.warning("KG logging for image index failed: %s", exc)

        return {
            "image_uri": image_uri,
            "description": description,
            "gcs_url": gcs_url,
            "public_url": public_url,
            "collection": _image_embedding_service.collection_name,
            "vector_dimension": len(embedding),
            "metadata": metadata,
        }
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


@app.post("/api/images/search-similar")
async def api_search_similar_images(
    image_file: UploadFile = File(...),
    limit: int = Form(10),
    score_threshold: float = Form(None),
):
    """
    Search for similar images using Qdrant vector similarity.
    
    Accepts an image file, generates an embedding, and searches Qdrant
    for the most similar images based on visual content.
    
    Args:
        image_file: The image file to search for similar images
        limit: Maximum number of results to return (default: 10)
        score_threshold: Minimum similarity score 0-1 (optional). 
                        Note: If None or 0.0, no threshold is applied (all results returned).
                        Values > 0.0 filter results to only those with similarity >= threshold.
    
    Returns:
        {
            "query_image": "description of uploaded image",
            "results": [
                {
                    "image_uri": "http://...",
                    "image_url": "https://storage.googleapis.com/...",  # Actual accessible URL
                    "score": 0.95,
                    "metadata": {...}
                },
                ...
            ]
        }
    """
    if not _image_embedding_service:
        raise HTTPException(
            status_code=503,
            detail="Image embedding service not available. Check Qdrant connection."
        )
    
    try:
        # Save uploaded file temporarily
        ext = Path(image_file.filename).suffix if image_file.filename else ".jpg"
        temp_filename = f"{uuid.uuid4()}{ext}"
        temp_path = UPLOADS_DIR / temp_filename
        
        # Save file
        with open(temp_path, "wb") as f:
            content = await image_file.read()
            f.write(content)
        
        _logger.info("Processing image for similarity search: %s", image_file.filename)
        
        # Generate embedding for the uploaded image
        query_embedding, image_description = await _image_embedding_service.embed_image(
            temp_path
        )
        
        # Search for similar images
        # Note: score_threshold=0.0 is treated as "no threshold" (allows all results)
        # This is intentional - 0.0 means "no minimum similarity required"
        normalized_threshold = score_threshold if score_threshold and score_threshold > 0.0 else None
        results = _image_embedding_service.search_similar_images(
            query_embedding=query_embedding,
            limit=limit,
            score_threshold=normalized_threshold,
        )
        
        # Convert placeholder URIs to actual accessible URLs
        # CRITICAL: Never fallback to placeholder - must find real URL or log error
        for result in results:
            image_uri = result.get("image_uri", "")
            metadata = result.get("metadata", {})
            
            # ALWAYS check metadata first (most reliable source)
            gcs_url = metadata.get("gcs_url", "")
            
            if gcs_url:
                # Convert gs:// URL to public HTTP URL
                public_url = _convert_gcs_url_to_public(gcs_url)
                result["image_url"] = public_url
                _logger.info(f"✅ Found gcs_url in Qdrant metadata for {image_uri[:50]}: {public_url[:80]}")
            elif metadata.get("public_url"):
                # Use public_url directly if available (stored during ingestion)
                result["image_url"] = metadata["public_url"]
                _logger.info(f"✅ Found public_url in Qdrant metadata for {image_uri[:50]}: {metadata['public_url'][:80]}")
            else:
                # NO gcs_url or public_url in metadata - try KG fallback
                _logger.warning(f"⚠️  No gcs_url or public_url in Qdrant metadata for {image_uri[:50]}, trying KG fallback...")
                _logger.debug(f"   Metadata keys available: {list(metadata.keys())}")
                kg_gcs_url = None
                
                try:
                    if _kg_manager and image_uri:
                        # Query KG for schema:contentUrl (which stores gcs_url)
                        query = f"""
                        PREFIX schema: <http://schema.org/>
                        SELECT ?gcs_url WHERE {{
                            <{image_uri}> schema:contentUrl ?gcs_url .
                        }}
                        LIMIT 1
                        """
                        kg_results = await _kg_manager.query_graph(query)
                        if kg_results and len(kg_results) > 0:
                            kg_gcs_url = str(kg_results[0].get("gcs_url", ""))
                            if kg_gcs_url:
                                public_url = _convert_gcs_url_to_public(kg_gcs_url)
                                result["image_url"] = public_url
                                _logger.info(f"✅ Found GCS URL in KG for {image_uri[:50]}: {public_url[:80]}")
                            else:
                                _logger.error(f"❌ KG query returned empty gcs_url for {image_uri[:50]}")
                        else:
                            _logger.error(f"❌ No GCS URL found in KG for {image_uri[:50]} (KG query returned no results)")
                    else:
                        _logger.error(f"❌ Cannot query KG (manager={_kg_manager is not None}, uri={bool(image_uri)})")
                except Exception as e:
                    _logger.error(f"❌ Exception querying KG for {image_uri[:50]}: {e}", exc_info=True)
                
                # If we still don't have a real URL, this is an ERROR
                if not result.get("image_url") or result.get("image_url") == image_uri or result.get("image_url", "").startswith("http://example.org"):
                    _logger.error(f"❌❌❌ FAILED to find real URL for {image_uri[:50]} - THIS IS AN ERROR")
                    _logger.error(f"   Metadata keys: {list(metadata.keys())}")
                    _logger.error(f"   gcs_url in metadata: {gcs_url}")
                    _logger.error(f"   KG gcs_url: {kg_gcs_url}")
                    _logger.error(f"   Current image_url: {result.get('image_url', 'NOT SET')}")
                    # DO NOT set placeholder - leave it missing so frontend can handle gracefully
                    # Or set to empty string so frontend shows error
                    result["image_url"] = ""  # Empty string signals error, not placeholder
        
        # Clean up temp file
        try:
            temp_path.unlink()
        except Exception:
            pass
        
        return {
            "query_image": image_description,
            "results": results,
            "total_found": len(results)
        }
    
    except Exception as e:
        _logger.error("/api/images/search-similar error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _ensure_gcs_client() -> gcs_storage.Client:
    global _gcs_storage_client
    if gcs_storage is None:
        raise HTTPException(status_code=500, detail="google-cloud-storage package is not installed")
    if _gcs_storage_client is None:
        _gcs_storage_client = gcs_storage.Client()
    return _gcs_storage_client


def _parse_gcs_url(gcs_url: str) -> tuple[str, str]:
    path = gcs_url[5:]  # strip gs://
    if "/" not in path:
        raise ValueError("Invalid GCS URL, missing blob path")
    bucket_name, blob_name = path.split("/", 1)
    if not bucket_name or not blob_name:
        raise ValueError("Invalid GCS URL components")
    return bucket_name, blob_name


async def _download_gcs_bytes(gcs_url: str) -> tuple[bytes, str]:
    bucket_name, blob_name = _parse_gcs_url(gcs_url)
    client = _ensure_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, blob.download_as_bytes)
    content_type = blob.content_type or mimetypes.guess_type(blob_name)[0] or "image/png"
    return data, content_type


async def _download_http_bytes(url: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", mimetypes.guess_type(url)[0] or "image/png")
        return response.content, content_type


async def _download_file_bytes(file_url: str) -> tuple[bytes, str]:
    file_path = file_url[7:]  # strip file://
    resolved = Path(file_path).resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        raise HTTPException(status_code=403, detail="File path outside workspace")
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, resolved.read_bytes)
    content_type = mimetypes.guess_type(resolved.name)[0] or "image/png"
    return data, content_type


def _get_qdrant_metadata_for_image(image_uri: str) -> Optional[Dict[str, Any]]:
    if not _image_embedding_service:
        return None
    preferred_id = generate_stable_point_id(image_uri)
    legacy_id = str(generate_legacy_point_id(image_uri))
    query_ids = [preferred_id]
    if legacy_id != preferred_id:
        query_ids.append(legacy_id)

    try:
        records = _image_embedding_service.qdrant_client.retrieve(
            collection_name=_image_embedding_service.collection_name,
            ids=query_ids,
            with_payload=True,
            with_vectors=False,
        )
    except Exception as exc:
        _logger.error("Failed to retrieve metadata for %s: %s", image_uri, exc)
        return None

    if not records:
        return None

    for record in records:
        payload = record.payload or {}
        if payload.get("image_uri") == image_uri or str(record.id) == preferred_id:
            return payload

    return records[0].payload or {}


async def _load_image_bytes_from_source(source_url: str) -> tuple[bytes, str]:
    try:
        if source_url.startswith("gs://"):
            return await _download_gcs_bytes(source_url)
        if source_url.startswith("file://"):
            return await _download_file_bytes(source_url)
        return await _download_http_bytes(source_url)
    except HTTPException:
        raise
    except Exception as exc:
        _logger.error("Failed to load image bytes from %s: %s", source_url, exc)
        raise HTTPException(status_code=500, detail="Failed to load image data")


async def _load_image_bytes_from_metadata(image_uri: str) -> tuple[bytes, str]:
    payload = _get_qdrant_metadata_for_image(image_uri)
    if not payload:
        raise HTTPException(status_code=404, detail="Image metadata not found in Qdrant")

    source_url = payload.get("public_url") or payload.get("gcs_url")
    if not source_url:
        raise HTTPException(status_code=404, detail="Image missing public URL metadata")

    return await _load_image_bytes_from_source(source_url)


@app.get("/api/images/view")
async def api_view_image(image_uri: str, source_url: Optional[str] = None):
    """
    Stream the actual image bytes for a Qdrant-stored result.

    The frontend requests this endpoint instead of hitting GCS directly so we
    can handle private buckets, local file:// URLs, and consistent headers.
    """
    if not _image_embedding_service:
        raise HTTPException(status_code=503, detail="Image embedding service unavailable")

    try:
        content, media_type = await _load_image_bytes_from_metadata(image_uri)
    except HTTPException as exc:
        if exc.status_code != 404 or not source_url:
            raise
        content, media_type = await _load_image_bytes_from_source(source_url)
    return Response(content=content, media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})


# New: One-call batch with uploads → themed portraits (6 refs → N images)
@app.post("/api/midjourney/generate-persona-themed-batch")
async def api_generate_persona_themed_batch(
    theme: str = Form(...),
    version: str = Form("v7"),
    count: int = Form(10),
    files: List[UploadFile] = File(...),
):
    """
    Accepts 6 uploaded images for a single persona, uploads them to GCS, then
    generates a themed set of images using the appropriate reference mode.

    Returns a list of final image URLs (and any workflow-provided metadata).
    """
    try:
        if not files or len(files) != 6:
            raise HTTPException(status_code=400, detail="Exactly 6 images are required.")

        uploaded_urls: List[str] = []
        for f in files:
            if not f.filename:
                raise HTTPException(status_code=400, detail="Each image must have a file name.")
            ext = Path(f.filename).suffix or ".png"
            unique_filename = f"{uuid.uuid4()}{ext}"
            local_path = UPLOADS_DIR / unique_filename
            with open(local_path, "wb") as out:
                out.write(await f.read())

            public_url = upload_to_gcs_and_get_public_url(local_path, unique_filename)
            uploaded_urls.append(public_url)

        # Delegate to existing workflow (handles version-aware cref/oref logic)
        try:
            results = await generate_themed_portraits(
                image_urls=uploaded_urls,
                theme=theme,
                model_version=version,
                num_images=count,
            )
        except Exception as e:
            _logger.error("generate_themed_portraits failed: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Workflow failed: {e}")

        # Normalize response shape
        if isinstance(results, list):
            return {"image_urls": results, "count": len(results)}
        if isinstance(results, dict):
            return results
        return {"result": results}

    except HTTPException:
        raise
    except Exception as e:
        _logger.error("/api/midjourney/generate-persona-themed-batch error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------- Health & Monitoring Endpoints ---------------------------

@app.get("/api/health")
async def health_check():
    """Comprehensive system health check endpoint."""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "components": {}
        }
        
        # Check agent registry
        if _refine_registry:
            try:
                agents = await _refine_registry.list_agents()
                health_status["components"]["agent_registry"] = {
                    "status": "healthy",
                    "agent_count": len(agents)
                }
            except Exception as e:
                health_status["components"]["agent_registry"] = {"status": "unhealthy", "error": str(e)}
                health_status["status"] = "degraded"
        
        # Check knowledge graph
        if _kg_manager:
            try:
                test_query = "SELECT ?s WHERE { ?s ?p ?o } LIMIT 1"
                await _kg_manager.query_graph(test_query)
                health_status["components"]["knowledge_graph"] = {
                    "status": "healthy",
                    "metrics": {
                        "queries": _kg_manager.metrics.get("query_count", 0),
                        "cache_hits": _kg_manager.metrics.get("cache_hits", 0)
                    }
                }
            except Exception as e:
                health_status["components"]["knowledge_graph"] = {"status": "unhealthy", "error": str(e)}
                health_status["status"] = "degraded"
        
        return health_status
    except Exception as e:
        _logger.error("Health check error: %s", e, exc_info=True)
        return {"status": "unhealthy", "timestamp": datetime.now().isoformat(), "error": str(e)}


@app.get("/api/metrics")
async def system_metrics():
    """Get system performance metrics."""
    try:
        metrics = {"timestamp": datetime.now().isoformat(), "knowledge_graph": {}, "agents": {}}
        
        if _kg_manager and hasattr(_kg_manager, 'metrics'):
            kg_m = _kg_manager.metrics
            cache_total = kg_m.get("cache_hits", 0) + kg_m.get("cache_misses", 0)
            metrics["knowledge_graph"] = {
                "total_queries": kg_m.get("query_count", 0),
                "cache_hit_ratio": kg_m.get("cache_hits", 0) / cache_total if cache_total > 0 else 0
            }
        
        if _refine_registry:
            agents = await _refine_registry.list_agents()
            metrics["agents"] = {"total_count": len(agents)}
        
        return metrics
    except Exception as e:
        _logger.error("Metrics error: %s", e, exc_info=True)
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

@app.post("/api/midjourney/imagine-and-mirror", response_model=MidjourneyImagineAndMirrorResponse)
async def api_midjourney_imagine_and_mirror(
    prompt: str = Form(...),
    version: str = Form("v7"),
    aspect_ratio: str | None = Form(None),
    process_mode: str | None = Form(None),
    cref: str | None = Form(None),
    cw: int | None = Form(None),
    oref: str | None = Form(None),
    ow: int | None = Form(None),
    interval: float = Form(5.0),
    timeout: int = Form(900),
):
    """Runs the agent-tools workflow: imagine → poll → mirror to GCS.

    Notes:
    - Version rules enforced in client (v6: cref/cw; v7: oref/ow)
    - Mirrors to gs://<bucket>/midjourney/<task_id>/image.png when possible
    - Logs to the knowledge graph via KGLogger
    """
    try:
        result = await imagine_then_mirror(
            prompt=prompt,
            version=version,
            aspect_ratio=aspect_ratio,
            process_mode=process_mode,
            cref=cref,
            cw=cw,
            oref=oref,
            ow=ow,
            poll_interval=interval,
            poll_timeout=timeout,
        )
        return MidjourneyImagineAndMirrorResponse(**result)
    except MidjourneyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _logger.error("/api/midjourney/imagine-and-mirror error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
            
            # Prepend the public URLs to the prompt
            if public_urls:
                # Replace placeholders in the prompt with the real URLs
                for url in public_urls:
                    final_prompt = final_prompt.replace("URL_PLACEHOLDER", url, 1)

        
        # Extract V7 parameters: --oref URL and --ow weight from the raw prompt BEFORE sanitization
        oref_match = re.search(r"--oref\s+(\S+)", final_prompt, re.IGNORECASE)
        ow_match = re.search(r"--ow\s+(\d+)", final_prompt, re.IGNORECASE)
        oref_url: Optional[str] = oref_match.group(1) if oref_match else None
        oref_weight: Optional[int] = int(ow_match.group(1)) if ow_match else None

        # Extract V6 parameters: --cref URL and --cw weight
        cref_match = re.search(r"--cref\s+(\S+)", final_prompt, re.IGNORECASE)
        cw_match = re.search(r"--cw\s+(\d+)", final_prompt, re.IGNORECASE)
        cref_url: Optional[str] = cref_match.group(1) if cref_match else None
        cref_weight: Optional[int] = int(cw_match.group(1)) if cw_match else None

        # Remove --oref <url> and --ow <int> segments from the prompt to avoid GoAPI parser errors
        # Handle both start-of-string and whitespace-prefixed occurrences
        if oref_match:
            final_prompt = re.sub(r"(?:^|\s)--oref\s+\S+", " ", final_prompt, flags=re.IGNORECASE)
        if ow_match:
            final_prompt = re.sub(r"(?:^|\s)--ow\s+\d+", " ", final_prompt, flags=re.IGNORECASE)
        
        # Remove --cref <url> and --cw <int> segments
        if cref_match:
            final_prompt = re.sub(r"(?:^|\s)--cref\s+\S+", " ", final_prompt, flags=re.IGNORECASE)
        if cw_match:
            final_prompt = re.sub(r"(?:^|\s)--cw\s+\d+", " ", final_prompt, flags=re.IGNORECASE)

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

        # Force/upgrade to v7 if --oref/--ow were detected and version is not already v7/niji 6/nano-banana
        if (oref_url or (oref_weight is not None)) and model_version not in {"v7", "niji 6", "nano-banana"}:
            model_version = "v7"
            _logger.info("Model_version set to v7 due to presence of --oref/--ow flags")
        
        # Force v6 if --cref/--cw were detected and version is not already set
        elif (cref_url or (cref_weight is not None)) and not model_version:
            model_version = "v6"
            _logger.info("Model_version set to v6 due to presence of --cref/--cw flags")

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

        # Check cache first (only if no file uploads - they make prompts unique)
        cache = get_cache()
        cached_result = None
        
        if cache and not image_files:
            cached_result = await cache.get(
                final_prompt,
                version=model_version,
                aspect_ratio=aspect_ratio_to_pass,
                process_mode=process_mode,
                cref=cref_url,
                cw=cref_weight,
                oref=oref_url,
                ow=oref_weight
            )
            
            if cached_result:
                _logger.info("Cache hit for prompt, returning cached result")
                cached_task_id = cached_result.get("result", {}).get("task_id")
                if cached_task_id:
                    return {"task_id": cached_task_id, "status": "cached"}

        # 2. Submit the task to Midjourney
        response = await _midjourney_client.submit_imagine(
            prompt=final_prompt,
            aspect_ratio=aspect_ratio_to_pass,
            process_mode=process_mode,
            oref_url=oref_url,
            oref_weight=oref_weight,
            cref_url=cref_url,
            cref_weight=cref_weight,
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
        
        # Cache the result for future use
        if cache and not image_files:
            await cache.set(
                final_prompt,
                {"task_id": task_id, "response": response},
                version=model_version,
                aspect_ratio=aspect_ratio_to_pass,
                process_mode=process_mode,
                cref=cref_url,
                cw=cref_weight,
                oref=oref_url,
                ow=oref_weight
            )

        # Also log to the knowledge graph so traces are visible for UI-driven flows
        try:
            await _kg_logger_uploads.log_tool_call(
                tool_name="mj.imagine",
                inputs={
                    "prompt": final_prompt,
                    "aspect_ratio": aspect_ratio_to_pass,
                    "process_mode": process_mode,
                    "model_version": model_version,
                    "oref_url": oref_url,
                    "oref_weight": oref_weight,
                    "cref_url": cref_url,
                    "cref_weight": cref_weight,
                },
                outputs=response,
                goapi_task=response,
                images=None,
            )
        except Exception as e:
            _logger.warning("KG logging (imagine) failed: %s", e)

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

        # Log to knowledge graph for trace visibility
        try:
            await _kg_logger_uploads.log_tool_call(
                tool_name="mj.action",
                inputs={
                    "origin_task_id": request.origin_task_id,
                    "action": request.action,
                },
                outputs=response,
                goapi_task=response,
                images=None,
            )
        except Exception as e:
            _logger.warning("KG logging (action) failed: %s", e)

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

        # 2. Submit the describe task
        response = await _midjourney_client.submit_describe(public_url)
        task_id = response.get("data", response).get("task_id")
        if not task_id:
            raise MidjourneyError(f"Could not get task_id from describe response: {response}")

        # 3. Poll for the result directly, as describe is usually fast
        final_payload = await poll_until_complete(client=_midjourney_client, task_id=task_id, kg_manager=_kg_manager)
        
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
        response = await _midjourney_client.submit_describe(image_url)
        task_id = response.get("data", response).get("task_id")
        if not task_id:
            raise MidjourneyError(f"Could not get task_id from describe response: {response}")
        final_payload = await poll_until_complete(client=_midjourney_client, task_id=task_id, kg_manager=_kg_manager)
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

        final_payload = await poll_until_complete(client=_midjourney_client, task_id=task_id, kg_manager=_kg_manager)
        
        seed = final_payload.get("output", {}).get("seed")
        if not seed:
            raise MidjourneyError("Seed task finished but no seed was found.")

        return {"seed": seed}

    except Exception as e:
        _logger.error("/api/midjourney/seed error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/midjourney/pan")
async def api_midjourney_pan(request: MidjourneyPanRequest):
    """Perform a pan operation using agent tools and mirror the result to GCS."""
    try:
        pan_tool = REGISTRY["mj.pan"]()
        get_task = REGISTRY["mj.get_task"]()
        mirror = REGISTRY["mj.gcs_mirror"]()

        res = await pan_tool.run(origin_task_id=request.origin_task_id, direction=request.direction)
        task_id = (res.get("data") or res).get("task_id") or (res.get("data") or res).get("id")
        if not task_id:
            raise MidjourneyError("No task_id returned from pan")
        # simple poll
        final = await poll_until_complete(client=_midjourney_client, task_id=task_id, kg_manager=_kg_manager)
        image_url = (final.get("output") or {}).get("image_url")
        gcs = None
        if image_url:
            m = await mirror.run(source_url=image_url, task_id=task_id, filename=f"pan_{request.direction}.png")
            gcs = m.get("gcs_url")
        return {"task_id": task_id, "image_url": image_url, "gcs_url": gcs}
    except Exception as e:
        _logger.error("/api/midjourney/pan error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/midjourney/outpaint")
async def api_midjourney_outpaint(request: MidjourneyOutpaintRequest):
    """Perform an outpaint operation using agent tools and mirror the result to GCS."""
    try:
        outpaint_tool = REGISTRY["mj.outpaint"]()
        mirror = REGISTRY["mj.gcs_mirror"]()

        res = await outpaint_tool.run(image_url=request.image_url, prompt=request.prompt)
        task_id = (res.get("data") or res).get("task_id") or (res.get("data") or res).get("id")
        if not task_id:
            raise MidjourneyError("No task_id returned from outpaint")
        final = await poll_until_complete(client=_midjourney_client, task_id=task_id, kg_manager=_kg_manager)
        image_url = (final.get("output") or {}).get("image_url")
        gcs = None
        if image_url:
            m = await mirror.run(source_url=image_url, task_id=task_id, filename="outpaint.png")
            gcs = m.get("gcs_url")
        return {"task_id": task_id, "image_url": image_url, "gcs_url": gcs}
    except Exception as e:
        _logger.error("/api/midjourney/outpaint error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/midjourney/variation")
async def api_midjourney_variation(request: MidjourneyVariationRequest):
    """Perform a variation (1-4) using agent tools action wrapper and mirror the result to GCS."""
    try:
        action_tool = REGISTRY["mj.action"]()
        mirror = REGISTRY["mj.gcs_mirror"]()

        action = f"variation{request.index}"
        res = await action_tool.run(origin_task_id=request.origin_task_id, action=action)
        task_id = (res.get("data") or res).get("task_id") or (res.get("data") or res).get("id")
        if not task_id:
            raise MidjourneyError("No task_id returned from variation")
        final = await poll_until_complete(client=_midjourney_client, task_id=task_id, kg_manager=_kg_manager)
        image_url = (final.get("output") or {}).get("image_url")
        gcs = None
        if image_url:
            m = await mirror.run(source_url=image_url, task_id=task_id, filename=f"variation{request.index}.png")
            gcs = m.get("gcs_url")
        return {"task_id": task_id, "image_url": image_url, "gcs_url": gcs}
    except Exception as e:
        _logger.error("/api/midjourney/variation error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/midjourney/cancel")
async def api_midjourney_cancel(request: MidjourneyCancelRequest):
    """Cancel a task using agent tools (current provider supports cancel via unified /task)."""
    try:
        cancel_tool = REGISTRY["mj.cancel"]()
        res = await cancel_tool.run(task_id=request.task_id)
        return res
    except Exception as e:
        _logger.error("/api/midjourney/cancel error: %s", e, exc_info=True)
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
    Optionally tracks refinement in history if session_id is provided.
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
        
        # Track in history if session_id provided
        if request.session_id:
            history = get_refinement_history()
            history.add_step(
                session_id=request.session_id,
                original_prompt=request.prompt,
                refined_prompt=final_prompt,
                method="agent",
                metadata={"agent": "agentic_prompt_agent"}
            )
        
        return {"refined_prompt": final_prompt, "session_id": request.session_id}
    except Exception as e:
        _logger.error("/api/midjourney/refine-prompt error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- ADDED: Multi-agent refinement endpoint (keeps original endpoint) ---
@app.post("/api/midjourney/refine-prompt-workflow")
async def api_midjourney_refine_prompt_workflow(request: RefinePromptRequest):
    """Run the multi-agent Planner workflow to refine prompts.
    Returns { refined_prompt, transcript }.
    Optionally tracks refinement in history if session_id is provided.
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
        
        # Track in history if session_id provided
        if request.session_id:
            history = get_refinement_history()
            history.add_step(
                session_id=request.session_id,
                original_prompt=request.prompt,
                refined_prompt=final_prompt,
                method="workflow",
                metadata={
                    "agent": "planner",
                    "transcript": transcript
                }
            )
        
        return {
            "refined_prompt": final_prompt,
            "transcript": transcript,
            "session_id": request.session_id
        }
    except Exception as e:
        _logger.error("/api/midjourney/refine-prompt-workflow error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- Refinement History & Undo/Redo Endpoints ---

@app.post("/api/midjourney/refine-history/new")
async def api_create_refinement_session():
    """Create a new refinement session for tracking history."""
    try:
        history = get_refinement_history()
        session_id = history.create_session()
        return {"session_id": session_id, "status": "created"}
    except Exception as e:
        _logger.error("/api/midjourney/refine-history/new error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/midjourney/refine-history/{session_id}")
async def api_get_refinement_history(session_id: str):
    """Get all refinement steps for a session."""
    try:
        history = get_refinement_history()
        steps = history.get_history(session_id)
        stats = history.get_session_stats(session_id)
        
        return {
            "session_id": session_id,
            "steps": [step.to_dict() for step in steps],
            "stats": stats
        }
    except Exception as e:
        _logger.error("/api/midjourney/refine-history/%s error: %s", session_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/midjourney/refine-undo/{session_id}")
async def api_refine_undo(session_id: str):
    """Undo the last refinement and return the previous prompt."""
    try:
        history = get_refinement_history()
        previous_step = history.undo(session_id)
        
        if previous_step is None:
            raise HTTPException(status_code=400, detail="Cannot undo: already at beginning of history")
        
        return {
            "session_id": session_id,
            "previous_prompt": previous_step.refined_prompt,
            "step": previous_step.to_dict(),
            "can_undo": history.can_undo(session_id),
            "can_redo": history.can_redo(session_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("/api/midjourney/refine-undo/%s error: %s", session_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/midjourney/refine-redo/{session_id}")
async def api_refine_redo(session_id: str):
    """Redo the next refinement and return the next prompt."""
    try:
        history = get_refinement_history()
        next_step = history.redo(session_id)
        
        if next_step is None:
            raise HTTPException(status_code=400, detail="Cannot redo: already at end of history")
        
        return {
            "session_id": session_id,
            "next_prompt": next_step.refined_prompt,
            "step": next_step.to_dict(),
            "can_undo": history.can_undo(session_id),
            "can_redo": history.can_redo(session_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("/api/midjourney/refine-redo/%s error: %s", session_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/midjourney/refine-history/{session_id}")
async def api_clear_refinement_history(session_id: str):
    """Clear all refinement history for a session."""
    try:
        history = get_refinement_history()
        success = history.clear_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        return {"session_id": session_id, "status": "cleared"}
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("/api/midjourney/refine-history/%s delete error: %s", session_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/midjourney/refine-stats/{session_id}")
async def api_get_refinement_stats(session_id: str):
    """Get statistics about a refinement session."""
    try:
        history = get_refinement_history()
        stats = history.get_session_stats(session_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("/api/midjourney/refine-stats/%s error: %s", session_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/midjourney/generate-themed-portraits")
async def api_generate_themed_portraits(req: ThemedPortraitsRequest):
    """Generate N themed images using reference images and mirror them to GCS.
    Returns: { images: [ {task_id, image_url, gcs_url}... ], errors: [] }
    """
    try:
        result = await generate_themed_portraits(
            theme=req.theme,
            face_image_urls=req.face_image_urls,
            count=req.count,
            version=req.version,
            aspect_ratio=req.aspect_ratio,
            process_mode=req.process_mode,
            cw=req.cw,
            ow=req.ow,
        )
        return result
    except Exception as e:
        _logger.error("/api/midjourney/generate-themed-portraits error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/persona-batch/generate")
async def api_persona_batch_generate(
    theme: str = Form(...),
    batch_size: int = Form(10),
    model_version: Optional[str] = Form(None),
    max_concurrent: int = Form(3),
    persona_urls: Optional[str] = Form(None),  # JSON array of URLs
    persona_files: List[UploadFile] = File([])  # Or upload files
):
    """
    Generate a batch of themed images using persona photos.
    
    Requires exactly 6 persona images (either as URLs or uploaded files).
    Uses the PersonaBatchGenerator with rate limiting and KG tracking.
    
    Args:
        theme: Theme description (e.g., "Lord of the Rings")
        batch_size: Number of images to generate (default 10)
        model_version: Optional MJ version (e.g., "6" or "7")
        max_concurrent: Max concurrent operations (default 3)
        persona_urls: JSON array of 6 persona image URLs
        persona_files: Or upload 6 persona image files
    
    Returns:
        Batch generation results with generated images and metadata
    """
    try:
        # Collect persona image URLs
        final_persona_urls = []
        
        # Option 1: Use provided URLs
        if persona_urls:
            try:
                import json
                urls = json.loads(persona_urls)
                if isinstance(urls, list):
                    final_persona_urls = urls
            except:
                raise HTTPException(status_code=400, detail="Invalid persona_urls JSON format")
        
        # Option 2: Upload files if no URLs provided
        if not final_persona_urls and persona_files:
            for file in persona_files:
                if not file.filename:
                    raise HTTPException(status_code=400, detail="All files must have names")
                
                # Upload to GCS
                ext = Path(file.filename).suffix
                unique_filename = f"persona_{uuid.uuid4()}{ext}"
                file_content = await file.read()
                
                public_url = upload_to_gcs_and_get_public_url(
                    file_content, unique_filename, file.content_type
                )
                final_persona_urls.append(public_url)
                _logger.info(f"Uploaded persona image: {public_url}")
        
        # Validate we have exactly 6 personas
        if len(final_persona_urls) != 6:
            raise HTTPException(
                status_code=400,
                detail=f"Exactly 6 persona images required, got {len(final_persona_urls)}"
            )
        
        # Create batch generator
        batch_generator = await create_batch_generator(
            kg_manager=_kg_manager,
            mj_client=_midjourney_client,
            max_concurrent=max_concurrent
        )
        
        # Generate batch
        _logger.info(f"Starting persona batch generation: theme='{theme}', size={batch_size}")
        result = await batch_generator.generate_themed_batch(
            persona_images=final_persona_urls,
            theme_prompt=theme,
            batch_size=batch_size,
            model_version=model_version
        )
        
        # Log success metrics
        if result["success"]:
            _logger.info(
                f"Batch {result['batch_id']} completed: "
                f"{result['total_generated']}/{result['total_requested']} generated"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        _logger.error(f"Persona batch generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/persona-batch/{batch_id}/status")
async def api_persona_batch_status(batch_id: str):
    """
    Get the status of a persona batch generation process.
    
    Args:
        batch_id: The batch identifier
        
    Returns:
        Batch status information from Knowledge Graph
    """
    try:
        # Create batch generator to access status method
        batch_generator = await create_batch_generator(
            kg_manager=_kg_manager,
            mj_client=_midjourney_client
        )
        
        # Get status
        status = await batch_generator.get_batch_status(batch_id)
        
        if not status["found"]:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        _logger.error(f"Error getting batch status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/midjourney/generate-themed-set")
async def api_generate_themed_set(req: ThemedSetRequest, background_tasks: BackgroundTasks):
    """Generate N distinct prompts for a theme via Planner refinement and submit N jobs.
    Uses reference images (V7: --oref/--ow, V6: --cref/--cw). Returns list of started task ids.
    """
    try:
        if not req.face_image_urls or len(req.face_image_urls) < 1:
            raise HTTPException(status_code=400, detail="face_image_urls must include at least one URL")

        # Helper: ask Planner to generate prompts from just the theme (preferred)
        async def planner_generate_prompts(theme: str, count: int, image_urls: list[str]) -> list[str]:
            if _planner is None:
                return []
            transcript: list[str] = []
            async def on_stream(text: str):
                transcript.append(text)
            # Best-effort generic prompt-generation request; tolerate different planner schemas
            msg = AgentMessage(
                sender_id="api",
                recipient_id="planner",
                content={
                    "theme": (theme or "").strip(),
                    "count": int(max(1, count)),
                    "image_urls": image_urls[:6],
                    "streaming_callback": on_stream,
                },
                message_type="prompt_generation_request",
            )
            try:
                result = await _planner.process_message(msg)
                content = getattr(result, "content", {}) or {}
                prompts = content.get("prompts")
                if isinstance(prompts, list) and prompts:
                    # Ensure strings only
                    return [str(p) for p in prompts if isinstance(p, (str,))]
                # Fallback: some planners return a single final_prompt
                fp = content.get("final_prompt")
                if isinstance(fp, str) and fp.strip():
                    return [fp.strip()]
            except Exception:
                pass
            return []

        # Helper to refine a single prompt via the Planner (fallback path)
        async def refine_prompt(raw: str) -> str:
            # Check if planner is available and is a real agent (not None or Mock)
            if _planner is None:
                return raw
            # Safety check: ensure _planner is not a mock object
            if hasattr(_planner, '__class__') and 'Mock' in _planner.__class__.__name__:
                _logger.warning("Planner is a Mock object, skipping refinement")
                return raw
            # Additional check for callable process_message
            if not hasattr(_planner, 'process_message') or not callable(getattr(_planner, 'process_message', None)):
                _logger.warning("Planner does not have callable process_message, skipping refinement")
                return raw
            
            transcript: list[str] = []
            async def on_stream(text: str):
                transcript.append(text)
            msg = AgentMessage(
                sender_id="api",
                recipient_id="planner",
                content={
                    "prompt": raw,
                    "image_urls": req.face_image_urls[:6],
                    "streaming_callback": on_stream,
                },
                message_type="refine_request",
            )
            try:
                result = await _planner.process_message(msg)
                return result.content.get("final_prompt") or raw
            except Exception as e:
                _logger.warning(f"Planner refinement failed: {e}")
                return raw

        # Use internal generator then Planner refinement per-prompt
        # (Disabled direct Planner generation - it was describing images instead of using theme)
        theme = (req.theme or "").strip() or "portrait photography"
        
        # Generate theme-aware prompts using internal generator (this works reliably)
        generated_prompts: list[str] = []
        for _ in range(max(1, req.count)):
            generated_prompts.append(_generate_theme_aware_prompt(theme))
        
        # Optionally refine each prompt via Planner (preserves theme)
        refined_prompts = []
        for base in generated_prompts:
            refined = await refine_prompt(base)
            refined_prompts.append(refined)

        # Submit N imagine jobs: include ALL face URLs in prompt; pick a random one for oref; force V7 + FAST
        started: list[dict[str, str]] = []
        for i, prompt in enumerate(refined_prompts):
            try:
                # Build prompt prefix with all reference images
                face_list = req.face_image_urls[:6]
                images_prefix = " ".join(face_list)
                suffix = (req.extra_params or "").strip()
                full_prompt = (images_prefix + " " + prompt + (" " + suffix if suffix else "")).strip()

                # Choose random oref from provided faces
                ref_url = random.choice(face_list)
                is_v7 = True
                kwargs = dict(
                    prompt=full_prompt,
                    aspect_ratio=(req.aspect_ratio or "1:1"),
                    process_mode="fast" if not req.process_mode else req.process_mode,
                    model_version="v7",
                )
                if is_v7:
                    kwargs.update({"oref_url": ref_url, "oref_weight": (req.ow if req.ow is not None else 120)})
                else:
                    # For V6 path, the client reads cref/cw inside prompt strip; pass via kwargs compatible with client
                    kwargs.update({"oref_url": None})

                response = await _midjourney_client.submit_imagine(**kwargs)
                data = response.get("data", response)
                task_id = (data or {}).get("task_id") or (data or {}).get("id")
                if not task_id:
                    continue

                # persist metadata and poll
                task_dir = JOBS_DIR / task_id
                task_dir.mkdir(exist_ok=True)
                _save_json_atomic(task_dir / "metadata.json", data)
                background_tasks.add_task(poll_and_store_task, task_id)

                # log to KG
                try:
                    await _kg_logger_uploads.log_tool_call(
                        tool_name="mj.imagine",
                        inputs={
                            "prompt": full_prompt,
                            "aspect_ratio": kwargs["aspect_ratio"],
                            "process_mode": kwargs["process_mode"],
                            "model_version": "v7",
                            "oref_url": ref_url,
                            "oref_weight": kwargs.get("oref_weight"),
                            "all_refs": face_list,
                        },
                        outputs=response,
                        goapi_task=response,
                        images=None,
                    )
                except Exception:
                    pass

                started.append({"task_id": task_id, "refined_prompt": full_prompt})
            except Exception:
                continue

        return {"tasks": started}
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("/api/midjourney/generate-themed-set error: %s", e, exc_info=True)
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


@app.get("/api/midjourney/kg/uploads")
async def api_midjourney_list_uploads():
    """List uploaded images recorded in the knowledge graph.

    Returns recent ToolCalls for mj.upload_image with associated media URLs.
    """
    try:
        await _kg_manager.initialize()
        query = """
PREFIX core: <http://example.org/core#>
PREFIX mj: <http://example.org/midjourney#>
PREFIX schema: <http://schema.org/>

SELECT ?call ?when ?url
WHERE {
  ?call core:type <http://example.org/midjourney#ToolCall> .
  ?call core:name "mj.upload_image" .
  OPTIONAL { ?call core:timestamp ?when }
  ?call schema:associatedMedia ?media .
  ?media schema:contentUrl ?url .
}
ORDER BY DESC(?when)
LIMIT 200
"""
        rows = await _kg_manager.query_graph(query)
        return rows
    except Exception as e:
        _logger.error("/api/midjourney/kg/uploads error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/midjourney/kg/trace/{task_id}")
async def api_midjourney_trace_task(task_id: str):
    """Return a full trace for a task id: tool calls, inputs, outputs, images."""
    try:
        await _kg_manager.initialize()
        query = f"""
PREFIX core: <http://example.org/core#>
PREFIX mj: <http://example.org/midjourney#>
PREFIX schema: <http://schema.org/>

SELECT ?call ?name ?when ?input ?output ?media
WHERE {{
  BIND(<http://example.org/midjourney#Task/{task_id}> AS ?task)
  ?call core:type <http://example.org/midjourney#ToolCall> .
  ?call core:relatedTo ?task .
  ?call core:name ?name .
  OPTIONAL {{ ?call core:timestamp ?when }}
  OPTIONAL {{ ?call mj:input ?input }}
  OPTIONAL {{ ?call mj:output ?output }}
  OPTIONAL {{ ?call schema:associatedMedia ?m . ?m schema:contentUrl ?media }}
}}
ORDER BY ?when
"""
        rows = await _kg_manager.query_graph(query)
        return rows
    except Exception as e:
        _logger.error("/api/midjourney/kg/trace error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/api/planner-status")
async def api_planner_status():
    """Check if the Planner agent is available and working."""
    status = {
        "imports_ok": _MA_IMPORTS_OK,
        "planner_available": _planner is not None,
        "planner_type": type(_planner).__name__ if _planner else None,
        "registry_available": _refine_registry is not None,
        "registry_agents": []
    }
    
    # Check if planner is a Mock
    if _planner and hasattr(_planner, '__class__') and 'Mock' in _planner.__class__.__name__:
        status["warning"] = "Planner is a Mock object - not functional"
        status["planner_available"] = False
    
    # List registered agents if registry exists
    if _refine_registry:
        try:
            from agents.core.base_agent import BaseAgent
            status["registry_agents"] = list(BaseAgent._GLOBAL_AGENTS.keys())
        except:
            pass
    
    # Test planner if available
    if _planner and status["planner_available"]:
        try:
            # Simple test message
            from agents.core.message_types import AgentMessage
            test_msg = AgentMessage(
                sender_id="api_test",
                recipient_id="planner",
                content={"prompt": "test prompt"},
                message_type="refine_request"
            )
            # We won't actually await this, just check it's callable
            if hasattr(_planner, 'process_message'):
                status["planner_functional"] = "process_message method exists"
            else:
                status["planner_functional"] = "Missing process_message method"
        except Exception as e:
            status["planner_functional"] = f"Error testing: {str(e)}"
    else:
        status["planner_functional"] = "Not available to test"
    
    # Add troubleshooting tips
    if not _MA_IMPORTS_OK:
        status["troubleshooting"] = [
            "Agent imports failed - check if agents/ directory exists",
            "Check: from agents.domain.planner_agent import PlannerAgent",
            "Check: from agents.core.agent_registry import AgentRegistry",
            "Run: python -c 'from agents.domain.planner_agent import PlannerAgent'"
        ]
    elif not _planner:
        status["troubleshooting"] = [
            "Planner initialization failed during startup",
            "Check server logs for 'Multi-agent refinement not available' message",
            "Restart the server to reinitialize"
        ]
    
    return status

@app.post("/api/planner/create-plan")
async def api_create_plan(request: Dict[str, Any]):
    """Create a plan using the Planner agent and store it in the Knowledge Graph."""
    if not _planner:
        raise HTTPException(status_code=503, detail="Planner agent not available")
    
    # Extract parameters
    theme = request.get("theme", "")
    if not theme:
        raise HTTPException(status_code=400, detail="Theme is required")
    
    context = request.get("context", {})
    
    try:
        from agents.domain.planner_kg_extension import create_and_store_plan
        
        # Create and store the plan
        plan = await create_and_store_plan(_planner, theme, context)
        
        _logger.info(f"Created plan {plan['id']} for theme: {theme}")
        return plan
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Plan creation module not found")
    except Exception as e:
        _logger.error(f"Error creating plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/planner/get-plan/{plan_id}")
async def api_get_plan(plan_id: str):
    """Retrieve a plan from the Knowledge Graph."""
    if not _planner:
        raise HTTPException(status_code=503, detail="Planner agent not available")
    
    try:
        from agents.domain.planner_kg_extension import retrieve_plan
        
        plan = await retrieve_plan(_planner, plan_id)
        
        if "error" in plan:
            raise HTTPException(status_code=404, detail=plan["error"])
        
        return plan
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Plan retrieval module not found")
    except HTTPException:
        raise
    except Exception as e:
        _logger.error(f"Error retrieving plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/planner/list-plans")
async def api_list_plans(theme_filter: str = None):
    """List all plans in the Knowledge Graph."""
    if not _planner:
        raise HTTPException(status_code=503, detail="Planner agent not available")
    
    try:
        from agents.domain.planner_kg_extension import list_plans
        
        plans = await list_plans(_planner, theme_filter)
        return {"plans": plans, "count": len(plans)}
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Plan listing module not found")
    except Exception as e:
        _logger.error(f"Error listing plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/planner/execute-step")
async def api_execute_plan_step(request: Dict[str, Any]):
    """Execute a specific step from a stored plan."""
    if not _planner:
        raise HTTPException(status_code=503, detail="Planner agent not available")
    
    plan_id = request.get("plan_id")
    step_number = request.get("step_number")
    
    if not plan_id or step_number is None:
        raise HTTPException(status_code=400, detail="plan_id and step_number are required")
    
    try:
        from agents.domain.planner_kg_extension import execute_plan_step
        
        result = await execute_plan_step(_planner, plan_id, int(step_number))
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Plan execution module not found")
    except HTTPException:
        raise
    except Exception as e:
        _logger.error(f"Error executing plan step: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/kg/sparql-query")
async def api_sparql_query(request: Dict[str, Any]):
    """Execute a SPARQL query on the Knowledge Graph."""
    query = request.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="SPARQL query is required")
    
    try:
        # Try to use the planner's KG if available
        if _planner and _planner.knowledge_graph:
            kg = _planner.knowledge_graph
        else:
            # Fall back to creating a new KG manager
            from kg.models.graph_manager import KnowledgeGraphManager
            kg = KnowledgeGraphManager(persistent_storage=True)
            await kg.initialize()
        
        # Execute the query
        results = await kg.query_graph(query)
        
        return {
            "results": results,
            "count": len(results),
            "query": query
        }
        
    except Exception as e:
        _logger.error(f"SPARQL query error: {e}")
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

@app.post("/api/orchestration/create-workflow")
async def api_create_orchestration_workflow(request: Dict[str, Any]):
    """Create a comprehensive orchestration workflow from text file."""
    if not _planner:
        raise HTTPException(status_code=503, detail="Planner agent not available")
    
    text_file = request.get("text_file")
    user_email = request.get("user_email")
    workflow_name = request.get("workflow_name", "Orchestrated Workflow")
    
    if not text_file or not user_email:
        raise HTTPException(status_code=400, detail="text_file and user_email are required")
    
    try:
        from agents.domain.orchestration_workflow import OrchestrationWorkflow
        from agents.domain.code_review_agent import CodeReviewAgent
        
        # Initialize review agents
        review_agents = []
        try:
            # Create a code review agent for reviews
            review_agent = CodeReviewAgent("code_reviewer")
            await review_agent.initialize()
            review_agents.append(review_agent)
        except Exception as e:
            _logger.warning(f"Could not initialize review agent: {e}")
        
        # Create workflow
        workflow = OrchestrationWorkflow(_planner, review_agents)
        await workflow.initialize()
        
        # Create workflow from text
        result = await workflow.create_workflow_from_text(
            text_file, user_email, workflow_name
        )
        
        _logger.info(f"Created orchestration workflow: {result.get('workflow_id')}")
        return result
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        _logger.error(f"Error creating orchestration workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/orchestration/execute-step")
async def api_execute_orchestration_step(request: Dict[str, Any]):
    """Execute a specific step in the orchestration workflow."""
    if not _planner:
        raise HTTPException(status_code=503, detail="Planner agent not available")
    
    workflow_id = request.get("workflow_id")
    step_name = request.get("step")
    
    if not workflow_id or not step_name:
        raise HTTPException(status_code=400, detail="workflow_id and step are required")
    
    try:
        from agents.domain.orchestration_workflow import OrchestrationWorkflow
        from agents.domain.code_review_agent import CodeReviewAgent
        
        # Initialize review agents
        review_agents = []
        try:
            review_agent = CodeReviewAgent("code_reviewer")
            await review_agent.initialize()
            review_agents.append(review_agent)
        except Exception as e:
            _logger.warning(f"Could not initialize review agent: {e}")
        
        # Create workflow
        workflow = OrchestrationWorkflow(_planner, review_agents)
        await workflow.initialize()
        
        # Execute the requested step
        if step_name == "send_email":
            user_email = request.get("user_email")
            if not user_email:
                raise HTTPException(status_code=400, detail="user_email required for send_email step")
            result = await workflow.send_plan_for_review(workflow_id, user_email)
        elif step_name == "visualize":
            result = await workflow.visualize_plan_in_kg(workflow_id)
        elif step_name == "review":
            result = await workflow.conduct_agent_review(workflow_id)
        elif step_name == "validate":
            result = await workflow.validate_execution_readiness(workflow_id)
        elif step_name == "execute":
            result = await workflow.execute_workflow(workflow_id)
        elif step_name == "analyze":
            result = await workflow.conduct_post_execution_analysis(workflow_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown step: {step_name}")
        
        return result
        
    except Exception as e:
        _logger.error(f"Error executing orchestration step: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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

@app.post("/api/visualize-workflow")
async def api_visualize_workflow(request: Dict[str, Any]):
    """Visualize a workflow from the Knowledge Graph."""
    try:
        workflow_id = request.get("workflow_id")
        if not workflow_id:
            return {"error": "workflow_id is required"}

        from agents.domain.orchestration_workflow import OrchestrationWorkflow
        from agents.domain.planner_agent import PlannerAgent
        from agents.domain.code_review_agent import CodeReviewAgent
        from agents.core.agent_registry import AgentRegistry

        # Initialize registry and get planner
        registry = AgentRegistry(disable_auto_discovery=False)
        planner = PlannerAgent("planner", registry)

        # Initialize review agents
        review_agents = []
        try:
            review_agent = CodeReviewAgent("code_reviewer")
            review_agents.append(review_agent)
        except Exception as e:
            print(f"⚠️ Could not initialize review agent: {e}")

        # Create workflow
        workflow = OrchestrationWorkflow(planner, review_agents)

        # Visualize the plan
        result = await workflow.visualize_plan_in_kg(workflow_id)

        return result

    except Exception as e:
        return {"error": str(e)}

@app.get("/api/list-workflows")
async def api_list_workflows():
    """List all workflows in the Knowledge Graph."""
    try:
        await _kg_manager.initialize()
        query = """
        PREFIX wf: <http://example.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?workflow ?theme ?createdAt ?status ?workflowName
        WHERE {
            ?workflow a wf:Workflow .
            ?workflow wf:hasTheme ?theme .
            ?workflow wf:createdAt ?createdAt .
            ?workflow wf:status ?status .
            OPTIONAL { ?workflow wf:workflowName ?workflowName . }
        }
        ORDER BY DESC(?createdAt)
        """
        workflows = await _kg_manager.query_graph(query)

        return workflows

    except Exception as e:
        _logger.error("/api/list-workflows error: %s", e, exc_info=True)
        return {"error": str(e)}

@app.get("/api/midjourney/occurrences")
async def api_list_occurrences():
    """List all Midjourney job occurrences in the Knowledge Graph."""
    try:
        await _kg_manager.initialize()
        query = """
        PREFIX mj: <http://example.org/midjourney#>
        PREFIX core: <http://example.org/core#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?occurrence ?jobType ?taskId ?status ?startTime ?endTime ?progress
        WHERE {
            ?occurrence a core:JobOccurrent .
            ?occurrence core:hasJobType ?jobType .
            ?occurrence core:hasTaskId ?taskId .
            ?occurrence core:hasStatus ?status .
            ?occurrence core:hasStartTime ?startTime .
            OPTIONAL { ?occurrence core:hasEndTime ?endTime }
            OPTIONAL { ?occurrence core:hasProgress ?progress }
        }
        ORDER BY DESC(?startTime)
        """
        occurrences = await _kg_manager.query_graph(query)

        return occurrences

    except Exception as e:
        _logger.error("/api/midjourney/occurrences error: %s", e, exc_info=True)
        return {"error": str(e)}

@app.get("/api/midjourney/occurrences/{task_id}")
async def api_get_occurrence(task_id: str):
    """Get a specific Midjourney job occurrence by task ID."""
    try:
        await _kg_manager.initialize()
        query = f"""
        PREFIX mj: <http://example.org/midjourney#>
        PREFIX core: <http://example.org/core#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?occurrence ?jobType ?status ?startTime ?endTime ?progress ?prompt ?error
        WHERE {{
            ?occurrence a core:JobOccurrent .
            ?occurrence core:hasTaskId "{task_id}" .
            ?occurrence core:hasJobType ?jobType .
            ?occurrence core:hasStatus ?status .
            ?occurrence core:hasStartTime ?startTime .
            OPTIONAL {{ ?occurrence core:hasEndTime ?endTime }}
            OPTIONAL {{ ?occurrence core:hasProgress ?progress }}
            OPTIONAL {{ ?occurrence mj:hasPrompt ?prompt }}
            OPTIONAL {{ ?occurrence core:hasError ?error }}
        }}
        """
        occurrences = await _kg_manager.query_graph(query)

        if not occurrences:
            return {"error": f"No occurrence found for task ID: {task_id}"}

        return occurrences[0]

    except Exception as e:
        _logger.error("/api/midjourney/occurrences/{task_id} error: %s", e, exc_info=True)
        return {"error": str(e)}

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
