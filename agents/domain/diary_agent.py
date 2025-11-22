from typing import Dict, Any, Optional, Set
from agents.core.base_agent import BaseAgent, AgentMessage
from agents.core.capability_types import Capability, CapabilityType
from datetime import datetime

class DiaryAgent(BaseAgent):
    """Agent that maintains a diary of events."""
    
    def __init__(
        self,
        agent_id: str = "diary_agent",
        agent_type: str = "diary",
        capabilities: Optional[Set[Capability]] = None,
        knowledge_graph: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        default_capabilities = {
            Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
            Capability(CapabilityType.DIARY_MANAGEMENT, "1.0")
        }
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities or default_capabilities,
            knowledge_graph=knowledge_graph,
            config=config
        )
        self._entries = []
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message."""
        if message.message_type == "add_entry":
            entry = message.content.get("entry")
            if not entry:
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    content={"status": "error", "message": "No entry provided"},
                    timestamp=datetime.utcnow(),
                    message_type="error"
                )
                
            self._entries.append({
                "timestamp": datetime.utcnow().isoformat(),
                "entry": entry
            })
            
            if self.knowledge_graph:
                await self.knowledge_graph.add_triple(
                    f"diary:{len(self._entries)}",
                    "diary:entry",
                    entry
                )
                
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "success"},
                timestamp=datetime.utcnow(),
                message_type="add_entry_response"
            )
            
        elif message.message_type == "query_diary":
            query = message.content.get("query")
            if not query:
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    content={"status": "error", "message": "No query provided"},
                    timestamp=datetime.utcnow(),
                    message_type="error"
                )
                
            results = []
            for entry in self._entries:
                if query.lower() in entry["entry"].lower():
                    results.append(entry)
                    
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "success", "results": results},
                timestamp=datetime.utcnow(),
                message_type="query_diary_response"
            )
            
        else:
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "error", "message": "Unknown message type"},
                timestamp=datetime.utcnow(),
                message_type="error"
            )
            
    def get_entries(self) -> list:
        """Get all diary entries."""
        return self._entries
