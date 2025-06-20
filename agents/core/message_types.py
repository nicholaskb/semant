"""
Message types for agent communication.
Provides a standardized message format for all agent communication.
"""
import uuid
from datetime import datetime
import time
from typing import Any, Optional, Dict, Union
from pydantic import BaseModel, Field, validator

class AgentMessage(BaseModel):
    """Base message class for agent communication.
    
    Attributes:
        message_id: Unique identifier for the message
        sender_id: ID of the sending agent (also accessible as 'sender' for backward compatibility)
        recipient_id: ID of the receiving agent (also accessible as 'recipient' for backward compatibility)
        content: Message content (any type)
        message_type: Type of message (default: "default")
        timestamp: Message timestamp (can be datetime or float)
        metadata: Optional additional metadata
    """
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    recipient_id: str
    content: Any
    message_type: str = "default"
    timestamp: Union[datetime, float] = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True
        allow_population_by_field_name = True
        
    def __init__(self, **data):
        # Handle legacy field names
        if 'sender' in data and 'sender_id' not in data:
            data['sender_id'] = data.pop('sender')
        if 'recipient' in data and 'recipient_id' not in data:
            data['recipient_id'] = data.pop('recipient')
            
        # Handle timestamp conversion
        if 'timestamp' in data and isinstance(data['timestamp'], (int, float)):
            data['timestamp'] = datetime.fromtimestamp(data['timestamp'])
            
        super().__init__(**data)

    @property
    def sender(self) -> str:
        """Legacy accessor for sender_id."""
        return self.sender_id

    @property
    def recipient(self) -> str:
        """Legacy accessor for recipient_id."""
        return self.recipient_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary (legacy format)."""
        return {
            "sender": self.sender_id,
            "recipient": self.recipient_id,
            "content": self.content,
            "timestamp": self.timestamp.timestamp() if isinstance(self.timestamp, datetime) else self.timestamp,
            "message_type": self.message_type,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create message from dictionary (legacy format)."""
        return cls(
            sender_id=data["sender"],
            recipient_id=data["recipient"],
            content=data["content"],
            timestamp=data.get("timestamp", time.time()),
            message_type=data.get("message_type", "default"),
            metadata=data.get("metadata")
        )

    @validator('timestamp', pre=True)
    def validate_timestamp(cls, v):
        """Convert timestamp to datetime if needed."""
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v)
        return v

    # ------------------------------------------------------------------
    # Dict-like convenience accessors (for backwards-compat tests)
    # ------------------------------------------------------------------
    def __getitem__(self, item: str) -> Any:
        """Allow dict-style access (e.g., msg["sender_id"])."""
        try:
            return getattr(self, item)
        except AttributeError as exc:
            raise KeyError(item) from exc

    def __iter__(self):
        """Iterate over keys to mimic minimal Mapping interface."""
        return iter(self.__dict__)

    def keys(self):  # type: ignore[override]
        return self.__dict__.keys()

    def items(self):  # type: ignore[override]
        return self.__dict__.items()

    def values(self):  # type: ignore[override]
        return self.__dict__.values()
