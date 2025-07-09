import os
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import logging
import pickle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def get_gmail_credentials():
    """Get Gmail API credentials."""
    creds = None
    # Check if token.pickle exists
    if os.path.exists('credentials/token.pickle'):
        with open('credentials/token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If credentials are not valid or don't exist, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Allow overriding the default credentials path via environment variable.
            cred_path = os.getenv("GMAIL_OAUTH_CREDENTIALS", "credentials/credentials.json")

            if not os.path.exists(cred_path):
                raise FileNotFoundError(
                    "Gmail API credentials not found. Please follow these steps:\n"
                    "1. Go to Google Cloud Console (https://console.cloud.google.com)\n"
                    "2. Create a new project or select existing one\n"
                    "3. Enable Gmail API\n"
                    "4. Create OAuth 2.0 credentials (Desktop)\n"
                    "5. Download credentials and set GMAIL_OAUTH_CREDENTIALS or place as 'credentials/credentials.json'"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                cred_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for future use
        os.makedirs('credentials', exist_ok=True)
        with open('credentials/token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def create_message(sender, to, subject, message_text):
    """Create a message for an email."""
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

def send_message(service, user_id, message):
    """Send an email message."""
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        logger.info(f"Message Id: {message['id']}")
        return message
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None

def expand_path(path):
    """Expand path variables like $(pwd)."""
    if path.startswith('$(pwd)'):
        return os.path.join(os.getcwd(), path[7:])
    return path

def send_test_email():
    """Send a test email using Vertex AI and Gmail API."""
    try:
        # Initialize Vertex AI
        vertexai.init(
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            credentials=service_account.Credentials.from_service_account_file(
                expand_path(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
            )
        )
        logger.info("Vertex AI initialized successfully")

        # Initialize the model
        model = GenerativeModel("gemini-2.0-flash-001")
        
        # Create email content
        prompt = """
        Write a professional email with the following details:
        - Subject: Test Email from Vertex AI
        - Recipient: nicholas.k.baro@gmail.com
        - Purpose: Testing the email enhancement capabilities
        - Tone: Professional but friendly
        - Include: A brief explanation of what we're testing
        """
        
        # Generate enhanced content
        response = model.generate_content(prompt)
        enhanced_content = response.text
        
        # Get Gmail API credentials
        gmail_creds = get_gmail_credentials()
        service = build('gmail', 'v1', credentials=gmail_creds)
        
        # Create and send the email
        sender = "me"  # This will use the authenticated user's email
        to = "nicholas.k.baro@gmail.com"
        subject = "Test Email from Vertex AI"
        
        message = create_message(sender, to, subject, enhanced_content)
        result = send_message(service, "me", message)
        
        if result:
            logger.info("Email sent successfully!")
            return True
        else:
            logger.error("Failed to send email")
            return False
            
    except Exception as e:
        logger.error(f"Error sending test email: {str(e)}")
        return False

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Send test email
    success = send_test_email()
    if success:
        logger.info("Test email sent successfully!")
    else:
        logger.error("Failed to send test email") 