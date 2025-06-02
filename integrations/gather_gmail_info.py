import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from dotenv import load_dotenv
import subprocess
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gmail_research.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def expand_path(path):
    """Expand path variables like $(pwd)."""
    if path.startswith('$(pwd)'):
        return os.path.join(os.getcwd(), path[7:])
    return path

def check_gcloud_config():
    """Check gcloud configuration."""
    try:
        # Get current project
        project = subprocess.check_output(
            ['gcloud', 'config', 'get-value', 'project'],
            stderr=subprocess.STDOUT
        ).decode().strip()
        
        # Get account
        account = subprocess.check_output(
            ['gcloud', 'config', 'get-value', 'account'],
            stderr=subprocess.STDOUT
        ).decode().strip()
        
        logger.info(f"Current gcloud project: {project}")
        logger.info(f"Current gcloud account: {account}")
        
        return project, account
    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking gcloud config: {e.output.decode()}")
        return None, None

def check_api_enablement(project_id):
    """Check if Gmail API is enabled."""
    try:
        result = subprocess.check_output(
            ['gcloud', 'services', 'list', '--enabled', '--project', project_id],
            stderr=subprocess.STDOUT
        ).decode()
        
        logger.info("Enabled APIs:")
        logger.info(result)
        
        return 'gmail.googleapis.com' in result
    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking API enablement: {e.output.decode()}")
        return False

def check_service_account_permissions(project_id, service_account):
    """Check service account permissions."""
    try:
        result = subprocess.check_output(
            ['gcloud', 'projects', 'get-iam-policy', project_id,
             '--flatten=bindings[].members',
             f'--format=table(bindings.role,bindings.members)',
             f'--filter=bindings.members:{service_account}'],
            stderr=subprocess.STDOUT
        ).decode()
        
        logger.info(f"Service account permissions for {service_account}:")
        logger.info(result)
        
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Error checking service account permissions: {e.output.decode()}")
        return None

def analyze_credentials():
    """Analyze credential files and permissions."""
    try:
        # Check service account credentials
        sa_path = expand_path(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        if os.path.exists(sa_path):
            logger.info(f"Service account credentials found at: {sa_path}")
            with open(sa_path, 'r') as f:
                sa_info = json.load(f)
                logger.info(f"Service account email: {sa_info.get('client_email')}")
                logger.info(f"Project ID: {sa_info.get('project_id')}")
        else:
            logger.error(f"Service account credentials not found at: {sa_path}")
        
        # Check OAuth credentials
        oauth_path = "credentials/credentials.json"
        if os.path.exists(oauth_path):
            logger.info(f"OAuth credentials found at: {oauth_path}")
            with open(oauth_path, 'r') as f:
                oauth_info = json.load(f)
                logger.info(f"OAuth client type: {oauth_info.get('type')}")
                logger.info(f"Client ID: {oauth_info.get('client_id')}")
        else:
            logger.error(f"OAuth credentials not found at: {oauth_path}")
        
        # Check token file
        token_path = "credentials/token.pickle"
        if os.path.exists(token_path):
            logger.info(f"Token file found at: {token_path}")
            permissions = oct(os.stat(token_path).st_mode)[-3:]
            logger.info(f"Token file permissions: {permissions}")
        else:
            logger.info("No token file found (this is normal for first-time setup)")
            
    except Exception as e:
        logger.error(f"Error analyzing credentials: {str(e)}")

def check_environment():
    """Check environment variables and configuration."""
    load_dotenv()
    
    required_vars = [
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_LOCATION"
    ]
    
    logger.info("Environment Variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"{var}: {value}")
        else:
            logger.error(f"{var} not set")

def main():
    """Main function to gather Gmail API information."""
    logger.info("Starting Gmail API configuration analysis...")
    
    # Check environment
    check_environment()
    
    # Check gcloud configuration
    project_id, account = check_gcloud_config()
    
    if project_id:
        # Check API enablement
        api_enabled = check_api_enablement(project_id)
        logger.info(f"Gmail API enabled: {api_enabled}")
        
        # Check service account permissions
        service_account = "semant-vertex-sa@semant-vertex-ai.iam.gserviceaccount.com"
        permissions = check_service_account_permissions(project_id, service_account)
        
        # Analyze credentials
        analyze_credentials()
        
        # Summary
        logger.info("\nConfiguration Summary:")
        logger.info(f"Project ID: {project_id}")
        logger.info(f"Account: {account}")
        logger.info(f"Gmail API Enabled: {api_enabled}")
        logger.info(f"Service Account: {service_account}")
        
        if not api_enabled:
            logger.info("\nRequired Actions:")
            logger.info("1. Enable Gmail API:")
            logger.info("   gcloud services enable gmail.googleapis.com --project={project_id}")
            logger.info("2. Set up OAuth consent screen")
            logger.info("3. Create OAuth credentials")
            logger.info("4. Configure service account permissions")
    else:
        logger.error("Could not determine project ID. Please check gcloud configuration.")

if __name__ == "__main__":
    main() 