import pytest
import pytest_asyncio
import asyncio
import time
from agents.core.base_agent import BaseAgent, AgentMessage, AgentStatus
from agents.core.capability_types import Capability, CapabilityType
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS
from typing import Set, Dict, Any

class TestPerformanceAgent(BaseAgent):
    """Test agent for performance testing."""
    
    def __init__(self, agent_id: str = "test_performance_agent", agent_type: str = "performance", capabilities: Set[Capability] = None, default_response: Dict[str, Any] = None, knowledge_graph=None, **kwargs):
        if capabilities is None:
            capabilities = {
                Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
                Capability(CapabilityType.TASK_EXECUTION, "1.0")
            }
        super().__init__(agent_id, agent_type, capabilities, default_response, knowledge_graph=knowledge_graph)
        self.message_count = 0
        self.total_processing_time = 0
        self.max_memory_usage = 0
        self.cpu_usage_samples = []
    
    async def process_message(self, message):
        start_time = time.time()
        self.message_count += 1
        
        # Simulate CPU-intensive work
        await asyncio.sleep(0.1)
        
        # Record metrics
        processing_time = time.time() - start_time
        self.total_processing_time += processing_time
        
        # Update knowledge graph with metrics
        await self.update_knowledge_graph({
            "agent_id": self.agent_id,
            "message_count": self.message_count,
            "processing_time": processing_time,
            "total_processing_time": self.total_processing_time,
            "timestamp": time.time()
        })
        
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender,
            content={
                "status": "success",
                "processing_time": processing_time,
                "message_count": self.message_count
            },
            message_type="performance_metrics"
        )
    
    async def query_knowledge_graph(self, query):
        """Query the knowledge graph for performance metrics."""
        return await super().query_knowledge_graph(query)
    
    async def update_knowledge_graph(self, data):
        """Update the knowledge graph with performance metrics."""
        return await super().update_knowledge_graph(data)

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        return await self.process_message(message)

@pytest.mark.asyncio
class TestPerformance:
    """Tests for system performance."""
    
    @pytest_asyncio.fixture
    async def setup_performance_test(self):
        """Set up test environment for performance testing."""
        knowledge_graph = Graph()
        agent = TestPerformanceAgent(
            "test_performance_agent",
            capabilities={
                Capability(CapabilityType.TASK_EXECUTION, "1.0"),
                Capability(CapabilityType.KNOWLEDGE_GRAPH_QUERY, "1.0"),
                Capability(CapabilityType.KNOWLEDGE_GRAPH_UPDATE, "1.0")
            }
        )
        agent.knowledge_graph = knowledge_graph
        await agent.initialize()
        return agent, knowledge_graph
    
    async def test_message_processing_performance(self, setup_performance_test):
        """Test message processing performance."""
        agent, knowledge_graph = setup_performance_test
        
        # Send multiple messages in parallel
        messages = [
            AgentMessage(
                sender_id="test_sender",
                recipient_id="test_performance_agent",
                content={"test": f"data_{i}"},
                message_type="test_message"
            )
            for i in range(10)
        ]
        
        start_time = time.time()
        responses = await asyncio.gather(*[
            agent.process_message(message)
            for message in messages
        ])
        total_time = time.time() - start_time
        
        # Verify performance metrics
        assert len(responses) == 10
        assert agent.message_count == 10
        assert agent.total_processing_time > 0
        assert total_time < 2.0  # Should process 10 messages in under 2 seconds
        
        # Verify knowledge graph updates
        query = """
        SELECT ?agent ?count ?time
        WHERE {
            ?agent rdf:type core:Agent .
            ?agent core:hasMessageCount ?count .
            ?agent core:hasProcessingTime ?time .
        }
        """
        results = await agent.query_knowledge_graph(query)
        assert len(results) > 0
    
    async def test_concurrent_operations(self, setup_performance_test):
        """Test concurrent operations performance."""
        agent, knowledge_graph = setup_performance_test
        
        # Simulate concurrent operations
        async def perform_operation():
            message = AgentMessage(
                sender_id="test_sender",
                recipient_id="test_performance_agent",
                content={"operation": "test"},
                message_type="test_message"
            )
            return await agent.process_message(message)
        
        # Run multiple operations concurrently
        operations = [perform_operation() for _ in range(5)]
        start_time = time.time()
        results = await asyncio.gather(*operations)
        total_time = time.time() - start_time
        
        # Verify results
        assert len(results) == 5
        assert total_time < 1.0  # Should complete 5 operations in under 1 second
        
        # Verify knowledge graph consistency
        query = """
        SELECT ?agent ?count
        WHERE {
            ?agent rdf:type core:Agent .
            ?agent core:hasMessageCount ?count .
        }
        """
        results = await agent.query_knowledge_graph(query)
        assert len(results) == 1
        assert int(results[0]["count"]) == 5
    
    async def test_resource_usage(self, setup_performance_test):
        """Test resource usage monitoring."""
        agent, knowledge_graph = setup_performance_test
        
        # Simulate high load
        messages = [
            AgentMessage(
                sender_id="test_sender",
                recipient_id="test_performance_agent",
                content={"load": "high"},
                message_type="test_message"
            )
            for _ in range(20)
        ]
        
        # Process messages and monitor resource usage
        start_time = time.time()
        responses = await asyncio.gather(*[
            agent.process_message(message)
            for message in messages
        ])
        total_time = time.time() - start_time
        
        # Verify performance under load
        assert len(responses) == 20
        assert total_time < 3.0  # Should handle 20 messages in under 3 seconds
        
        # Verify knowledge graph updates
        query = """
        SELECT ?agent ?count ?time
        WHERE {
            ?agent rdf:type core:Agent .
            ?agent core:hasMessageCount ?count .
            ?agent core:hasProcessingTime ?time .
        }
        """
        results = await agent.query_knowledge_graph(query)
        assert len(results) > 0
        assert int(results[0]["count"]) == 20
    
    async def test_recovery_performance(self, setup_performance_test):
        """Test recovery performance under failure conditions."""
        agent, knowledge_graph = setup_performance_test
        
        # Simulate failure and recovery
        async def simulate_failure():
            message = AgentMessage(
                sender_id="test_sender",
                recipient_id="test_performance_agent",
                content={"should_fail": True},
                message_type="test_message"
            )
            try:
                await agent.process_message(message)
            except Exception:
                await agent.update_status(AgentStatus.ERROR)
                await asyncio.sleep(0.1)  # Simulate recovery time
                await agent.update_status(AgentStatus.IDLE)
        
        # Run multiple failure/recovery cycles
        operations = [simulate_failure() for _ in range(3)]
        start_time = time.time()
        await asyncio.gather(*operations)
        total_time = time.time() - start_time
        
        # Verify recovery performance
        assert total_time < 1.0  # Should recover from 3 failures in under 1 second
        
        # Verify knowledge graph updates
        query = """
        SELECT ?agent ?status
        WHERE {
            ?agent rdf:type core:Agent .
            ?agent core:hasStatus ?status .
        }
        """
        results = await agent.query_knowledge_graph(query)
        assert len(results) > 0
        assert results[0]["status"] == "IDLE" 