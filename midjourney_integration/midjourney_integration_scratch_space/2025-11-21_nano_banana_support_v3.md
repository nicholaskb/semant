# Thought Log: Nano-Banana Model Support

**Timestamp:** 2025-11-21 10:20:00
**Objective:** Implement support for the "Nano-Banana" model in the Midjourney integration.
**Correction:** User explicitly stated "Nano-Banana" is NOT Niji. It is a distinct model found at `https://goapi.ai/dashboard/nano-banana`.

## Plan
1.  **Frontend (`static/midjourney.html`)**:
    -   Add a radio button option for "Nano-Banana" in the Version/Model selector.
    -   Value should probably be `nano-banana`.

2.  **Backend (`midjourney_integration/client.py`)**:
    -   Update `submit_imagine` to accept a `model` parameter or infer it.
    -   The payload to GoAPI should look like:
        ```json
        {
            "model": "nano-banana",
            "task_type": "imagine",
            "input": { ... }
        }
        ```
    -   **Crucial:** Do *not* map this to `nijijourney`. Use `nano-banana` as the model string (assuming this is the API identifier based on the dashboard URL slug).

3.  **Task Update**:
    -   Update the existing task #2 to reflect this specific "Nano-Banana" requirement and remove mentions of Niji mapping.

## Verification
-   The UI should send `version="nano-banana"` (or similar) in the form data.
-   The backend `main_api.py` (which calls `client.py` or `cli.py`) needs to handle this.
    -   *Wait*, `main_api.py` calls `midjourney_integration.cli.cmd_imagine`.
    -   `midjourney_integration/cli.py` calls `client.submit_imagine`.
    -   I need to check `midjourney_integration/cli.py` and `main_api.py` to see how the version/model is propagated.

## File Trace
-   `static/midjourney.html` -> POST `/api/midjourney/imagine`
-   `main.py` (or `main_api.py`) -> `cmd_imagine`
-   `midjourney_integration/cli.py` -> `client.submit_imagine`
-   `midjourney_integration/client.py` -> GoAPI Payload

I will read `main_api.py` and `midjourney_integration/cli.py` to ensure the parameter plumbing is correct.

