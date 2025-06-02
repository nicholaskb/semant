import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from dotenv import load_dotenv

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

def verify_gmail_api():
    """Verify Gmail API configuration and access."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get project configuration
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        credentials_path = expand_path(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        
        logger.info(f"Verifying Gmail API for project: {project_id}")
        logger.info(f"Using credentials from: {credentials_path}")
        
        # Check if credentials file exists
        if not os.path.exists(credentials_path):
            logger.error(f"Credentials file not found at: {credentials_path}")
            return False
            
        # Load service account credentials
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        
        # Build service
        service = build('gmail', 'v1', credentials=credentials)
        
        # Try to get Gmail API settings
        try:
            settings = service.users().getSettings(userId='me').execute()
            logger.info("Successfully accessed Gmail API settings")
            logger.info(f"Settings: {settings}")
            return True
        except HttpError as error:
            logger.error(f"Error accessing Gmail API: {error}")
            if error.resp.status == 403:
                logger.error("Permission denied. Please check if Gmail API is enabled and service account has correct permissions.")
            elif error.resp.status == 404:
                logger.error("Gmail API not found. Please check if API is enabled in the project.")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying Gmail API: {str(e)}")
        return False

def check_oauth_config():
    """Check OAuth configuration."""
    try:
        # Check for OAuth credentials
        oauth_credentials_path = "credentials/credentials.json"
        if not os.path.exists(oauth_credentials_path):
            logger.error(f"OAuth credentials not found at: {oauth_credentials_path}")
            logger.info("Please follow these steps to set up OAuth credentials:")
            logger.info("1. Go to Google Cloud Console (https://console.cloud.google.com)")
            logger.info("2. Navigate to APIs & Services > Credentials")
            logger.info("3. Click 'Create Credentials' > 'OAuth client ID'")
            logger.info("4. Choose 'Desktop app' as application type")
            logger.info("5. Download credentials and save as 'credentials/credentials.json'")
            return False
            
        logger.info("OAuth credentials found")
        return True
        
    except Exception as e:
        logger.error(f"Error checking OAuth configuration: {str(e)}")
        return False

def verify_token_storage():
    """Verify token storage configuration."""
    try:
        token_path = "credentials/token.pickle"
        if os.path.exists(token_path):
            logger.info(f"Token file found at: {token_path}")
            # Check file permissions
            permissions = oct(os.stat(token_path).st_mode)[-3:]
            logger.info(f"Token file permissions: {permissions}")
            if permissions != "600":
                logger.warning("Token file should have restricted permissions (600)")
        else:
            logger.info("No token file found. This is normal for first-time setup.")
        return True
    except Exception as e:
        logger.error(f"Error verifying token storage: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting Gmail API configuration verification...")
    
    # Verify Gmail API access
    api_verified = verify_gmail_api()
    logger.info(f"Gmail API verification: {'Success' if api_verified else 'Failed'}")
    
    # Check OAuth configuration
    oauth_verified = check_oauth_config()
    logger.info(f"OAuth configuration check: {'Success' if oauth_verified else 'Failed'}")
    
    # Verify token storage
    token_verified = verify_token_storage()
    logger.info(f"Token storage verification: {'Success' if token_verified else 'Failed'}")
    
    # Summary
    logger.info("\nVerification Summary:")
    logger.info(f"Gmail API Access: {'✓' if api_verified else '✗'}")
    logger.info(f"OAuth Configuration: {'✓' if oauth_verified else '✗'}")
    logger.info(f"Token Storage: {'✓' if token_verified else '✗'}")
    
    if not (api_verified and oauth_verified):
        logger.info("\nTroubleshooting Steps:")
        logger.info("1. Enable Gmail API in Google Cloud Console")
        logger.info("2. Set up OAuth consent screen")
        logger.info("3. Create OAuth 2.0 credentials")
        logger.info("4. Download and save credentials")
        logger.info("5. Run the verification script again") 