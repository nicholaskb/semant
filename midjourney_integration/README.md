# Midjourney UI & Integration

This document outlines the features and usage of the comprehensive Midjourney web interface and its backend API. The UI provides a powerful tool for generating and managing images, giving users direct access to a wide range of Midjourney parameters.

## Core Features

*   **Advanced Prompting:** A full suite of controls for Midjourney parameters, including aspect ratio, versions, stylize, chaos, weird, and more.
*   **Image Prompts & Weighting:** Upload images to use as part of your prompt, with per-image weighting using the correct `URL::weight` syntax.
*   **Character & Style Referencing:** Upload images to easily generate URLs for use with `--cref` and `--sref`, with a UI designed to assign them correctly.
*   **Historical Job Gallery:** View all your past and in-progress jobs in a gallery that loads on startup and refreshes automatically.
*   **Post-Processing Actions:** Perform follow-up actions on completed jobs, such as **Upscale**, **Reroll**, and **Variation**.
*   **Grid Splitting:** Automatically split a completed 2x2 image grid into four individual quadrant images, which are saved to GCS and can be used in future prompts.
*   **Command-Line Interface (CLI):** A `cli.py` script provides direct command-line access to submit `imagine` and `action` commands, and list local jobs.
*   **Describe (image → prompts):** Submit an image to receive suggested prompts. The UI button posts to backend endpoints and renders suggestions; clicking **Use** fills the prompt and opens Advanced Settings so you can tweak parameters before pressing **Imagine**.
*   **Blend (2–5 images):** Merge 2–5 images by dimension (portrait/square/landscape). The UI prefers URL-based submission to the backend (no browser-side GCS fetch), with an automatic fallback to file-upload.

## Known Issues & Limitations

*   **`--cref` with V7 Models:** Known limitation; `--cref` is not supported by V7. Use V6 or omit `--cref` when `--v 7` is selected.
*   **GCS URL accessibility:** Ensure uploaded images are publicly readable. The backend verifies accessibility before task submission, but private buckets will still fail.

## Quick Start

1.  **Set Environment Variables:**
    Ensure you have a `.env` file in the project root with the following keys:
    ```
    MIDJOURNEY_API_TOKEN=your-goapi-token-here
    GCS_BUCKET_NAME=your-gcs-bucket-name
    GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/gcs_credentials.json
    ```

2.  **Install Dependencies:**
    Make sure your virtual environment is active and all requirements are installed.
    ```bash
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Run the Server:**
    ```bash
    python main.py
    ```

4.  **Access the UI:**
    Open your browser and navigate to `http://localhost:8000/static/midjourney.html`.

## Using the UI: A Full Workflow

The UI is designed to be a powerful and flexible tool. Here is a typical workflow:

### 1. Uploading Images (Optional)

The UI has a single **"Upload Image(s)"** button that handles all image uploads. Once an image is uploaded to GCS, a thumbnail preview appears. Each thumbnail has its own set of controls.

*   **For Image Prompts:**
    1.  Click "Upload Image(s)" and select one or more images.
    2.  For each thumbnail that appears, a **weight input** is shown beneath it. You can adjust this value to control its influence in a multi-prompt (e.g., `image_url::2`).
    3.  These images will be automatically added to the start of your prompt when you click "Imagine".

*   **For Character or Style References:**
    1.  Click "Upload Image(s)" and select an image.
    2.  In the thumbnail preview, click the **"Use as --cref"** or **"Use as --sref"** button.
    3.  This will automatically populate the corresponding field in the "Advanced Settings" panel and add a visual badge to the thumbnail.

### 2. Crafting Your Prompt

*   **Text Prompt:** Type your main text prompt into the large text area.
*   **Advanced Settings:** Click the "Advanced Settings" button to reveal a comprehensive panel of Midjourney parameters. Here you can control:
    *   `--cref` & `--sref` (populated from uploads)
    *   `--cw` & `--sw` (weights for references)
    *   `--iw` (global image weight for single image prompts)
    *   `--no` (negative prompts)
    *   Aspect Ratio (including custom)
    *   Version, Seed, Stylize, Chaos, Weird, and more.

### 3. Submitting the Job

Click the **"Imagine"** button. The UI will intelligently construct the final prompt string, combining your weighted image prompts, your text prompt, and all selected parameters, and send it to the backend.

### 4. Viewing and Managing Jobs

*   Your new job will immediately appear at the top of the **Historical Gallery**.
*   The gallery will automatically refresh every 15 seconds, updating the progress of any running jobs.
*   Once a job is complete, its final image will be displayed.
*   You can then perform follow-up actions:
    *   Click **"Split Grid"** to process the image into four quadrants. The card will update to show the four new images, each with its own `--cref`/`--sref` buttons.
    *   Click **"U1"**, **"V2"**, **"Reroll"**, etc. to start a new job based on the result. These buttons are automatically disabled for jobs older than 24 hours but can be re-enabled with the "Force Enable" button.

## API Endpoints

The backend provides several key endpoints to support the UI:

*   `POST /api/midjourney/imagine`: Submits a new task.
*   `POST /api/upload-image`: Uploads a single image to GCS and returns its public URL.
*   `GET /api/midjourney/jobs`: Returns a list of all historical jobs.
*   `GET /api/midjourney/jobs/{task_id}`: Returns the metadata for a single job.
*   `POST /api/midjourney/split-grid/{task_id}`: Triggers the grid-splitting process for a completed job.
*   `POST /api/midjourney/action`: Performs a follow-up action (upscale, etc.) on a job.
*   `POST /api/midjourney/describe`: Describe via file upload (`image_file` form field). Returns `{ "prompts": [ ... ] }`.
*   `POST /api/midjourney/describe-url`: Describe via URL (`image_url` form field). Returns `{ "prompts": [ ... ] }`.
*   `POST /api/midjourney/blend`: Blend via either `image_urls` (JSON array or comma-separated string) or `image_files` (2–5 uploads) plus `dimension`.

## Troubleshooting

*   **Failed to fetch / CORS errors:** The UI now prefers URL-based submissions so the server (not the browser) verifies and submits GCS URLs. If you still see failures, confirm bucket objects are public and that `GCS_BUCKET_NAME` and `GOOGLE_APPLICATION_CREDENTIALS` are set.
*   **Authentication:** Ensure `MIDJOURNEY_API_TOKEN` is present and valid.

## Command-Line Interface (CLI)

For users who prefer the command line, `midjourney_integration/cli.py` offers direct access to core functions.

*   **`python -m midjourney_integration.cli imagine "your prompt"`**: Submit a new prompt.
    *   `--image-path`: Attach a local image to the prompt.
    *   `--aspect_ratio`, `--mode`, `--nowait`
*   **`python -m midjourney_integration.cli action <action> <task_id>`**: Perform an action (e.g., `upscale1`, `reroll`) on a completed job.
*   **`python -m midjourney_integration.cli list`**: List all locally stored job metadata.
