import asyncio
import time
from kg.models.graph_manager import KnowledgeGraphManager
from agents.core.agent_integrator import AgentIntegrator
from agents.core.sensor_agent import SensorAgent
from agents.core.data_processor_agent import DataProcessorAgent
from agents.core.base_agent import AgentMessage

async def main():
    # Initialize the knowledge graph
    kg_manager = KnowledgeGraphManager()
    integrator = AgentIntegrator(kg_manager)

    # Instantiate agents
    sensor_agent = SensorAgent("sensor_agent")
    data_processor_agent = DataProcessorAgent("data_processor_agent")

    # Register agents
    await integrator.register_agent(sensor_agent)
    await integrator.register_agent(data_processor_agent)

    # Send a message to SensorAgent
    sensor_message = AgentMessage(
        sender="system",
        recipient="sensor_agent",
        content={"sensor_id": "http://example.org/core#Sensor1", "reading": 42.0, "predicate": "http://example.org/core#latestReading"},
        timestamp=time.time(),
        message_type="sensor_update"
    )
    sensor_response = await integrator.route_message(sensor_message)
    print(f"SensorAgent response: {sensor_response.content}")

    # Send a message to DataProcessorAgent
    data_message = AgentMessage(
        sender="system",
        recipient="data_processor_agent",
        content={"data": "Sample processed data", "subject": "http://example.org/core#Data1", "predicate": "http://example.org/core#hasValue", "object": "ProcessedValue"},
        timestamp=time.time(),
        message_type="data_update"
    )
    data_response = await integrator.route_message(data_message)
    print(f"DataProcessorAgent response: {data_response.content}")

    # Show agent statuses
    statuses = await integrator.get_all_agent_statuses()
    print("\nAgent statuses:")
    for agent_id, status in statuses.items():
        print(f"- {agent_id}: {status}")

    # Query the knowledge graph for triples
    print("\nKnowledge Graph Triples:")
    for s, p, o in kg_manager.graph:
        print(f"  {s} {p} {o}")

if __name__ == "__main__":
    asyncio.run(main()) 