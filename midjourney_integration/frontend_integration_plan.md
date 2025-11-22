# Midjourney Frontend Integration Plan

This document outlines the strategy for creating a web-based graphical user interface (GUI) for the Midjourney image generation toolkit.

## 1. Objective

The goal is to provide a user-friendly web interface that allows users to:
1.  Submit new image generation prompts.
2.  (Future) Upload images to use as part of a prompt.
3.  View a gallery of past and in-progress jobs.
4.  Perform follow-up actions (upscale, variation, reroll) on completed jobs.
5.  See real-time progress updates.

## 2. Architecture

The integration will consist of a simple frontend communicating with a new set of API endpoints on the existing FastAPI backend.

```mermaid
graph TD
    subgraph Browser
        A[Frontend UI <br> static/midjourney.html]
    end

    subgraph "FastAPI Server (main_api.py)"
        B[Imagine Endpoint <br> /midjourney/imagine]
        C[Action Endpoint <br> /midjourney/action]
        D[Jobs Endpoint <br> /midjourney/jobs]
        E[Status Endpoint <br> /midjourney/jobs/{id}]
    end

    subgraph "Midjourney Logic (goapi_generate.py)"
        F[submit_imagine()]
        G[submit_action()]
        H[poll_task()]
    end

    subgraph "External Service"
        I[GoAPI AI]
    end

    A -- "HTTP Request" --> B
    A -- "HTTP Request" --> C
    A -- "HTTP Request" --> D
    A -- "Polling for status" --> E

    B --> F
    C --> G
    E --> H

    F -- "API Call" --> I
    G -- "API Call" --> I
    H -- "API Call" --> I
```

## 3. Implementation Steps

### Step 1: Backend - API Endpoint Creation

The existing `main_api.py` will be modified to include new routes for Midjourney functionality. This leverages the existing server and avoids creating new Python scripts.

-   **File to Modify:** `main_api.py`
-   **New Endpoints:**
    -   `POST /api/midjourney/imagine`:
        -   **Request Body:** `{"prompt": "...", "aspect_ratio": "..."}`
        -   **Action:** Calls `midjourney_integration.cli.cmd_imagine` logic to start a new job.
        -   **Response:** The initial task JSON, including the `task_id`.
    -   `POST /api/midjourney/action`:
        -   **Request Body:** `{"action": "upscale1", "origin_task_id": "..."}`
        -   **Action:** Calls `midjourney_integration.cli.cmd_action` logic.
        -   **Response:** The new task JSON, including the `task_id`.
    -   `GET /api/midjourney/jobs`:
        -   **Action:** Reads the contents of the `midjourney_integration/jobs` directory.
        -   **Response:** A list of all job metadata.
    -   `GET /api/midjourney/jobs/{task_id}`:
        -   **Action:** Reads the `metadata.json` for the specified task.
        -   **Response:** The current status and data for that task.

### Step 2: Frontend - UI Development

A new HTML file will be created in the `static` directory to house the user interface.

-   **File to Create:** `static/midjourney.html`
-   **Key Components:**
    -   **Prompt Form:** A simple form with a text area for the prompt and a submit button.
    -   **Job Gallery:** A display area where job results will be rendered. Each job will show:
        -   The generated image (or a placeholder if in progress).
        -   The task status and progress percentage.
        -   Action buttons (`U1`, `V1`, `Reroll`, etc.) upon completion.
    -   **JavaScript Logic:**
        -   On page load, fetch from `/api/midjourney/jobs` to populate the gallery.
        -   Implement a polling mechanism that periodically calls `/api/midjourney/jobs/{task_id}` for any "in-progress" tasks to update the UI in real time.
        -   Handle form submission to `POST` to `/api/midjourney/imagine`.
        -   Handle action button clicks to `POST` to `/api/midjourney/action`.
        -   Dynamically add new jobs to the gallery.

### Step 3: Integration and Refinement

-   Connect the frontend to the backend endpoints.
-   Ensure proper error handling and user feedback (e.g., showing loading states, displaying error messages).
-   Refine the UI/UX for a clean and intuitive experience. 