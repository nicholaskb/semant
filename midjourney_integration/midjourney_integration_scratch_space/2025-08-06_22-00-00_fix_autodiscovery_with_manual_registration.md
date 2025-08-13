## 2025-08-06_22-00-00_fix_autodiscovery_with_manual_registration

**Objective:** Resolve application startup failures caused by the agent auto-discovery mechanism.

**Issue:**
- After fixing the `simple_agents.py` constructor issue, new errors appeared during startup related to imports.
- `ERROR ... attempted relative import with no known parent package` in `workflow_monitor.py`.
- `ERROR ... No module named 'diary_agent'` in `example.py`.
- The root cause was the `_auto_discover_agents` function in `agent_registry.py` being too aggressive. It was attempting to import every `.py` file, including infrastructure code and examples that are not self-contained, importable agents.

**Investigation:**
- The user pointed to `scripts/demo_scientific_refinement.py` as a working example.
- Analysis of this script showed that it **disables auto-discovery** (`AgentRegistry(disable_auto_discovery=True)`) and instead **manually imports and registers** only the agents required for its specific workflow.
- This pattern is more robust and avoids the errors caused by the fragile auto-discovery.

**Fix:**
- **Adopted the manual registration pattern in the main application (`main.py`).**
1.  **Disabled Auto-Discovery:** Changed the `AgentRegistry` instantiation in `main.py` to `_agent_registry = AgentRegistry(disable_auto_discovery=True)`.
2.  **Manual Registration:** In the `startup_event` function in `main.py`, added explicit imports for all necessary agents (`PlannerAgent`, `LogoAnalysisAgent`, the `simple_agents`, etc.).
3.  Created a list of agent instances and looped through it, calling `await _agent_registry.register_agent(agent)` for each one.

**Outcome:**
- The application's agent loading mechanism is no longer dependent on the fragile auto-discovery process.
- Startup is now deterministic, loading only the specified agents.
- The import errors related to `workflow_monitor.py` and `example.py` are resolved because those files are no longer being improperly loaded by the registry.
- The application should now start without any agent-related errors.

