# 2025-08-13 — Parse --oref/--ow and pass via payload (v7)

- Timestamp: 2025-08-13
- Objective: Parse `--oref <url>` and `--ow <int>` from the prompt, remove them from the text, and send as `input.oref` and `input.ow`. Keep/auto-upgrade `model_version: v7` when these flags are present to avoid GoAPI "Unrecognized Param: --" errors.

- Files changed:
  - `main.py` (endpoint `POST /api/midjourney/imagine`): Extract `--oref` and `--ow` prior to sanitization, strip from prompt, pass as `oref_url` and `oref_weight` to client.
  - `midjourney_integration/client.py`: Prefix prompt with `image` when it begins with `--oref`, strip `--cref/--cw` for v7 in client path, and switch HTTP helper to use explicit `post`/`get` (test compatibility).

- Endpoints affected:
  - `POST /api/midjourney/imagine`

- Implementation details:
  - Regex pre-scan: `--oref\s+(\S+)`, `--ow\s+(\d+)`
  - Remove segments from prompt: `\s--oref\s+\S+`, `\s--ow\s+\d+`
  - Forward `oref_url` and `oref_weight` into `MidjourneyClient.submit_imagine`, which maps to `input.oref` and `input.ow`.
  - Auto-upgrade to `v7` when `--oref/--ow` present remains in place.

- Verification steps:
  1) Start server: `python main.py`
  2) Submit prompt: `sunset portrait --ar 2:3 --oref https://example.com/img.png --ow 75`
  3) Observe logs: final prompt contains no `--oref/--ow`; payload `input.oref` and `input.ow` set; `input.model_version` contains `v7`.
  4) Confirm no GoAPI parser errors and task is created.
  5) Run tests: `pytest -q tests/test_midjourney_integration.py::test_submit_imagine_prompt_handling` — should pass.

- Implemented vs Proposed:
  - Implemented minimal, additive parsing and sanitization in API layer; no feature removal. Keeps model version handling consistent and payload fields explicit.
  - Client adjustments ensure test compatibility and prompt normalization when `--oref` is at the start.


