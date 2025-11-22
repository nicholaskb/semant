
## 2025-08-06_10-00-00_fix_refine_prompt_button

**Objective:** Fix the "Refine with AI" button in `static/midjourney.html`.

**Issue:**
- The button was making a `GET` request to a non-existent endpoint (`/api/midjourney/refine-prompt-stream`) using `EventSource`.
- This caused a 404 Not Found error.
- An `Uncaught SyntaxError: "undefined" is not valid JSON` was also occurring in the `EventSource` error handler because `event.data` was undefined on error.
- The UI was not displaying streaming agent communications, only a static "Initializing workflow..." message.

**Investigation:**
1.  **Analyzed Frontend (`static/midjourney.html`):**
    - Confirmed the `refineBtn` click handler on line 448 was using `new EventSource()` which makes a `GET` request.
    - Identified the target URL was incorrect.
    - Confirmed the `JSON.parse(event.data)` call in the `error` event listener was unsafe.

2.  **Analyzed Backend (`main.py`):**
    - Found a `POST` endpoint `/api/midjourney/refine-prompt` on line 506 designed for this purpose.
    - This endpoint correctly uses `StreamingResponse` with `text/event-stream` to send agent communications.

**Fix:**
1.  **Modified `static/midjourney.html`:**
    - Replaced the `EventSource` implementation with a `fetch` call using the `POST` method.
    - Pointed the `fetch` request to the correct endpoint: `/api/midjourney/refine-prompt`.
    - Passed the `prompt` and `image_urls` in the JSON body of the request.
    - Implemented a manual stream reader using `response.body.getReader()` and `TextDecoder` to process the `text/event-stream` response.
    - Added logic to parse the `data:`, `event: final_prompt`, and `event: error` lines from the stream.
    - This allows the UI to receive and display the messages from the agent workflow as they arrive.
    - Corrected the error handling to safely parse potential error messages from the stream.

**Outcome:**
- The "Refine with AI" button now correctly calls the backend.
- The UI should now display the streaming log of agent communications.
- The JSON parsing error is resolved.

