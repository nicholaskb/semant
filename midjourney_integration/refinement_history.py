"""
Refinement History Store for tracking prompt refinement iterations.
Supports undo/redo and session management.
"""
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import uuid
from collections import defaultdict
from loguru import logger


@dataclass
class RefinementStep:
    """Represents a single refinement iteration."""
    step_id: str
    timestamp: str
    original_prompt: str
    refined_prompt: str
    method: str  # 'agent', 'workflow', 'manual'
    metadata: Dict = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class RefinementHistory:
    """
    In-memory store for refinement history with undo/redo capabilities.
    
    Each session maintains a stack of refinement steps with a cursor position
    for navigating through history.
    """
    
    def __init__(self):
        # Session ID -> List of RefinementStep
        self._history: Dict[str, List[RefinementStep]] = defaultdict(list)
        # Session ID -> Current position in history (for undo/redo)
        self._cursor: Dict[str, int] = {}
        
    def create_session(self) -> str:
        """Create a new refinement session and return session ID."""
        session_id = str(uuid.uuid4())
        self._history[session_id] = []
        self._cursor[session_id] = -1
        logger.info(f"Created refinement session: {session_id}")
        return session_id
    
    def add_step(
        self,
        session_id: str,
        original_prompt: str,
        refined_prompt: str,
        method: str = "agent",
        metadata: Optional[Dict] = None
    ) -> RefinementStep:
        """
        Add a new refinement step to the session.
        Clears any redo history if we're not at the end of the stack.
        """
        if session_id not in self._history:
            logger.warning(f"Session {session_id} not found, creating it")
            self._history[session_id] = []
            self._cursor[session_id] = -1
        
        # If we're in the middle of history (after undo), clear forward history
        cursor = self._cursor[session_id]
        if cursor < len(self._history[session_id]) - 1:
            self._history[session_id] = self._history[session_id][:cursor + 1]
            logger.debug(f"Cleared redo history for session {session_id}")
        
        step = RefinementStep(
            step_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            original_prompt=original_prompt,
            refined_prompt=refined_prompt,
            method=method,
            metadata=metadata or {}
        )
        
        self._history[session_id].append(step)
        self._cursor[session_id] = len(self._history[session_id]) - 1
        
        logger.info(f"Added refinement step to session {session_id}: {step.step_id}")
        return step
    
    def get_history(self, session_id: str) -> List[RefinementStep]:
        """Get all refinement steps for a session."""
        return self._history.get(session_id, [])
    
    def get_current_step(self, session_id: str) -> Optional[RefinementStep]:
        """Get the current refinement step based on cursor position."""
        if session_id not in self._history:
            return None
        
        cursor = self._cursor.get(session_id, -1)
        if cursor < 0 or cursor >= len(self._history[session_id]):
            return None
        
        return self._history[session_id][cursor]
    
    def undo(self, session_id: str) -> Optional[RefinementStep]:
        """
        Move cursor back one step and return the previous refinement.
        Returns None if already at the beginning.
        """
        if session_id not in self._history:
            logger.warning(f"Cannot undo: session {session_id} not found")
            return None
        
        cursor = self._cursor[session_id]
        if cursor <= 0:
            logger.debug(f"Cannot undo: already at beginning of history for session {session_id}")
            return None
        
        self._cursor[session_id] = cursor - 1
        previous_step = self._history[session_id][self._cursor[session_id]]
        
        logger.info(f"Undo in session {session_id}: moved to step {previous_step.step_id}")
        return previous_step
    
    def redo(self, session_id: str) -> Optional[RefinementStep]:
        """
        Move cursor forward one step and return the next refinement.
        Returns None if already at the end.
        """
        if session_id not in self._history:
            logger.warning(f"Cannot redo: session {session_id} not found")
            return None
        
        cursor = self._cursor[session_id]
        if cursor >= len(self._history[session_id]) - 1:
            logger.debug(f"Cannot redo: already at end of history for session {session_id}")
            return None
        
        self._cursor[session_id] = cursor + 1
        next_step = self._history[session_id][self._cursor[session_id]]
        
        logger.info(f"Redo in session {session_id}: moved to step {next_step.step_id}")
        return next_step
    
    def can_undo(self, session_id: str) -> bool:
        """Check if undo is available for the session."""
        if session_id not in self._history:
            return False
        return self._cursor.get(session_id, -1) > 0
    
    def can_redo(self, session_id: str) -> bool:
        """Check if redo is available for the session."""
        if session_id not in self._history:
            return False
        cursor = self._cursor.get(session_id, -1)
        return cursor < len(self._history[session_id]) - 1
    
    def clear_session(self, session_id: str) -> bool:
        """Clear all history for a session."""
        if session_id not in self._history:
            return False
        
        del self._history[session_id]
        if session_id in self._cursor:
            del self._cursor[session_id]
        
        logger.info(f"Cleared session {session_id}")
        return True
    
    def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics about a refinement session."""
        if session_id not in self._history:
            return {}
        
        history = self._history[session_id]
        cursor = self._cursor.get(session_id, -1)
        
        return {
            "session_id": session_id,
            "total_steps": len(history),
            "current_position": cursor + 1,
            "can_undo": self.can_undo(session_id),
            "can_redo": self.can_redo(session_id),
            "created_at": history[0].timestamp if history else None,
            "last_modified": history[-1].timestamp if history else None,
        }


# Global singleton instance
_refinement_history = RefinementHistory()


def get_refinement_history() -> RefinementHistory:
    """Get the global refinement history instance."""
    return _refinement_history

