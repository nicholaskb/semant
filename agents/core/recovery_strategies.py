from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from loguru import logger
from agents.core.base_agent import BaseAgent, AgentStatus
import asyncio

class RecoveryStrategy(ABC):
    """Abstract base class for recovery strategies."""
    
    @abstractmethod
    async def recover(self, agent: BaseAgent) -> bool:
        """Attempt to recover the agent using this strategy."""
        pass
        
    @abstractmethod
    async def can_handle(self, error_type: str) -> bool:
        """Check if this strategy can handle the given error type."""
        pass

class TimeoutRecoveryStrategy(RecoveryStrategy):
    """Strategy for handling timeout-related failures."""
    
    async def recover(self, agent: BaseAgent) -> bool:
        """Attempt to recover from a timeout failure."""
        try:
            # Reset any pending operations
            await agent.reset_pending_operations()
            
            # Clean up resources
            await agent.cleanup_resources()
            
            # Reset communication channels
            await agent.reset_communication()
            
            # Backup current state
            await agent.backup_state()
            
            # Update knowledge graph
            await agent.knowledge_graph.add_triple(
                agent.agent_uri(),
                "http://example.org/agent/hasStatus",
                f"http://example.org/agent/idle"
            )
            
            # Update agent status
            agent.status = AgentStatus.IDLE
            
            return True
        except Exception as e:
            logger.error(f"Timeout recovery failed: {e}")
            return False
            
    async def can_handle(self, error_type: str) -> bool:
        return error_type in ["timeout", "operation_timeout", "response_timeout"]

class ResourceExhaustionRecoveryStrategy(RecoveryStrategy):
    """Strategy for handling resource exhaustion failures."""
    
    async def recover(self, agent: BaseAgent) -> bool:
        """Attempt to recover from resource exhaustion."""
        try:
            # Clean up resources
            await agent.cleanup_resources()
            # Reallocate resources
            await agent.allocate_resources()
            return True
        except Exception as e:
            logger.error(f"Resource exhaustion recovery failed: {e}")
            return False
            
    async def can_handle(self, error_type: str) -> bool:
        return error_type in ["memory_exhaustion", "cpu_exhaustion", "resource_exhaustion"]

class CommunicationRecoveryStrategy(RecoveryStrategy):
    """Strategy for handling communication-related failures."""
    
    async def recover(self, agent: BaseAgent) -> bool:
        """Attempt to recover from communication failures."""
        try:
            # Reset communication channels
            await agent.reset_communication()
            # Reestablish connections
            await agent.establish_connections()
            return True
        except Exception as e:
            logger.error(f"Communication recovery failed: {e}")
            return False
            
    async def can_handle(self, error_type: str) -> bool:
        return error_type in ["connection_error", "communication_error", "network_error"]

class StateCorruptionRecoveryStrategy(RecoveryStrategy):
    """Strategy for handling state corruption failures."""
    
    async def recover(self, agent: BaseAgent) -> bool:
        """Attempt to recover from state corruption."""
        try:
            # Backup current state
            await agent.backup_state()
            
            # Clean up resources
            await agent.cleanup_resources()
            
            # Reset communication channels
            await agent.reset_communication()
            
            # Restore from last known good state
            await agent.restore_state()
            
            # Update knowledge graph
            await agent.knowledge_graph.add_triple(
                agent.agent_uri(),
                "http://example.org/agent/hasStatus",
                f"http://example.org/agent/idle"
            )
            
            # Update agent status
            agent.status = AgentStatus.IDLE
            
            return True
        except Exception as e:
            logger.error(f"State corruption recovery failed: {e}")
            return False
            
    async def can_handle(self, error_type: str) -> bool:
        return error_type in ["state_corruption", "data_corruption", "inconsistent_state"]

class DefaultRecoveryStrategy(RecoveryStrategy):
    """Default strategy for handling unknown error types."""
    
    async def recover(self, agent: BaseAgent) -> bool:
        """Attempt basic recovery steps."""
        try:
            # Reset pending operations
            await agent.reset_pending_operations()
            
            # Clean up resources
            await agent.cleanup_resources()
            
            # Reset communication channels
            await agent.reset_communication()
            
            # Backup current state
            await agent.backup_state()
            
            # Restore state
            await agent.restore_state()
            
            # Update knowledge graph
            await agent.knowledge_graph.add_triple(
                agent.agent_uri(),
                "http://example.org/agent/hasStatus",
                f"http://example.org/agent/idle"
            )
            
            # Update agent status
            agent.status = AgentStatus.IDLE
            
            return True
        except Exception as e:
            logger.error(f"Default recovery failed: {e}")
            return False
            
    async def can_handle(self, error_type: str) -> bool:
        return True  # Can handle any error type as fallback

class RecoveryStrategyFactory:
    """Factory for creating recovery strategies."""
    
    def __init__(self):
        """Initialize the factory."""
        self._strategies = {}
        self._default_strategy = DefaultRecoveryStrategy()
        
    async def initialize(self) -> None:
        """Initialize recovery strategies."""
        # Register default strategies
        self._strategies["timeout"] = TimeoutRecoveryStrategy()
        self._strategies["state_corruption"] = StateCorruptionRecoveryStrategy()
        self._strategies["default"] = self._default_strategy
        
    async def get_strategy(self, error_type: str) -> Optional[RecoveryStrategy]:
        """Get a recovery strategy for the given error type.
        
        Args:
            error_type: The type of error to handle.
            
        Returns:
            RecoveryStrategy: The strategy to use, or None if no suitable strategy is found.
        """
        # Check if we have a specific strategy for this error type
        for strategy in self._strategies.values():
            if await strategy.can_handle(error_type):
                return strategy
                
        # Fall back to default strategy
        return self._default_strategy
        
    def register_strategy(self, error_type: str, strategy: RecoveryStrategy) -> None:
        """Register a new recovery strategy.
        
        Args:
            error_type: The type of error to handle.
            strategy: The strategy to use.
        """
        self._strategies[error_type] = strategy 