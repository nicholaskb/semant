import os
import json
from pathlib import Path
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_credentials_directory():
    """Create credentials directory if it doesn't exist."""
    creds_dir = Path('credentials')
    creds_dir.mkdir(exist_ok=True)
    logger.info(f"Credentials directory: {creds_dir.absolute()}")
    return creds_dir

def setup_env_file():
    """Create or update .env file with required variables."""
    env_path = Path('.env')
    env_vars = {
        'GOOGLE_CLOUD_PROJECT': 'semant-vertex-ai',
        'GOOGLE_APPLICATION_CREDENTIALS': 'credentials/credentials.json',
        'GOOGLE_CLOUD_LOCATION': 'us-central1'
    }
    
    if env_path.exists():
        # Load existing variables
        load_dotenv()
        existing_vars = {key: os.getenv(key) for key in env_vars.keys()}
        # Update only if different
        env_vars.update({k: v for k, v in existing_vars.items() if v != env_vars.get(k)})
    
    # Write to .env file
    with open(env_path, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    logger.info(f"Environment variables configured in {env_path.absolute()}")

def verify_credentials():
    """Verify that credentials file exists and is valid JSON."""
    creds_path = Path('credentials/credentials.json')
    if not creds_path.exists():
        logger.error("Credentials file not found. Please download from Google Cloud Console.")
        logger.info("1. Go to Google Cloud Console")
        logger.info("2. Navigate to APIs & Services > Credentials")
        logger.info("3. Create OAuth 2.0 Client ID")
        logger.info("4. Download JSON and save as credentials/credentials.json")
        return False
    
    try:
        with open(creds_path) as f:
            json.load(f)
        logger.info("Credentials file is valid JSON")
        return True
    except json.JSONDecodeError:
        logger.error("Credentials file is not valid JSON")
        return False

def main():
    """Main setup function."""
    logger.info("Starting Gmail API configuration setup...")
    
    # Create credentials directory
    setup_credentials_directory()
    
    # Setup environment variables
    setup_env_file()
    
    # Verify credentials
    if verify_credentials():
        logger.info("Gmail API configuration setup complete!")
    else:
        logger.error("Gmail API configuration setup incomplete. Please follow the instructions above.")

if __name__ == "__main__":
    main() 