import pytest
import asyncio
from typing import Dict, Any

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Provide test configuration settings."""
    return {
        "test_client": {
            "name": "Test Healthcare Provider",
            "type": "Healthcare",
            "size": "Large"
        },
        "test_engagement": {
            "budget_range": ["$5M", "$10M", "$20M", "$50M"],
            "timeline_range": ["6 months", "12 months", "18 months", "24 months"],
            "scope_types": [
                "Digital Transformation",
                "AI Implementation",
                "Process Optimization",
                "Strategic Planning"
            ]
        },
        "knowledge_graph": {
            "namespaces": [
                "http://example.org/demo/",
                "http://example.org/demo/consulting/",
                "http://example.org/demo/task/",
                "http://example.org/demo/agent/"
            ]
        }
    } 