Date: 2025-08-08 15:55 UTC
Objective: Scaffold Kontext integration mirroring midjourney_integration

Actions:
- Created package with client, CLI, README, and scratch entry.
- Client uses Bearer KONTEXT_API_TOKEN, retry/backoff for 429/5xx.
- CLI supports generate/action, optional GCS image upload.

Next:
- Wire server routes if needed (mirror midjourney endpoints) and add tests.



