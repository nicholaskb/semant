import inspect
import pkgutil
import importlib

import pytest

from agents.core.base_agent import BaseAgent


EXEMPT_MODULE_PREFIXES = {
    "examples.",  # demo scripts outside production agents
    "agents.diary",
}


@pytest.mark.parametrize("module_info", [m for m in pkgutil.walk_packages(["agents"], prefix="agents.")])
def test_agent_classes_inherit_baseagent(module_info):
    # Skip exempt modules
    if any(module_info.name.startswith(p) for p in EXEMPT_MODULE_PREFIXES):
        pytest.skip("example module")

    module = importlib.import_module(module_info.name)
    for name, obj in inspect.getmembers(module, inspect.isclass):
        # Heuristic: class name ends with 'Agent'
        if not name.endswith("Agent"):
            continue
        # Ignore BaseAgent itself and subclasses defined in tests
        if obj is BaseAgent:
            continue
        # Ensure subclass relationship
        assert issubclass(obj, BaseAgent), f"{obj.__module__}.{name} does not inherit from BaseAgent" 