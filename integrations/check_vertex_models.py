import os
import logging
from dotenv import load_dotenv
from google.cloud import aiplatform
from vertexai.preview.generative_models import GenerativeModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_vertex_ai_setup():
    """Check Vertex AI setup and available models."""
    try:
        # Load environment variables
        load_dotenv(override=True)
        
        # Initialize Vertex AI
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = "us-central1"
        
        logger.info(f"Initializing Vertex AI with project: {project}, location: {location}")
        aiplatform.init(project=project, location=location)
        
        # Try to initialize a text-bison model
        logger.info("Attempting to initialize text-bison model...")
        try:
            model = GenerativeModel("text-bison@002")
            logger.info("Successfully initialized text-bison model!")
            return True
        except Exception as model_error:
            logger.error(f"Error initializing text-bison model: {str(model_error)}")
            
            # Check if it's an API enablement issue
            if "API" in str(model_error) and "not enabled" in str(model_error):
                logger.warning("Vertex AI API may not be fully enabled")
                logger.info("Run: gcloud services enable aiplatform.googleapis.com")
            
            # Check if it's a model access issue
            elif "not found" in str(model_error) or "does not have access" in str(model_error):
                logger.warning("Model access issue detected")
                logger.info("Visit: https://console.cloud.google.com/vertex-ai/model-garden")
                logger.info("Select text-bison model and click 'Enable' or 'Request Access'")
            
            return False
            
    except Exception as e:
        logger.error(f"Error checking Vertex AI setup: {str(e)}")
        return False

def main():
    """Main function to check Vertex AI setup."""
    logger.info("Starting Vertex AI model check")
    
    if check_vertex_ai_setup():
        logger.info("Vertex AI setup check completed successfully")
        logger.info("You can now use the text-bison model in your application")
    else:
        logger.error("Vertex AI setup check failed")
        logger.info("\nNext steps:")
        logger.info("1. Enable Vertex AI API:")
        logger.info("   gcloud services enable aiplatform.googleapis.com")
        logger.info("2. Request access to text-bison model:")
        logger.info("   Visit: https://console.cloud.google.com/vertex-ai/model-garden")
        logger.info("3. Check project permissions and quotas")
        logger.info("4. Run this script again after completing the steps")

if __name__ == "__main__":
    main() 