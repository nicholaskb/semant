"""
Comprehensive Test for Workflow Visualization System
Tests the complete integration from workflow creation to HTML generation.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

from agents.domain.orchestration_workflow import OrchestrationWorkflow
from agents.utils.workflow_visualizer import WorkflowVisualizer
from kg.models.graph_manager import KnowledgeGraphManager


class TestWorkflowVisualizationComprehensive:
    """Comprehensive tests for workflow visualization."""
    
    @pytest.fixture
    def mock_planner(self):
        """Create a mock planner agent."""
        planner = MagicMock()
        planner.agent_id = "test_planner"
        planner.knowledge_graph = AsyncMock()
        planner.knowledge_graph.add_triple = AsyncMock()
        planner.knowledge_graph.query_graph = AsyncMock(return_value=[])
        return planner
    
    @pytest.fixture
    async def real_kg_manager(self):
        """Create a real KG manager for testing."""
        kg = KnowledgeGraphManager(persistent_storage=True)
        await kg.initialize()
        yield kg
        # Cleanup if needed
    
    @pytest.mark.asyncio
    async def test_visualizer_initialization(self):
        """Test 1: WorkflowVisualizer can be initialized."""
        viz = WorkflowVisualizer()
        assert viz is not None
        assert hasattr(viz, 'kg_manager')
        assert hasattr(viz, 'generate_html_visualization')
        print("✅ TEST 1 PASSED: Visualizer initialization")
    
    @pytest.mark.asyncio
    async def test_visualizer_with_kg_manager(self, real_kg_manager):
        """Test 2: WorkflowVisualizer works with real KG manager."""
        viz = WorkflowVisualizer(kg_manager=real_kg_manager)
        assert viz.kg_manager == real_kg_manager
        print("✅ TEST 2 PASSED: Visualizer with KG manager")
    
    @pytest.mark.asyncio
    async def test_html_generation_basic(self, real_kg_manager):
        """Test 3: HTML file is generated successfully."""
        viz = WorkflowVisualizer(kg_manager=real_kg_manager)
        workflow_id = f"test_workflow_{uuid.uuid4().hex[:8]}"
        
        # Generate HTML
        html_path = await viz.generate_html_visualization(workflow_id)
        
        # Verify file exists
        assert html_path is not None
        assert isinstance(html_path, str)
        file_path = Path(html_path)
        assert file_path.exists(), f"HTML file not found: {html_path}"
        assert file_path.stat().st_size > 0, "HTML file is empty"
        
        print(f"✅ TEST 3 PASSED: HTML generated at {html_path} ({file_path.stat().st_size} bytes)")
    
    @pytest.mark.asyncio
    async def test_html_content_structure(self, real_kg_manager):
        """Test 4: HTML contains all required components."""
        viz = WorkflowVisualizer(kg_manager=real_kg_manager)
        workflow_id = f"test_workflow_{uuid.uuid4().hex[:8]}"
        
        html_path = await viz.generate_html_visualization(workflow_id)
        content = Path(html_path).read_text()
        
        # Check for required HTML structure
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
            "decisions",
            "images",
            "retries",
            "tasks"
        ]
        
        missing = [elem for elem in required_elements if elem not in content]
        assert len(missing) == 0, f"Missing required elements: {missing}"
        
        print(f"✅ TEST 4 PASSED: All HTML components present")
    
    @pytest.mark.asyncio
    async def test_html_valid_structure(self, real_kg_manager):
        """Test 5: HTML has valid structure (can be parsed)."""
        viz = WorkflowVisualizer(kg_manager=real_kg_manager)
        workflow_id = f"test_workflow_{uuid.uuid4().hex[:8]}"
        
        html_path = await viz.generate_html_visualization(workflow_id)
        content = Path(html_path).read_text()
        
        # Check for balanced tags
        assert content.count("<html>") == content.count("</html>"), "Unbalanced html tags"
        assert content.count("<head>") == content.count("</head>"), "Unbalanced head tags"
        assert content.count("<body>") == content.count("</body>"), "Unbalanced body tags"
        
        # Check for JavaScript libraries
        assert "vis-network.min.js" in content, "vis-network library missing"
        assert "mermaid.min.js" in content, "mermaid library missing"
        
        print(f"✅ TEST 5 PASSED: HTML structure is valid")
    
    @pytest.mark.asyncio
    async def test_workflow_integration(self, mock_planner, real_kg_manager):
        """Test 6: OrchestrationWorkflow integrates with visualizer."""
        workflow = OrchestrationWorkflow(mock_planner)
        
        # Verify visualizer is initialized
        assert hasattr(workflow, 'visualizer'), "Visualizer not initialized"
        assert isinstance(workflow.visualizer, WorkflowVisualizer), "Visualizer wrong type"
        
        # Mock the KG manager
        workflow.kg_manager = real_kg_manager
        
        await workflow.initialize()
        
        print("✅ TEST 6 PASSED: Workflow integrates with visualizer")
    
    @pytest.mark.asyncio
    async def test_visualize_plan_generates_html(self, mock_planner, real_kg_manager):
        """Test 7: visualize_plan_in_kg generates HTML file."""
        workflow = OrchestrationWorkflow(mock_planner)
        workflow.kg_manager = real_kg_manager
        await workflow.initialize()
        
        workflow_id = f"test_workflow_{uuid.uuid4().hex[:8]}"
        
        # Mock plan retrieval
        async def mock_retrieve_plan(planner, plan_id):
            return {
                "id": plan_id,
                "steps": [
                    {"step": 1, "action": "Generate image", "agent": "midjourney"},
                    {"step": 2, "action": "Review quality", "agent": "critic"}
                ]
            }
        
        with patch('agents.domain.orchestration_workflow.retrieve_plan', side_effect=mock_retrieve_plan):
            # Mock query_graph to return plan data
            async def mock_query_graph(query):
                if "hasPlan" in query:
                    return [{"plan": f"http://example.org/plan/{workflow_id}"}]
                return []
            
            workflow.kg_manager.query_graph = AsyncMock(side_effect=mock_query_graph)
            workflow.kg_manager.add_triple = AsyncMock()
            
            result = await workflow.visualize_plan_in_kg(workflow_id)
        
        # Verify HTML was generated
        assert "html_visualization" in result, "html_visualization not in result"
        assert result["html_visualization"] is not None, "html_visualization is None"
        
        html_path = result["html_visualization"]
        assert Path(html_path).exists(), f"HTML file not found: {html_path}"
        
        print(f"✅ TEST 7 PASSED: HTML generated via visualize_plan_in_kg: {html_path}")
    
    @pytest.mark.asyncio
    async def test_html_with_workflow_data(self, real_kg_manager):
        """Test 8: HTML contains workflow data when available."""
        workflow_id = f"test_workflow_{uuid.uuid4().hex[:8]}"
        
        # Add some test data to KG
        execution_uri = f"http://example.org/execution/{workflow_id}"
        step_uri = f"{execution_uri}/step/1"
        
        await real_kg_manager.add_triple(
            execution_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/ontology#Execution"
        )
        await real_kg_manager.add_triple(
            step_uri,
            "http://example.org/ontology#action",
            "Generate hot dog image"
        )
        await real_kg_manager.add_triple(
            step_uri,
            "http://example.org/ontology#status",
            "completed"
        )
        await real_kg_manager.add_triple(
            execution_uri,
            "http://example.org/ontology#hasStep",
            step_uri
        )
        
        # Generate HTML
        viz = WorkflowVisualizer(kg_manager=real_kg_manager)
        html_path = await viz.generate_html_visualization(workflow_id)
        content = Path(html_path).read_text()
        
        # Check that workflow data appears in HTML
        assert workflow_id in content, "Workflow ID not in HTML"
        
        print(f"✅ TEST 8 PASSED: HTML contains workflow data")
    
    @pytest.mark.asyncio
    async def test_multiple_workflows(self, real_kg_manager):
        """Test 9: Can generate multiple workflow visualizations."""
        viz = WorkflowVisualizer(kg_manager=real_kg_manager)
        
        workflow_ids = [f"test_workflow_{uuid.uuid4().hex[:8]}" for _ in range(3)]
        html_paths = []
        
        for workflow_id in workflow_ids:
            html_path = await viz.generate_html_visualization(workflow_id)
            html_paths.append(html_path)
            assert Path(html_path).exists(), f"HTML not generated for {workflow_id}"
        
        # Verify all files are unique
        assert len(set(html_paths)) == len(html_paths), "Duplicate HTML files generated"
        
        print(f"✅ TEST 9 PASSED: Generated {len(html_paths)} unique visualizations")
    
    @pytest.mark.asyncio
    async def test_custom_output_path(self, real_kg_manager, tmp_path):
        """Test 10: Can specify custom output path."""
        viz = WorkflowVisualizer(kg_manager=real_kg_manager)
        workflow_id = f"test_workflow_{uuid.uuid4().hex[:8]}"
        
        custom_path = tmp_path / "custom_viz.html"
        html_path = await viz.generate_html_visualization(workflow_id, output_path=custom_path)
        
        assert html_path == str(custom_path), "Custom path not used"
        assert custom_path.exists(), "Custom path file not created"
        
        print(f"✅ TEST 10 PASSED: Custom output path works: {custom_path}")


async def run_all_tests():
    """Run all comprehensive tests."""
    print("=" * 70)
    print("COMPREHENSIVE WORKFLOW VISUALIZATION TEST SUITE")
    print("=" * 70)
    print()
    
    # Run pytest programmatically
    import sys
    exit_code = pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short"
    ])
    
    print()
    print("=" * 70)
    if exit_code == 0:
        print("✅ ALL TESTS PASSED!")
    else:
        print(f"❌ SOME TESTS FAILED (exit code: {exit_code})")
    print("=" * 70)
    
    return exit_code == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)

