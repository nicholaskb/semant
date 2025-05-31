from typing import Any, Dict, Optional
from dataclasses import dataclass
import time

@dataclass
class AgentMessage:
    """Message class for agent communication."""
    sender: str
    recipient: str
    content: Dict[str, Any]
    timestamp: float = time.time()
    message_type: str = "message"
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_type": self.message_type,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create message from dictionary."""
        return cls(
            sender=data["sender"],
            recipient=data["recipient"],
            content=data["content"],
            timestamp=data.get("timestamp", time.time()),
            message_type=data.get("message_type", "message"),
            metadata=data.get("metadata")
        ) 