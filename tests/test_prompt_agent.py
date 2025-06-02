import pytest
import pytest_asyncio
from agents.core.agentic_prompt_agent import AgenticPromptAgent
from agents.core.base_agent import AgentMessage, AgentStatus
from agents.core.capability_types import Capability, CapabilityType
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS

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
                    },
                    "task_execution": {
                        "role": "You are a {role}.",
                        "task": "Task:\n{task}",
                        "constraints": "Constraints:\n{constraints}",
                        "expected_output": "Expected Output:\n{expected_output}"
                    }
                }
            }
        )
        agent.knowledge_graph = knowledge_graph
        await agent.initialize()
        return agent, knowledge_graph
    
    async def test_prompt_generation(self, setup_prompt_agent):
        """Test prompt generation with different templates."""
        agent, knowledge_graph = setup_prompt_agent
        
        # Test code review prompt
        message = AgentMessage(
            sender="test_agent",
            recipient="test_prompt_agent",
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
        
        # Test task execution prompt
        message = AgentMessage(
            sender="test_agent",
            recipient="test_prompt_agent",
            content={
                "prompt_type": "task_execution",
                "context": {
                    "role": "data engineer",
                    "task": "Process sensor data",
                    "constraints": "Must handle missing values",
                    "expected_output": "Cleaned dataset"
                }
            },
            message_type="prompt_request"
        )
        
        response = await agent.process_message(message)
        assert response.message_type == "prompt_response"
        assert "prompt" in response.content
        
        prompt = response.content["prompt"]
        assert "role" in prompt
        assert "task" in prompt
        assert "constraints" in prompt
        assert "expected_output" in prompt
    
    async def test_knowledge_graph_integration(self, setup_prompt_agent):
        """Test knowledge graph integration for prompts."""
        agent, knowledge_graph = setup_prompt_agent
        
        # Generate a prompt
        message = AgentMessage(
            sender="test_agent",
            recipient="test_prompt_agent",
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
        
        # Verify knowledge graph updates
        prompt_uri = URIRef("prompt:code_review")
        assert (prompt_uri, RDF.type, URIRef("prompt:Prompt")) in knowledge_graph
        assert (prompt_uri, RDFS.label, Literal("Code Review Prompt")) in knowledge_graph
        
        # Query knowledge graph for prompt history
        query = """
        SELECT ?prompt ?timestamp
        WHERE {
            ?prompt rdf:type prompt:Prompt .
            ?prompt prompt:hasTimestamp ?timestamp .
        }
        """
        results = await agent.query_knowledge_graph(query)
        assert len(results) > 0
    
    async def test_prompt_validation(self, setup_prompt_agent):
        """Test prompt validation and error handling."""
        agent, knowledge_graph = setup_prompt_agent
        
        # Test missing required fields
        message = AgentMessage(
            sender="test_agent",
            recipient="test_prompt_agent",
            content={
                "prompt_type": "code_review",
                "context": {
                    "role": "senior backend engineer"
                    # Missing specialization, approach, documentation
                }
            },
            message_type="prompt_request"
        )
        
        response = await agent.process_message(message)
        assert response.message_type == "error"
        assert "missing required fields" in response.content["error"].lower()
        
        # Test invalid prompt type
        message = AgentMessage(
            sender="test_agent",
            recipient="test_prompt_agent",
            content={
                "prompt_type": "invalid_type",
                "context": {
                    "role": "senior backend engineer",
                    "specialization": "Python and SPARQL",
                    "approach": "Follow best practices",
                    "documentation": "Document all changes"
                }
            },
            message_type="prompt_request"
        )
        
        response = await agent.process_message(message)
        assert response.message_type == "error"
        assert "invalid prompt type" in response.content["error"].lower()
    
    async def test_prompt_metrics(self, setup_prompt_agent):
        """Test prompt metrics collection and reporting."""
        agent, knowledge_graph = setup_prompt_agent
        
        # Generate multiple prompts
        for i in range(3):
            message = AgentMessage(
                sender="test_agent",
                recipient="test_prompt_agent",
                content={
                    "prompt_type": "code_review",
                    "context": {
                        "role": "senior backend engineer",
                        "specialization": "Python and SPARQL",
                        "approach": "Follow best practices",
                        "documentation": "Document all changes"
                    },
                    "objective": f"Debug and enhance module {i}"
                },
                message_type="prompt_request"
            )
            await agent.process_message(message)
        
        # Query metrics
        message = AgentMessage(
            sender="test_agent",
            recipient="test_prompt_agent",
            content={
                "metric_type": "prompt_usage"
            },
            message_type="metrics_request"
        )
        
        response = await agent.process_message(message)
        assert response.message_type == "metrics_response"
        assert "metrics" in response.content
        
        metrics = response.content["metrics"]
        assert "total_prompts" in metrics
        assert metrics["total_prompts"] >= 3
        assert "prompt_types" in metrics
        assert "code_review" in metrics["prompt_types"] 