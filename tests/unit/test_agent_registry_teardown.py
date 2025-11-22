import asyncio

from agents.core.agent_registry import AgentRegistry


def test_agent_registry_del_without_running_loop(monkeypatch):
    """__del__ should not raise when no event loop is running."""
    reg = AgentRegistry(disable_auto_discovery=True)
    # Simulate initialized registry at GC time
    reg._is_initialized = True  # type: ignore[attr-defined]

    def raise_no_loop():
        raise RuntimeError("no running event loop")

    monkeypatch.setattr(asyncio, "get_running_loop", raise_no_loop)

    # Should not raise
    reg.__del__()


def test_agent_registry_del_with_loop_schedules_cleanup(monkeypatch):
    """__del__ should schedule cleanup when a loop is available and open."""
    reg = AgentRegistry(disable_auto_discovery=True)
    reg._is_initialized = True  # type: ignore[attr-defined]

    called = {"created": False}

    class DummyLoop:
        def is_closed(self):
            return False

        def create_task(self, coro):  # noqa: D401
            called["created"] = True
            # Do not actually run the coroutine in this unit test
            class DummyTask:
                pass

            return DummyTask()

    monkeypatch.setattr(asyncio, "get_running_loop", lambda: DummyLoop())

    reg.__del__()
    assert called["created"] is True


