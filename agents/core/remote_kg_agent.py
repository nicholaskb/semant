from agents.core.base_agent import BaseAgent, AgentMessage
from kg.models.remote_graph_manager import RemoteKnowledgeGraphManager

class RemoteKGAgent(BaseAgent):
    """
    Agent that interacts with a remote knowledge graph via SPARQL endpoint.
    Message content should include {'query': ...} or {'update': ...}
    """
    def __init__(self, agent_id: str = "remote_kg_agent", query_endpoint: str = None, update_endpoint: str = None):
        super().__init__(agent_id, "remote_kg")
        self.kg = RemoteKnowledgeGraphManager(query_endpoint, update_endpoint)

    async def initialize(self) -> None:
        self.logger.info("Remote KG Agent initialized")

    async def process_message(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "sparql_query":
            query = message.content.get('query')
            if not query:
                return AgentMessage(
                    sender=self.agent_id,
                    recipient=message.sender,
                    content={"error": "No query provided."},
                    timestamp=message.timestamp,
                    message_type="sparql_query_response"
                )
            try:
                results = await self.kg.query_graph(query)
                return AgentMessage(
                    sender=self.agent_id,
                    recipient=message.sender,
                    content={"results": results},
                    timestamp=message.timestamp,
                    message_type="sparql_query_response"
                )
            except Exception as e:
                return AgentMessage(
                    sender=self.agent_id,
                    recipient=message.sender,
                    content={"error": str(e)},
                    timestamp=message.timestamp,
                    message_type="sparql_query_response"
                )
        elif message.message_type == "sparql_update":
            update = message.content.get('update')
            if not update:
                return AgentMessage(
                    sender=self.agent_id,
                    recipient=message.sender,
                    content={"error": "No update provided."},
                    timestamp=message.timestamp,
                    message_type="sparql_update_response"
                )
            try:
                await self.kg.update_graph(update)
                return AgentMessage(
                    sender=self.agent_id,
                    recipient=message.sender,
                    content={"status": "Update successful."},
                    timestamp=message.timestamp,
                    message_type="sparql_update_response"
                )
            except Exception as e:
                return AgentMessage(
                    sender=self.agent_id,
                    recipient=message.sender,
                    content={"error": str(e)},
                    timestamp=message.timestamp,
                    message_type="sparql_update_response"
                )
        else:
            return await self._handle_unknown_message(message)

    async def query_knowledge_graph(self, query: dict) -> dict:
        return {}

    async def update_knowledge_graph(self, update_data: dict) -> None:
        pass 