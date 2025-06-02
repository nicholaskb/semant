import asyncio
import os
from dotenv import load_dotenv
from agents.utils.email_integration import EmailIntegration
from loguru import logger

def test_vertex_email():
    """Test email sending with Vertex AI enhancement."""
    logger.info("Starting Vertex AI email integration test...")
    
    # Initialize email integration
    email = EmailIntegration()
    
    # Test email content
    test_content = {
        "recipient": "nicholas.k.baro@gmail.com",
        "subject": "Test Email with Vertex AI Enhancement",
        "body": """
        Hello,
        
        This is a test email to verify the Vertex AI integration.
        The content should be enhanced by Vertex AI before sending.
        
        Best regards,
        Test System
        """
    }
    
    # Send the email
    logger.info("Sending test email...")
    email.send_email(
        recipient=test_content["recipient"],
        subject=test_content["subject"],
        body=test_content["body"]
    )
    
    # Log the result
    logger.info("Email sent successfully with Vertex AI enhancement")

def say_hi_from_kg():
    """Send an email with a message from the knowledge graph."""
    logger.info("Sending 'Hi from the Knowledge Graph' email...")
    
    # Initialize email integration
    email = EmailIntegration()
    
    # Email content
    kg_message = {
        "recipient": "nicholas.k.baro@gmail.com",
        "subject": "Hi from the Knowledge Graph",
        "body": """
        Hello,
        
        Hi from the knowledge graph!
        
        Best regards,
        Vertex Agent
        """
    }
    
    # Send the email
    email.send_email(
        recipient=kg_message["recipient"],
        subject=kg_message["subject"],
        body=kg_message["body"]
    )
    
    # Log the result
    logger.info("'Hi from the Knowledge Graph' email sent successfully")

if __name__ == "__main__":
    # Configure logger
    logger.add("logs/vertex_email_test.log", rotation="1 day")
    
    # Load environment variables
    load_dotenv()
    
    # Run the tests
    test_vertex_email()
    say_hi_from_kg() 