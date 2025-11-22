import asyncio
from agents.core.agent_integrator import AgentIntegrator
from agents.core.research_agent import ResearchAgent
from agents.core.data_processor_agent import DataProcessorAgent
from agents.core.sensor_agent import SensorAgent
from agents.core.feature_z_agent import FeatureZAgent
from kg.models.graph_manager import KnowledgeGraphManager
from agents.core.base_agent import AgentMessage
import time

async def run_workflow():
    # Initialize knowledge graph and integrator
    kg_manager = KnowledgeGraphManager()
    integrator = AgentIntegrator(kg_manager)

    # Create agents
    research_agent = ResearchAgent("research_agent")
    data_processor_agent = DataProcessorAgent("data_processor_agent")
    sensor_agent = SensorAgent("sensor_agent")
    feature_z_agent = FeatureZAgent("feature_z_agent")

    # Register agents
    await integrator.register_agent(research_agent)
    await integrator.register_agent(data_processor_agent)
    await integrator.register_agent(sensor_agent)
    await integrator.register_agent(feature_z_agent)

    print("--- Multi-Agent Workflow Start ---")

    # 1. SensorAgent receives sensor data
    sensor_message = AgentMessage(
        sender="system",
        recipient="sensor_agent",
        content={"sensor_id": "SensorX", "reading": 42.0},
        timestamp=time.time(),
        message_type="sensor_update"
    )
    sensor_response = await integrator.route_message(sensor_message)
    print(f"SensorAgent response: {sensor_response.content}")

    # 2. DataProcessorAgent processes data
    data_message = AgentMessage(
        sender="sensor_agent",
        recipient="data_processor_agent",
        content={"data": {"sensor_id": "SensorX", "reading": 42.0}},
        timestamp=time.time(),
        message_type="data_processing"
    )
    data_response = await integrator.route_message(data_message)
    print(f"DataProcessorAgent response: {data_response.content}")

    # 3. ResearchAgent investigates a topic based on processed data
    research_message = AgentMessage(
        sender="data_processor_agent",
        recipient="research_agent",
        content={"topic": "SensorX anomaly", "depth": 2, "require_confidence": True},
        timestamp=time.time(),
        message_type="research_request"
    )
    research_response = await integrator.route_message(research_message)
    print(f"ResearchAgent response: {research_response.content}")

    # 4. FeatureZAgent is triggered with a feature-specific message
    feature_z_message = AgentMessage(
        sender="research_agent",
        recipient="feature_z_agent",
        content={"feature_data": {"action": "trigger", "reason": "anomaly detected"}},
        timestamp=time.time(),
        message_type="feature_z_request"
    )
    feature_z_response = await integrator.route_message(feature_z_message)
    print(f"FeatureZAgent response: {feature_z_response.content}")

    print("--- Multi-Agent Workflow Complete ---")

if __name__ == "__main__":
    asyncio.run(run_workflow()) 