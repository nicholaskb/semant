
Midjourney GoAPI Integration & TaskMaster Workflow
This README provides a high‑level overview and step‑by‑step guidance for integrating Midjourney’s GoAPI into the Semant framework while leveraging TaskMaster for planning and execution. The objective is to build a comprehensive suite of agent‑callable tools for every GoAPI feature (imagine, action, describe, blend, inpaint, outpaint, pan, zoom, seed, get_task, cancel_tasks) and to record all inputs and outputs in the knowledge graph. The process described here emphasises careful project management, incremental development, and continuous documentation.

Overview
The integration is designed for a swarm of agents working collaboratively. Agents will:

Create new modules under a dedicated semant/agent_tools/midjourney namespace without altering the existing midjourney_integration code. This prevents duplication and preserves existing UI and CLI functionality.

Implement a GoAPIClient to abstract HTTP requests to the unified GoAPI endpoints, supporting all Midjourney task types and handling authentication.

Build a KGLogger to capture every tool invocation as RDF triples, ensuring complete traceability in the knowledge graph.

Provide individual wrapper classes for each GoAPI feature, along with a registry exposing metadata (name, description, input and output schemas, and run method). This enables other agents to discover and call tools without reading the underlying code.

Orchestrate complex workflows such as “Generate Themed Portraits” that upload multiple face images, choose the correct reference mode (--cref or --oref), submit imagination tasks, describe results, and reroll or upscale as needed.

Agents will also use TaskMaster to plan and manage the work, breaking tasks into subtasks, tracking progress, and updating the README as the project evolves.

Agent Tools & Demos
- See `docs/midjourney_agent_tools.md` for the new agent toolset, live demos, KG queries, and GCS mirroring.
- Quick live imagine:
```bash
export MIDJOURNEY_API_TOKEN='YOUR_TOKEN'
python -m examples.midjourney_agent_tools_live_demo --prompt "a minimalist watercolor fox, soft palette" --version v7
```
- Quick live action (upscale2):
```bash
python -m examples.midjourney_agent_tools_action_live --task-id <task_id> --action upscale2
```

UI: Refine with AI
- The “Refine with AI” button in `static/midjourney.html` is wired to:
  - First call: `/api/midjourney/refine-prompt-workflow` (returns transcript when available)
  - Fallback: `/api/midjourney/refine-prompt`
- On success, the prompt textbox is updated with `refined_prompt` and the transcript panel is shown.

Initial Assessment & Environment Setup
Review existing code and documentation. Familiarise yourself with the current Midjourney integration in midjourney_integration/ and the TaskMaster rules in .cursor/rules/taskmaster/. Note any existing API endpoints, UI features, and limitations such as --cref being valid only for V6 models
GitHub
. Understand the core TaskMaster loop: list → next → show → expand → implement → update‑subtask → set‑status
GitHub
.

Initialise TaskMaster. If .taskmaster/config.json or tasks.json does not exist, run initialize_project (task-master init) to generate them【410879868530904†L2-L7】. Operate within the default master tag unless there is a clear need for separate task contexts such as feature branches or experimental work
GitHub
.

Configure AI models. Use the models tool to set up the AI provider(s) for planning, research, and fallback roles. Store sensitive API keys in .env or .cursor/mcp.json according to TaskMaster’s configuration guidelines【410879868530904†L0-L8】.

Designing the Tool Framework
GoAPI Client. Implement a GoAPIClient in semant/agent_tools/midjourney/goapi_client.py to encapsulate all HTTP interactions with the GoAPI. The client should support the imagine, action, describe, blend, inpaint, outpaint, pan, zoom, seed, get_task, and cancel_tasks endpoints. Include helper methods like upload_image for uploading files.

Knowledge Graph Logging. Create a KGLogger in semant/agent_tools/midjourney/kg_logging.py. Each tool call should produce a mj:ToolCall node referencing a mj:Task (if applicable) and record each parameter as a mj:input literal and each result as a mj:output. Use schema:ImageObject nodes for any returned image URLs. Adhere to existing RDF namespace conventions.

Tool Wrappers. Write a wrapper class for each GoAPI feature. Each wrapper should accept structured inputs, invoke the correct GoAPI endpoint via GoAPIClient, log the call through KGLogger, and return the raw response. Implement version‑specific behaviour: --cref and --cw only for V6, --oref and --ow only for V7
GitHub
.

Tool Metadata Registry. Expose a registry in semant/agent_tools/midjourney/__init__.py mapping each tool to a ToolMeta entry (name, description, input schema, output schema, and run method). Include a higher‑level workflow like GenerateThemedPortraits for uploading images, generating portraits, verifying prompts, and rerunning actions.

TaskMaster Planning & Execution
Create parent tasks. Use add_task to set up high‑level tasks such as implementing the client and logger, writing tool wrappers, creating the registry, writing tests, integrating with the planner, and documenting the work. Each task should clearly describe its goal, dependencies, and acceptance criteria.

Analyse and expand. Run analyze_project_complexity to determine which tasks are complex and then call expand_task with --force and --research to break them down into subtasks. Example subtasks include designing class interfaces, writing HTTP handling, creating RDF triples, adding tests, and updating the README.

Maintain dependencies and status. Use add_dependency to express prerequisites between tasks (e.g., tool classes depend on the client). Mark tasks as done with set_task_status when they are complete. Use update_task or update when changes arise instead of editing task files directly.

Document iteratively. After each milestone, call generate to regenerate individual task markdown files and, if necessary, sync-readme to update this README. Avoid overwriting user-written sections or conflicting with other ongoing work.

Record research findings. Use the research tool to gather up‑to‑date information (e.g., on Midjourney features) and save the results to tasks or subtasks via update_subtask. This preserves findings for the entire agent team.

Review & Quality Control
Unit testing. Create tests that exercise typical workflows (imagine → action) and ensure API calls and knowledge graph logging behave correctly. Write tasks for the tests and mark them done once they pass.

Peer review. Assign a Critic agent to review each component for code quality, error handling, and adherence to version‑specific rules. Capture feedback using update_subtask and address issues before marking tasks complete.

Approval. A Judge agent must verify that a task meets its criteria (tests pass, documentation updated, dependencies satisfied) before it is considered done.

Integration & Documentation
Planner integration. Modify the Planner agent to call these tools via the registry. Implement a GenerateThemedPortraits plan that uploads face images, generates themed portraits, verifies prompts through describe, rerolls if necessary, upscales results, and logs everything to the knowledge graph. Represent each step as a subtask.

Create detailed docs. Draft a new file (e.g., docs/midjourney_agent_tools.md) explaining how to use each tool, the meaning of each parameter, and examples. Highlight differences between these new agent tools and the existing UI/CLI code.

Iterate documentation. After each milestone, update the documentation and regenerate task files. Encourage use of TaskMaster tags if multiple features are being developed concurrently
GitHub
.

Final Review & Continuous Improvement
Validate dependencies. Use validate_dependencies to ensure there are no circular or missing dependencies and run fix_dependencies if issues are found.

Swarm review. At the end of the implementation, have multiple agents review the code and documentation. Update tasks accordingly with update_task or update.

Future roadmap. Follow this same process when adding new Midjourney or GoAPI features: define tasks, analyse complexity, expand tasks, implement and test, log all actions, update documentation, and review. Capture future enhancements and ideas in TaskMaster to maintain a forward‑looking roadmap.

By following the guidelines in this README, a team of agents can methodically implement a robust Midjourney GoAPI integration within the Semant framework. TaskMaster ensures that work is planned, tracked, and documented, while the knowledge graph provides an auditable history of all tool interactions. The combination empowers agents to produce high‑quality themed images, iterate on prompts, and maintain comprehensive project documentation.

---

## Changelog

### 2025-10-25: Fixed --cref V6 Compatibility Issue
- **Problem**: Users received error "Invalid parameter `--cref` is not compatible with `--version 7`" when using character reference
- **Root Cause**: System wasn't detecting `--cref` usage and was defaulting to V7
- **Solution**: 
  - Added extraction of `--cref` and `--cw` parameters from prompts in `main.py`
  - Auto-detect and set `model_version="v6"` when these parameters are present
  - Pass `cref_url` and `cref_weight` to the client via payload fields
  - Updated `client.py` to handle V6 parameters properly
- **Files Modified**: `main.py`, `midjourney_integration/client.py`
- **Verification**: Test with `--cref URL` in prompt - should now auto-set V6 and work correctly

### 2025-11-14: Stabilized Qdrant Similarity Index IDs
- **Problem**: Image embeddings stored in Qdrant could not be retrieved reliably after a restart because point IDs relied on Python's salted `hash()` implementation.
- **Root Cause**: `ImageEmbeddingService` converted `image_uri` values to numeric IDs via `hash(image_uri) % (2**63)`, producing different IDs per process and risking silent duplicates.
- **Solution**:
  - Added deterministic SHA-256 based point IDs with legacy fallback logic.
  - Included `point_id_version` in Qdrant payloads for observability.
  - Added regression tests covering the new helper functions.
- **Files Modified**: `kg/services/image_embedding_service.py`, `tests/test_qdrant_point_ids.py`, `RISK_ANALYSIS_QDRANT_DEMO.md`
- **Verification**: Unit tests for the helper functions (`pytest tests/test_qdrant_point_ids.py`) and manual ingestion/search flows now work across service restarts.

### 2025-11-14: Restored Kids Monsters GCS Download Fix
- **Problem**: Local operators no longer had the helper script that automates downloading `input_kids_monster/` and `generated_images/` assets from the GCS bucket, forcing manual `gsutil` usage for each drop.
- **Root Cause**: `scripts/tools/download_and_batch.py` had been removed, so there was no checked-in workflow to batch images for Apple Photos uploads.
- **Fix**:
  - Re-created the script with argument parsing, extension filtering, folder batching, and type-based organization exactly as used previously.
  - Ensured the CLI validates mutually exclusive flags, surfaces helpful logging, and cleans staging folders after batching.
- **Files Modified**: `scripts/tools/download_and_batch.py`
- **Verification**: Logic review only (GCS credentials unavailable in sandbox); run `python3 scripts/tools/download_and_batch.py --help` locally to confirm importability.

### 2025-11-21: Implemented Nano-Banana Model Support
- **Problem**: Users needed access to the new "Nano-Banana" model, which is distinct from Niji.
- **Solution**:
  - Added "Nano-Banana" option to the UI version selector.
  - Updated `midjourney_integration/client.py` to explicitly handle `model_version="nano-banana"` and set the correct GoAPI payload.
  - Updated `midjourney_integration/cli.py` to support `--version nano-banana`.
- **Files Modified**: `static/midjourney.html`, `midjourney_integration/client.py`, `midjourney_integration/cli.py`
- **Verification**: Verified via code review and manual testing of the new option in UI and CLI.
