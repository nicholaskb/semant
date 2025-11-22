import asyncio
import inspect
import importlib
import pkgutil
import types
import traceback

import pytest

from agents.core.base_agent import BaseAgent


def iter_agent_classes():
    """Yield (module_name, class_obj) for all subclasses of BaseAgent under agents.*

    We only consider classes whose required constructor params are limited to
    `agent_id` so we can instantiate them safely without external deps.
    """
    packages = ["agents.domain", "agents.core"]
    for pkg_name in packages:
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception:
            continue

        if not hasattr(pkg, "__path__"):
            # Not a package (module only)
            for name, obj in inspect.getmembers(pkg, inspect.isclass):
                if issubclass(obj, BaseAgent) and obj is not BaseAgent:
                    yield pkg_name, obj
            continue

        for modinfo in pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + "."):
            modname = modinfo.name
            try:
                mod = importlib.import_module(modname)
            except Exception:
                # Skip modules that fail to import in test env
                continue
            for name, obj in inspect.getmembers(mod, inspect.isclass):
                try:
                    if issubclass(obj, BaseAgent) and obj is not BaseAgent:
                        yield modname, obj
                except Exception:
                    continue


def ctor_required_params_and_flags(cls: type):
    sig = inspect.signature(cls.__init__)
    required = set()
    has_varargs = False
    has_varkw = False
    for p in sig.parameters.values():
        if p.name == "self":
            continue
        if p.kind == p.VAR_POSITIONAL:
            has_varargs = True
        elif p.kind == p.VAR_KEYWORD:
            has_varkw = True
        elif p.default is inspect._empty and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY):
            required.add(p.name)
    return required, has_varargs, has_varkw


@pytest.mark.asyncio
async def test_agents_with_simple_constructors_can_initialize_and_cleanup():
    """Instantiate all agents whose only required arg is `agent_id`.

    This ensures constructor compatibility without modifying runtime code.
    """
    seen = 0
    skipped = 0
    errors = []

    skip_modules = {
        # Require OpenAI API key or external services
        "agents.domain.prompt_construction_agent",
        "agents.domain.critic_agent",
        "agents.domain.image_analysis_agent",
        "agents.domain.prompt_judge_agent",
        "agents.domain.logo_analysis_agent",
    }

    for modname, cls in iter_agent_classes():
        if any(modname.startswith(m) for m in skip_modules):
            skipped += 1
            continue

        req, has_varargs, has_varkw = ctor_required_params_and_flags(cls)
        # Skip variadic constructors to avoid ambiguous kwargs forwarding
        if has_varargs or has_varkw:
            skipped += 1
            continue
        # Only test simple constructors requiring only agent_id
        if req - {"agent_id"}:
            skipped += 1
            continue
        seen += 1
        agent = None
        try:
            agent = cls(agent_id=f"ctor_test_{cls.__name__}")
            # initialize and cleanup are async on BaseAgent
            if hasattr(agent, "initialize") and inspect.iscoroutinefunction(agent.initialize):
                await agent.initialize()
            if hasattr(agent, "cleanup") and inspect.iscoroutinefunction(agent.cleanup):
                await agent.cleanup()
        except Exception as exc:
            tb = traceback.format_exc(limit=2)
            errors.append((modname, cls.__name__, str(exc), tb))

    if errors:
        details = "\n".join(
            f"{m}.{c}: {e}\n{tb}" for m, c, e, tb in errors
        )
        pytest.fail(f"Constructor compatibility failures (simple agent_id):\n{details}")

    # Sanity: we should have covered at least one class
    assert seen >= 1


