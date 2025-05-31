import pytest
import pytest_asyncio
import asyncio
import os
import json
import time
from datetime import datetime
from agents.core.workflow_persistence import WorkflowPersistence
from agents.core.workflow_monitor import WorkflowMonitor
from agents.core.workflow_manager import WorkflowManager
from agents.core.agent_registry import AgentRegistry

@pytest_asyncio.fixture
async def persistence():
    """Create a WorkflowPersistence instance for testing."""
    persistence = WorkflowPersistence()
    yield persistence
    # Cleanup test files
    if os.path.exists(persistence.storage_dir):
        for file in os.listdir(persistence.storage_dir):
            os.remove(os.path.join(persistence.storage_dir, file))
        os.rmdir(persistence.storage_dir)

@pytest_asyncio.fixture
async def monitor():
    """Create a WorkflowMonitor instance for testing."""
    return WorkflowMonitor()

@pytest_asyncio.fixture
async def workflow_manager():
    """Create a WorkflowManager instance for testing."""
    registry = AgentRegistry()
    manager = WorkflowManager(registry)
    await manager.initialize()
    yield manager
    # Cleanup test files
    if os.path.exists(manager.persistence.storage_dir):
        for file in os.listdir(manager.persistence.storage_dir):
            os.remove(os.path.join(manager.persistence.storage_dir, file))
        os.rmdir(manager.persistence.storage_dir)

@pytest.mark.asyncio
async def test_workflow_persistence_save_load(persistence):
    """Test saving and loading workflows."""
    # Create test workflow
    workflow = {
        "id": "test-workflow-1",
        "name": "Test Workflow",
        "description": "Test workflow for persistence",
        "required_capabilities": ["test_capability"],
        "state": "created",
        "created_at": time.time(),
        "updated_at": time.time(),
        "agents": [],
        "results": [],
        "version": "1.0"
    }
    
    # Save workflow
    await persistence.save_workflow(workflow)
    
    # Load workflow
    loaded_workflow = await persistence.load_workflow("test-workflow-1")
    
    # Verify workflow data
    assert loaded_workflow["id"] == workflow["id"]
    assert loaded_workflow["name"] == workflow["name"]
    assert loaded_workflow["state"] == workflow["state"]
    assert loaded_workflow["version"] == workflow["version"]

@pytest.mark.asyncio
async def test_workflow_persistence_versioning(persistence):
    """Test workflow versioning functionality."""
    # Create initial workflow
    workflow = {
        "id": "test-workflow-2",
        "name": "Test Workflow",
        "description": "Test workflow for versioning",
        "required_capabilities": ["test_capability"],
        "state": "created",
        "created_at": time.time(),
        "updated_at": time.time(),
        "agents": [],
        "results": [],
        "version": "1.0"
    }
    
    # Save initial version
    await persistence.save_workflow(workflow)
    
    # Update workflow
    workflow["state"] = "updated"
    workflow["version"] = "1.1"
    workflow["updated_at"] = time.time()
    
    # Save updated version
    await persistence.save_workflow(workflow)
    
    # Get version history
    history = await persistence.get_workflow_history("test-workflow-2")
    
    # Verify version history (oldest first)
    assert len(history) == 2
    assert history[0]["version"] == "1.0"
    assert history[1]["version"] == "1.1"

@pytest.mark.asyncio
async def test_workflow_persistence_recovery(persistence):
    """Test workflow recovery functionality."""
    # Create test workflow
    workflow = {
        "id": "test-workflow-3",
        "name": "Test Workflow",
        "description": "Test workflow for recovery",
        "required_capabilities": ["test_capability"],
        "state": "created",
        "created_at": time.time(),
        "updated_at": time.time(),
        "agents": [],
        "results": [],
        "version": "1.0"
    }
    
    # Save initial version
    await persistence.save_workflow(workflow)
    
    # Update workflow
    workflow["state"] = "updated"
    workflow["version"] = "1.1"
    workflow["updated_at"] = time.time()
    
    # Save updated version
    await persistence.save_workflow(workflow)
    
    # Recover to initial version
    recovered_workflow = await persistence.recover_workflow("test-workflow-3", "1.0")
    
    # Verify recovered workflow
    assert recovered_workflow["version"] == "1.0"
    assert recovered_workflow["state"] == "recovered"

@pytest.mark.asyncio
async def test_workflow_monitoring(monitor):
    """Test workflow monitoring functionality."""
    workflow_id = "test-workflow-4"
    
    # Track initial metrics
    await monitor.track_workflow_metrics(workflow_id, {
        "state": "created",
        "response_time": 0.0
    })
    
    # Track execution metrics
    await monitor.track_workflow_metrics(workflow_id, {
        "state": "executing",
        "response_time": 1.5,
        "resource_usage": {
            "cpu": 0.5,
            "memory": 0.3
        }
    })
    
    # Get metrics
    metrics = await monitor.get_workflow_metrics(workflow_id)
    
    # Verify metrics: check last state in state_changes
    assert metrics["state_changes"][-1]["state"] == "executing"
    assert metrics["response_times"][-1] == 1.5
    assert metrics["resource_usage"]["cpu"][-1]["usage"] == 0.5
    assert metrics["resource_usage"]["memory"][-1]["usage"] == 0.3

@pytest.mark.asyncio
async def test_workflow_alerts(monitor):
    """Test workflow alerting functionality."""
    workflow_id = "test-workflow-5"
    
    # Track metrics that should trigger alerts
    await monitor.track_workflow_metrics(workflow_id, {
        "state": "executing",
        "response_time": 10.0,  # Exceeds threshold
        "resource_usage": {
            "cpu": 0.9,  # Exceeds threshold
            "memory": 0.8
        }
    })
    
    # Get active alerts
    alerts = await monitor.get_active_alerts(workflow_id)
    
    # Verify alerts
    assert len(alerts) > 0
    assert any(alert["type"] == "high_response_time" for alert in alerts)
    assert any(alert["type"] == "high_cpu_usage" for alert in alerts)

@pytest.mark.asyncio
async def test_workflow_manager_integration(workflow_manager):
    """Test integration of persistence and monitoring in WorkflowManager."""
    # Create workflow
    workflow_id = await workflow_manager.create_workflow(
        name="Test Workflow",
        description="Test workflow for integration",
        required_capabilities=["test_capability"]
    )
    
    # Assemble workflow
    assembly_result = await workflow_manager.assemble_workflow(workflow_id)
    assert assembly_result["status"] == "error"  # No agents available
    
    # Get workflow history
    history = await workflow_manager.get_workflow_history(workflow_id)
    assert len(history) > 0
    
    # Get workflow metrics
    metrics = await workflow_manager.get_workflow_metrics(workflow_id)
    assert metrics["state_changes"][-1]["state"] == "created"
    
    # Get system health
    health = await workflow_manager.get_system_health()
    assert "total_workflows" in health
    assert "active_alerts" in health 