# Kontext Integration (GoAPI PPU)

This module mirrors the project's `midjourney_integration` but targets a
separate model/service called "Kontext" via GoAPI's `/task` endpoint.

## Features
- Async `KontextClient` with retry/backoff for 429/5xx
- `generate` and `action` operations
- CLI parity: `python -m kontext_integration.cli generate ...`
- GCS upload helper for image-based prompts

## Environment Variables
Add to your `.env`:
```
KONTEXT_API_TOKEN=your-goapi-token
GOAPI_BASE_URL=https://api.goapi.ai/api/v1   # optional
GCS_BUCKET_NAME=your-gcs-bucket
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

## Quick Start
```bash
# Generate (PPU modes: relax|fast|turbo)
python -m kontext_integration.cli generate "A modern abstract poster" --aspect_ratio 16:9 --mode relax

# With image prompt (uploads to GCS first)
python -m kontext_integration.cli generate "Stylized variant" --image_path ./local.png --mode fast

# Action on existing task
python -m kontext_integration.cli action reroll <task_id>
```

## Notes
- Secrets are read from environment; nothing is hard-coded.
- Logging avoids printing sensitive tokens.
- If you see HTTP 429/5xx, client automatically retries with exponential backoff.


