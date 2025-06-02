import os
import pytest
from dotenv import load_dotenv

def setup_environment():
    """Set up environment variables for testing."""
    # Load .env file
    load_dotenv(override=True)
    
    # Set Google Cloud environment variables
    os.environ["GOOGLE_CLOUD_PROJECT"] = "baa-roo"
    os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(
        os.getcwd(), "credentials.json"
    )
    
    # Print environment for debugging
    print("\nEnvironment Variables:")
    print(f"GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    print(f"GOOGLE_CLOUD_LOCATION: {os.getenv('GOOGLE_CLOUD_LOCATION')}")
    print(f"GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
    
    # Verify credentials file exists
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if os.path.exists(creds_path):
        print(f"\nCredentials file exists at: {creds_path}")
        print(f"File permissions: {oct(os.stat(creds_path).st_mode)[-3:]}")
    else:
        print(f"\nWARNING: Credentials file not found at: {creds_path}")

if __name__ == "__main__":
    # Set up environment
    setup_environment()
    
    # Run the tests
    pytest.main(["-v", "scratch_space/test_vertex_integration.py"]) 