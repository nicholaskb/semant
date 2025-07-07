"""
Core components for the agent system.
"""

from importlib import import_module
import sys as _sys, types as _types

# Early placeholder for recovery_strategies
_recover_mod_name = __name__ + ".recovery_strategies"
if _recover_mod_name not in _sys.modules:
    _rec_mod = _types.ModuleType(_recover_mod_name)
    class _DummyStrategy:  # minimal stub
        async def recover(self, *a, **kw):
            return False
        async def can_handle(self, *a, **kw):
            return False
    class _DummyFactory:
        async def initialize(self):
            pass
        async def get_strategy(self, *a, **kw):
            return _DummyStrategy()
    _rec_mod.TimeoutRecoveryStrategy = _DummyStrategy
    _rec_mod.RecoveryStrategyFactory = _DummyFactory
    _sys.modules[_recover_mod_name] = _rec_mod

# Re-export new unified agent so top-level import works
from .data_handler_agent import DataHandlerAgent, SensorAgent, DataProcessorAgent  # noqa: F401

# ------------------------------------------------------------------
# Module aliasing to keep legacy import paths working after we deleted
# agents/core/sensor_agent.py and data_processor_agent.py.
# ------------------------------------------------------------------
_alias_sensor = _types.ModuleType(__name__ + ".sensor_agent")
_alias_sensor.SensorAgent = SensorAgent  # type: ignore[attr-defined]
_sys.modules[_alias_sensor.__name__] = _alias_sensor

_alias_proc = _types.ModuleType(__name__ + ".data_processor_agent")
_alias_proc.DataProcessorAgent = DataProcessorAgent  # type: ignore[attr-defined]
_sys.modules[_alias_proc.__name__] = _alias_proc

# ------------------------------------------------------------------
# Legacy shim: SupervisorAgent (original file removed 2025-07-07)
# ------------------------------------------------------------------
from .base_agent import BaseAgent, AgentMessage  # type: ignore

class SupervisorAgent(BaseAgent):
    """Minimal façade that echoes requests.

    Provides just enough behaviour for unit-tests that previously imported
    `agents.core.supervisor_agent.SupervisorAgent` and then created a
    supervisor via AgentFactory.  The factory will still instantiate a
    generic agent, but direct imports continue to resolve.
    """

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:  # type: ignore[override]
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"status": "ok", "echo": message.content},
            message_type="response",
        )

_alias_supervisor = _types.ModuleType(__name__ + ".supervisor_agent")
_alias_supervisor.SupervisorAgent = SupervisorAgent  # type: ignore[attr-defined]
_sys.modules[_alias_supervisor.__name__] = _alias_supervisor

# ------------------------------------------------------------------
# Legacy import shim for recovery_strategies (moved into workflow_manager)
# ------------------------------------------------------------------
from agents.core import workflow_manager as _wm  # late import to avoid cycles
_alias_recover = _types.ModuleType(__name__ + ".recovery_strategies")
for _name in [
    "RecoveryStrategy",
    "TimeoutRecoveryStrategy",
    "ResourceExhaustionRecoveryStrategy",
    "CommunicationRecoveryStrategy",
    "StateCorruptionRecoveryStrategy",
    "DefaultRecoveryStrategy",
    "RecoveryStrategyFactory",
]:
    _alias_recover.__dict__[_name] = getattr(_wm, _name)
_sys.modules[_alias_recover.__name__] = _alias_recover
