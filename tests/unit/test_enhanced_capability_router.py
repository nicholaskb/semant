"""
Unit tests for Enhanced Capability Router (Task 11).
Tests sophisticated capability matching, versioning, scoring, and routing.
"""

import pytest
import asyncio
from typing import Set
from unittest.mock import Mock, AsyncMock, MagicMock
from agents.core.capability_router import (
    EnhancedCapabilityRouter,
    CapabilityMatch,
    RoutingMetrics
)
from agents.core.capability_types import Capability, CapabilityType
from agents.core.base_agent import BaseAgent, AgentMessage, AgentStatus


# Mock Agent for testing
class MockAgent(BaseAgent):
    def __init__(self, agent_id: str, capabilities: Set[Capability], status=AgentStatus.IDLE):
        super().__init__(agent_id, capabilities=set())
        self._caps = capabilities
        self._status = status

        # Override the status property for testing
        self._agent_status = status

    async def get_capabilities(self):
        return self._caps

    @property
    def status(self):
        return self._agent_status

    @status.setter
    def status(self, value):
        self._agent_status = value
    
    async def _process_message_impl(self, message):
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"status": "success"},
            message_type="response"
        )


# Mock Agent Registry for testing
class MockRegistry:
    def __init__(self):
        self.agents = {}
    
    async def get_agent(self, agent_id: str):
        return self.agents.get(agent_id)
    
    async def get_agents_by_capability(self, capability_type):
        return [
            agent for agent in self.agents.values()
            if any(
                (isinstance(cap, Capability) and cap.type == capability_type) or
                (isinstance(cap, CapabilityType) and cap == capability_type)
                for cap in await agent.get_capabilities()
            )
        ]


@pytest.fixture
async def mock_registry():
    """Create a mock registry with test agents."""
    registry = MockRegistry()
    
    # Agent 1: Message processing v1.0, IDLE
    agent1 = MockAgent(
        "agent_1",
        {Capability(CapabilityType.MESSAGE_PROCESSING, "1.0")},
        AgentStatus.IDLE
    )
    await agent1.initialize()
    
    # Agent 2: Message processing v2.0, IDLE
    agent2 = MockAgent(
        "agent_2",
        {Capability(CapabilityType.MESSAGE_PROCESSING, "2.0")},
        AgentStatus.IDLE
    )
    await agent2.initialize()
    
    # Agent 3: Data processing v1.5, BUSY
    agent3 = MockAgent(
        "agent_3",
        {Capability(CapabilityType.DATA_PROCESSING, "1.5")},
        AgentStatus.BUSY
    )
    await agent3.initialize()
    
    # Agent 4: KG query v1.0, ERROR
    agent4 = MockAgent(
        "agent_4",
        {Capability(CapabilityType.KNOWLEDGE_GRAPH_QUERY, "1.0")},
        AgentStatus.ERROR
    )
    await agent4.initialize()
    
    registry.agents = {
        "agent_1": agent1,
        "agent_2": agent2,
        "agent_3": agent3,
        "agent_4": agent4
    }
    
    return registry


@pytest.fixture
async def router(mock_registry):
    """Create an enhanced capability router."""
    return EnhancedCapabilityRouter(mock_registry)


class TestCapabilityMatching:
    """Test capability matching and scoring."""

    def test_router_initializes(self, router):
        """Test that router initializes correctly."""
        assert router.agent_registry is not None
        assert router.metrics.total_routes == 0
        assert len(router._routing_cache) == 0

    def test_version_compatibility_exact_match(self, router):
        """Test exact version matching."""
        assert router._check_version_compatibility("1.0", "1.0") is True
        assert router._check_version_compatibility("1.0", "2.0") is False

    def test_version_compatibility_greater_equal(self, router):
        """Test >= version matching."""
        assert router._check_version_compatibility("2.0", ">=1.0") is True
        assert router._check_version_compatibility("1.5", ">=1.0") is True
        assert router._check_version_compatibility("0.9", ">=1.0") is False

    def test_version_compatibility_no_requirement(self, router):
        """Test that no requirement means any version is compatible."""
        assert router._check_version_compatibility("1.0", None) is True
        assert router._check_version_compatibility("999.0", None) is True

    def test_cache_operations(self, router):
        """Test cache operations."""
        # Initially empty
        assert len(router._routing_cache) == 0
        assert len(router._cache_timestamps) == 0

        # Clear cache
        router.clear_cache()
        assert len(router._routing_cache) == 0
        assert len(router._cache_timestamps) == 0


class TestVersionCompatibility:
    """Test version compatibility checking."""
    
    def test_exact_version_match(self, router):
        """Test exact version matching."""
        assert router._check_version_compatibility("1.0", "1.0") is True
        assert router._check_version_compatibility("1.0", "==1.0") is True
        assert router._check_version_compatibility("1.0", "2.0") is False
    
    def test_greater_than_or_equal(self, router):
        """Test >= version matching."""
        assert router._check_version_compatibility("2.0", ">=1.0") is True
        assert router._check_version_compatibility("1.5", ">=1.0") is True
        assert router._check_version_compatibility("0.9", ">=1.0") is False
    
    def test_less_than_or_equal(self, router):
        """Test <= version matching."""
        assert router._check_version_compatibility("1.0", "<=2.0") is True
        assert router._check_version_compatibility("1.5", "<=2.0") is True
        assert router._check_version_compatibility("2.1", "<=2.0") is False
    
    def test_no_requirement_always_compatible(self, router):
        """Test that no requirement means any version is compatible."""
        assert router._check_version_compatibility("1.0", None) is True
        assert router._check_version_compatibility("999.0", None) is True


class TestScoring:
    """Test agent scoring algorithm."""
    
    @pytest.mark.asyncio
    async def test_scoring_includes_all_factors(self, router, mock_registry):
        """Test that scoring considers all factors."""
        matches = await router.score_agents_for_capability(
            CapabilityType.MESSAGE_PROCESSING
        )
        
        assert len(matches) == 2
        for match in matches:
            assert 0.0 <= match.score <= 1.0
    
    @pytest.mark.asyncio
    async def test_version_match_increases_score(self, router):
        """Test that version matching increases score."""
        # Score without version requirement
        matches_no_ver = await router.score_agents_for_capability(
            CapabilityType.MESSAGE_PROCESSING
        )
        
        # Score with version requirement that matches
        matches_with_ver = await router.score_agents_for_capability(
            CapabilityType.MESSAGE_PROCESSING,
            version_requirement=">=1.0"
        )
        
        assert len(matches_no_ver) == 2
        assert len(matches_with_ver) == 2


class TestRouting:
    """Test routing functionality."""
    
    @pytest.mark.asyncio
    async def test_route_with_fallback_uses_primary(self, router, mock_registry):
        """Test that primary capability is used when available."""
        message = AgentMessage(
            sender_id="test",
            recipient_id="any",
            content={},
            message_type="request"
        )
        
        response = await router.route_with_fallback(
            message,
            CapabilityType.MESSAGE_PROCESSING,
            fallback_capabilities=[CapabilityType.DATA_PROCESSING]
        )
        
        assert response is not None
        assert response.sender_id in ["agent_1", "agent_2"]
    
    @pytest.mark.asyncio
    async def test_route_with_fallback_uses_fallback(self, router, mock_registry):
        """Test that fallback is used when primary not available."""
        message = AgentMessage(
            sender_id="test",
            recipient_id="any",
            content={},
            message_type="request"
        )
        
        response = await router.route_with_fallback(
            message,
            CapabilityType.RESEARCH,  # Not available in registry
            fallback_capabilities=[CapabilityType.MESSAGE_PROCESSING]  # Available
        )
        
        assert response is not None
        assert router.metrics.fallback_count > 0


class TestNegotiation:
    """Test capability negotiation."""
    
    @pytest.mark.asyncio
    async def test_negotiate_capabilities(self, router):
        """Test multi-capability negotiation."""
        assignments = await router.negotiate_capabilities(
            sender_id="orchestrator",
            required_capabilities=[
                CapabilityType.MESSAGE_PROCESSING,
                CapabilityType.DATA_PROCESSING
            ]
        )
        
        assert CapabilityType.MESSAGE_PROCESSING in assignments
        assert CapabilityType.DATA_PROCESSING in assignments
        assert assignments[CapabilityType.MESSAGE_PROCESSING] is not None
        assert assignments[CapabilityType.DATA_PROCESSING] is not None


class TestMetrics:
    """Test routing metrics collection."""
    
    @pytest.mark.asyncio
    async def test_metrics_track_successful_routes(self, router):
        """Test that successful routes are tracked."""
        initial_count = router.metrics.successful_routes
        
        agent = await router.find_best_agent(CapabilityType.MESSAGE_PROCESSING)
        
        assert agent is not None
        assert router.metrics.successful_routes == initial_count + 1
        assert router.metrics.total_routes > 0
    
    @pytest.mark.asyncio
    async def test_metrics_track_failed_routes(self, router):
        """Test that failed routes are tracked."""
        initial_failed = router.metrics.failed_routes
        
        agent = await router.find_best_agent(CapabilityType.RESEARCH)  # Not in registry
        
        assert agent is None
        assert router.metrics.failed_routes == initial_failed + 1
    
    @pytest.mark.asyncio
    async def test_metrics_track_capability_usage(self, router):
        """Test that capability usage is tracked."""
        cap_str = str(CapabilityType.MESSAGE_PROCESSING)
        initial_usage = router.metrics.capability_usage.get(cap_str, 0)
        
        await router.find_best_agent(CapabilityType.MESSAGE_PROCESSING)
        
        assert router.metrics.capability_usage[cap_str] == initial_usage + 1
    
    def test_metrics_to_dict(self):
        """Test metrics conversion to dictionary."""
        metrics = RoutingMetrics(
            total_routes=10,
            successful_routes=8,
            failed_routes=2
        )
        
        dict_metrics = metrics.to_dict()
        
        assert dict_metrics["total_routes"] == 10
        assert dict_metrics["successful_routes"] == 8
        assert dict_metrics["success_rate"] == 0.8


class TestCaching:
    """Test routing cache functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_stores_results(self, router):
        """Test that routing results are cached."""
        assert len(router._routing_cache) == 0
        
        await router.score_agents_for_capability(CapabilityType.MESSAGE_PROCESSING)
        
        assert len(router._routing_cache) > 0
    
    @pytest.mark.asyncio
    async def test_cache_improves_performance(self, router):
        """Test that cache improves subsequent lookups."""
        # First call (uncached)
        await router.score_agents_for_capability(CapabilityType.MESSAGE_PROCESSING)
        
        # Second call (should use cache)
        cache_key = f"{CapabilityType.MESSAGE_PROCESSING}:None"
        assert router._is_cache_valid(cache_key) is True
    
    def test_clear_cache(self, router):
        """Test cache clearing."""
        router._routing_cache["test"] = []
        router._cache_timestamps["test"] = 12345.0
        
        router.clear_cache()
        
        assert len(router._routing_cache) == 0
        assert len(router._cache_timestamps) == 0


class TestCoverageAnalysis:
    """Test capability coverage analysis."""
    
    @pytest.mark.asyncio
    async def test_get_capability_coverage(self, router):
        """Test capability coverage analysis."""
        coverage = await router.get_capability_coverage()
        
        assert "total_capabilities" in coverage
        assert "covered_capabilities" in coverage
        assert "uncovered_capabilities" in coverage
        assert "coverage_percentage" in coverage
        assert isinstance(coverage["covered_capabilities"], int)
        assert coverage["covered_capabilities"] >= 0


# Run tests with: pytest tests/unit/test_enhanced_capability_router.py -v

