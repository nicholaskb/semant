# Kids Monsters GCS Downloader Restore
**Timestamp:** 2025-11-14 13:05 PT  
**Objective:** Reintroduce the local helper that downloads `kids_monsters` inputs/outputs from GCS and auto-batches them for Apple Photos so we can fetch large drops without manual `gsutil` work.

## Files Changed
1. `scripts/tools/download_and_batch.py`
   - Recreated the CLI helper exactly as previously shared so it can list, download, and batch both `input_kids_monster/` and `generated_images/` prefixes with filters, overwrite controls, and Apple Photos batch prep.

## Endpoints / Workflows Affected
- CLI workflow `scripts/tools/download_and_batch.py`: local-only tool to pull from GCS and prepare upload folders; no HTTP API endpoints changed.

## Verification
- Not run yet (no GCP creds in sandbox). Logic review only; run `python3 scripts/tools/download_and_batch.py --help` locally after loading `google-cloud-storage` to confirm.

## Implemented vs Proposed
- **Implemented.** Script restored per original spec; no pending follow-ups besides local smoke test when credentials are available.

