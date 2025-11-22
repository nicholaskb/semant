2025-08-12 00:00:00 - Midjourney README + Describe/Blend Audit (Implemented vs. Claims)

Objective
- Document the exact changes implemented today and reconcile scratch notes with code so future agents can trust the docs.

Scope (files touched today)
- static/midjourney.html
- main.py
- midjourney_integration/README.md

Implemented Today (True in code)
- Describe: UI posts image_url to /api/midjourney/describe-url with file-upload fallback to /api/midjourney/describe. Suggestions render; “Use” opens Advanced Settings. Backend polls and returns prompts.
- Blend: UI prefers URL-based submission (image_urls JSON) with fallback to file-upload. Backend /api/midjourney/blend now accepts image_urls or image_files and verifies public accessibility.
- README updated: Adds Describe/Blend behavior, endpoints, troubleshooting.

Scratch Notes: Truth Status
- 2025-08-05_cref-v7-fix.md → Partially True: V7 does not support --cref; UI guards + README reflects limitation.
- 2025-08-06_10-00-00_fix_refine_prompt_button.md → Outdated: Current UI uses non-streaming POST to /api/midjourney/refine-prompt and shows transcript from JSON, not SSE.
- 2025-08-05_20-45-00_streaming_implemented.md → Outdated: No EventSource stream in current UI; backend has non-streaming refine endpoints, plus optional workflow endpoint returning transcript array.
- 2025-08-06_22-35-00_sref_url_issue.md, 2025-08-06_23-00-00_v7_image_url_failures.md → Still Relevant context and mitigations (public GCS, version awareness). Backend now verifies URL reachability.
- Agent registry and planner-related notes (multiple) → True: AgentRegistry.get_all_agents exists; optional planner endpoint present.

Open Risks / Next Actions
- If streaming refine UX is desired, add SSE or chunked streaming and wire UI accordingly. Mark current refine behavior as non-streaming.
- Add unit tests around /api/midjourney/blend URL vs file paths and describe-url happy path.

Protocol I (the agent) will follow from now on
1) Every code change must have a same-day scratch entry with:
   - Timestamp, Objective, Files touched, Endpoints affected, Constraints/assumptions, Test/verification steps, and a Truth stamp (Implemented vs Proposed).
2) Any claim in scratch must link to code paths (file + function) and, when relevant, line spans.
3) After changing behavior, immediately update README and add a one-line “Changelog” at the bottom referencing the scratch entry filename.
4) For historical scratch files that are no longer correct, append “Status: Outdated (superseded by <filename>)” at the top—never delete.
5) For Midjourney features, include version-awareness notes (e.g., --cref unsupported on v7) and client-side validation.

Verification (manual today)
- Describe: tested path via UI with uploaded image → prompts rendered.
- Blend: tested URL-first submission and fallback locally; backend received image_urls and returned task_id.

References
- Code: static/midjourney.html, main.py (/api/midjourney/describe, /describe-url, /blend), midjourney_integration/client.py (submit_describe, submit_blend)

