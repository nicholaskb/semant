"""Test agent recovery functionality.

Mock Patterns:
-------------
1. Knowledge Graph Mocking:
   - Use AsyncMock(spec=KnowledgeGraphManager) for the base mock
   - Handle both raw SPARQL strings and dict queries in mock functions
   - Maintain consistent error propagation across tests

2. Error Cases:
   - Use side_effect for error simulation
   - Ensure errors propagate through the agent's error handling
   - Verify error states and metrics

3. Lock Management:
   - Follow lock ordering: metrics_lock -> status_lock -> lock
   - Use proper lock cleanup in finally blocks
   - Handle lock timeouts appropriately

4. Query Format Handling:
   - Support both raw SPARQL strings and dict queries
   - Maintain consistent return value structure
   - Handle query parsing errors appropriately
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from agents.core.base_agent import BaseAgent, AgentStatus
from agents.core.message_types import AgentMessage
from agents.core.capability_types import Capability, CapabilityType
from agents.core.agent_registry import AgentRegistry
from agents.core.agent_factory import AgentFactory
from agents.core.workflow_notifier import WorkflowNotifier
from kg.models.graph_manager import KnowledgeGraphManager
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF
import time
from typing import Dict, Any, List, Set, Optional
import threading
import logging
from loguru import logger
import sys
from tests.utils.test_helpers import EnhancedMockAgent, resource_manager, knowledge_graph, agent_registry
import psutil
import json
import copy
from unittest.mock import AsyncMock
from unittest.mock import create_autospec

@pytest.fixture(autouse=True)
def setup_logging():
    """Setup and teardown logging for tests."""
    # Remove default handler
    logger.remove()
    
    # Add test-specific handler
    logger.add(
        sys.stderr,
        format="{time} | {level} | {message}",
        level="DEBUG",
        backtrace=True,
        diagnose=True
    )
    
    yield
    
    # Cleanup logging
    logger.remove()

class TestRecoveryAgent(EnhancedMockAgent):
    """Test agent with recovery capabilities."""
    pass


    @property
    def role(self) -> Optional[str]:
        """Get the agent's role."""
        return self._role
        
    @role.setter
    def role(self, value: Optional[str]) -> None:
        """Set the agent's role and create a task to update the knowledge graph."""
        self._role = value
        if hasattr(self, 'knowledge_graph') and self.knowledge_graph is not None:
            # Create task and store it so it can be awaited later
            self._last_kg_update = asyncio.create_task(self._update_role_in_kg(value))

    async def _update_role_in_kg(self, value: Optional[str]) -> None:
        """Update role in knowledge graph."""
        try:
            async with self._lock:
                # Remove old role if it exists
                await self.knowledge_graph.remove_triple(
                    self.agent_uri(),
                    "http://example.org/agent/hasRole",
                    None
                )
                # Add new role if not None
                if value is not None:
                    await self.knowledge_graph.add_triple(
                        self.agent_uri(),
                        "http://example.org/agent/hasRole",
                        value
                    )
        except Exception as e:
            self.logger.error(f"Failed to update role in knowledge graph: {str(e)}")
            raise

    async def update_role(self, value: Optional[str]) -> None:
        """Async method to set role and wait for knowledge graph update."""
        self.role = value
        if hasattr(self, '_last_kg_update'):
            await self._last_kg_update

    def _parse_status(self, status_str: str) -> AgentStatus:
        """Parse status string from knowledge graph into AgentStatus enum.
        
        Args:
            status_str: The status string to parse
            
        Returns:
            AgentStatus: The parsed status
        """
        try:
            # Handle both enum values and raw strings
            if isinstance(status_str, str):
                # Strip any URI prefix and convert to lowercase
                status_str = status_str.split('/')[-1].lower()
                # Handle both raw enum values and string values
                try:
                    return AgentStatus(status_str)
                except ValueError:
                    # If direct conversion fails, try mapping common strings
                    status_map = {
                        'error': AgentStatus.ERROR,
                        'idle': AgentStatus.IDLE,
                        'busy': AgentStatus.BUSY,
                        'initializing': AgentStatus.INITIALIZING
                    }
                    if status_str in status_map:
                        return status_map[status_str]
                    self.logger.error(f"Unknown status value: {status_str}")
                    return AgentStatus.ERROR
            elif isinstance(status_str, AgentStatus):
                return status_str
            return AgentStatus.ERROR
        except (ValueError, AttributeError) as e:
            self.logger.error(f"Invalid status value: {status_str}")
            return AgentStatus.ERROR

    def _status_uri(self, status: AgentStatus) -> str:
        """Convert status to URI format.
        
        Args:
            status: The status to convert
            
        Returns:
            str: The status URI
        """
        if isinstance(status, str):
            # If we get a string, try to parse it first
            status = self._parse_status(status)
        return f"http://example.org/agent/{status.value}"

    @property
    def status(self) -> AgentStatus:
        """Get the agent's status."""
        return self._status

    @status.setter
    def status(self, value: AgentStatus) -> None:
        """Set the agent's status."""
        self._status = value

    async def update_status(self, new_status: AgentStatus) -> None:
        """Update agent status with proper locking.
        
        Args:
            new_status: The new status to set
        """
        try:
            old_status = self.status
            self.status = new_status
            self.logger.debug(f"Updated agent {self.agent_id} status from {old_status} to {new_status}")
            
            # Update knowledge graph
            try:
                await self.knowledge_graph.remove_triple(
                    self.agent_uri(),
                    "http://example.org/agent/hasStatus",
                    None
                )
                await self.knowledge_graph.add_triple(
                    self.agent_uri(),
                    "http://example.org/agent/hasStatus",
                    self._status_uri(new_status)
                )
            except Exception as e:
                self.logger.error(f"Failed to update status in knowledge graph: {str(e)}")
                # Revert status on KG failure
                self.status = old_status
                raise  # Re-raise to propagate failure
        except Exception as e:
            self.logger.error(f"Failed to update status: {str(e)}")
            raise  # Re-raise to propagate failure
        
    async def get_kg_status(self) -> AgentStatus:
        """Get current status from knowledge graph.
        
        Returns:
            AgentStatus: The current status
            
        Raises:
            Exception: If there is an error querying the knowledge graph
        """
        self.logger.debug("Entering get_kg_status")
        try:
            # Query knowledge graph - let exceptions propagate up
            self.logger.debug("Querying knowledge graph for status")
            kg_state = await self.query_knowledge_graph(f"""
                SELECT ?status WHERE {{
                    <{self.agent_uri()}> <http://example.org/agent/hasStatus> ?status .
                }}
            """)
            
            # Only handle the case where no state is found
            if not kg_state:
                self.logger.debug("No status found in knowledge graph, returning ERROR")
                return AgentStatus.ERROR
            
            self.logger.debug(f"Found status in knowledge graph: {kg_state[0]['status']}")
            try:
                return self._parse_status(kg_state[0]["status"])
            except (KeyError, ValueError) as e:
                self.logger.error(f"Error parsing status: {str(e)}")
                raise Exception("Invalid status format") from e
        except Exception as e:
            self.logger.error(f"Error in get_kg_status: {str(e)}")
            # Re-raise the original exception to maintain error propagation
            raise e
        
    async def initialize(self) -> None:
        """Initialize the agent with proper error handling."""
        try:
            if not self.knowledge_graph:
                self.knowledge_graph = KnowledgeGraphManager()
                self.knowledge_graph.initialize_namespaces()
            await super().initialize()
            try:
                await self._initialize_kg_state()
            except Exception as e:
                self.logger.error(f"Failed to initialize knowledge graph state: {str(e)}")
                self._is_initialized = False
                self.status = AgentStatus.ERROR
                raise Exception(f"Failed to initialize knowledge graph state: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to initialize agent {self.agent_id}: {str(e)}")
            self._is_initialized = False
            self.status = AgentStatus.ERROR
            raise

    async def query_knowledge_graph(self, query) -> List[Dict[str, str]]:
        """Query knowledge graph with proper SPARQL/dict routing.
        
        Updated on 2025-12-10: Fixed method routing for SPARQL vs dict queries.
        This override ensures SPARQL strings are routed to query_graph method
        while maintaining backward compatibility for dict queries.
        """
        try:
            self._knowledge_graph_queries.append(query)
            if self.knowledge_graph:
                # Route SPARQL strings to query_graph method (for mocking compatibility)
                if isinstance(query, str):
                    return await self.knowledge_graph.query_graph(query)
                else:
                    # Route dict queries to query method (backward compatibility)
                    return await self.knowledge_graph.query(query)
            return []
        except Exception as e:
            self.logger.error(f"Failed to query knowledge graph: {str(e)}")
            raise
            
    async def _update_recovery_metrics(self, strategy: str, success: bool, duration_ms: float) -> None:
        """Update recovery metrics with proper locking.
        
        Args:
            strategy: The recovery strategy used
            success: Whether the recovery was successful
            duration_ms: The duration of the recovery attempt in milliseconds
        """
        try:
            # Update strategy-specific metrics
            if strategy not in self._recovery_metrics["strategy_metrics"]:
                self._recovery_metrics["strategy_metrics"][strategy] = {
                    "attempts": 0,
                    "successes": 0,
                    "failures": 0,
                    "avg_duration_ms": 0
                }
            
            strategy_metrics = self._recovery_metrics["strategy_metrics"][strategy]
            strategy_metrics["attempts"] += 1
            if success:
                strategy_metrics["successes"] += 1
            else:
                strategy_metrics["failures"] += 1
            
            # Update average duration with proper handling of edge cases
            old_avg = strategy_metrics["avg_duration_ms"]
            old_count = strategy_metrics["attempts"] - 1
            if old_count > 0:
                strategy_metrics["avg_duration_ms"] = (old_avg * old_count + duration_ms) / strategy_metrics["attempts"]
            else:
                strategy_metrics["avg_duration_ms"] = duration_ms
            
            # Update resource metrics with error handling
            try:
                process = psutil.Process()
                self._recovery_metrics["resource_metrics"]["memory_usage_mb"] = process.memory_info().rss / 1024 / 1024
                self._recovery_metrics["resource_metrics"]["cpu_usage_percent"] = process.cpu_percent()
            except Exception as e:
                self.logger.warning(f"Failed to update resource metrics: {str(e)}")
                # Don't fail the whole operation if resource metrics fail
            
            # Update knowledge graph with retries
            for attempt in range(3):  # Try up to 3 times
                try:
                    await self.knowledge_graph.remove_triple(
                        self.agent_uri(),
                        "http://example.org/agent/hasRecoveryMetrics",
                        None
                    )
                    await self.knowledge_graph.add_triple(
                        self.agent_uri(),
                        "http://example.org/agent/hasRecoveryMetrics",
                        json.dumps(self._recovery_metrics)
                    )
                    break  # Success, exit retry loop
                except Exception as e:
                    if attempt == 2:  # Last attempt failed
                        self.logger.error(f"Failed to update recovery metrics in KG after retries: {str(e)}")
                        raise
                    await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    
        except Exception as e:
            self.logger.error(f"Failed to update recovery metrics: {str(e)}")
            raise  # Re-raise to propagate failure

    async def _validate_state(self, context: str) -> bool:
        """Validate agent state consistency.
        
        Args:
            context: Context string for logging
            
        Returns:
            bool: True if state is valid, False otherwise
            
        Raises:
            Exception: If KG operations fail
        """
        try:
            # Query current state from KG with retries
            for attempt in range(3):  # Try up to 3 times
                try:
                    kg_state = await self.query_knowledge_graph(f"""
                        SELECT ?status ?role ?recovery_attempts ?metrics WHERE {{
                            <{self.agent_uri()}> <http://example.org/agent/hasStatus> ?status .
                            OPTIONAL {{ <{self.agent_uri()}> <http://example.org/agent/hasRole> ?role }}
                            OPTIONAL {{ <{self.agent_uri()}> <http://example.org/agent/hasRecoveryAttempts> ?recovery_attempts }}
                            OPTIONAL {{ <{self.agent_uri()}> <http://example.org/agent/hasRecoveryMetrics> ?metrics }}
                        }}
                    """)
                    break  # Success, exit retry loop
                except Exception as e:
                    if attempt == 2:  # Last attempt failed
                        self.logger.error(f"{context}: Failed to query knowledge graph after retries: {str(e)}")
                        raise
                    await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
            
            # Check if query returned results
            if not kg_state:
                self.logger.error(f"{context}: No state found in knowledge graph")
                return False
                
            # Validate status consistency
            kg_status = kg_state[0]["status"]
            expected_status = self._status_uri(self.status)
            if kg_status != expected_status:
                self.logger.error(f"{context}: Status mismatch - Internal: {self.status.value}, KG: {kg_status}")
                # Fix status mismatch
                await self.knowledge_graph.remove_triple(
                    self.agent_uri(),
                    "http://example.org/agent/hasStatus",
                    None
                )
                await self.knowledge_graph.add_triple(
                    self.agent_uri(),
                    "http://example.org/agent/hasStatus",
                    expected_status
                )
                self.logger.debug(f"Fixed status mismatch in KG: {expected_status}")
            
            # Validate recovery attempts consistency
            kg_attempts = kg_state[0].get("recovery_attempts")
            if kg_attempts is not None:
                try:
                    kg_attempts = int(kg_attempts)
                    if self._recovery_attempts != kg_attempts:
                        self.logger.error(f"{context}: Recovery attempts mismatch - Internal: {self._recovery_attempts}, KG: {kg_attempts}")
                        # Fix attempts mismatch
                        await self.knowledge_graph.remove_triple(
                            self.agent_uri(),
                            "http://example.org/agent/hasRecoveryAttempts",
                            None
                        )
                        await self.knowledge_graph.add_triple(
                            self.agent_uri(),
                            "http://example.org/agent/hasRecoveryAttempts",
                            str(self._recovery_attempts)
                        )
                        self.logger.debug(f"Fixed recovery attempts mismatch in KG: {self._recovery_attempts}")
                except (ValueError, TypeError) as e:
                    self.logger.error(f"{context}: Invalid recovery attempts value in KG: {kg_attempts}")
                    return False
            
            # Validate metrics consistency if present
            kg_metrics = kg_state[0].get("metrics")
            if kg_metrics:
                try:
                    kg_metrics_dict = json.loads(kg_metrics)
                    if kg_metrics_dict != self._recovery_metrics:
                        self.logger.error(f"{context}: Metrics mismatch detected")
                        # Fix metrics mismatch
                        await self.knowledge_graph.remove_triple(
                            self.agent_uri(),
                            "http://example.org/agent/hasRecoveryMetrics",
                            None
                        )
                        await self.knowledge_graph.add_triple(
                            self.agent_uri(),
                            "http://example.org/agent/hasRecoveryMetrics",
                            json.dumps(self._recovery_metrics)
                        )
                        self.logger.debug("Fixed metrics mismatch in KG")
                except json.JSONDecodeError:
                    self.logger.error(f"{context}: Invalid metrics JSON in KG")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"{context}: Failed to validate state: {str(e)}")
            raise  # Re-raise to propagate failure

    async def recover(self, strategy: str = None) -> bool:
        """Simulate recovery with configurable success."""
        start_time = time.time()
        strategy = strategy if strategy else self._recovery_strategy
        if not strategy:
            strategy = "default"
        
        try:
            # Check if already at max attempts
            if self._recovery_attempts >= self._max_recovery_attempts:
                self._recovery_metrics["total_attempts"] += 1
                self._recovery_metrics["failed_recoveries"] += 1
                await self.update_status(AgentStatus.ERROR)
                duration_ms = (time.time() - start_time) * 1000
                await self._update_recovery_metrics(strategy, False, duration_ms)
                return False

            # Update recovery metrics first
            self._recovery_attempts += 1
            self._recovery_metrics["total_attempts"] += 1
            
            # Update knowledge graph with recovery attempt
            await self.knowledge_graph.remove_triple(
                self.agent_uri(),
                "http://example.org/agent/hasRecoveryAttempts",
                None
            )
            await self.knowledge_graph.add_triple(
                self.agent_uri(),
                "http://example.org/agent/hasRecoveryAttempts",
                str(self._recovery_attempts)
            )

            # Validate pre-recovery state
            if not await self._validate_state("Pre-recovery"):
                self.logger.error("Pre-recovery validation failed")
                await self.update_status(AgentStatus.ERROR)
                self._recovery_metrics["failed_recoveries"] += 1
                duration_ms = (time.time() - start_time) * 1000
                await self._update_recovery_metrics(strategy, False, duration_ms)
                return False
                    
            # Attempt recovery
            if self._recovery_success:
                await self.update_status(AgentStatus.IDLE)
                self._recovery_metrics["successful_recoveries"] += 1
                duration_ms = (time.time() - start_time) * 1000
                await self._update_recovery_metrics(strategy, True, duration_ms)
                
                # Validate post-recovery state
                if not await self._validate_state("Post-recovery"):
                    self.logger.error("Post-recovery validation failed")
                    await self.update_status(AgentStatus.ERROR)
                    return False
                
                return True
            else:
                await self.update_status(AgentStatus.ERROR)
                self._recovery_metrics["failed_recoveries"] += 1
                duration_ms = (time.time() - start_time) * 1000
                await self._update_recovery_metrics(strategy, False, duration_ms)
                return False
                
        except asyncio.TimeoutError:
            self.logger.error("Recovery timed out")
            self._recovery_metrics["failed_recoveries"] += 1
            duration_ms = (time.time() - start_time) * 1000
            await self._update_recovery_metrics(strategy, False, duration_ms)
            await self.update_status(AgentStatus.ERROR)
            return False
        except Exception as e:
            self.logger.error(f"Recovery failed: {str(e)}")
            self._recovery_metrics["failed_recoveries"] += 1
            duration_ms = (time.time() - start_time) * 1000
            await self._update_recovery_metrics(strategy, False, duration_ms)
            await self.update_status(AgentStatus.ERROR)
            return False

    @property
    def recovery_success(self) -> bool:
        """Get whether recovery will succeed."""
        return self._recovery_success

    @recovery_success.setter
    def recovery_success(self, value: bool):
        """Set whether recovery will succeed."""
        self._recovery_success = value

    def set_recovery_success(self, success: bool):
        """Legacy method for backward compatibility."""
        self.recovery_success = success
        
    async def reset_pending_operations(self) -> None:
        """Reset any pending operations."""
        try:
            self._pending_operations = []
            self.logger.info("Reset pending operations")
        except Exception as e:
            self.logger.error(f"Failed to reset pending operations: {str(e)}")
            raise
        
    async def cleanup_resources(self) -> None:
        """Clean up agent resources."""
        try:
            self._resources = {}
            self.logger.info("Cleaned up resources")
        except Exception as e:
            self.logger.error(f"Failed to cleanup resources: {str(e)}")
            raise
        
    async def allocate_resources(self) -> None:
        """Allocate resources for the agent."""
        try:
            self._resources = {"memory": 100, "cpu": 50}
            self.logger.info("Allocated resources")
        except Exception as e:
            self.logger.error(f"Failed to allocate resources: {str(e)}")
            raise
        
    async def reset_communication(self) -> None:
        """Reset communication channels."""
        try:
            self._connections = {}
            self.logger.info("Reset communication channels")
        except Exception as e:
            self.logger.error(f"Failed to reset communication: {str(e)}")
            raise
        
    async def establish_connections(self) -> None:
        """Establish necessary connections."""
        try:
            self._connections = {"main": True, "backup": True}
            self.logger.info("Established connections")
        except Exception as e:
            self.logger.error(f"Failed to establish connections: {str(e)}")
            raise
        
    async def backup_state(self) -> None:
        """Backup agent state."""
        try:
            self._state_backup = {
                "status": self.status,
                "capabilities": await self.get_capabilities(),
                "config": self.config.copy() if hasattr(self, 'config') else None,
                "role": self.role,
                "recovery_metrics": copy.deepcopy(self._recovery_metrics)
            }
            self.logger.info("Backed up state")
        except Exception as e:
            self.logger.error(f"Failed to backup state: {str(e)}")
            raise
            
    async def restore_state(self) -> None:
        """Restore agent state from backup."""
        try:
            if self._state_backup:
                await self.update_status(self._state_backup["status"], use_existing_locks=True)
                for capability in self._state_backup["capabilities"]:
                    await self.add_capability(capability)
                if self._state_backup["config"]:
                    self.config = self._state_backup["config"].copy()
                if self._state_backup["role"]:
                    self.role = self._state_backup["role"]
                    await self.knowledge_graph.add_triple(
                        self.agent_uri(),
                        "http://example.org/agent/hasRole",
                        self.role
                    )
                if self._state_backup["recovery_metrics"]:
                    self._recovery_metrics = copy.deepcopy(self._state_backup["recovery_metrics"])
                self.logger.info("Restored state")
        except Exception as e:
            self.logger.error(f"Failed to restore state: {str(e)}")
            raise
            
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process a message with proper error handling."""
        try:
            async with asyncio.timeout(1.0):
                async with self._lock:
                    self._message_history.append(message)
                    return AgentMessage(
                        sender_id=self.agent_id,
                        recipient_id=message.sender_id,
                        content=self._default_response,
                        timestamp=message.timestamp,
                        message_type="response"
                    )
        except asyncio.TimeoutError:
            self.logger.error("Message processing timed out")
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "error", "error": "timeout"},
                timestamp=message.timestamp,
                message_type="error"
            )
        except Exception as e:
            self.logger.error(f"Failed to process message: {str(e)}")
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "error", "error": str(e)},
                timestamp=message.timestamp,
                message_type="error"
            )

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process a message with recovery logic."""
        try:
            self._recovery_attempts += 1
            self._recovery_metrics["total_attempts"] += 1

            if self._recovery_attempts > self._max_recovery_attempts:
                self._recovery_metrics["failed_recoveries"] += 1
                raise RuntimeError("Maximum recovery attempts exceeded")

            # Simulate processing with potential failure
            if self._recovery_attempts < self._max_recovery_attempts:
                self._recovery_metrics["successful_recoveries"] += 1
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    content=f"Processed message with recovery attempt {self._recovery_attempts}",
                    timestamp=message.timestamp,
                    message_type="response"
                )
            else:
                raise RuntimeError("Simulated failure")

        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            raise

    @property
    def recovery_attempts(self) -> int:
        """Get the number of recovery attempts."""
        return self._recovery_attempts

    @recovery_attempts.setter
    def recovery_attempts(self, value: int):
        """Set the number of recovery attempts."""
        self._recovery_attempts = value
        # Update knowledge graph with new value
        if hasattr(self, 'knowledge_graph') and self.knowledge_graph is not None:
            # Create task and store it so it can be awaited later
            self._last_kg_update = asyncio.create_task(self.knowledge_graph.add_triple(
                self.agent_uri(),
                "http://example.org/agent/hasRecoveryAttempts",
                str(value)
            ))

    @property
    def max_recovery_attempts(self) -> int:
        """Get the maximum number of recovery attempts."""
        return self._max_recovery_attempts

    @max_recovery_attempts.setter
    def max_recovery_attempts(self, value: int):
        """Set the maximum number of recovery attempts."""
        self._max_recovery_attempts = value

    def get_status(self) -> Dict[str, Any]:
        """Get the agent's status including recovery metrics."""
        status = super().get_status()
        status.update({
            "recovery_attempts": self._recovery_attempts,
            "max_recovery_attempts": self._max_recovery_attempts,
            "recovery_strategy": self._recovery_strategy,
            "recovery_metrics": self._recovery_metrics
        })
        return status

    async def cleanup(self) -> None:
        """Clean up agent resources."""
        try:
            # Wait for any pending KG updates with timeout
            if hasattr(self, '_last_kg_update'):
                try:
                    async with asyncio.timeout(5.0):  # 5 second timeout for cleanup
                        await self._last_kg_update
                except asyncio.TimeoutError:
                    self.logger.error("Timeout waiting for KG updates during cleanup")
                except Exception as e:
                    self.logger.error(f"Error waiting for last KG update: {str(e)}")
            
            # Clean up KG state first
            try:
                await self.knowledge_graph.remove_triple(self.agent_uri(), None, None)
            except Exception as e:
                self.logger.error(f"Failed to clean up KG state: {str(e)}")
                # Don't re-raise, continue with cleanup
            
            # Reset state
            self._role = None
            self._recovery_attempts = 0
            self._recovery_metrics = {
                "total_attempts": 0,
                "successful_recoveries": 0,
                "failed_recoveries": 0
            }
            
            # Clean up resources
            self._pending_operations = []
            self._resources = {}
            self._connections = {}
            self._state_backup = None
            
            self.logger.info("Cleaned up agent resources")
        except Exception as e:
            self.logger.error(f"Failed to cleanup agent resources: {str(e)}")
            # Don't re-raise, continue with cleanup
        finally:
            try:
                await super().cleanup()
            except Exception as e:
                self.logger.error(f"Error in parent cleanup: {str(e)}")
                # Don't re-raise, we've done our best to clean up

@pytest_asyncio.fixture
async def recovery_agent(knowledge_graph):
    """Create a test recovery agent."""
    agent = TestRecoveryAgent(
        agent_id="recovery_test_agent",
        agent_type="recovery_test",
        capabilities={
            Capability(CapabilityType.TASK_EXECUTION, "1.0"),
            Capability(CapabilityType.RECOVERY, "1.0")
        }
    )
    try:
        # Set knowledge graph
        agent.knowledge_graph = knowledge_graph
        assert agent.knowledge_graph is not None, "Knowledge graph not set"
        
        # Initialize agent
        await agent.initialize()
        assert agent._is_initialized, "Agent failed to initialize"
        
        # Clean any existing KG state
        await agent.knowledge_graph.remove_triple(agent.agent_uri(), None, None)
        
        # Set initial state
        agent.recovery_timeout = 15.0  # Increased timeout for tests
        agent._recovery_success = True  # Default to successful recovery
        agent._recovery_attempts = 0
        agent._recovery_metrics = {
            "total_attempts": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "strategy_metrics": {
                "timeout": {"attempts": 0, "successes": 0, "failures": 0, "avg_duration_ms": 0},
                "state_corruption": {"attempts": 0, "successes": 0, "failures": 0, "avg_duration_ms": 0},
                "default": {"attempts": 0, "successes": 0, "failures": 0, "avg_duration_ms": 0}
            },
            "resource_metrics": {
                "memory_usage_mb": 0,
                "cpu_usage_percent": 0,
                "lock_contention_count": 0
            }
        }
        
        # Initialize KG state
        await agent._initialize_kg_state()
        
        # Set initial status
        await agent.update_status(AgentStatus.IDLE)
        if hasattr(agent, '_last_kg_update'):
            await agent._last_kg_update
            
        yield agent
    finally:
        try:
            # Clean up KG state first
            await agent.knowledge_graph.remove_triple(agent.agent_uri(), None, None)
            # Then clean up agent
            await agent.cleanup()
        except Exception as e:
            logger.error(f"Failed to cleanup recovery agent: {str(e)}")
            raise

@pytest.mark.asyncio
async def test_agent_recovery(agent_registry):
    """Test basic agent recovery functionality."""
    capabilities = {Capability(CapabilityType.TASK_EXECUTION, version="1.0")}
    agent = TestRecoveryAgent("test_agent", "recovery_test", capabilities)
    agent.set_recovery_success(True)  # Ensure recovery succeeds
    
    try:
        async with asyncio.timeout(15.0):
            # Initialize agent
            await agent.initialize()
            assert agent._is_initialized, "Agent failed to initialize"
            
            # Register agent
            await agent_registry.register_agent(agent, capabilities)
            
            # Set initial state
            await agent.update_status(AgentStatus.ERROR)
            if hasattr(agent, '_last_kg_update'):
                await agent._last_kg_update
                
            # Verify initial state
            await verify_kg_state(agent, AgentStatus.ERROR, 0)
            
            # Test successful recovery
            success = await agent_registry.recover_agent("test_agent")
            assert success, "Recovery should succeed"
            
            # Verify final state
            await verify_kg_state(agent, AgentStatus.IDLE, 1)
            assert agent.status == AgentStatus.IDLE, "Agent should be in IDLE state after recovery"
            assert agent.recovery_attempts == 1, "Should record one recovery attempt"
            assert agent._recovery_metrics["total_attempts"] == 1, "Should record total attempts"
            assert agent._recovery_metrics["successful_recoveries"] == 1, "Should record successful recovery"
            assert agent._recovery_metrics["failed_recoveries"] == 0, "Should not record failed recoveries"
    except asyncio.TimeoutError:
        pytest.fail("Test timed out")
    except Exception as e:
        pytest.fail(f"Test failed with error: {str(e)}")
    finally:
        await agent.cleanup()

@pytest.mark.asyncio
async def test_agent_recovery_success(recovery_agent, agent_registry):
    """Test successful agent recovery."""
    try:
        async with asyncio.timeout(15.0):  # Increased timeout
            # Register agent with capabilities
            capabilities = {
                Capability(CapabilityType.TASK_EXECUTION, "1.0"),
                Capability(CapabilityType.RECOVERY, "1.0")
            }
            await agent_registry.register_agent(recovery_agent, capabilities)
            
            # Set agent to error state
            await recovery_agent.update_status(AgentStatus.ERROR)
            await agent_registry.update_agent_status(recovery_agent.agent_id, "error")
            
            # Attempt recovery
            success = await agent_registry.recover_agent(recovery_agent.agent_id)
            assert success, "Recovery should succeed"
            assert recovery_agent.status == AgentStatus.IDLE
            assert recovery_agent.recovery_attempts == 1
            
            # Verify knowledge graph state
            kg_status = await recovery_agent.get_kg_status()
            assert kg_status == AgentStatus.IDLE
            
            # Verify recovery attempts
            kg_state = await recovery_agent.query_knowledge_graph(f"""
                SELECT ?recovery_attempts WHERE {{
                    <{recovery_agent.agent_uri()}> <http://example.org/agent/hasRecoveryAttempts> ?recovery_attempts .
                }}
            """)
            assert kg_state
            assert int(kg_state[0]["recovery_attempts"]) == 1
    except asyncio.TimeoutError:
        pytest.fail("Test timed out after 15 seconds")
    finally:
        await recovery_agent.cleanup()

@pytest.mark.asyncio
async def test_agent_recovery_failure(recovery_agent, agent_registry):
    """Test failed agent recovery."""
    try:
        async with asyncio.timeout(15.0):  # Increased timeout
            # Register agent with capabilities
            capabilities = {
                Capability(CapabilityType.TASK_EXECUTION, "1.0"),
                Capability(CapabilityType.RECOVERY, "1.0")
            }
            await agent_registry.register_agent(recovery_agent, capabilities)
            
            # Set agent to error state and configure recovery to fail
            await recovery_agent.update_status(AgentStatus.ERROR)
            recovery_agent.set_recovery_success(False)
            await agent_registry.update_agent_status(recovery_agent.agent_id, "error")
            
            # Attempt recovery
            success = await agent_registry.recover_agent(recovery_agent.agent_id)
            assert not success
            assert recovery_agent.status == AgentStatus.ERROR
            assert recovery_agent.recovery_attempts == 1
            
            # Verify knowledge graph state
            kg_status = await recovery_agent.get_kg_status()
            assert kg_status == AgentStatus.ERROR
            
            # Verify recovery attempts
            kg_state = await recovery_agent.query_knowledge_graph(f"""
                SELECT ?recovery_attempts WHERE {{
                    <{recovery_agent.agent_uri()}> <http://example.org/agent/hasRecoveryAttempts> ?recovery_attempts .
                }}
            """)
            assert kg_state
            assert int(kg_state[0]["recovery_attempts"]) == 1
    except asyncio.TimeoutError:
        pytest.fail("Test timed out after 15 seconds")
    finally:
        await recovery_agent.cleanup()

@pytest.mark.asyncio
async def test_max_recovery_attempts(agent_registry):
    """Test that recovery stops after maximum attempts."""
    capabilities = {Capability(CapabilityType.TASK_EXECUTION, version="1.0")}
    agent = TestRecoveryAgent("test_agent", "recovery_test", capabilities)

    try:
        # Initialize agent
        await agent.initialize()
        assert agent._is_initialized, "Agent failed to initialize"

        # Configure agent for failure
        agent._recovery_attempts = 3  # Set to max attempts
        agent.set_recovery_success(False)  # Make recovery fail

        # Register agent
        await agent_registry.register_agent(agent, capabilities)

        # Set initial state
        await agent.update_status(AgentStatus.ERROR)
        await agent.knowledge_graph.add_triple(
            agent.agent_uri(),
            "http://example.org/agent/hasStatus",
            agent._status_uri(AgentStatus.ERROR)
        )
        await agent.knowledge_graph.add_triple(
            agent.agent_uri(),
            "http://example.org/agent/hasRecoveryAttempts",
            str(agent._recovery_attempts)  # Set initial recovery attempts
        )

        # Attempt recovery with timeout
        try:
            async with asyncio.timeout(5.0):  # Shorter timeout for recovery
                success = await agent_registry.recover_agent("test_agent")
                assert not success, "Recovery should fail at max attempts"
                assert agent.status == AgentStatus.ERROR, "Agent should remain in ERROR state"
                assert agent._recovery_attempts == 3, "Should not increment beyond max attempts"

                # Verify knowledge graph state
                kg_state = await agent.query_knowledge_graph(f"""
                    SELECT ?status ?recovery_attempts WHERE {{
                        <{agent.agent_uri()}> <http://example.org/agent/hasStatus> ?status ;
                                             <http://example.org/agent/hasRecoveryAttempts> ?recovery_attempts .
                    }}
                """)
                assert kg_state, "Knowledge graph state should exist"
                assert kg_state[0]["status"] == agent._status_uri(AgentStatus.ERROR), "Status should be ERROR in knowledge graph"
                assert int(kg_state[0]["recovery_attempts"]) == 3, "Should record max attempts in knowledge graph"

                # Verify metrics
                assert agent._recovery_metrics["total_attempts"] == 1, "Should record total attempts"
                assert agent._recovery_metrics["successful_recoveries"] == 0, "Should not record successful recoveries"
                assert agent._recovery_metrics["failed_recoveries"] == 1, "Should record failed recovery"
        except asyncio.TimeoutError:
            pytest.fail("Recovery operation timed out")
    except Exception as e:
        pytest.fail(f"Test failed with error: {str(e)}")
    finally:
        await agent.cleanup()

@pytest_asyncio.fixture(scope="function")
async def setup_recovery_test():
    """Set up the test environment for agent recovery tests."""
    # Create new event loop for this test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    registry = AgentRegistry()
    kg = KnowledgeGraphManager()
    factory = AgentFactory()
    notifier = WorkflowNotifier()
    
    try:
        # Initialize components
        await notifier.initialize()
        await registry.initialize()
        await factory.initialize()
        await kg.initialize()
        await registry.register_agent_template(TestRecoveryAgent)
        
        yield registry, kg, factory, notifier
    finally:
        # Cleanup in reverse order
        await registry.cleanup()
        await factory.cleanup()
        await kg.cleanup()
        await notifier.cleanup()
        
        # Clean up event loop
        loop.close()

@pytest_asyncio.fixture(scope="function")
async def agent_registry():
    """Create an AgentRegistry instance for testing."""
    registry = AgentRegistry()
    await registry.initialize()
    yield registry
    try:
        # Clean up resources
        await registry.cleanup()
        await registry.shutdown()
    except Exception as e:
        pytest.fail(f"Error during registry cleanup: {e}")

@pytest.mark.asyncio
async def test_role_recovery(recovery_agent, agent_registry):
    """Test role recovery."""
    try:
        # Register agent with capabilities
        capabilities = {
            Capability(CapabilityType.TASK_EXECUTION, "1.0"),
            Capability(CapabilityType.RECOVERY, "1.0")
        }
        await agent_registry.register_agent(recovery_agent, capabilities)

        # Set agent role and state
        await recovery_agent.update_role("test_role")
        # Wait for role update to complete
        if hasattr(recovery_agent, '_last_kg_update'):
            await recovery_agent._last_kg_update

        # Update status
        await recovery_agent.update_status(AgentStatus.ERROR)
        # Wait for status update to complete
        if hasattr(recovery_agent, '_last_kg_update'):
            await recovery_agent._last_kg_update

        # Verify initial state
        kg_state = await recovery_agent.query_knowledge_graph(f"""
            SELECT ?status ?role WHERE {{
                <{recovery_agent.agent_uri()}> <http://example.org/agent/hasStatus> ?status ;
                                             <http://example.org/agent/hasRole> ?role .
            }}
        """)
        assert kg_state, "Initial state not found in knowledge graph"
        expected_status_uri = f"http://example.org/agent/{AgentStatus.ERROR.value}"
        assert kg_state[0]["status"] == expected_status_uri, "Status not set correctly"
        assert kg_state[0]["role"] == "test_role", "Role not set correctly"

        # Attempt recovery with timeout
        try:
            async with asyncio.timeout(5.0):  # Shorter timeout for recovery
                success = await agent_registry.recover_agent(recovery_agent.agent_id)
                assert success, "Recovery should succeed"
                assert recovery_agent.status == AgentStatus.IDLE, "Status should be IDLE after recovery"
        except asyncio.TimeoutError:
            pytest.fail("Recovery operation timed out")

        # Verify role persisted through recovery
        kg_state = await recovery_agent.query_knowledge_graph(f"""
            SELECT ?status ?role WHERE {{
                <{recovery_agent.agent_uri()}> <http://example.org/agent/hasStatus> ?status ;
                                             <http://example.org/agent/hasRole> ?role .
            }}
        """)
        assert kg_state, "Post-recovery state not found in knowledge graph"
        expected_status_uri = f"http://example.org/agent/{AgentStatus.IDLE.value}"
        assert kg_state[0]["status"] == expected_status_uri, "Status not updated correctly"
        assert kg_state[0]["role"] == "test_role", "Role not preserved during recovery"
    except Exception as e:
        pytest.fail(f"Test failed with error: {str(e)}")
    finally:
        await recovery_agent.cleanup()

@pytest.mark.asyncio
async def test_knowledge_graph_integration(recovery_agent, agent_registry):
    """Test knowledge graph integration."""
    try:
        async with asyncio.timeout(15.0):  # Increased timeout
            # Register agent with capabilities
            capabilities = {
                Capability(CapabilityType.TASK_EXECUTION, "1.0"),
                Capability(CapabilityType.RECOVERY, "1.0")
            }
            await agent_registry.register_agent(recovery_agent, capabilities)

            # Set agent to error state
            recovery_agent.status = AgentStatus.ERROR
            await recovery_agent.knowledge_graph.add_triple(
                recovery_agent.agent_uri(),
                "http://example.org/agent/hasStatus",
                f"http://example.org/agent/{AgentStatus.ERROR.value}"
            )

            # Attempt recovery
            success = await agent_registry.recover_agent(recovery_agent.agent_id)
            assert success, "Recovery should succeed"
            assert recovery_agent.status == AgentStatus.IDLE, "Status should be IDLE after recovery"

            # Verify final state
            kg_state = await recovery_agent.query_knowledge_graph(f"""
                SELECT ?status WHERE {{
                    <{recovery_agent.agent_uri()}> <http://example.org/agent/hasStatus> ?status .
                }}
            """)
            assert kg_state, "Knowledge graph state not found"
            expected_status_uri = f"http://example.org/agent/{AgentStatus.IDLE.value}"
            assert kg_state[0]["status"] == expected_status_uri, f"Expected status {expected_status_uri}, got {kg_state[0]['status']}"
    except asyncio.TimeoutError:
        pytest.fail("Test timed out")
    except Exception as e:
        pytest.fail(f"Test failed with error: {str(e)}")
    finally:
        await recovery_agent.cleanup()

@pytest.mark.asyncio
async def test_recovery_strategy_metrics(recovery_agent, agent_registry):
    """Test recovery strategy metrics collection."""
    try:
        async with asyncio.timeout(15.0):  # Increased timeout
            # Register agent with capabilities
            capabilities = {
                Capability(CapabilityType.TASK_EXECUTION, "1.0"),
                Capability(CapabilityType.RECOVERY, "1.0")
            }
            await agent_registry.register_agent(recovery_agent, capabilities)

            # Set agent to error state
            await recovery_agent.update_status(AgentStatus.ERROR)
            recovery_agent._recovery_success = True  # Ensure recovery succeeds
            
            # Wait for status update to complete
            if hasattr(recovery_agent, '_last_kg_update'):
                await recovery_agent._last_kg_update
            
            # Verify initial state
            kg_state = await recovery_agent.query_knowledge_graph(f"""
                SELECT ?status ?recovery_attempts WHERE {{
                    <{recovery_agent.agent_uri()}> <http://example.org/agent/hasStatus> ?status ;
                                                 <http://example.org/agent/hasRecoveryAttempts> ?recovery_attempts .
                }}
            """)
            assert kg_state, "Initial state not found in knowledge graph"
            expected_status_uri = f"http://example.org/agent/{AgentStatus.ERROR.value}"
            assert kg_state[0]["status"] == expected_status_uri, "Status not set correctly"
            assert kg_state[0]["recovery_attempts"] == "0", "Recovery attempts not initialized correctly"

            # Attempt recovery multiple times
            for i in range(3):
                success = await agent_registry.recover_agent(recovery_agent.agent_id)
                assert success, f"Recovery attempt {i+1} should succeed"
                assert recovery_agent.status == AgentStatus.IDLE, f"Agent should be in IDLE state after recovery attempt {i+1}"
                assert recovery_agent.recovery_attempts == i+1, f"Should record {i+1} recovery attempts"
                assert recovery_agent._recovery_metrics["total_attempts"] == i+1, f"Should record {i+1} total attempts"
                assert recovery_agent._recovery_metrics["successful_recoveries"] == i+1, f"Should record {i+1} successful recoveries"
                assert recovery_agent._recovery_metrics["failed_recoveries"] == 0, "Should not record failed recoveries"

                # Verify knowledge graph state
                kg_state = await recovery_agent.query_knowledge_graph(f"""
                    SELECT ?status ?recovery_attempts WHERE {{
                        <{recovery_agent.agent_uri()}> <http://example.org/agent/hasStatus> ?status ;
                                                     <http://example.org/agent/hasRecoveryAttempts> ?recovery_attempts .
                    }}
                """)
                assert kg_state, f"Knowledge graph state should exist for attempt {i+1}"
                expected_status_uri = f"http://example.org/agent/{AgentStatus.IDLE.value}"
                assert kg_state[0]["status"] == expected_status_uri, f"Status should be IDLE in knowledge graph for attempt {i+1}"
                assert int(kg_state[0]["recovery_attempts"]) == i+1, f"Should record {i+1} recovery attempts in knowledge graph"

                # Reset agent to error state for next attempt
                if i < 2:  # Don't reset after last attempt
                    await recovery_agent.update_status(AgentStatus.ERROR)
                    # Wait for status update to complete
                    if hasattr(recovery_agent, '_last_kg_update'):
                        await recovery_agent._last_kg_update
                    
                    # Verify error state
                    kg_state = await recovery_agent.query_knowledge_graph(f"""
                        SELECT ?status WHERE {{
                            <{recovery_agent.agent_uri()}> <http://example.org/agent/hasStatus> ?status .
                        }}
                    """)
                    assert kg_state, "Error state not found in knowledge graph"
                    expected_status_uri = f"http://example.org/agent/{AgentStatus.ERROR.value}"
                    assert kg_state[0]["status"] == expected_status_uri, "Status not set to ERROR correctly"
    except asyncio.TimeoutError:
        pytest.fail("Test timed out")
    except Exception as e:
        pytest.fail(f"Test failed with error: {str(e)}")
    finally:
        await recovery_agent.cleanup()

@pytest_asyncio.fixture
async def knowledge_graph():
    """Create a fresh knowledge graph for each test."""
    kg = KnowledgeGraphManager()
    try:
        await kg.initialize()
        assert await kg.is_initialized(), "Knowledge graph failed to initialize"
        yield kg
    finally:
        try:
            await kg.cleanup()
            await kg.shutdown()
        except Exception as e:
            logger.error(f"Failed to cleanup knowledge graph: {str(e)}")
            raise 

async def verify_kg_state(agent, expected_status, expected_attempts):
    """Verify agent state in knowledge graph.
    
    Updated on 2035-07-21: Added timeout handling and improved error messages."""
    try:
        # Wait for any pending updates with timeout
        if hasattr(agent, '_last_kg_update'):
            try:
                async with asyncio.timeout(5.0):  # 5 second timeout for verification
                    await agent._last_kg_update
            except asyncio.TimeoutError:
                pytest.fail("Timeout waiting for KG updates during verification")
            except Exception as e:
                pytest.fail(f"Error waiting for KG updates: {str(e)}")
            
        kg_state = await agent.query_knowledge_graph(f"""
            SELECT ?status ?attempts WHERE {{
                <{agent.agent_uri()}> <http://example.org/agent/hasStatus> ?status ;
                                     <http://example.org/agent/hasRecoveryAttempts> ?attempts .
            }}
        """)
        assert kg_state, "Knowledge graph state not found"
        expected_status_uri = f"http://example.org/agent/{expected_status.value}"
        assert kg_state[0]["status"] == expected_status_uri, f"Expected status {expected_status_uri}, got {kg_state[0]['status']}"
        assert int(kg_state[0]["attempts"]) == expected_attempts, f"Expected {expected_attempts} attempts, got {kg_state[0]['attempts']}"
    except Exception as e:
        pytest.fail(f"Failed to verify knowledge graph state: {str(e)}")

@pytest.mark.asyncio
async def test_kg_initialization_failure(agent_registry):
    """Test agent behavior when knowledge graph initialization fails."""
    capabilities = {Capability(CapabilityType.TASK_EXECUTION, version="1.0")}
    agent = TestRecoveryAgent("test_agent", "recovery_test", capabilities)
    
    # Mock KG to fail initialization
    mock_kg = AsyncMock(spec=KnowledgeGraphManager)
    mock_kg.initialize.side_effect = Exception("KG initialization failed")
    agent.knowledge_graph = mock_kg
    
    try:
        # Attempt initialization
        with pytest.raises(Exception) as exc_info:
            await agent.initialize()
        assert "KG initialization failed" in str(exc_info.value)
        assert not agent._is_initialized
        
        # Verify agent state
        assert agent.status == AgentStatus.ERROR
        assert agent._recovery_attempts == 0
        
        # Attempt recovery should fail
        success = await agent_registry.recover_agent("test_agent")
        assert not success, "Recovery should fail when KG is not initialized"
        
    finally:
        await agent.cleanup()

@pytest.mark.asyncio
async def test_kg_query_failure(agent_registry):
    """Test agent behavior when knowledge graph queries fail."""
    capabilities = {Capability(CapabilityType.TASK_EXECUTION, version="1.0")}
    agent = TestRecoveryAgent("test_agent", "recovery_test", capabilities)
    
    # Mock KG with SPARQL queries failing but basic operations succeeding
    mock_kg = AsyncMock(spec=KnowledgeGraphManager)
    mock_kg.query_graph.side_effect = Exception("Query failed")  # SPARQL queries fail
    mock_kg.add_triple = AsyncMock(return_value=None)  # Basic operations succeed
    mock_kg.remove_triple = AsyncMock(return_value=None)  # Basic operations succeed  
    mock_kg.initialize = AsyncMock(return_value=True)  # Mock initialize to succeed
    mock_kg.get_triple_count = AsyncMock(return_value=0)  # Add mock for get_triple_count
    mock_kg.get_query_metrics = AsyncMock(return_value={})  # Add mock for get_query_metrics
    mock_kg.get_cache_stats = AsyncMock(return_value={})  # Add mock for get_cache_stats
    mock_kg.validate_graph = AsyncMock(return_value=True)  # Add mock for validate_graph
    agent.knowledge_graph = mock_kg
    
    try:
        # Initialize agent (should succeed since basic operations work)
        await agent.initialize()
        assert agent._is_initialized
        
        # Register agent (should succeed)
        await agent_registry.register_agent(agent, capabilities)
        
        # Set agent to error state to trigger recovery
        agent.status = AgentStatus.ERROR
        
        # Attempt recovery should fail due to SPARQL query failures
        success = await agent_registry.recover_agent("test_agent")
        assert not success, "Recovery should fail when KG queries fail"
        
        # Verify mock was called - SPARQL queries should have been attempted during recovery
        mock_kg.query_graph.assert_called(), "KG query should have been attempted"
        assert mock_kg.query_graph.call_count >= 1, "KG query should have been called at least once"
    finally:
        try:
            await agent.cleanup()
        except Exception as e:
            # Log but don't fail the test on cleanup errors
            logger.error(f"Error during cleanup: {str(e)}")

@pytest.mark.asyncio
async def test_kg_update_failure(agent_registry):
    """Test agent behavior when knowledge graph updates fail."""
    capabilities = {Capability(CapabilityType.TASK_EXECUTION, version="1.0")}
    agent = TestRecoveryAgent("test_agent", "recovery_test", capabilities)
    
    # Mock KG with failing updates
    mock_kg = AsyncMock(spec=KnowledgeGraphManager)
    mock_kg.add_triple.side_effect = Exception("Update failed")
    agent.knowledge_graph = mock_kg
    
    try:
        # Initialize agent should fail
        with pytest.raises(Exception) as exc_info:
            await agent.initialize()
        assert "Update failed" in str(exc_info.value)
        
        # Verify error state
        assert not agent._is_initialized
        assert agent.status == AgentStatus.ERROR
        
    finally:
        await agent.cleanup()

@pytest.mark.asyncio
async def test_kg_transaction_rollback(agent_registry):
    """Test agent behavior during knowledge graph transaction rollback."""
    capabilities = {Capability(CapabilityType.TASK_EXECUTION, version="1.0")}
    agent = TestRecoveryAgent("test_agent", "recovery_test", capabilities)
    
    # Mock KG with transaction failure
    mock_kg = AsyncMock(spec=KnowledgeGraphManager)
    update_count = 0
    
    async def mock_add_triple(*args, **kwargs):
        nonlocal update_count
        update_count += 1
        if update_count > 1:  # Fail after first update
            raise Exception("Transaction failed")
        return None
    
    mock_kg.add_triple.side_effect = mock_add_triple
    agent.knowledge_graph = mock_kg
    
    try:
        # Initialize agent should fail
        with pytest.raises(Exception) as exc_info:
            await agent.initialize()
        assert "Transaction failed" in str(exc_info.value)
        
        # Verify error state
        assert not agent._is_initialized
        assert agent.status == AgentStatus.ERROR
        assert update_count == 2  # First update succeeds, second fails
        
    finally:
        await agent.cleanup()

@pytest.mark.asyncio
async def test_kg_cache_invalidation(agent_registry):
    """Test agent behavior during cache invalidation failures."""
    capabilities = {Capability(CapabilityType.TASK_EXECUTION, version="1.0")}
    agent = TestRecoveryAgent("test_agent", "recovery_test", capabilities)
    
    # Mock KG with cache invalidation issues
    mock_kg = AsyncMock(spec=KnowledgeGraphManager)
    
    # Set up mock behavior
    query_count = 0
    
    async def mock_query_graph(sparql_query: str) -> List[Dict[str, str]]:
        nonlocal query_count
        query_count += 1
        
        # First query succeeds
        if query_count == 1:
            return [{"status": AgentStatus.ERROR.value}]
        
        # Second query fails with cache invalid error
        if query_count == 2:
            raise Exception("Cache invalid")
        
        return []
    
    # Set up mock with proper async behavior
    mock_kg.query_graph = mock_query_graph
    mock_kg.add_triple = AsyncMock()
    mock_kg.initialize = AsyncMock(return_value=None)
    mock_kg.is_initialized = AsyncMock(return_value=True)
    mock_kg.query = AsyncMock(side_effect=mock_query_graph)  # Add mock for query method
    agent.knowledge_graph = mock_kg
    
    try:
        # Initialize agent
        await agent.initialize()
        assert agent._is_initialized
        
        # Set initial status
        await agent.update_status(AgentStatus.ERROR)
        
        # First query works
        status = await agent.get_kg_status()
        assert status == AgentStatus.ERROR
        
        # Next query should fail with cache invalid error
        with pytest.raises(Exception, match="Cache invalid"):
            await agent.get_kg_status()
            
        # Verify agent state after cache invalidation
        assert agent.status == AgentStatus.ERROR, "Agent should remain in ERROR state after cache invalidation"
        
    finally:
        await agent.cleanup()

# Add test helper for verifying cleanup
async def verify_cleanup(agent):
    """Verify agent cleanup was successful.
    
    Updated on 2035-07-21: Added timeout handling, KG state verification, and improved error messages."""
    try:
        # Wait for any pending updates with timeout
        if hasattr(agent, '_last_kg_update'):
            try:
                async with asyncio.timeout(5.0):  # 5 second timeout for cleanup verification
                    await agent._last_kg_update
            except asyncio.TimeoutError:
                pytest.fail("Timeout waiting for KG updates during cleanup verification")
            except Exception as e:
                pytest.fail(f"Error waiting for KG updates: {str(e)}")
        
        # Verify internal state reset
        assert agent._recovery_attempts == 0, "Recovery attempts not reset"
        assert agent._recovery_metrics == {
            "total_attempts": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0
        }, "Recovery metrics not reset"
        assert agent._pending_operations == [], "Pending operations not cleared"
        assert agent._resources == {}, "Resources not cleared"
        assert agent._connections == {}, "Connections not cleared"
        assert agent._state_backup is None, "State backup not cleared"
        
        # Verify KG state cleared
        if agent.knowledge_graph:
            kg_state = await agent.query_knowledge_graph(f"""
                SELECT ?status ?recovery_attempts WHERE {{
                    <{agent.agent_uri()}> ?p ?o .
                }}
            """)
            assert not kg_state, "Knowledge graph state not fully cleared"
    except Exception as e:
        pytest.fail(f"Cleanup verification failed: {str(e)}") 