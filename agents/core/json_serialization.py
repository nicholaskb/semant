"""Custom JSON serialization utilities for complex types.

This module provides JSON encoders and decoders for types that are not
natively JSON-serializable, including:
- Capability objects
- Sets
- Enums
- Dataclasses
- Other custom types
"""
import json
from typing import Any, Dict, Set, Union
from enum import Enum
from dataclasses import is_dataclass, asdict

from agents.core.capability_types import Capability, CapabilityType


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles complex types."""
    
    def default(self, obj: Any) -> Any:
        """Convert non-serializable objects to JSON-serializable format."""
        # Handle Capability objects
        if isinstance(obj, Capability):
            return {
                "__type__": "Capability",
                "data": obj.to_dict()
            }
        
        # Handle CapabilityType enums
        if isinstance(obj, CapabilityType):
            return {
                "__type__": "CapabilityType",
                "data": obj.value
            }
        
        # Handle sets
        if isinstance(obj, set):
            return {
                "__type__": "set",
                "data": list(obj)
            }
        
        # Handle other enums
        if isinstance(obj, Enum):
            return {
                "__type__": "Enum",
                "class": obj.__class__.__name__,
                "data": obj.value
            }
        
        # Handle dataclasses
        if is_dataclass(obj) and not isinstance(obj, type):
            return {
                "__type__": "dataclass",
                "class": obj.__class__.__name__,
                "data": asdict(obj)
            }
        
        # Let the base class handle the rest
        return super().default(obj)


def custom_json_dumps(obj: Any, **kwargs) -> str:
    """Serialize object to JSON string with custom encoding."""
    return json.dumps(obj, cls=CustomJSONEncoder, **kwargs)


def custom_json_dump(obj: Any, fp: Any, **kwargs) -> None:
    """Serialize object to JSON file with custom encoding."""
    json.dump(obj, fp, cls=CustomJSONEncoder, **kwargs)


def custom_json_loads(s: str, **kwargs) -> Any:
    """Deserialize JSON string with custom decoding."""
    data = json.loads(s, **kwargs)
    return _decode_object(data)


def custom_json_load(fp: Any, **kwargs) -> Any:
    """Deserialize JSON file with custom decoding."""
    data = json.load(fp, **kwargs)
    return _decode_object(data)


def _decode_object(obj: Any) -> Any:
    """Recursively decode custom types from JSON data."""
    if isinstance(obj, dict):
        # Check for custom type markers
        if "__type__" in obj:
            type_marker = obj["__type__"]
            data = obj["data"]
            
            if type_marker == "Capability":
                return Capability.from_dict(data)
            
            elif type_marker == "CapabilityType":
                return CapabilityType(data)
            
            elif type_marker == "set":
                return set(data)
            
            elif type_marker == "Enum":
                # For generic enums, we need to know the enum class
                # This is a simplified version - may need enhancement for specific enums
                class_name = obj.get("class")
                if class_name == "WorkflowStatus":
                    from agents.core.workflow_types import WorkflowStatus
                    return WorkflowStatus(data)
                # Add more enum classes as needed
                return data  # Fallback to raw value
            
            elif type_marker == "dataclass":
                # For dataclasses, we'd need to import and reconstruct
                # This is a simplified version - may need enhancement
                class_name = obj.get("class")
                if class_name == "WorkflowStep":
                    from agents.core.workflow_types import WorkflowStep
                    return WorkflowStep(**data)
                elif class_name == "Workflow":
                    from agents.core.workflow_types import Workflow
                    return Workflow(**data)
                return data  # Fallback to dict
        
        # Recursively decode nested dictionaries
        return {key: _decode_object(value) for key, value in obj.items()}
    
    elif isinstance(obj, list):
        # Recursively decode list items
        return [_decode_object(item) for item in obj]
    
    else:
        # Primitive type, return as-is
        return obj


def make_json_serializable(obj: Any) -> Any:
    """Convert an object to JSON-serializable format without encoding markers.
    
    This is useful when you want to serialize to a plain dict/list structure
    without the __type__ markers, for example when storing in databases or
    sending over APIs that don't support custom types.
    """
    if isinstance(obj, Capability):
        return obj.to_dict()
    
    if isinstance(obj, CapabilityType):
        return obj.value
    
    if isinstance(obj, set):
        return list(obj)
    
    if isinstance(obj, Enum):
        return obj.value
    
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    
    if isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    
    if isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    
    return obj
