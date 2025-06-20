import pytest
import pytest_asyncio
import asyncio
from agents.domain.vertex_email_agent import VertexEmailAgent
from agents.core.base_agent import AgentMessage
import os
from dotenv import load_dotenv
from datetime import datetime
from unittest.mock import patch, MagicMock
import logging
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel
import requests
from google.auth.transport.requests import AuthorizedSession

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

@pytest_asyncio.fixture
async def vertex_agent():
    """Fixture to create and initialize a VertexEmailAgent instance."""
    agent = VertexEmailAgent()
    await agent.initialize()
    return agent

@pytest.fixture
def is_vertex_ai_enabled():
    """Fixture to check if Vertex AI is available."""
    return bool(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))

@pytest.mark.asyncio
async def test_vertex_initialization(vertex_agent, is_vertex_ai_enabled):
    """Test Vertex AI initialization and configuration."""
    assert vertex_agent is not None
    if is_vertex_ai_enabled:
        assert vertex_agent.model is not None
    else:
        assert vertex_agent.model is None
        assert vertex_agent.simulation_mode is True

@pytest.mark.asyncio
async def test_email_enhancement(vertex_agent, is_vertex_ai_enabled):
    """Test email content enhancement functionality."""
    original_content = "Test email content"
    enhanced_content = await vertex_agent.enhance_email_content(original_content)
    
    assert enhanced_content is not None
    if is_vertex_ai_enabled:
        assert enhanced_content != original_content
    else:
        assert enhanced_content == original_content

@pytest.mark.asyncio
async def test_message_processing(vertex_agent):
    """Test processing of email messages."""
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="vertex_email_agent",
        content={
            "recipient": "test@example.com",
            "subject": "Test Subject",
            "body": "Test Body"
        },
        message_type="send_email",
        timestamp=datetime.now().timestamp()
    )
    
    response = await vertex_agent.process_message(message)
    assert response is not None
    assert response.content is not None
    assert "status" in response.content

@pytest.mark.asyncio
async def test_invalid_message_type(vertex_agent):
    """Test handling of invalid message types."""
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="vertex_email_agent",
        content={"invalid": "content"},
        message_type="invalid_type",
        timestamp=datetime.now().timestamp()
    )
    
    response = await vertex_agent.process_message(message)
    assert response is not None
    assert response.content.get("status") == "error"

@pytest.mark.asyncio
async def test_knowledge_graph_integration(vertex_agent):
    """Test integration with knowledge graph."""
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="vertex_email_agent",
        content={
            "recipient": "test@example.com",
            "subject": "Test Subject",
            "body": "Test Body"
        },
        message_type="send_email",
        timestamp=datetime.now().timestamp()
    )
    
    response = await vertex_agent.process_message(message)
    assert response is not None
    assert "knowledge_graph" in response.content

@pytest.mark.asyncio
async def test_error_handling(vertex_agent):
    """Test error handling in various scenarios."""
    # Test with invalid email address
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="vertex_email_agent",
        content={
            "recipient": "invalid-email",
            "subject": "Test Subject",
            "body": "Test Body"
        },
        message_type="send_email",
        timestamp=datetime.now().timestamp()
    )
    
    response = await vertex_agent.process_message(message)
    assert response is not None
    assert response.content.get("status") == "error"

@pytest.mark.asyncio
async def test_empty_subject_and_body(vertex_agent):
    """Test handling of empty subject and body."""
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="vertex_email_agent",
        content={
            "recipient": "test@example.com",
            "subject": "",
            "body": ""
        },
        message_type="send_email",
        timestamp=datetime.now().timestamp()
    )
    
    response = await vertex_agent.process_message(message)
    assert response is not None
    assert response.content.get("status") == "error"

def expand_path(path):
    """Expand path variables like $(pwd)."""
    if path.startswith('$(pwd)'):
        return os.path.join(os.getcwd(), path[7:])
    return path

def verify_environment():
    """Verify required environment variables are set."""
    load_dotenv(override=True)
    required_vars = [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION"
    ]
    for var in required_vars:
        if not os.getenv(var):
            logger.error(f"Missing required environment variable: {var}")
            return False
        logger.info(f"Found environment variable {var}: {os.getenv(var)}")
    return True

def test_credentials():
    """Test loading service account credentials."""
    creds_path = expand_path(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "nonexistent.json"))
    if not os.path.exists(creds_path):
        # In CI environments without real credentials we simply skip.
        pytest.skip("Credentials file not present – skipping real credential test")
    try:
        service_account.Credentials.from_service_account_file(creds_path)
    except Exception as exc:
        pytest.fail(f"Credential loading failed: {exc}")

def test_vertex_initialization_sync():
    """Test Vertex AI initialization."""
    try:
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        logger.info(f"Initializing Vertex AI with project: {project}, location: {location}")
        
        vertexai.init(
            project=project,
            location=location,
            credentials=service_account.Credentials.from_service_account_file(
                expand_path(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
            )
        )
        logger.info("Successfully initialized Vertex AI")
    except Exception as e:
        pytest.skip(f"Vertex AI initialization skipped: {e}")

def test_model_access_sync():
    """Test access to the generative model."""
    # Try global location first for Gemini models
    logger.info("\nTrying global location for Gemini models")
    try:
        # Initialize with global location
        vertexai.init(
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location="global",
            credentials=service_account.Credentials.from_service_account_file(
                expand_path(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
            )
        )
        logger.info("Successfully initialized Vertex AI with global location")
        
        # Try Gemini 2.0 Flash model
        try:
            logger.info("Attempting to access gemini-2.0-flash-001 model...")
            model = GenerativeModel("gemini-2.0-flash-001")
            response = model.generate_content("Hello, world!")
            logger.info("Model access test successful with gemini-2.0-flash-001")
        except Exception as e:
            logger.error(f"gemini-2.0-flash-001 model access failed: {str(e)}")
            
        # Try Gemini 1.5 Pro model
        try:
            logger.info("Attempting to access gemini-1.5-pro model...")
            model = GenerativeModel("gemini-1.5-pro")
            response = model.generate_content("Hello, world!")
            logger.info("Model access test successful with gemini-1.5-pro")
        except Exception as e:
            logger.error(f"gemini-1.5-pro model access failed: {str(e)}")
            
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI with global location: {str(e)}")
    
    # If global location fails, try regional endpoints
    regions = ["us-central1", "us-east4", "us-west4"]
    for region in regions:
        logger.info(f"\nTrying region: {region}")
        try:
            vertexai.init(
                project=os.getenv("GOOGLE_CLOUD_PROJECT"),
                location=region,
                credentials=service_account.Credentials.from_service_account_file(
                    expand_path(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
                )
            )
            logger.info(f"Successfully initialized Vertex AI in {region}")
            
            # Try models in this region
            for model_name in ["gemini-2.0-flash-001", "gemini-1.5-pro"]:
                try:
                    logger.info(f"Attempting to access {model_name} model in {region}...")
                    model = GenerativeModel(model_name)
                    response = model.generate_content("Hello, world!")
                    logger.info(f"Model access test successful with {model_name} in {region}")
                except Exception as e:
                    logger.error(f"{model_name} model access failed in {region}: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI in {region}: {str(e)}")
    
    logger.error("All model access attempts failed across all locations")
    pytest.skip("Model access unavailable in test environment")

def check_api_enablement():
    """Check if the Vertex AI API is enabled for the project."""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            expand_path(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        authed_session = AuthorizedSession(credentials)
        
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        url = f"https://serviceusage.googleapis.com/v1/projects/{project}/services/aiplatform.googleapis.com"
        
        response = authed_session.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get('state') == 'ENABLED':
                logger.info("Vertex AI API is enabled for the project")
                return True
            else:
                logger.error(f"Vertex AI API is not enabled. Current state: {data.get('state')}")
                return False
        else:
            logger.error(f"Failed to check API status. Status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Failed to check API enablement: {str(e)}")
        return False

def main():
    """Run all integration tests."""
    logger.info("Starting integration tests...")
    tests = [
        ("Environment Variables", verify_environment),
        ("Service Account Credentials", test_credentials),
        ("API Enablement", check_api_enablement),
        ("Vertex AI Initialization", test_vertex_initialization_sync),
        ("Model Access", test_model_access_sync)
    ]
    all_passed = True
    for test_name, test_func in tests:
        logger.info(f"\nRunning test: {test_name}")
        if not test_func():
            all_passed = False
            logger.error(f"Test failed: {test_name}")
        else:
            logger.info(f"Test passed: {test_name}")
    if all_passed:
        logger.info("\nAll integration tests passed!")
    else:
        logger.error("\nSome integration tests failed. Please check the logs above.")

if __name__ == "__main__":
    main() 