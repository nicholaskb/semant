#!/usr/bin/env python3
"""
Test the Stock Analysis Swarm Integration
==========================================
This test verifies that all stock swarm components are working properly.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from kg.models.graph_manager import KnowledgeGraphManager
from agents.tools.kg_tools import KGTools
from stock_analysis_swarm.agents.orchestrator import StockOrchestratorAgent
from loguru import logger
import pytest


@pytest.mark.asyncio
async def test_stock_swarm_initialization():
    """Test that stock swarm components can be initialized"""
    # Initialize Knowledge Graph
    kg = KnowledgeGraphManager(persistent_storage=False)
    await kg.initialize()
    assert kg is not None
    
    # Initialize KG Tools
    kg_tools = KGTools(kg, "test-agent")
    assert kg_tools is not None
    
    # Initialize Stock Orchestrator
    orchestrator = StockOrchestratorAgent(
        agent_id="test-orchestrator",
        knowledge_graph=kg
    )
    await orchestrator.initialize()
    assert orchestrator is not None
    assert orchestrator.agent_id == "test-orchestrator"
    
    await kg.shutdown()


@pytest.mark.asyncio
async def test_stock_analysis_workflow():
    """Test complete stock analysis workflow"""
    # Setup
    kg = KnowledgeGraphManager(persistent_storage=False)
    await kg.initialize()
    
    orchestrator = StockOrchestratorAgent(
        agent_id="test-orchestrator",
        knowledge_graph=kg
    )
    await orchestrator.initialize()
    
    # Perform analysis
    result = await orchestrator.analyze_stock("TSLA", "quick")
    
    # Verify results structure
    assert result is not None
    assert "ticker" in result
    assert result["ticker"] == "TSLA"
    assert "analysis_id" in result
    assert "opportunity_score" in result
    assert "risk_assessment" in result
    assert "recommendation" in result
    
    # Verify opportunity score is reasonable
    assert 0 <= result["opportunity_score"] <= 10
    
    # Verify risk assessment
    assert "risk_level" in result["risk_assessment"]
    assert result["risk_assessment"]["risk_level"] in ["low", "medium", "high"]
    
    # Cleanup
    await kg.shutdown()


@pytest.mark.asyncio
async def test_kg_storage_and_retrieval():
    """Test that analysis results are stored in KG and can be retrieved"""
    # Setup
    kg = KnowledgeGraphManager(persistent_storage=False)
    await kg.initialize()
    
    orchestrator = StockOrchestratorAgent(
        agent_id="test-orchestrator",
        knowledge_graph=kg
    )
    await orchestrator.initialize()
    
    # Perform analysis
    result = await orchestrator.analyze_stock("GOOGL", "quick")
    
    # Query KG for stored analysis
    query = """
    PREFIX stock: <http://example.org/stock#>
    
    SELECT ?analysis ?ticker ?score WHERE {
        ?analysis a stock:StockAnalysis ;
                  stock:ticker ?ticker ;
                  stock:opportunityScore ?score .
        FILTER(?ticker = "GOOGL")
    }
    """
    
    kg_results = await kg.query_graph(query)
    
    # Verify data was stored
    assert len(kg_results) > 0
    assert any(r.get("ticker") == "GOOGL" for r in kg_results)
    
    # Cleanup
    await kg.shutdown()


@pytest.mark.asyncio
async def test_task_creation_in_kg():
    """Test that tasks are properly created in the knowledge graph"""
    # Setup
    kg = KnowledgeGraphManager(persistent_storage=False)
    await kg.initialize()
    kg_tools = KGTools(kg, "test-agent")
    
    # Create a task
    task_id = await kg_tools.create_task_node(
        task_name="Test Stock Analysis",
        task_type="stock_analysis",
        description="Test task for stock analysis",
        priority="high",
        metadata={"ticker": "MSFT"}
    )
    
    assert task_id is not None
    assert task_id.startswith("http://example.org/task/")
    
    # Query for the task
    query = """
    PREFIX core: <http://example.org/core#>
    
    SELECT ?task ?name WHERE {
        ?task core:taskName ?name .
        FILTER(?name = "Test Stock Analysis")
    }
    """
    
    results = await kg.query_graph(query)
    assert len(results) > 0
    
    # Cleanup
    await kg.shutdown()


@pytest.mark.asyncio
async def test_multiple_stock_analyses():
    """Test that multiple stocks can be analyzed sequentially"""
    # Setup
    kg = KnowledgeGraphManager(persistent_storage=False)
    await kg.initialize()
    
    orchestrator = StockOrchestratorAgent(
        agent_id="test-orchestrator",
        knowledge_graph=kg
    )
    await orchestrator.initialize()
    
    stocks = ["AAPL", "MSFT", "GOOGL"]
    results = []
    
    # Analyze multiple stocks
    for ticker in stocks:
        result = await orchestrator.analyze_stock(ticker, "quick")
        results.append(result)
    
    # Verify all analyses completed
    assert len(results) == 3
    for i, result in enumerate(results):
        assert result["ticker"] == stocks[i]
        assert "opportunity_score" in result
        assert "recommendation" in result
    
    # Query KG for all analyses
    query = """
    PREFIX stock: <http://example.org/stock#>
    
    SELECT ?ticker (COUNT(?analysis) as ?count) WHERE {
        ?analysis a stock:StockAnalysis ;
                  stock:ticker ?ticker .
    } GROUP BY ?ticker
    """
    
    kg_results = await kg.query_graph(query)
    
    # Verify all stocks are in KG
    stored_tickers = {r.get("ticker") for r in kg_results if r.get("ticker")}
    assert "AAPL" in stored_tickers
    assert "MSFT" in stored_tickers
    assert "GOOGL" in stored_tickers
    
    # Cleanup
    await kg.shutdown()


def test_stock_swarm_sync():
    """Synchronous test wrapper to verify the system works"""
    async def run_tests():
        # Test initialization
        await test_stock_swarm_initialization()
        print("✅ Stock swarm initialization test passed")
        
        # Test workflow
        await test_stock_analysis_workflow()
        print("✅ Stock analysis workflow test passed")
        
        # Test KG storage
        await test_kg_storage_and_retrieval()
        print("✅ KG storage and retrieval test passed")
        
        # Test task creation
        await test_task_creation_in_kg()
        print("✅ Task creation in KG test passed")
        
        # Test multiple analyses
        await test_multiple_stock_analyses()
        print("✅ Multiple stock analyses test passed")
        
        return True
    
    result = asyncio.run(run_tests())
    assert result is True


if __name__ == "__main__":
    print("\n🧪 Testing Stock Analysis Swarm Integration...")
    print("=" * 60)
    
    try:
        test_stock_swarm_sync()
        print("\n✨ All tests passed! Stock swarm is working properly.")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("=" * 60)
        sys.exit(1)
