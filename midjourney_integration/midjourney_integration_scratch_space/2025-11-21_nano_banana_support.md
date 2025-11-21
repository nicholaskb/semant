# Thought Log: Nano-Banana Support and GoAPI Refactor

**Timestamp:** 2025-11-21 10:00:00
**Objective:** Enable "nano-banana" model option for agents via GoAPI.
**Context:** User requested "nano-banana" option using the same API as Midjourney integration. User also asked if we should "fix the code first".

## Analysis of Current State
1.  **Duplicate Clients:**
    - `midjourney_integration/client.py`: Uses `MidjourneyClient`. Hardcodes `model="midjourney"`.
    - `semant/agent_tools/midjourney/goapi_client.py`: Uses `GoAPIClient`. Hardcodes `model="midjourney"`. Strictly validates `model_version` to only {"v6", "v7"}.

2.  **The "Fix"**:
    - To support a new model (e.g., Niji, which "nano-banana" likely refers to), we must break the hardcoding of `model` in the payload.
    - We need to relax or update validation logic in `GoAPIClient` to accept the new model identifier.
    - Ideally, we should consolidate usage or at least ensure `GoAPIClient` (the agent tool) is flexible enough.

## Proposed Changes
1.  **Refactor `GoAPIClient`**:
    - Add `model` parameter to `imagine` method (defaulting to "midjourney").
    - Or derive `model` from `model_version` (e.g., if version starts with "niji", set model="nijijourney").
    - Update `_validate_model_version` to allow "niji" (and "nano-banana" as alias).
2.  **TaskMaster**:
    - Create a task for "Refactor GoAPI Client for Multi-Model Support".
    - Subtask: Implement "nano-banana" alias mapping.

## Hypothesis
"Nano-banana" is a playful alias for "Niji" (Nijijourney). I will implement it as such, mapping `nano-banana` -> `nijijourney` model in GoAPI payload.

## Verification Plan
1.  Unit test `GoAPIClient` with `model_version="nano-banana"`.
2.  Verify payload contains `"model": "nijijourney"` (or whatever the mapping is).

