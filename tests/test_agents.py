import pytest
from agents.core.sensor_agent import SensorAgent
from agents.core.data_processor_agent import DataProcessorAgent
from agents.core.base_agent import AgentMessage

@pytest.mark.asyncio
async def test_sensor_agent_process_message():
    agent = SensorAgent()
    await agent.initialize()
    message = AgentMessage(
        sender="test_sender",
        recipient="sensor_agent",
        content={"sensor_id": "sensor1", "reading": 42},
        timestamp=1234567890,
        message_type="sensor_data"
    )
    response = await agent.process_message(message)
    assert response.content["status"] == "Sensor data updated successfully."

@pytest.mark.asyncio
async def test_data_processor_agent_process_message():
    agent = DataProcessorAgent()
    await agent.initialize()
    message = AgentMessage(
        sender="test_sender",
        recipient="data_processor_agent",
        content={"data": "test_data"},
        timestamp=1234567890,
        message_type="data_processor_data"
    )
    response = await agent.process_message(message)
    assert response.content["status"] == "Data processed successfully." 