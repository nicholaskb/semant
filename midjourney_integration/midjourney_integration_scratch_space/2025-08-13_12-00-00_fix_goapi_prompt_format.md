# 2025-08-13 12:00:00 – Fix GoAPI prompt format error

- Timestamp: 2025-08-13 12:00:00
- Objective: Resolve GoAPI 500 error "Invalid Param Format: there should be space before --" when submitting imagine jobs that include inline flags like `--v 6` and `--ar`.
- Context: Error observed in logs during POST /api/midjourney/imagine. GoAPI rejected prompt due to inline flag formatting. We already pass `aspect_ratio` and `model_version` via payload.

Files changed:
- `main.py` – Additive normalization in `_sanitize_mj_prompt` to remove inline `--v <x>` flags and keep spacing normalization; retain existing removals for `--ar` (when aspect ratio sent separately) and v7-incompatible flags. Pre-extract `--ar` before sanitation to preserve user-selected ratio.

Endpoints affected:
- `POST /api/midjourney/imagine` (server-side prompt sanitation only; no API change)

Implementation details:
- Added `_MJ_FLAG_PATTERNS["version"] = re.compile(r"\\s--v\\s+\\S+", re.IGNORECASE)`.
- Updated `_sanitize_mj_prompt` to always strip inline version flags before sending to GoAPI, ensure spacing before flags, collapse whitespace.
- Extract aspect ratio before sanitization to avoid losing it when removing `--ar` inline.
- Rationale: We already parse version and pass `model_version` in payload; removing `--v` from the inline prompt prevents GoAPI format checks from tripping on flag spacing or duplication.

Verification steps:
1) Start server: `python main.py`.
2) From UI, submit a prompt containing `--v 6` and `--ar 1:1` inline.
3) Confirm server log shows sanitized prompt without `--v`/`--ar`, aspect ratio extracted and sent via `input.aspect_ratio`, and `model_version` present in payload.
4) Verify GoAPI no longer returns 500 and job is created; gallery updates accordingly.

Implemented vs Proposed:
- Implemented minimal, non-destructive sanitation at the API layer. No removals of features. Maintains support for all advanced parameters with server-side validation/normalization.

Potential side effects:
- None expected; users still see their original text minus redundant flags. `model_version` and `aspect_ratio` are preserved via payload fields.
