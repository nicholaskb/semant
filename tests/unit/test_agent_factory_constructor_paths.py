import pytest

from agents.core.agent_factory import AgentFactory
from agents.core.agent_registry import AgentRegistry
from agents.core.capability_types import Capability, CapabilityType

from agents.domain.diary_agent import DiaryAgent
from agents.core.data_handler_agent import DataHandlerAgent


@pytest.mark.asyncio
async def test_agent_factory_can_register_and_create_simple_agents():
    """Non-invasive check: use AgentFactory to register and create simple agents.

    Skips any agents that require external services. Ensures initialize/cleanup paths
    are exercised without changing production code.
    """
    registry = AgentRegistry(disable_auto_discovery=True)
    factory = AgentFactory(registry=registry, knowledge_graph=None)

    await factory.initialize()

    default_caps = {Capability(CapabilityType.MESSAGE_PROCESSING, "1.0")}

    # Register representative agents with simple constructors
    await factory.register_agent_template("diary", DiaryAgent, default_capabilities=default_caps)
    await factory.register_agent_template("data_handler", DataHandlerAgent, default_capabilities=default_caps)

    # Create agents via factory
    diary = await factory.create_agent("diary")
    data = await factory.create_agent("data_handler")

    assert isinstance(diary, DiaryAgent)
    assert isinstance(data, DataHandlerAgent)

    # Cleanup to avoid teardown warnings
    await factory.cleanup()
    # Prefer full shutdown to avoid async __del__ warnings
    try:
        await registry.shutdown()
    except Exception:
        await registry.cleanup()


