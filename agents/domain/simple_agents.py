from typing import Any, Dict, Optional
from agents.core.base_agent import BaseAgent, AgentMessage
import uuid
from datetime import datetime
from loguru import logger


class SimpleResponderAgent(BaseAgent):
    """Base class for simple agents that return a predefined response."""

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        default_response: str,
        knowledge_graph: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a simple responder agent.
        
        Args:
            agent_id: Unique identifier for this agent
            agent_type: Type of agent
            default_response: Default response to return
            knowledge_graph: Optional knowledge graph instance
            config: Optional configuration
        """
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            knowledge_graph=knowledge_graph,
            config=config or {}
        )
        self.default_response = default_response
        self.response_count = 0

    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info(f"SimpleResponderAgent '{self.agent_id}' initialized")

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """
        Process incoming messages and return the default or custom response.
        
        Args:
            message: The incoming message
            
        Returns:
            Response message
        """
        self.response_count += 1
        
        # Check if a custom response was requested
        custom_response = message.content.get('custom_response')
        response_text = custom_response if custom_response else self.default_response
        
        # Log to knowledge graph if available
        if self.knowledge_graph:
            await self._log_response_to_kg(message, response_text)
        
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={
                "response": response_text,
                "response_count": self.response_count,
                "agent_type": self.agent_type
            },
            timestamp=datetime.now(),
            message_type="response"
        )

    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """
        Update the knowledge graph with agent-specific data.
        
        Args:
            update_data: Data to add to the knowledge graph
        """
        if not self.knowledge_graph:
            self.logger.debug("Knowledge graph not available for updates")
            return
        
        try:
            # Add a record of this update
            update_id = f"simple_agent_update_{uuid.uuid4().hex[:8]}"
            update_uri = f"http://example.org/updates/{update_id}"
            
            await self.knowledge_graph.add_triple(
                update_uri,
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                "http://example.org/SimpleAgentUpdate"
            )
            
            await self.knowledge_graph.add_triple(
                update_uri,
                "http://example.org/agentId",
                self.agent_id
            )
            
            await self.knowledge_graph.add_triple(
                update_uri,
                "http://example.org/timestamp",
                datetime.now().isoformat()
            )
            
            # Add custom fields from update_data
            for key, value in update_data.items():
                if value is not None:
                    await self.knowledge_graph.add_triple(
                        update_uri,
                        f"http://example.org/{key}",
                        str(value)
                    )
            
            self.logger.debug(f"Knowledge graph updated: {update_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update knowledge graph: {e}")

    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query the knowledge graph.
        
        Args:
            query: Query parameters (should contain 'sparql' key)
            
        Returns:
            Query results or empty dict if KG not available
        """
        if not self.knowledge_graph:
            return {"error": "Knowledge graph not available"}
        
        try:
            sparql_query = query.get("sparql")
            if not sparql_query:
                # Provide a default query for agent responses
                sparql_query = f"""
                PREFIX ex: <http://example.org/>
                SELECT ?response ?timestamp
                WHERE {{
                    ?msg a ex:SimpleAgentResponse ;
                         ex:agentId "{self.agent_id}" ;
                         ex:responseText ?response ;
                         ex:timestamp ?timestamp .
                }}
                ORDER BY DESC(?timestamp)
                LIMIT 10
                """
            
            results = await self.knowledge_graph.query_graph(sparql_query)
            return {"results": results}
            
        except Exception as e:
            self.logger.error(f"Knowledge graph query failed: {e}")
            return {"error": str(e)}
    
    async def _log_response_to_kg(self, message: AgentMessage, response_text: str) -> None:
        """
        Log a response to the knowledge graph.
        
        Args:
            message: The incoming message
            response_text: The response being sent
        """
        if not self.knowledge_graph:
            return
        
        try:
            response_id = f"simple_response_{uuid.uuid4().hex[:8]}"
            response_uri = f"http://example.org/responses/{response_id}"
            
            await self.knowledge_graph.add_triple(
                response_uri,
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                "http://example.org/SimpleAgentResponse"
            )
            
            await self.knowledge_graph.add_triple(
                response_uri,
                "http://example.org/agentId",
                self.agent_id
            )
            
            await self.knowledge_graph.add_triple(
                response_uri,
                "http://example.org/responseText",
                response_text
            )
            
            await self.knowledge_graph.add_triple(
                response_uri,
                "http://example.org/timestamp",
                datetime.now().isoformat()
            )
            
            await self.knowledge_graph.add_triple(
                response_uri,
                "http://example.org/responseCount",
                str(self.response_count)
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to log response to KG: {e}")


class FinanceAgent(SimpleResponderAgent):
    """Agent that provides financial information."""
    
    def __init__(
        self,
        agent_id: str = "finance_agent",
        knowledge_graph: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(
            agent_id,
            "finance",
            "Finance information not available.",
            knowledge_graph,
            config
        )


class CoachingAgent(SimpleResponderAgent):
    """Agent that provides coaching and motivational responses."""
    
    def __init__(
        self,
        agent_id: str = "coaching_agent",
        knowledge_graph: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(
            agent_id,
            "coaching",
            "Keep learning and growing!",
            knowledge_graph,
            config
        )


class IntelligenceAgent(SimpleResponderAgent):
    """Agent that provides intelligence reports."""
    
    def __init__(
        self,
        agent_id: str = "intelligence_agent",
        knowledge_graph: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(
            agent_id,
            "intelligence",
            "No intelligence reports.",
            knowledge_graph,
            config
        )


class DeveloperAgent(SimpleResponderAgent):
    """Agent that provides development and code generation services."""
    
    def __init__(
        self,
        agent_id: str = "developer_agent",
        knowledge_graph: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(
            agent_id,
            "developer",
            "Code generation not supported.",
            knowledge_graph,
            config
        )
