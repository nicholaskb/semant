"""
Enhanced Capability-Based Routing System
Provides sophisticated agent selection based on capabilities, versioning, and scoring.

Date: 2025-01-11
Task: #11 - Enhance Capability-Based Routing
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from loguru import logger

from agents.core.capability_types import Capability, CapabilityType, CapabilitySet
from agents.core.base_agent import BaseAgent, AgentMessage


@dataclass
class CapabilityMatch:
    """Represents a capability match between requirement and agent."""
    agent_id: str
    capability: Capability
    score: float  # 0.0 to 1.0, higher is better match
    version_compatible: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingMetrics:
    """Metrics for routing decisions."""
    total_routes: int = 0
    successful_routes: int = 0
    failed_routes: int = 0
    avg_selection_time_ms: float = 0.0
    capability_usage: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    agent_utilization: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    fallback_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_routes": self.total_routes,
            "successful_routes": self.successful_routes,
            "failed_routes": self.failed_routes,
            "success_rate": self.successful_routes / self.total_routes if self.total_routes > 0 else 0.0,
            "avg_selection_time_ms": self.avg_selection_time_ms,
            "capability_usage": dict(self.capability_usage),
            "agent_utilization": dict(self.agent_utilization),
            "fallback_count": self.fallback_count
        }


class EnhancedCapabilityRouter:
    """
    Enhanced capability-based routing system for agent selection.
    
    Features:
    - Sophisticated matching algorithm with scoring
    - Version compatibility checking
    - Capability negotiation
    - Routing metrics collection
    - Performance optimization with caching
    - Fallback mechanisms
    """
    
    def __init__(self, agent_registry: 'AgentRegistry'):
        """
        Initialize the enhanced capability router.
        
        Args:
            agent_registry: The agent registry to route from
        """
        self.agent_registry = agent_registry
        self.metrics = RoutingMetrics()
        self.logger = logger.bind(component="CapabilityRouter")
        
        # Performance optimization: cache recent routing decisions
        self._routing_cache: Dict[str, List[CapabilityMatch]] = {}
        self._cache_ttl_seconds = 60  # Cache for 60 seconds
        self._cache_timestamps: Dict[str, float] = {}
    
    async def find_best_agent(
        self,
        required_capability: CapabilityType,
        version_requirement: Optional[str] = None,
        min_score: float = 0.5,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseAgent]:
        """
        Find the best agent for a required capability.
        
        Args:
            required_capability: The capability type needed
            version_requirement: Optional version requirement (e.g., ">=1.0")
            min_score: Minimum match score (0.0 to 1.0)
            preferences: Optional preferences for agent selection
            
        Returns:
            The best matching agent, or None if no suitable agent found
        """
        start_time = datetime.now()
        
        try:
            # Find all matching agents with scores
            matches = await self.score_agents_for_capability(
                required_capability,
                version_requirement,
                preferences
            )
            
            # Filter by minimum score
            qualified_matches = [m for m in matches if m.score >= min_score]
            
            if not qualified_matches:
                self.logger.warning(
                    f"No agents found with capability {required_capability} "
                    f"and min_score {min_score}"
                )
                self.metrics.failed_routes += 1
                return None
            
            # Sort by score (highest first)
            qualified_matches.sort(key=lambda m: m.score, reverse=True)
            
            # Get the best agent
            best_match = qualified_matches[0]
            best_agent = await self.agent_registry.get_agent(best_match.agent_id)
            
            if best_agent:
                self.metrics.successful_routes += 1
                self.metrics.capability_usage[str(required_capability)] += 1
                self.metrics.agent_utilization[best_match.agent_id] += 1
                
                self.logger.info(
                    f"Selected agent {best_match.agent_id} for {required_capability} "
                    f"(score: {best_match.score:.3f})"
                )
            else:
                self.metrics.failed_routes += 1
                
            return best_agent
            
        finally:
            # Update average selection time
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            total = self.metrics.total_routes
            self.metrics.avg_selection_time_ms = (
                (self.metrics.avg_selection_time_ms * total + duration_ms) / (total + 1)
                if total > 0 else duration_ms
            )
            self.metrics.total_routes += 1
    
    async def score_agents_for_capability(
        self,
        required_capability: CapabilityType,
        version_requirement: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> List[CapabilityMatch]:
        """
        Score all agents for a required capability.
        
        Args:
            required_capability: The capability type needed
            version_requirement: Optional version requirement
            preferences: Optional preferences (e.g., prefer specific agents)
            
        Returns:
            List of CapabilityMatch objects with scores
        """
        # Check cache first
        cache_key = f"{required_capability}:{version_requirement}"
        if self._is_cache_valid(cache_key):
            return self._routing_cache[cache_key]
        
        matches: List[CapabilityMatch] = []
        agents = await self.agent_registry.get_agents_by_capability(required_capability)
        
        for agent in agents:
            # Get agent's capabilities
            agent_caps = await agent.get_capabilities()
            
            # Find matching capability
            matching_cap = None
            for cap in agent_caps:
                if isinstance(cap, Capability) and cap.type == required_capability:
                    matching_cap = cap
                    break
                elif isinstance(cap, CapabilityType) and cap == required_capability:
                    # Create Capability object
                    matching_cap = Capability(cap, "1.0")
                    break
            
            if not matching_cap:
                continue
            
            # Calculate match score
            score = self._calculate_match_score(
                matching_cap,
                version_requirement,
                preferences,
                agent
            )
            
            # Check version compatibility
            version_compatible = self._check_version_compatibility(
                matching_cap.version if isinstance(matching_cap, Capability) else "1.0",
                version_requirement
            )
            
            matches.append(CapabilityMatch(
                agent_id=agent.agent_id,
                capability=matching_cap if isinstance(matching_cap, Capability) else Capability(matching_cap, "1.0"),
                score=score,
                version_compatible=version_compatible,
                metadata={
                    "agent_status": str(agent.status) if hasattr(agent, 'status') else "unknown"
                }
            ))
        
        # Cache the results
        self._routing_cache[cache_key] = matches
        self._cache_timestamps[cache_key] = datetime.now().timestamp()
        
        return matches
    
    def _calculate_match_score(
        self,
        capability: Capability,
        version_requirement: Optional[str],
        preferences: Optional[Dict[str, Any]],
        agent: BaseAgent
    ) -> float:
        """
        Calculate match score for an agent.
        
        Scoring factors:
        - Base score: 0.5
        - Version match: +0.3
        - Agent preference: +0.2
        - Agent availability: +0.1
        
        Returns:
            Score from 0.0 to 1.0
        """
        score = 0.5  # Base score
        
        # Version compatibility
        if version_requirement:
            cap_version = capability.version if isinstance(capability, Capability) else "1.0"
            if self._check_version_compatibility(cap_version, version_requirement):
                score += 0.3
        else:
            score += 0.3  # No version requirement = automatic bonus
        
        # Agent preferences
        if preferences:
            if 'preferred_agents' in preferences:
                if agent.agent_id in preferences['preferred_agents']:
                    score += 0.2
            if 'avoid_agents' in preferences:
                if agent.agent_id in preferences['avoid_agents']:
                    score -= 0.3
        else:
            score += 0.1  # No preferences = small bonus for flexibility
        
        # Agent availability (if status available)
        if hasattr(agent, 'status'):
            from agents.core.base_agent import AgentStatus
            if agent.status == AgentStatus.IDLE:
                score += 0.1
            elif agent.status == AgentStatus.ERROR:
                score -= 0.2
        
        # Clamp score to [0.0, 1.0]
        return max(0.0, min(1.0, score))
    
    def _check_version_compatibility(
        self,
        agent_version: str,
        requirement: Optional[str]
    ) -> bool:
        """
        Check if agent version meets requirement.
        
        Supports:
        - ">=1.0" - greater than or equal
        - "<=2.0" - less than or equal
        - "==1.5" - exact match
        - "1.0" - exact match (no operator)
        
        Args:
            agent_version: Agent's capability version
            requirement: Version requirement string
            
        Returns:
            True if compatible, False otherwise
        """
        if not requirement:
            return True
        
        requirement = requirement.strip()
        
        # Parse operator and version
        if requirement.startswith(">="):
            op = ">="
            req_ver = requirement[2:].strip()
        elif requirement.startswith("<="):
            op = "<="
            req_ver = requirement[2:].strip()
        elif requirement.startswith("=="):
            op = "=="
            req_ver = requirement[2:].strip()
        elif requirement.startswith(">"):
            op = ">"
            req_ver = requirement[1:].strip()
        elif requirement.startswith("<"):
            op = "<"
            req_ver = requirement[1:].strip()
        else:
            op = "=="
            req_ver = requirement
        
        # Convert versions to tuples for comparison
        try:
            agent_ver_tuple = tuple(map(int, agent_version.split('.')))
            req_ver_tuple = tuple(map(int, req_ver.split('.')))
        except (ValueError, AttributeError):
            # If version parsing fails, assume compatible
            return True
        
        # Perform comparison
        if op == ">=":
            return agent_ver_tuple >= req_ver_tuple
        elif op == "<=":
            return agent_ver_tuple <= req_ver_tuple
        elif op == ">":
            return agent_ver_tuple > req_ver_tuple
        elif op == "<":
            return agent_ver_tuple < req_ver_tuple
        else:  # ==
            return agent_ver_tuple == req_ver_tuple
    
    async def negotiate_capabilities(
        self,
        sender_id: str,
        required_capabilities: List[CapabilityType],
        version_requirements: Optional[Dict[CapabilityType, str]] = None
    ) -> Dict[CapabilityType, Optional[str]]:
        """
        Negotiate capabilities between agents.
        
        Finds the best agent for each required capability and returns
        a mapping of capability → agent_id.
        
        Args:
            sender_id: ID of the requesting agent
            required_capabilities: List of capabilities needed
            version_requirements: Optional version requirements per capability
            
        Returns:
            Dictionary mapping each capability to selected agent_id (or None if not available)
        """
        assignments: Dict[CapabilityType, Optional[str]] = {}
        
        for cap_type in required_capabilities:
            version_req = version_requirements.get(cap_type) if version_requirements else None
            
            best_agent = await self.find_best_agent(
                required_capability=cap_type,
                version_requirement=version_req,
                preferences={'avoid_agents': [sender_id]}  # Don't assign to self
            )
            
            assignments[cap_type] = best_agent.agent_id if best_agent else None
            
            if not best_agent:
                self.logger.warning(
                    f"No agent found for capability {cap_type} "
                    f"(requested by {sender_id})"
                )
        
        return assignments
    
    async def route_with_fallback(
        self,
        message: AgentMessage,
        required_capability: CapabilityType,
        fallback_capabilities: Optional[List[CapabilityType]] = None
    ) -> Optional[AgentMessage]:
        """
        Route a message with fallback capabilities.
        
        Tries to route to an agent with the required capability first.
        If not found, tries fallback capabilities in order.
        
        Args:
            message: Message to route
            required_capability: Primary capability needed
            fallback_capabilities: List of fallback capabilities to try
            
        Returns:
            Response message from selected agent, or None if all fail
        """
        # Try primary capability first
        agent = await self.find_best_agent(required_capability)
        
        if agent:
            try:
                response = await agent.process_message(message)
                return response
            except Exception as e:
                self.logger.error(
                    f"Agent {agent.agent_id} failed to process message: {e}"
                )
        
        # Try fallback capabilities
        if fallback_capabilities:
            for fallback_cap in fallback_capabilities:
                self.logger.info(
                    f"Trying fallback capability: {fallback_cap}"
                )
                agent = await self.find_best_agent(fallback_cap)
                
                if agent:
                    try:
                        self.metrics.fallback_count += 1
                        response = await agent.process_message(message)
                        self.logger.info(
                            f"Fallback successful with agent {agent.agent_id}"
                        )
                        return response
                    except Exception as e:
                        self.logger.error(
                            f"Fallback agent {agent.agent_id} failed: {e}"
                        )
                        continue
        
        self.logger.error(
            f"All routing attempts failed for capability {required_capability}"
        )
        return None
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached routing decision is still valid."""
        if cache_key not in self._routing_cache:
            return False
        
        timestamp = self._cache_timestamps.get(cache_key, 0)
        age = datetime.now().timestamp() - timestamp
        
        return age < self._cache_ttl_seconds
    
    def clear_cache(self) -> None:
        """Clear routing cache (useful after agent registration changes)."""
        self._routing_cache.clear()
        self._cache_timestamps.clear()
        self.logger.debug("Routing cache cleared")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get routing metrics."""
        return self.metrics.to_dict()
    
    async def get_capability_coverage(self) -> Dict[str, Any]:
        """
        Analyze capability coverage across the agent network.
        
        Returns:
            Dictionary with coverage statistics
        """
        coverage = {
            "total_capabilities": len(CapabilityType),
            "covered_capabilities": 0,
            "uncovered_capabilities": [],
            "redundancy": {},  # capability -> agent count
            "single_point_failures": []  # capabilities with only 1 agent
        }
        
        # Check each capability
        for cap_type in CapabilityType:
            agents = await self.agent_registry.get_agents_by_capability(cap_type)
            agent_count = len(agents)
            
            if agent_count > 0:
                coverage["covered_capabilities"] += 1
                coverage["redundancy"][str(cap_type)] = agent_count
                
                if agent_count == 1:
                    coverage["single_point_failures"].append(str(cap_type))
            else:
                coverage["uncovered_capabilities"].append(str(cap_type))
        
        coverage["coverage_percentage"] = (
            coverage["covered_capabilities"] / coverage["total_capabilities"] * 100
            if coverage["total_capabilities"] > 0 else 0.0
        )
        
        return coverage
    
    async def optimize_routing_table(self) -> Dict[str, Any]:
        """
        Optimize the routing table for faster agent selection.
        
        Pre-computes common routing scenarios and caches results.
        
        Returns:
            Optimization statistics
        """
        start_time = datetime.now()
        optimized_routes = 0
        
        # Pre-cache common capability lookups
        common_capabilities = [
            CapabilityType.MESSAGE_PROCESSING,
            CapabilityType.DATA_PROCESSING,
            CapabilityType.KNOWLEDGE_GRAPH_QUERY,
            CapabilityType.KNOWLEDGE_GRAPH_UPDATE
        ]
        
        for cap_type in common_capabilities:
            try:
                cache_key = f"{cap_type}:None"
                matches = await self.score_agents_for_capability(cap_type)
                self._routing_cache[cache_key] = matches
                self._cache_timestamps[cache_key] = datetime.now().timestamp()
                optimized_routes += 1
            except Exception as e:
                self.logger.warning(f"Failed to pre-cache {cap_type}: {e}")
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            "optimized_routes": optimized_routes,
            "duration_ms": duration_ms,
            "cache_size": len(self._routing_cache)
        }

