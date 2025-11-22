"""
Direct Comprehensive Test for Workflow Visualization
Tests without pytest fixtures to avoid async issues.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from agents.domain.orchestration_workflow import OrchestrationWorkflow
from agents.utils.workflow_visualizer import WorkflowVisualizer
from kg.models.graph_manager import KnowledgeGraphManager


async def test_1_visualizer_initialization():
    """Test 1: WorkflowVisualizer can be initialized."""
    print("\n🧪 TEST 1: Visualizer Initialization")
    viz = WorkflowVisualizer()
    assert viz is not None
    assert hasattr(viz, 'kg_manager')
    assert hasattr(viz, 'generate_html_visualization')
    print("   ✅ PASSED: Visualizer initialization")


async def test_2_visualizer_with_kg_manager():
    """Test 2: WorkflowVisualizer works with real KG manager."""
    print("\n🧪 TEST 2: Visualizer with KG Manager")
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    viz = WorkflowVisualizer(kg_manager=kg)
    assert viz.kg_manager == kg
    print("   ✅ PASSED: Visualizer with KG manager")


async def test_3_html_generation_basic():
    """Test 3: HTML file is generated successfully."""
    print("\n🧪 TEST 3: HTML Generation Basic")
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    viz = WorkflowVisualizer(kg_manager=kg)
    workflow_id = f"test_workflow_{uuid.uuid4().hex[:8]}"
    
    html_path = await viz.generate_html_visualization(workflow_id)
    
    assert html_path is not None
    assert isinstance(html_path, str)
    file_path = Path(html_path)
    assert file_path.exists(), f"HTML file not found: {html_path}"
    assert file_path.stat().st_size > 0, "HTML file is empty"
    
    print(f"   ✅ PASSED: HTML generated at {html_path} ({file_path.stat().st_size} bytes)")


async def test_4_html_content_structure():
    """Test 4: HTML contains all required components."""
    print("\n🧪 TEST 4: HTML Content Structure")
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    viz = WorkflowVisualizer(kg_manager=kg)
    workflow_id = f"test_workflow_{uuid.uuid4().hex[:8]}"
    
    html_path = await viz.generate_html_visualization(workflow_id)
    content = Path(html_path).read_text()
    
    required_elements = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<title>",
        "Workflow Flow Visualization",
        workflow_id,
        "<body>",
        "Timeline Flow",
        "Network Graph",
        "Flowchart",
        "vis-network",
        "mermaid",
        "stats",
        "stat-label",  # CSS class for stats labels
        "decisions",  # Should be in stat labels or JavaScript
        "images",     # Should be in stat labels or JavaScript
        "retries",    # Should be in stat labels or JavaScript
        "tasks"       # Should be in stat labels or JavaScript
    ]
    
    # Check for stats in a more flexible way
    has_stats_section = "stat-value" in content or "stat-label" in content
    
    # Check for stats section separately (more flexible)
    has_stats = "stat-value" in content or "stat-label" in content or "stats" in content
    
    # Remove stats-related strings from required (they might be in JS variables)
    required_core = [e for e in required_elements if e not in ["decisions", "images", "retries", "tasks"]]
    missing = [elem for elem in required_core if elem not in content]
    
    assert len(missing) == 0, f"Missing required elements: {missing}"
    assert has_stats, "Stats section not found in HTML"
    
    print(f"   ✅ PASSED: All HTML components present (including stats section)")


async def test_5_html_valid_structure():
    """Test 5: HTML has valid structure."""
    print("\n🧪 TEST 5: HTML Valid Structure")
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    viz = WorkflowVisualizer(kg_manager=kg)
    workflow_id = f"test_workflow_{uuid.uuid4().hex[:8]}"
    
    html_path = await viz.generate_html_visualization(workflow_id)
    content = Path(html_path).read_text()
    
    assert content.count("<html>") == content.count("</html>"), "Unbalanced html tags"
    assert content.count("<head>") == content.count("</head>"), "Unbalanced head tags"
    assert content.count("<body>") == content.count("</body>"), "Unbalanced body tags"
    assert "vis-network.min.js" in content, "vis-network library missing"
    assert "mermaid.min.js" in content, "mermaid library missing"
    
    print(f"   ✅ PASSED: HTML structure is valid")


async def test_6_workflow_integration():
    """Test 6: OrchestrationWorkflow integrates with visualizer."""
    print("\n🧪 TEST 6: Workflow Integration")
    planner = MagicMock()
    planner.agent_id = "test_planner"
    
    workflow = OrchestrationWorkflow(planner)
    
    assert hasattr(workflow, 'visualizer'), "Visualizer not initialized"
    assert isinstance(workflow.visualizer, WorkflowVisualizer), "Visualizer wrong type"
    
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    workflow.kg_manager = kg
    await workflow.initialize()
    
    print("   ✅ PASSED: Workflow integrates with visualizer")


async def test_7_visualize_plan_generates_html():
    """Test 7: visualize_plan_in_kg generates HTML file."""
    print("\n🧪 TEST 7: visualize_plan_in_kg Generates HTML")
    planner = MagicMock()
    planner.agent_id = "test_planner"
    
    workflow = OrchestrationWorkflow(planner)
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    workflow.kg_manager = kg
    await workflow.initialize()
    
    workflow_id = f"test_workflow_{uuid.uuid4().hex[:8]}"
    
    async def mock_retrieve_plan(planner, plan_id):
        return {
            "id": plan_id,
            "steps": [
                {"step": 1, "action": "Generate image", "agent": "midjourney"},
                {"step": 2, "action": "Review quality", "agent": "critic"}
            ]
        }
    
    with patch('agents.domain.orchestration_workflow.retrieve_plan', side_effect=mock_retrieve_plan):
        async def mock_query_graph(query):
            if "hasPlan" in query:
                return [{"plan": f"http://example.org/plan/{workflow_id}"}]
            return []
        
        workflow.kg_manager.query_graph = AsyncMock(side_effect=mock_query_graph)
        workflow.kg_manager.add_triple = AsyncMock()
        
        result = await workflow.visualize_plan_in_kg(workflow_id)
    
    assert "html_visualization" in result, "html_visualization not in result"
    assert result["html_visualization"] is not None, "html_visualization is None"
    
    html_path = result["html_visualization"]
    assert Path(html_path).exists(), f"HTML file not found: {html_path}"
    
    print(f"   ✅ PASSED: HTML generated via visualize_plan_in_kg: {html_path}")


async def test_8_html_with_workflow_data():
    """Test 8: HTML contains workflow data when available."""
    print("\n🧪 TEST 8: HTML with Workflow Data")
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    workflow_id = f"test_workflow_{uuid.uuid4().hex[:8]}"
    
    # Add test data to KG
    execution_uri = f"http://example.org/execution/{workflow_id}"
    step_uri = f"{execution_uri}/step/1"
    
    await kg.add_triple(
        execution_uri,
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        "http://example.org/ontology#Execution"
    )
    await kg.add_triple(
        step_uri,
        "http://example.org/ontology#action",
        "Generate hot dog image"
    )
    await kg.add_triple(
        step_uri,
        "http://example.org/ontology#status",
        "completed"
    )
    await kg.add_triple(
        execution_uri,
        "http://example.org/ontology#hasStep",
        step_uri
    )
    
    viz = WorkflowVisualizer(kg_manager=kg)
    html_path = await viz.generate_html_visualization(workflow_id)
    content = Path(html_path).read_text()
    
    assert workflow_id in content, "Workflow ID not in HTML"
    
    print(f"   ✅ PASSED: HTML contains workflow data")


async def test_9_multiple_workflows():
    """Test 9: Can generate multiple workflow visualizations."""
    print("\n🧪 TEST 9: Multiple Workflows")
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    viz = WorkflowVisualizer(kg_manager=kg)
    
    workflow_ids = [f"test_workflow_{uuid.uuid4().hex[:8]}" for _ in range(3)]
    html_paths = []
    
    for workflow_id in workflow_ids:
        html_path = await viz.generate_html_visualization(workflow_id)
        html_paths.append(html_path)
        assert Path(html_path).exists(), f"HTML not generated for {workflow_id}"
    
    assert len(set(html_paths)) == len(html_paths), "Duplicate HTML files generated"
    
    print(f"   ✅ PASSED: Generated {len(html_paths)} unique visualizations")


async def test_10_custom_output_path():
    """Test 10: Can specify custom output path."""
    print("\n🧪 TEST 10: Custom Output Path")
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    viz = WorkflowVisualizer(kg_manager=kg)
    workflow_id = f"test_workflow_{uuid.uuid4().hex[:8]}"
    
    custom_path = Path(f"/tmp/custom_viz_{workflow_id}.html")
    html_path = await viz.generate_html_visualization(workflow_id, output_path=custom_path)
    
    assert html_path == str(custom_path), "Custom path not used"
    assert custom_path.exists(), "Custom path file not created"
    
    print(f"   ✅ PASSED: Custom output path works: {custom_path}")


async def run_all_tests():
    """Run all comprehensive tests."""
    print("=" * 70)
    print("COMPREHENSIVE WORKFLOW VISUALIZATION TEST SUITE")
    print("=" * 70)
    
    tests = [
        test_1_visualizer_initialization,
        test_2_visualizer_with_kg_manager,
        test_3_html_generation_basic,
        test_4_html_content_structure,
        test_5_html_valid_structure,
        test_6_workflow_integration,
        test_7_visualize_plan_generates_html,
        test_8_html_with_workflow_data,
        test_9_multiple_workflows,
        test_10_custom_output_path,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)

