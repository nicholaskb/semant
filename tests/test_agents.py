import pytest
import pytest_asyncio
from agents.core.sensor_agent import SensorAgent
from agents.core.data_processor_agent import DataProcessorAgent
from agents.core.base_agent import BaseAgent, AgentMessage, AgentStatus
from agents.core.agentic_prompt_agent import AgenticPromptAgent
from agents.core.capability_types import Capability, CapabilityType
from rdflib import Graph, URIRef
from rdflib.namespace import RDF
import uuid
from datetime import datetime
from agents.core.message_types import AgentMessage

class TestableBaseAgent(BaseAgent):
    async def process_message(self, message):
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"error": "Not implemented"},
            message_type="error"
        )
    async def query_knowledge_graph(self, *args, **kwargs):
        return {}
    async def update_knowledge_graph(self, *args, **kwargs):
        return True


    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages - REQUIRED IMPLEMENTATION."""
        try:
            # Process the message based on its type and content
            response_content = f"Agent {self.agent_id} processed: {message.content}"
            
            return AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=response_content,
                message_type=getattr(message, 'message_type', 'response'),
                timestamp=datetime.now()
            )
        except Exception as e:
            # Error handling
            return AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=f"Error processing message: {str(e)}",
                message_type="error",
                timestamp=datetime.now()
            )

@pytest.mark.asyncio
class TestBaseAgent:
    """Tests for base agent functionality."""
    
    @pytest_asyncio.fixture
    async def setup_base_agent(self):
        """Set up test environment for base agent."""
        agent = TestableBaseAgent(
            agent_id="test_base_agent",
            agent_type="test",
            capabilities={Capability(CapabilityType.TASK_EXECUTION, "1.0")}
        )
        await agent.initialize()
        return agent
    
    async def test_initialization(self, setup_base_agent):
        """Test agent initialization."""
        agent = setup_base_agent
        assert agent.agent_id == "test_base_agent"
        assert agent.agent_type == "test"
        assert agent.status == AgentStatus.IDLE
        
    async def test_state_transitions(self, setup_base_agent):
        """Test agent state transitions."""
        agent = setup_base_agent
        
        # Test transition to busy
        await agent.update_status(AgentStatus.BUSY)
        assert agent.status == AgentStatus.BUSY
        
        # Test transition to error
        await agent.update_status(AgentStatus.ERROR)
        assert agent.status == AgentStatus.ERROR
        
        # Test transition back to idle
        await agent.update_status(AgentStatus.IDLE)
        assert agent.status == AgentStatus.IDLE
        
    async def test_message_handling(self, setup_base_agent):
        """Test message handling functionality."""
        agent = setup_base_agent
        
        message = AgentMessage(
            sender_id="test_sender",
            recipient_id="test_base_agent",
            content={"test": "data"},
            message_type="test_message"
        )
        
        response = await agent.process_message(message)
        assert response.sender_id == agent.agent_id
        assert response.recipient_id == message.sender_id
        assert response.message_type == "error"  # Base agent should return error for unknown message types

@pytest.mark.asyncio
class TestSensorAgent:
    """Tests for sensor agent functionality."""
    
    @pytest_asyncio.fixture
    async def setup_sensor_agent(self):
        """Set up test environment for sensor agent."""
        agent = SensorAgent()
        await agent.initialize()
        return agent
    
    async def test_process_message(self, setup_sensor_agent):
        """Test message processing."""
        agent = setup_sensor_agent
        message = AgentMessage(
            sender_id="test_sender",
            recipient_id="sensor_agent",
            content={"sensor_id": "sensor1", "reading": 42},
            timestamp=1234567890,
            message_type="sensor_data"
        )
        response = await agent.process_message(message)
        assert response.content["status"] == "Sensor data updated successfully."

@pytest.mark.asyncio
class TestDataProcessorAgent:
    """Tests for data processor agent functionality."""
    
    @pytest_asyncio.fixture
    async def setup_data_processor_agent(self):
        """Set up test environment for data processor agent."""
        agent = DataProcessorAgent()
        await agent.initialize()
        return agent
    
    async def test_process_message(self, setup_data_processor_agent):
        """Test message processing."""
        agent = setup_data_processor_agent
        message = AgentMessage(
            sender_id="test_sender",
            recipient_id="data_processor_agent",
            content={"data": "test_data"},
            timestamp=1234567890,
            message_type="data_processor_data"
        )
        response = await agent.process_message(message)
        assert response.content["status"] == "Data processed successfully."

@pytest.mark.asyncio
class TestPromptAgent:
    """Tests for prompt agent functionality."""
    
    @pytest_asyncio.fixture
    async def setup_prompt_agent(self):
        """Set up test environment for prompt agent."""
        knowledge_graph = Graph()
        agent = AgenticPromptAgent(
            "test_prompt_agent",
            capabilities={
                Capability(CapabilityType.CODE_REVIEW, "1.0"),
                Capability(CapabilityType.KNOWLEDGE_GRAPH_QUERY, "1.0"),
                Capability(CapabilityType.KNOWLEDGE_GRAPH_UPDATE, "1.0")
            },
            config={
                "consensus_threshold": 0.75,
                "prompt_templates": {
                    "code_review": {
                        "role": "You are a {role} specializing in {specialization}.",
                        "context": "Context:\n{context}",
                        "objective": "Objective:\n{objective}",
                        "approach": "Approach:\n{approach}",
                        "documentation": "Documentation:\n{documentation}"
                    }
                }
            }
        )
        agent.knowledge_graph = knowledge_graph
        await agent.initialize()
        return agent, knowledge_graph
    
    async def test_prompt_generation(self, setup_prompt_agent):
        """Test prompt generation functionality."""
        agent, knowledge_graph = setup_prompt_agent
        
        message = AgentMessage(
            sender_id="test_agent",
            recipient_id="test_prompt_agent",
            content={
                "prompt_type": "code_review",
                "context": {
                    "role": "senior backend engineer",
                    "specialization": "Python and SPARQL",
                    "approach": "Follow best practices",
                    "documentation": "Document all changes"
                },
                "objective": "Debug and enhance the KnowledgeGraphManager module"
            },
            message_type="prompt_request"
        )
        
        response = await agent.process_message(message)
        assert response.message_type == "prompt_response"
        assert "prompt" in response.content
        
        prompt = response.content["prompt"]
        assert "role" in prompt
        assert "context" in prompt
        assert "objective" in prompt
        assert "approach" in prompt
        assert "documentation" in prompt
        
        # Verify knowledge graph update
        prompt_uri = URIRef("prompt:code_review")
        assert (prompt_uri, RDF.type, URIRef("prompt:Prompt")) in knowledge_graph
    
    async def test_code_review(self, setup_prompt_agent):
        """Test code review functionality."""
        agent, knowledge_graph = setup_prompt_agent
        
        message = AgentMessage(
            sender_id="test_agent",
            recipient_id="test_prompt_agent",
            content={
                "code_artifact": {
                    "file": "test.py",
                    "content": "def test_function():\n    pass"
                },
                "review_type": "general"
            },
            message_type="review_request"
        )
        
        response = await agent.process_message(message)
        assert response.message_type == "review_response"
        assert "review_result" in response.content
        
        review = response.content["review_result"]
        assert "status" in review
        assert "findings" in review
        assert "recommendations" in review
    
    async def test_template_management(self, setup_prompt_agent):
        """Test template management functionality."""
        agent, knowledge_graph = setup_prompt_agent
        
        message = AgentMessage(
            sender_id="test_agent",
            recipient_id="test_prompt_agent",
            content={
                "template_type": "code_review"
            },
            message_type="template_request"
        )
        
        response = await agent.process_message(message)
        assert response.message_type == "template_response"
        assert "template" in response.content
        
        template = response.content["template"]
        assert "role" in template
        assert "context" in template
        assert "objective" in template
        assert "approach" in template
        assert "documentation" in template
    
    async def test_error_handling(self, setup_prompt_agent):
        """Test error handling functionality."""
        agent, knowledge_graph = setup_prompt_agent
        
        # Test missing parameters
        message = AgentMessage(
            sender_id="test_agent",
            recipient_id="test_prompt_agent",
            content={},
            message_type="prompt_request"
        )
        
        response = await agent.process_message(message)
        assert response.message_type == "error"
        assert "error" in response.content
        
        # Test unknown template
        message = AgentMessage(
            sender_id="test_agent",
            recipient_id="test_prompt_agent",
            content={
                "template_type": "unknown_template"
            },
            message_type="template_request"
        )
        
        response = await agent.process_message(message)
        assert response.message_type == "error"
        assert "error" in response.content 