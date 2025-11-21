# Thought Log: Nano-Banana Support (Correction)

**Timestamp:** 2025-11-21 10:10:00
**Objective:** Enable "nano-banana" (Niji) support in the *legacy* `midjourney_integration/client.py` as per user feedback.
**Status:** Reverted changes to `semant/agent_tools/midjourney/goapi_client.py`. Now targeting `midjourney_integration/client.py`.

## Analysis of `midjourney_integration/client.py`
- **Method:** `submit_imagine` (Line 137)
- **Payload:** (Lines 165-172)
  ```python
  payload: Dict[str, Any] = {
      "model": "midjourney",
      "task_type": "imagine",
      ...
  }
  ```
- **Problem:** Hardcoded `model: "midjourney"`.
- **Solution:**
  1.  Update `submit_imagine` signature to accept a `model` parameter (default: `"midjourney"`).
  2.  Or infer it from `model_version` like I planned before, but user specifically asked for an "option to choose".
  3.  If "nano-banana" is passed, map it to `"nijijourney"`.

## Implementation Plan
1.  Modify `submit_imagine` in `midjourney_integration/client.py`.
2.  Add logic:
    ```python
    # Handle nano-banana alias
    target_model = "midjourney"
    if model_version and model_version.lower() in ("nano-banana", "niji"):
         target_model = "nijijourney"
         # Ensure version is passed correctly if needed, usually just model change is enough for Niji
    ```
3.  Actually, Niji often requires `model="nijijourney"` in the GoAPI payload.

## Verification
- Review `client.py` changes.
- Ensure existing tests won't break (default behavior preserved).

