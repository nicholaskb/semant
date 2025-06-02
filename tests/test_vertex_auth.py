import os
import logging
from dotenv import load_dotenv
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def expand_path(path):
    """Expand path variables like $(pwd)."""
    if path.startswith('$(pwd)'):
        return os.path.join(os.getcwd(), path[7:])
    return path

def verify_environment():
    """Verify required environment variables are set."""
    # Debug: Print current working directory
    logger.info(f"Current working directory: {os.getcwd()}")
    
    # Load environment variables from .env file
    load_dotenv(override=True)  # Force override existing variables
    
    # Debug: Print all environment variables
    logger.info("All environment variables:")
    for key, value in os.environ.items():
        if 'GOOGLE' in key:
            logger.info(f"{key}: {value}")
    
    required_vars = [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_PROJECT"
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            logger.error(f"Missing required environment variable: {var}")
            return False
            
        # Expand path if it's the credentials path
        if var == "GOOGLE_APPLICATION_CREDENTIALS":
            value = expand_path(value)
            logger.info(f"Expanded {var}: {value}")
            
        logger.info(f"{var}: {value}")
        
        # If it's the credentials path, check if it exists
        if var == "GOOGLE_APPLICATION_CREDENTIALS":
            if not os.path.exists(value):
                logger.error(f"Credentials file does not exist at: {value}")
                # List contents of the directory
                dir_path = os.path.dirname(value)
                if os.path.exists(dir_path):
                    logger.info(f"Contents of {dir_path}:")
                    for file in os.listdir(dir_path):
                        logger.info(f"- {file}")
                return False
    return True

def test_credentials():
    """Test loading service account credentials."""
    try:
        creds_path = expand_path(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        logger.info(f"Loading credentials from: {creds_path}")
        
        # Check if file exists
        if not os.path.exists(creds_path):
            logger.error(f"Credentials file not found: {creds_path}")
            # List contents of credentials directory
            creds_dir = os.path.dirname(creds_path)
            if os.path.exists(creds_dir):
                logger.info(f"Contents of {creds_dir}:")
                for file in os.listdir(creds_dir):
                    logger.info(f"- {file}")
            return False
            
        # Check file permissions
        perms = oct(os.stat(creds_path).st_mode)[-3:]
        logger.info(f"File permissions: {perms}")
        if perms != "600":
            logger.warning(f"File permissions should be 600, got {perms}")
            
        # Load credentials
        credentials = service_account.Credentials.from_service_account_file(creds_path)
        logger.info("Successfully loaded credentials")
        
        # Verify project ID matches
        if credentials.project_id != os.getenv("GOOGLE_CLOUD_PROJECT"):
            logger.error(f"Project ID mismatch: credentials file has {credentials.project_id}, environment has {os.getenv('GOOGLE_CLOUD_PROJECT')}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Credential loading failed: {str(e)}")
        return False

def test_vertex_initialization():
    """Test Vertex AI initialization."""
    try:
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = "us-central1"  # or your preferred region
        
        logger.info(f"Initializing Vertex AI with project: {project}, location: {location}")
        vertexai.init(
            project=project,
            location=location,
            credentials=service_account.Credentials.from_service_account_file(
                expand_path(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
            )
        )
        logger.info("Successfully initialized Vertex AI")
        return True
    except Exception as e:
        logger.error(f"Vertex AI initialization failed: {str(e)}")
        return False

def test_model_access():
    try:
        model = GenerativeModel("text-bison@002")
        response = model.generate_content("Hello world")
        logger.info(f"Model access test successful: {response.text}")
        return True
    except Exception as e:
        logger.error(f"Model access test failed: {str(e)}")
        return False

def main():
    """Run all authentication tests."""
    logger.info("Starting authentication tests...")
    
    # Run tests
    tests = [
        ("Environment Variables", verify_environment),
        ("Service Account Credentials", test_credentials),
        ("Vertex AI Initialization", test_vertex_initialization),
        ("Model Access", test_model_access)
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
        logger.info("\nAll authentication tests passed!")
    else:
        logger.error("\nSome authentication tests failed. Please check the logs above.")

if __name__ == "__main__":
    main() 