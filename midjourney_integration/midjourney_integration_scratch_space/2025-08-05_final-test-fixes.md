### Final Test Suite Fixes - 2025-08-05_07-57-23

**Issue:** The test suite was failing with a 'RuntimeError: asyncio.run() cannot be called from a running event loop' and an 'AttributeError: 'WorkflowMonitor' object has no attribute 'initialize''.

**Root Cause:**
- The 'asyncio.run()' error was caused by calling 'asyncio.run()' in the global scope of 'main.py' while 'uvicorn' was already running its own event loop.
- The 'AttributeError' was caused by the 'WorkflowMonitor' class missing an 'initialize' method.

**Fix:**
1.  **Refactored 'main.py' to use 'lifespan' context manager**:
    -   Removed the problematic 'asyncio.run()' call from the global scope.
    -   Replaced the deprecated '@app.on_event("startup")' function with a 'lifespan' async context manager.
    -   Moved all application startup logic into the 'lifespan' manager.
2.  **Added 'initialize' and 'shutdown' methods to 'WorkflowMonitor'**:
    -   Added the missing methods to 'agents/core/workflow_monitor.py' to allow the 'WorkflowManager' to initialize it correctly.
3.  **Removed premature initialization check from 'WorkflowManager'**:
    -   Removed the check for an initialized 'AgentRegistry' from the '__init__' method of the 'WorkflowManager' to allow for instantiation at the module level.

**Outcome:** All tests are now passing, and the application startup logic is now correctly handled by the 'lifespan' context manager.
