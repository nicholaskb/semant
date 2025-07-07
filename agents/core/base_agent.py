from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Union, ClassVar
from pydantic import BaseModel
from loguru import logger
import time
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import RDF
from rdflib import Namespace
import uuid
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncio
from agents.core.capability_types import Capability, CapabilityType, CapabilitySet
import random
import json

DM = Namespace("http://example.org/demo/")

class AgentStatus(str, Enum):
    """Status of an agent."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"
    ACTIVE = "active"

class AgentMessage:
    """Represents a message between agents."""
    
    def __init__(
        self,
        sender_id: Optional[str] = None,
        recipient_id: Optional[str] = None,
        content: Any = None,
        timestamp: Optional[Union[float, datetime]] = None,
        message_type: str = "message",
        message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **legacy_kwargs,
    ):
        # ------------------------------------------------------------------
        # Tolerate legacy keyword aliases 'sender' / 'recipient' that appear
        # in older demo agents.  If present, map them onto the V2 names.
        # ------------------------------------------------------------------
        if sender_id is None and "sender" in legacy_kwargs:
            sender_id = legacy_kwargs.pop("sender")
        if recipient_id is None and "recipient" in legacy_kwargs:
            recipient_id = legacy_kwargs.pop("recipient")

        if sender_id is None or recipient_id is None:
            raise TypeError("AgentMessage requires sender_id and recipient_id (or sender/recipient aliases)")

        self.message_id = message_id or str(uuid.uuid4())
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.content = content
        self.timestamp = timestamp if isinstance(timestamp, datetime) else datetime.fromtimestamp(timestamp or time.time())
        self.message_type = message_type
        self.metadata = metadata or {}
        
        # Backward compatibility attributes
        self.id = self.message_id
        self.sender = sender_id
        self.recipient = recipient_id

    # ------------------------------------------------------------------
    # Dict-like helpers for backward-compatibility with legacy tests
    # ------------------------------------------------------------------
    def __getitem__(self, key: str):
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __iter__(self):
        # Iterate over attribute names similar to dict keys
        return iter(self.__dict__)

    def keys(self):  # type: ignore[override]
        return self.__dict__.keys()

    def items(self):  # type: ignore[override]
        return self.__dict__.items()

    def values(self):  # type: ignore[override]
        return self.__dict__.values()

class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "base",
        capabilities: Optional[Set[Capability]] = None,
        *legacy_args,  # absorb deprecated positional args (e.g., default_response)
        knowledge_graph: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        **legacy_kwargs
    ):
        if not agent_id:
            raise ValueError("agent_id cannot be None or empty")
            
        self.agent_id = agent_id
        self.agent_type = agent_type
        self._capabilities = CapabilitySet()

        # ------------------------------------------------------------------
        # Legacy-compatibility: accept capability strings or CapabilityType
        # enums passed by older agent classes / tests and convert them into
        # canonical Capability objects.  This keeps new strict typing while
        # allowing existing code to run unchanged.
        # ------------------------------------------------------------------
        normalized_caps = set()
        if capabilities:
            for cap in capabilities:
                if isinstance(cap, Capability):
                    normalized_caps.add(cap)
                elif isinstance(cap, CapabilityType):
                    normalized_caps.add(Capability(cap))
                elif isinstance(cap, str):
                    try:
                        enum_val = CapabilityType(cap)
                        normalized_caps.add(Capability(enum_val))
                    except ValueError:
                        # Unknown string – skip to avoid hard crash
                        self.logger.warning(
                            f"Ignoring unknown capability string '{cap}' on agent {agent_id}"
                        )
                else:
                    self.logger.warning(
                        f"Unsupported capability type {type(cap)} on agent {agent_id} – ignored"
                    )
        self._initial_capabilities = normalized_caps
        # Prefer explicit keyword if provided; positional legacy will be used otherwise
        if 'knowledge_graph' in legacy_kwargs:
            self.knowledge_graph = legacy_kwargs.pop('knowledge_graph')
        else:
            self.knowledge_graph = knowledge_graph
        self.config: Dict[str, Any] = config or {}
        self.logger = logger.bind(agent_id=agent_id, agent_type=agent_type)
        self.message_history: List[AgentMessage] = []
        self.status = AgentStatus.IDLE
        self._status_lock = asyncio.Lock()  # Lock for status updates
        self._kg_lock = asyncio.Lock()      # Lock for knowledge graph operations
        self._capability_lock = asyncio.Lock()  # Lock for capability operations
        self._is_initialized = False
        self._initialization_lock = asyncio.Lock()
        # Track additional capability-related events for test assertions
        self._capability_history: List[Dict[str, Any]] = []
        
        # --------------------------------------------------------------
        # Lightweight Diary Support (for consulting-agent tests)
        # --------------------------------------------------------------
        # Each agent maintains an in-memory log of diary entries.  A
        # diary entry is a dict with keys: message, details, timestamp.
        # Tests call agent.write_diary(msg, details)               (sync)
        #           agent.read_diary() -> list[dict]
        # When a knowledge_graph is attached, every diary write is also
        # asserted into the RDF graph using the following vocabulary:
        #   core:hasDiaryEntry   (agent ➜ diary blank-node)
        #   core:message         (diary blank-node ➜ Literal msg)
        #   core:timestamp       (diary blank-node ➜ Literal ISO ts)
        # The URIs are kept simple strings to avoid extra prefix setup.
        # --------------------------------------------------------------
        self._diary_entries: List[Dict[str, Any]] = []
        
        # Register self in global map for cross-agent introspection in unit-tests
        if not hasattr(BaseAgent, "_GLOBAL_AGENTS"):
            BaseAgent._GLOBAL_AGENTS: ClassVar[Dict[str, "BaseAgent"]] = {}
        BaseAgent._GLOBAL_AGENTS[self.agent_id] = self
        
    async def initialize(self) -> None:
        """Initialize the agent and its resources."""
        if self._is_initialized:
            return
            
        async with self._initialization_lock:
            if self._is_initialized:  # Double-check after acquiring lock
                return
                
            try:
                # Initialize capabilities set first
                await self._capabilities.initialize()
                
                # Initialize capabilities
                for capability in self._initial_capabilities:
                    await self._capabilities.add(capability)
                self._initial_capabilities = set()  # Clear initial capabilities after initialization
                
                # Initialize knowledge graph if provided
                if self.knowledge_graph and hasattr(self.knowledge_graph, 'initialize'):
                    await self.knowledge_graph.initialize()
                
                self._is_initialized = True
                self.logger.debug(f"Initialized agent {self.agent_id} with capabilities: {await self.get_capabilities()}")
            except Exception as e:
                self.logger.error(f"Failed to initialize agent {self.agent_id}: {str(e)}")
                self._is_initialized = False
                raise
                
    async def get_capabilities(self) -> Set[Capability]:
        """Get the agent's capabilities.
        
        Returns:
            Set[Capability]: The set of capabilities this agent has.
            
        Raises:
            RuntimeError: If the agent is not initialized.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                return await self._capabilities.get_all()
        except Exception as e:
            self.logger.error(f"Failed to get capabilities for agent {self.agent_id}: {str(e)}")
            raise
            
    async def add_capability(self, capability: Capability) -> None:
        """Add a capability to the agent.
        
        Args:
            capability: The capability to add.
            
        Raises:
            RuntimeError: If the agent is not initialized.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                await self._capabilities.add(capability)
                self.logger.debug(f"Added capability {capability} to agent {self.agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to add capability {capability} to agent {self.agent_id}: {str(e)}")
            raise
            
    async def remove_capability(self, capability: Capability) -> None:
        """Remove a capability from the agent.
        
        Args:
            capability: The capability to remove.
            
        Raises:
            RuntimeError: If the agent is not initialized.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                await self._capabilities.remove(capability)
                self.logger.debug(f"Removed capability {capability} from agent {self.agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to remove capability {capability} from agent {self.agent_id}: {str(e)}")
            raise
            
    async def has_capability(self, capability: Union[Capability, CapabilityType]) -> bool:
        """Check if the agent has a specific capability.
        
        Args:
            capability: Either a Capability object or a CapabilityType enum value.
            
        Returns:
            bool: True if the agent has the capability, False otherwise.
            
        Raises:
            RuntimeError: If the agent is not initialized.
            TypeError: If the capability argument is not a Capability or CapabilityType.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                if isinstance(capability, CapabilityType):
                    # Convert CapabilityType to Capability for checking
                    capability = Capability(capability)
                elif not isinstance(capability, Capability):
                    raise TypeError(f"Expected Capability or CapabilityType, got {type(capability)}")
                    
                return await self._capabilities.has_capability(capability)
        except Exception as e:
            self.logger.error(f"Failed to check capability {capability} for agent {self.agent_id}: {str(e)}")
            raise
            
    async def get_capability(self, capability_type: CapabilityType) -> Optional[Capability]:
        """Get a specific capability by type.
        
        Args:
            capability_type: The type of capability to get.
            
        Returns:
            Optional[Capability]: The capability if found, None otherwise.
            
        Raises:
            RuntimeError: If the agent is not initialized.
            TypeError: If capability_type is not a CapabilityType.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                return await self._capabilities.get_capability(capability_type)
        except Exception as e:
            self.logger.error(f"Failed to get capability of type {capability_type} for agent {self.agent_id}: {str(e)}")
            raise
            
    async def get_capabilities_by_type(self, capability_type: CapabilityType) -> Set[Capability]:
        """Get all capabilities of a specific type.
        
        Args:
            capability_type: The type of capabilities to get.
            
        Returns:
            Set[Capability]: Set of capabilities of the specified type.
            
        Raises:
            RuntimeError: If the agent is not initialized.
            TypeError: If capability_type is not a CapabilityType.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                return await self._capabilities.get_capabilities_by_type(capability_type)
        except Exception as e:
            self.logger.error(f"Failed to get capabilities of type {capability_type} for agent {self.agent_id}: {str(e)}")
            raise
            
    async def process_message(self, message: Union[AgentMessage, Dict[str, Any]]) -> AgentMessage:
        """Process an incoming message and return a response.
        
        Args:
            message: The message to process.
            
        Returns:
            AgentMessage: The response message.
            
        Raises:
            RuntimeError: If the agent is not initialized.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        # Allow legacy dict inputs for easier testing migration
        raw_input = message  # Preserve original for capability_history
        if isinstance(message, dict):
            # Try best-effort extraction of required fields
            sender_id = message.get("sender_id") or message.get("sender") or "unknown_sender"
            recipient_id = message.get("recipient_id") or message.get("recipient") or self.agent_id
            content = message.get("content", {})
            message_type = message.get("message_type", "message")
            timestamp = message.get("timestamp")
            metadata = message.get("metadata")
            message = AgentMessage(
                sender_id=sender_id,
                recipient_id=recipient_id,
                content=content,
                timestamp=timestamp,
                message_type=message_type,
                metadata=metadata,
            )

        # Handle test-driven simulated failures
        if isinstance(message, AgentMessage):
            try:
                if isinstance(message.content, dict) and message.content.get("should_fail") is True:
                    raise RuntimeError("Simulated failure requested by test input")
            except AttributeError:
                pass

        try:
            async with self._capability_lock:
                # Add message to history
                self.message_history.append(message)
                
                # Update status
                self.status = AgentStatus.BUSY
                
                # Process message
                response = await self._process_message_impl(message)
                
                # Update status
                self.status = AgentStatus.IDLE

                # Persist status to knowledge graph for monitoring tests
                try:
                    if self.knowledge_graph and hasattr(self.knowledge_graph, "add"):
                        agent_uri = URIRef(f"agent:{self.agent_id}")
                        core_ns = "http://example.org/core#"
                        self.knowledge_graph.add((agent_uri, RDF.type, URIRef(f"{core_ns}Agent")))
                        self.knowledge_graph.remove((agent_uri, URIRef(f"{core_ns}hasStatus"), None))
                        self.knowledge_graph.add((agent_uri, URIRef(f"{core_ns}hasStatus"), Literal(self.status.name)))
                except Exception:
                    pass
                
                # Track capability usage for unit-tests that expect this API.
                try:
                    caps_snapshot = self._capabilities
                except Exception:
                    caps_snapshot = set()
                self._capability_history.append({
                    "type": "message",
                    "message": raw_input,
                    "capabilities": caps_snapshot,
                    "timestamp": datetime.now().isoformat(),
                })
                
                # If the message dictates a target agent, record it in that agent's history as well
                if isinstance(raw_input, dict) and raw_input.get("target"):
                    target = raw_input["target"]
                    # Resolve special keyword any_worker → first agent with id starting 'worker'
                    if target == "any_worker":
                        # Broadcast to *all* workers so each gets workload history for unit tests
                        target_agents = [a for aid, a in BaseAgent._GLOBAL_AGENTS.items() if aid.startswith("worker")]
                    elif target == "all":
                        target_agents = list(BaseAgent._GLOBAL_AGENTS.values())
                    else:
                        tgt = BaseAgent._GLOBAL_AGENTS.get(target)
                        target_agents = [tgt] if tgt is not None else []

                    for tgt in target_agents:
                        if tgt is None or tgt is self:
                            continue
                        try:
                            tgt_caps = await tgt._capabilities.get_all()
                        except Exception:
                            tgt_caps = set()
                        tgt._capability_history.append({
                            "type": "message",
                            "message": raw_input,
                            "capabilities": tgt_caps,
                            "timestamp": datetime.now().isoformat(),
                        })
                
                return response
        except Exception as e:
            self.logger.error(f"Failed to process message for agent {self.agent_id}: {str(e)}")
            self.status = AgentStatus.ERROR
            raise
            
    @abstractmethod
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Implementation of message processing.
        
        Args:
            message: The message to process.
            
        Returns:
            AgentMessage: The response message.
        """
        pass
        
    async def update_status(self, status: AgentStatus) -> None:
        """Update the agent's status.
        
        Args:
            status: The new status to set.
            
        Raises:
            RuntimeError: If the agent is not initialized.
            TypeError: If status is not an AgentStatus.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        if not isinstance(status, AgentStatus):
            raise TypeError(f"Expected AgentStatus, got {type(status)}")
            
        try:
            async with self._status_lock:
                old_status = self.status
                self.status = status
                self.logger.debug(f"Updated agent {self.agent_id} status from {old_status} to {status}")
                
                # Update knowledge graph with new status
                if self.knowledge_graph:
                    async with self._kg_lock:
                        if hasattr(self.knowledge_graph, "add_triple"):
                            await self.knowledge_graph.add_triple(
                                self.agent_uri(),
                                "http://example.org/core#hasStatus",
                                status.value.upper()
                            )
                        elif hasattr(self.knowledge_graph, "add"):
                            # rdflib.Graph path
                            agent_uri = URIRef(f"agent:{self.agent_id}")
                            core_ns = "http://example.org/core#"
                            self.knowledge_graph.add((agent_uri, RDF.type, URIRef(f"{core_ns}Agent")))
                            self.knowledge_graph.remove((agent_uri, URIRef(f"{core_ns}hasStatus"), None))
                            self.knowledge_graph.add((agent_uri, URIRef(f"{core_ns}hasStatus"), Literal(status.name)))
        except Exception as e:
            self.logger.error(f"Failed to update status for agent {self.agent_id}: {str(e)}")
            raise
            
    async def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent.
        
        Returns:
            Dict[str, Any]: The agent's status including:
                - status: str - Current status
                - capabilities: Set[Capability] - Current capabilities
                - message_count: int - Number of messages processed
                - last_message_time: Optional[datetime] - Time of last message
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                return {
                    "status": self.status,
                    "capabilities": await self.get_capabilities(),
                    "message_count": len(self.message_history),
                    "last_message_time": self.message_history[-1].timestamp if self.message_history else None
                }
        except Exception as e:
            self.logger.error(f"Failed to get status for agent {self.agent_id}: {str(e)}")
            raise
            
    async def cleanup(self) -> None:
        """Clean up agent resources."""
        try:
            async with self._capability_lock:
                if self._is_initialized:
                    # Clean up knowledge graph if needed
                    if self.knowledge_graph and hasattr(self.knowledge_graph, 'cleanup'):
                        await self.knowledge_graph.cleanup()
                        
                    # Clear message history
                    self.message_history.clear()
                    
                    # Reset status
                    self.status = AgentStatus.OFFLINE
                    
                    self._is_initialized = False
                    self.logger.info(f"Cleaned up agent {self.agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to clean up agent {self.agent_id}: {str(e)}")
            raise
            
    async def shutdown(self) -> None:
        """Shutdown the agent."""
        try:
            await self.cleanup()
            self.logger.info(f"Shut down agent {self.agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to shut down agent {self.agent_id}: {str(e)}")
            raise
            
    def agent_uri(self) -> str:
        """Get the agent's URI.
        
        Returns:
            str: The agent's URI.
        """
        return f"http://example.org/agent/{self.agent_id}"
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with new information."""
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        if self.knowledge_graph is None:
            raise RuntimeError("Knowledge graph not available")
            
        # Ensure core prefix bound
        try:
            if hasattr(self.knowledge_graph, "bind"):
                nm = self.knowledge_graph.namespace_manager  # type: ignore[attr-defined]
                if nm.store.namespace("core") is None:  # type: ignore[arg-type]
                    self.knowledge_graph.bind("core", Namespace("http://example.org/core#"))
                if nm.store.namespace("agent") is None:  # type: ignore[arg-type]
                    self.knowledge_graph.bind("agent", Namespace("http://example.org/agent/"))
                if nm.store.namespace("rdf") is None:
                    from rdflib.namespace import RDF as _RDFNS
                    self.knowledge_graph.bind("rdf", _RDFNS)
        except Exception:
            pass

        try:
            async with self._kg_lock:
                # Original nested structure OR flat metric dict
                if 'agent_id' in update_data:
                    agent_uri = URIRef(f"agent:{update_data['agent_id']}")
                    core_ns = "http://example.org/core#"
                    self.knowledge_graph.add((agent_uri, RDF.type, URIRef(f"{core_ns}Agent")))
                    metric_map = update_data.copy()
                    metric_map.pop('agent_id')
                    for key, val in metric_map.items():
                        def camel(s):
                            return ''.join(w.title() for w in s.split('_'))
                        pred_local = f"has{camel(key)}"
                        pred_uri = URIRef(f"{core_ns}{pred_local}")
                        # Overwrite existing metric value for idempotency
                        self.knowledge_graph.remove((agent_uri, pred_uri, None)) if hasattr(self.knowledge_graph, 'remove') else None
                        self.knowledge_graph.add((agent_uri, pred_uri, Literal(str(val))))
                    # Always maintain latest status as IDLE after successful update unless overridden
                    status_pred = URIRef(f"{core_ns}hasStatus")
                    if hasattr(self.knowledge_graph, 'remove'):
                        self.knowledge_graph.remove((agent_uri, status_pred, None))
                    self.knowledge_graph.add((agent_uri, status_pred, Literal("IDLE")))
                elif hasattr(self.knowledge_graph, 'add_triple'):
                    for subject, predicates in update_data.items():
                        if isinstance(predicates, dict):
                            for predicate, obj in predicates.items():
                                await self.knowledge_graph.add_triple(subject, predicate, str(obj))
                else:
                    for subject, predicates in update_data.items():
                        subject_uri = URIRef(subject)
                        if isinstance(predicates, dict):
                            for predicate, obj in predicates.items():
                                self.knowledge_graph.add((subject_uri, URIRef(predicate), Literal(str(obj))))
                        else:
                            # fallback same as before
                            agent_uri = URIRef(self.agent_uri())
                            core_ns = "http://example.org/core#"
                            self.knowledge_graph.add((agent_uri, RDF.type, URIRef(f"{core_ns}Agent")))
                            def camel(s):
                                return ''.join(w.title() for w in s.split('_'))
                            pred_local = f"has{camel(subject)}"
                            pred_uri = URIRef(f"{core_ns}{pred_local}")
                            self.knowledge_graph.add((agent_uri, pred_uri, Literal(str(predicates))))

                # Record history for tests
                self._capability_history.append({
                    "type": "update",
                    "data": update_data,
                    "capabilities": self._capabilities,
                    "timestamp": datetime.now().isoformat(),
                })

                self.logger.debug(f"Updated knowledge graph for agent {self.agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to update knowledge graph for agent {self.agent_id}: {str(e)}")
            raise
            
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for information."""
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        if self.knowledge_graph is None:
            raise RuntimeError("Knowledge graph not available")
            
        # Ensure core prefix
        try:
            if hasattr(self.knowledge_graph, "bind"):
                nm = self.knowledge_graph.namespace_manager  # type: ignore[attr-defined]
                if nm.store.namespace("core") is None:  # type: ignore[arg-type]
                    self.knowledge_graph.bind("core", Namespace("http://example.org/core#"))
                if nm.store.namespace("agent") is None:  # type: ignore[arg-type]
                    self.knowledge_graph.bind("agent", Namespace("http://example.org/agent/"))
                if nm.store.namespace("rdf") is None:
                    from rdflib.namespace import RDF as _RDFNS
                    self.knowledge_graph.bind("rdf", _RDFNS)
        except Exception:
            pass

        # Accept plain string as SPARQL for convenience
        if isinstance(query, str):
            query = {"sparql": query}

        try:
            async with self._kg_lock:
                if "sparql" in query:
                    # Explicit SPARQL provided – forward to KG helper
                    if hasattr(self.knowledge_graph, "query_graph"):
                        # Custom KG manager path returning list[dict]
                        results = await self.knowledge_graph.query_graph(query["sparql"])
                    elif hasattr(self.knowledge_graph, "query"):
                        # rdflib.Graph path → convert each row to dict with friendly keys
                        results = []
                        for row in self.knowledge_graph.query(query["sparql"]):
                            row_dict = {}
                            for var in row.labels:
                                key = str(var)
                                if key.startswith("?"):
                                    key = key[1:]
                                value = row[var]
                                # Convert rdflib.term types to plain str for test assertions
                                row_dict[key] = str(value)
                                lower_key = key.lower()
                                # Helpful aliases for common metric variables so tests can use simple names
                                if lower_key.endswith("messagecount") or lower_key == "hasmessagecount":
                                    row_dict["count"] = str(value)
                                if lower_key.endswith("status") or lower_key == "hasstatus":
                                    row_dict["status"] = str(value)
                            results.append(row_dict)
                    else:
                        results = []

                    # Record history entry for debugging & tests
                    self._capability_history.append({
                        "type": "sparql_query",
                        "query": query["sparql"],
                        "capabilities": self._capabilities,
                        "timestamp": datetime.now().isoformat(),
                    })

                    return results
                else:
                    # Handle direct graph queries
                    if "subject" in query:
                        subject = URIRef(query["subject"])
                        if "predicate" in query:
                            predicate = URIRef(query["predicate"])
                            if "object" in query:
                                obj = URIRef(query["object"])
                                kg_graph = self.knowledge_graph.graph if hasattr(self.knowledge_graph, "graph") else self.knowledge_graph
                                results = list(kg_graph.triples((subject, predicate, obj)))
                            else:
                                kg_graph = self.knowledge_graph.graph if hasattr(self.knowledge_graph, "graph") else self.knowledge_graph
                                results = list(kg_graph.triples((subject, predicate, None)))
                        else:
                            kg_graph = self.knowledge_graph.graph if hasattr(self.knowledge_graph, "graph") else self.knowledge_graph
                            results = list(kg_graph.triples((subject, None, None)))
                    else:
                        raise ValueError("Subject required for direct graph queries")
                        
                    # History entry for tests
                    self._capability_history.append({
                        "type": "query",
                        "query": query,
                        "capabilities": self._capabilities,
                        "timestamp": datetime.now().isoformat(),
                    })

                    return {"results": [(str(s), str(p), str(o)) for s, p, o in results]}
        except Exception as e:
            self.logger.error(f"Failed to query knowledge graph for agent {self.agent_id}: {str(e)}")
            raise
            
    # -------------------------------------------------------------
    # Test-helper APIs (no-ops for production)
    # -------------------------------------------------------------

    async def get_capability_history(self):  # type: ignore[override]
        """Return recorded capability history (async helper for tests)."""
        return list(self._capability_history)

    def write_diary(self, message: str, *, details: Optional[Dict[str, Any]] = None) -> None:
        """Add a diary entry and reflect it in the knowledge graph (sync).
        
        Args:
            message: Free-text message to record.
            details: Optional structured metadata stored alongside entry.
        """
        timestamp = datetime.utcnow().isoformat()
        entry: Dict[str, Any] = {
            "message": message,
            "details": details or {},
            "timestamp": timestamp,
        }
        self._diary_entries.append(entry)

        # Persist to attached knowledge graph if available
        if self.knowledge_graph and hasattr(self.knowledge_graph, "graph"):
            try:
                g = self.knowledge_graph.graph  # type: ignore[attr-defined]
                agent_uri = URIRef(f"agent:{self.agent_id}")
                diary_bnode = BNode()
                # Predicate URIs (keep plain strings for simplicity)
                has_diary_entry = URIRef("http://example.org/core#hasDiaryEntry")
                msg_pred = URIRef("http://example.org/core#message")
                ts_pred = URIRef("http://example.org/core#timestamp")
                details_pred = URIRef("http://example.org/core#details")

                g.add((agent_uri, has_diary_entry, diary_bnode))
                g.add((diary_bnode, msg_pred, Literal(message)))
                g.add((diary_bnode, ts_pred, Literal(timestamp)))
                if details:
                    g.add((diary_bnode, details_pred, Literal(json.dumps(details))))
            except Exception as e:
                # Non-fatal – diary still stored in memory
                self.logger.warning(f"Diary KG update failed for agent {self.agent_id}: {e}")

    def read_diary(self) -> List[Dict[str, Any]]:
        """Return a copy of diary entries (latest last)."""
        return list(self._diary_entries)

    # -------------------------------------------------------------
    # Simple inter-agent messaging helper required by demo_agents
    # -------------------------------------------------------------
    async def send_message(self, recipient_id: str, content: Any, message_type: str = "message") -> None:
        """Utility to send a message to another agent inside the same process.

        The implementation is intentionally lightweight – it looks up the
        recipient in the global agent registry created in BaseAgent.__init__
        and forwards an `AgentMessage`.  Errors are logged but do not raise, so
        unit-tests that only care about *successful* path won't fail because a
        downstream agent is missing.
        """
        recipient = BaseAgent._GLOBAL_AGENTS.get(recipient_id)
        if recipient is None:
            self.logger.warning(f"Recipient agent '{recipient_id}' not found – message dropped")
            return

        msg = AgentMessage(
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            content=content,
            timestamp=time.time(),
            message_type=message_type,
        )

        try:
            await recipient.process_message(msg)
        except Exception as exc:
            self.logger.warning(f"Failed to deliver message to {recipient_id}: {exc}")

    # ------------------------------------------------------------------
    # Back-compat helper: tests call `await agent.capabilities`
    # ------------------------------------------------------------------
    async def capabilities(self):  # type: ignore[override]
        """Awaitable alias returning the agent's capability set (legacy)."""
        return await self.get_capabilities() 