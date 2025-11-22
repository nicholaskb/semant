Midjourney Agent Tools (GoAPI + Knowledge Graph + GCS)

Overview
- Agent-oriented wrappers around GoAPI with client-side validation, retries/backoff, knowledge-graph logging, and optional GCS mirroring using existing helpers.
- Tools are exposed via a registry for easy discovery and orchestration.

Requirements
- Environment:
  - MIDJOURNEY_API_TOKEN (required)
  - GCS bucket (optional, required for mirroring): `config.settings.GCS_BUCKET_NAME`
- No hard-coded secrets. Tokens via environment or .env.

Implemented Tools (Registry Keys)
- mj.imagine: create new image task
- mj.action: post-process (upscale/variation/reroll)
- mj.describe: describe an image
- mj.seed: fetch seed
- mj.blend: blend images
- mj.get_task: fetch task status (also logs image URLs to KG)
- mj.cancel: cancel task (generic path, update when upstream confirms)
- mj.inpaint / mj.outpaint / mj.pan / mj.zoom: additional operations
- mj.gcs_mirror: mirror a remote image to GCS using existing uploader

Version Rules (validated client-side)
- V6 only: --cref, --cw
- V7 only: --oref, --ow

Quick Start (Live Imagine)
1) Export token
```bash
export MIDJOURNEY_API_TOKEN='YOUR_TOKEN'
```
2) Run a live job
```bash
python -m examples.midjourney_agent_tools_live_demo --prompt "a minimalist watercolor fox, soft palette" --version v7
```
- Behavior:
  - Submits imagine
  - Polls until complete
  - Prints final image URL
  - Mirrors to GCS at `gs://<GCS_BUCKET_NAME>/midjourney/<task_id>/image.png` if available
- Example output URL:
  - `https://storage.googleapis.com/<bucket>/midjourney/<task_id>/image.png`

Live Action (Upscale/Variation/Reroll)
```bash
python -m examples.midjourney_agent_tools_action_live --task-id <task_id> --action upscale2
```
- Behavior:
  - Submits action (e.g., `upscale2`)
  - Polls until complete
  - Mirrors resulting image to `gs://<bucket>/midjourney/<new_task_id>/upscale2.png`

Knowledge Graph Demos
- Verify prompt + image stored in KG:
```bash
python -m examples.midjourney_agent_tools_kg_check
```
- SPARQL view of recent ToolCalls (prompts + image URLs):
```bash
python -m examples.midjourney_agent_tools_sparql_demo
```
- Print latest prompt + image URL (optionally run a new imagine first):
```bash
python -m examples.midjourney_agent_tools_latest --run --prompt "a minimalist watercolor fox, soft palette" --version v7
python -m examples.midjourney_agent_tools_latest
```

Where the Code Lives
- Registry: `semant/agent_tools/midjourney/__init__.py`
- Client: `semant/agent_tools/midjourney/goapi_client.py`
- KG logging: `semant/agent_tools/midjourney/kg_logging.py`
- Tools: `semant/agent_tools/midjourney/tools/*.py`
- Examples: `examples/midjourney_agent_tools_*.py`

GCS Mirroring
- Uses existing uploader in `midjourney_integration/client.py` (`upload_to_gcs_and_get_public_url`, `verify_image_is_public`).
- Mirrors under `midjourney/<task_id>/image.png` and logs a `schema:ImageObject` in KG.

Testing
- Unit tests mock httpx and use an in-memory KG. Run:
```bash
pytest -q tests/unit/test_midjourney_*midjourney*.py
```

Known Limitations / Placeholders

API Endpoint (Workflow)
- Imagine + mirror in a single call:
```bash
curl -X POST http://localhost:8000/api/midjourney/imagine-and-mirror \
  -F prompt="a minimalist watercolor fox, soft palette" \
  -F version=v7 \
  -F interval=5 -F timeout=300
# Response: { "task_id": "...", "image_url": "...", "gcs_url": "..." }
```

Additional API Endpoints
- Pan:
```bash
curl -X POST http://localhost:8000/api/midjourney/pan \
  -H 'Content-Type: application/json' \
  -d '{"origin_task_id":"<task_id>", "direction":"right"}'
```
- Outpaint:
```bash
curl -X POST http://localhost:8000/api/midjourney/outpaint \
  -H 'Content-Type: application/json' \
  -d '{"image_url":"https://...", "prompt":"extend to the right"}'
```
- Variation:
```bash
curl -X POST http://localhost:8000/api/midjourney/variation \
  -H 'Content-Type: application/json' \
  -d '{"origin_task_id":"<task_id>", "index":2}'
```
- Cancel endpoint uses a generic task payload; update once the canonical upstream path is confirmed.
- Advanced param validation for in/outpaint/pan/zoom is minimal; expand as feature specs stabilize.


Parameter Validation (Client-Side)
- Inpaint: image_url and mask_url must be http(s)
- Outpaint: image_url must be http(s)
- Pan: direction must be one of [down, left, right, up]
- Zoom: factor must be numeric and > 0

