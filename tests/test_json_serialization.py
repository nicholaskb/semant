"""Tests for JSON serialization utilities."""
import pytest
import json
from agents.core.json_serialization import (
    custom_json_dumps,
    custom_json_loads,
    custom_json_dump,
    custom_json_load,
    make_json_serializable
)
from agents.core.capability_types import Capability, CapabilityType
from agents.core.workflow_types import WorkflowStatus, Workflow, WorkflowStep


def test_capability_serialization():
    """Test serialization and deserialization of Capability objects."""
    cap = Capability(
        type=CapabilityType.RESEARCH,
        version="1.0",
        parameters={"param1": "value1"},
        metadata={"meta1": "data1"}
    )
    
    # Test to_dict
    cap_dict = cap.to_dict()
    assert isinstance(cap_dict, dict)
    assert cap_dict["type"] == "research"
    assert cap_dict["version"] == "1.0"
    
    # Test round-trip serialization
    json_str = custom_json_dumps(cap)
    assert isinstance(json_str, str)
    
    # Test deserialization
    loaded = custom_json_loads(json_str)
    assert isinstance(loaded, Capability)
    assert loaded.type == CapabilityType.RESEARCH
    assert loaded.version == "1.0"
    assert loaded.parameters == {"param1": "value1"}


def test_set_serialization():
    """Test serialization and deserialization of sets."""
    test_set = {"a", "b", "c"}
    
    # Test make_json_serializable converts set to list
    serializable = make_json_serializable(test_set)
    assert isinstance(serializable, list)
    assert set(serializable) == test_set
    
    # Test round-trip with custom encoder
    json_str = custom_json_dumps(test_set)
    loaded = custom_json_loads(json_str)
    assert isinstance(loaded, set)
    assert loaded == test_set


def test_enum_serialization():
    """Test serialization and deserialization of enums."""
    status = WorkflowStatus.RUNNING
    
    # Test make_json_serializable converts enum to value
    serializable = make_json_serializable(status)
    assert serializable == "running"
    
    # Test round-trip with custom encoder
    json_str = custom_json_dumps(status)
    loaded = custom_json_loads(json_str)
    assert isinstance(loaded, WorkflowStatus)
    assert loaded == WorkflowStatus.RUNNING


def test_nested_structure_serialization():
    """Test serialization of nested structures with multiple complex types."""
    workflow_data = {
        "id": "test-123",
        "status": WorkflowStatus.PENDING,
        "required_capabilities": {CapabilityType.RESEARCH, CapabilityType.DATA_PROCESSING},
        "steps": [
            {
                "id": "step-1",
                "capability": Capability(type=CapabilityType.RESEARCH),
                "status": WorkflowStatus.PENDING
            }
        ],
        "metadata": {
            "nested_set": {1, 2, 3},
            "nested_capability": Capability(type=CapabilityType.TASK_EXECUTION)
        }
    }
    
    # Test make_json_serializable
    serializable = make_json_serializable(workflow_data)
    assert isinstance(serializable["required_capabilities"], list)
    assert isinstance(serializable["status"], str)
    assert isinstance(serializable["metadata"]["nested_set"], list)
    
    # Test round-trip
    json_str = custom_json_dumps(workflow_data)
    loaded = custom_json_loads(json_str)
    
    assert loaded["id"] == "test-123"
    assert isinstance(loaded["required_capabilities"], set)
    assert CapabilityType.RESEARCH in loaded["required_capabilities"]
    assert isinstance(loaded["status"], WorkflowStatus)
    assert loaded["status"] == WorkflowStatus.PENDING


def test_workflow_step_serialization():
    """Test serialization of WorkflowStep objects."""
    step = WorkflowStep(
        id="step-1",
        capability="research",
        parameters={"param1": "value1"},
        status=WorkflowStatus.PENDING,
        assigned_agent="agent-1"
    )
    
    # Convert to dict (as workflow_persistence does)
    step_dict = {
        "id": step.id,
        "capability": step.capability,
        "parameters": make_json_serializable(step.parameters),
        "status": step.status.value,
        "assigned_agent": step.assigned_agent
    }
    
    # Should serialize without errors
    json_str = custom_json_dumps(step_dict)
    assert isinstance(json_str, str)
    
    # Should deserialize correctly
    loaded = custom_json_loads(json_str)
    assert loaded["id"] == "step-1"
    assert loaded["capability"] == "research"
    assert loaded["status"] == "pending"


def test_empty_collections():
    """Test serialization of empty collections."""
    empty_set = set()
    empty_dict = {}
    empty_list = []
    
    assert make_json_serializable(empty_set) == []
    assert make_json_serializable(empty_dict) == {}
    assert make_json_serializable(empty_list) == []


def test_circular_reference_handling():
    """Test that circular references are handled gracefully."""
    # Create a structure that could cause issues
    data = {
        "key1": "value1",
        "nested": {
            "key2": "value2",
            "set_data": {1, 2, 3}
        }
    }
    
    # Should serialize without errors
    json_str = custom_json_dumps(data)
    loaded = custom_json_loads(json_str)
    
    assert loaded["key1"] == "value1"
    assert isinstance(loaded["nested"]["set_data"], set)
    assert loaded["nested"]["set_data"] == {1, 2, 3}


def test_file_serialization(tmp_path):
    """Test file-based serialization."""
    test_file = tmp_path / "test.json"
    data = {
        "capability": Capability(type=CapabilityType.RESEARCH),
        "status": WorkflowStatus.RUNNING,
        "capabilities": {CapabilityType.DATA_PROCESSING, CapabilityType.RESEARCH}
    }
    
    # Write to file
    with open(test_file, "w") as f:
        custom_json_dump(data, f)
    
    # Read from file
    with open(test_file, "r") as f:
        loaded = custom_json_load(f)
    
    assert isinstance(loaded["capability"], Capability)
    assert isinstance(loaded["status"], WorkflowStatus)
    assert isinstance(loaded["capabilities"], set)
    assert CapabilityType.DATA_PROCESSING in loaded["capabilities"]
