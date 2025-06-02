import os
import asyncio
from loguru import logger
from agents.utils.email_integration import EmailIntegration
from dotenv import load_dotenv

async def demonstrate_email():
    """Demonstrate the email integration functionality."""
    try:
        # Initialize environment
        load_dotenv()
        
        # Log current configuration
        logger.info("Starting email demonstration")
        logger.info(f"Using credentials from: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
        
        # Initialize email integration
        email = EmailIntegration()
        await email.initialize()
        
        # Test 1: Send a simple email
        logger.info("Test 1: Sending simple email")
        result1 = await email.send_email(
            to="nicholas.k.baro@gmail.com",
            subject="Email Integration Test",
            body="This is a test email to demonstrate the integration is working."
        )
        logger.info(f"Test 1 Result: {result1}")
        
        # Test 2: Send an email with formatted content
        logger.info("Test 2: Sending formatted email")
        result2 = await email.send_email(
            to="nicholas.k.baro@gmail.com",
            subject="Formatted Email Test",
            body="""
            Hello,
            
            This is a formatted test email with:
            - Multiple lines
            - Bullet points
            - Proper spacing
            
            Best regards,
            Email Integration Test
            """
        )
        logger.info(f"Test 2 Result: {result2}")
        
        # Print summary
        logger.info("Email demonstration completed")
        logger.info(f"Test 1 Status: {result1.get('status', 'unknown')}")
        logger.info(f"Test 2 Status: {result2.get('status', 'unknown')}")
        
    except Exception as e:
        logger.error(f"Demonstration failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Configure logger
    logger.add("email_demo.log", rotation="1 MB")
    
    # Run demonstration
    asyncio.run(demonstrate_email()) 