from typing import Any, Dict, List, Optional
from agents.core.base_agent import BaseAgent
from agents.core.message_types import AgentMessage
from agents.utils.email_integration import EmailIntegration
from loguru import logger
import uuid
from datetime import datetime
import os

try:
    from integrations.vertex_ai_client import get_vertex_client, VertexAIModel
    from integrations.google_cloud_auth import get_auth_manager
except ImportError:
    logger.warning("Enhanced Google Cloud integrations not available, falling back to simulation mode")
    get_vertex_client = None
    VertexAIModel = None
    get_auth_manager = None

class VertexEmailAgent(BaseAgent):
    """
    Agent that enhances email content using Google Vertex AI.

    Features:
    - AI-powered email content enhancement
    - Professional tone improvement
    - Grammar and clarity corrections
    - Multiple AI model support
    """

    CAPABILITIES = {
        "EMAIL_ENHANCEMENT",
        "CONTENT_GENERATION",
        "LANGUAGE_PROCESSING"
    }

    def __init__(self, agent_id: str = "vertex_email_agent"):
        super().__init__(agent_id, self.CAPABILITIES)
        self.sent_emails: List[Dict[str, str]] = []
        self.logger = logger.bind(agent_id=agent_id)

        # Enhanced integration components
        self.vertex_client = None
        self.auth_manager = None
        self.enhanced_mode = False
        
        # Email integration for actual sending
        self.email_integration = EmailIntegration(use_real_email=True)

    async def initialize(self) -> None:
        """Initialize the agent with enhanced Google Cloud integration."""
        await super().initialize()

        # Try to initialize enhanced Google Cloud integration
        if get_vertex_client and get_auth_manager:
            try:
                self.vertex_client = await get_vertex_client()
                self.auth_manager = await get_auth_manager()

                # Validate authentication
                validation = await self.auth_manager.validate_credentials()
                if validation['overall_status'] == 'valid':
                    self.enhanced_mode = True
                    self.logger.info("Vertex Email Agent initialized with enhanced Google Cloud integration")
                else:
                    self.logger.warning("Google Cloud validation failed, falling back to simulation mode")
                    self.enhanced_mode = False

            except Exception as e:
                self.logger.warning(f"Failed to initialize enhanced integration: {e}, falling back to simulation mode")
                self.enhanced_mode = False
        else:
            self.logger.info("Enhanced Google Cloud libraries not available, using simulation mode")
            self.enhanced_mode = False

        if not self.enhanced_mode:
            self.logger.info("Vertex Email Agent initialized in simulation mode")

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages for email operations."""
        try:
            if message.message_type == "send_email":
                email = {
                    "recipient": message.content.get("recipient"),
                    "subject": message.content.get("subject"),
                    "body": message.content.get("body"),
                }

                # ----------------------------------------------------
                # Validation  – tests expect an *error* status when the
                # recipient address is invalid or subject/body are empty.
                # ----------------------------------------------------
                if (
                    not email["recipient"]
                    or "@" not in email["recipient"]
                    or not email["subject"]
                    or not email["body"]
                ):
                    return AgentMessage(
                        message_id=str(uuid.uuid4()),
                        sender_id=self.agent_id,
                        recipient_id=message.sender_id,
                        content={"status": "error", "message": "Invalid email parameters"},
                        timestamp=datetime.now(),
                        message_type="send_email_response",
                    )

                await self.send_email(**email)

                response_payload = {"status": "sent", **email, "knowledge_graph": True}

                return AgentMessage(
                    message_id=str(uuid.uuid4()),
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    content=response_payload,
                    timestamp=datetime.now(),
                    message_type="send_email_response",
                )
            elif message.message_type == "enhance_email":
                content = message.content.get("content", "")
                enhanced = await self.enhance_email_content(content)
                return AgentMessage(
                    message_id=str(uuid.uuid4()),
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    content={"enhanced_content": enhanced},
                    timestamp=datetime.now(),
                    message_type="enhance_email_response",
                )
            else:
                # Unknown message type – tests expect status "error"
                return AgentMessage(
                    message_id=str(uuid.uuid4()),
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    content={"status": "error", "message": f"Unsupported message_type {message.message_type}"},
                    message_type="error_response",
                    timestamp=datetime.now(),
                )
        except Exception as e:
            return AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "error", "message": str(e)},
                timestamp=datetime.now(),
                message_type="error_response",
            )

    async def send_email(self, recipient: str, subject: str, body: str) -> None:
        """Send an email using EmailIntegration (real or simulated based on configuration)."""
        try:
            # Send email using EmailIntegration
            result = self.email_integration.send_email(
                recipient_id=recipient,
                subject=subject,
                body=body,
                force_real=True
            )
            
            # Log the result
            if result.get("status") == "sent_real":
                self.logger.info(
                    f"Successfully sent email to {recipient} with subject '{subject}'"
                )
            else:
                self.logger.info(
                    f"Email simulated for {recipient} with subject '{subject}' (status: {result.get('status')})"
                )
            
            # Track sent emails
            self.sent_emails.append(
                {
                    "recipient": recipient,
                    "subject": subject,
                    "body": body,
                    "status": result.get("status", "unknown"),
                    "timestamp": result.get("timestamp", datetime.now().isoformat())
                }
            )
            
            # Log the email sending activity to knowledge graph
            if self.knowledge_graph:
                await self.knowledge_graph.update_graph(
                    {
                        f"email:{len(self.sent_emails)}": {
                            "recipient": recipient,
                            "subject": subject,
                            "body": body,
                            "status": result.get("status", "unknown"),
                            "timestamp": result.get("timestamp", datetime.now().isoformat())
                        }
                    }
                )
        except Exception as e:
            self.logger.error(f"Failed to send email to {recipient}: {e}")
            # Still track the attempt
            self.sent_emails.append(
                {
                    "recipient": recipient,
                    "subject": subject,
                    "body": body,
                    "status": "error",
                    "error": str(e)
                }
            )
            raise

    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        if self.knowledge_graph:
            await self.knowledge_graph.update_graph(update_data)

    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        if not self.knowledge_graph:
            return {}
        return await self.knowledge_graph.query_graph(query.get("sparql", ""))

    async def enhance_email_content(self, content: str, model: Optional[str] = None) -> str:
        """
        Enhance email content using Vertex AI generative models.

        Args:
            content: Original email content to enhance
            model: Optional model to use (defaults to Gemini Flash)

        Returns:
            str: Enhanced email content with improved clarity and professionalism

        Raises:
            ValueError: If content is empty
        """
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")

        # Use enhanced Vertex AI client if available
        if self.enhanced_mode and self.vertex_client:
            return await self._enhance_with_vertex_ai(content, model)
        else:
            return await self._enhance_basic(content)

    async def _enhance_with_vertex_ai(self, content: str, model: Optional[str] = None) -> str:
        """Enhance content using real Vertex AI."""
        try:
            # Select model
            if model and VertexAIModel:
                try:
                    ai_model = VertexAIModel(model)
                except ValueError:
                    ai_model = VertexAIModel.GEMINI_FLASH
            else:
                ai_model = VertexAIModel.GEMINI_FLASH

            # Create enhancement prompt
            enhancement_prompt = f"""
            Enhance the following email content for clarity, professionalism, and engagement.
            Maintain the original intent while improving readability, tone, and effectiveness.

            Original content:
            {content}

            Please provide an enhanced version that is:
            - More professional and polished
            - Clear and concise
            - Engaging and appropriate for the context
            - Grammatically correct

            Enhanced content:
            """

            # Generate enhanced content using Vertex AI
            self.logger.info(f"Enhancing email content with {ai_model.value}...")

            response = await self.vertex_client.generate_text(
                prompt=enhancement_prompt,
                model=ai_model,
                max_output_tokens=1000,
                temperature=0.7
            )

            if response.success and response.content:
                enhanced_content = response.content.strip()

                # Validate enhancement quality
                if len(enhanced_content) < len(content) * 0.5:
                    self.logger.warning("Enhancement too short, falling back to basic enhancement")
                    return await self._enhance_basic(content)

                self.logger.info(f"Successfully enhanced email content using {ai_model.value}")
                return enhanced_content
            else:
                self.logger.warning(f"Vertex AI enhancement failed: {response.error_message}")
                return await self._enhance_basic(content)

        except Exception as e:
            self.logger.error(f"Vertex AI enhancement failed: {e}")
            return await self._enhance_basic(content)

    async def _enhance_basic(self, content: str) -> str:
        """Apply basic enhancement rules when AI is not available."""
        self.logger.info("Applying basic email enhancement")

        enhanced = content.strip()

        # Basic improvements
        if enhanced:
            # Capitalize first letter
            if not enhanced[0].isupper():
                enhanced = enhanced[0].upper() + enhanced[1:]

            # Ensure ending punctuation
            if not enhanced.endswith(('.', '!', '?', ':')):
                enhanced += '.'

            # Add polite closing for short messages
            if (len(enhanced) < 100 and
                not any(word in enhanced.lower() for word in
                       ['thank', 'regards', 'sincerely', 'best', 'cheers', 'yours'])):
                enhanced += ' Thank you.'

        return enhanced

    def _validate_email_params(self, recipient: str, subject: str, body: str) -> bool:
        """
        Validate email parameters.

        Args:
            recipient: Email recipient address
            subject: Email subject line
            body: Email body content

        Returns:
            True if parameters are valid, False otherwise
        """
        # Check recipient format
        if not recipient or "@" not in recipient:
            return False

        # Check subject and body are not empty
        if not subject or not subject.strip():
            return False

        if not body or not body.strip():
            return False

        return True

    def _simulate_ai_enhancement(self, content: str) -> str:
        """
        Simulate AI enhancement for testing purposes.
        In production, this would be replaced with actual Vertex AI calls.
        """
        # Simple enhancement simulation
        enhanced = content.strip()

        # Add professional greeting if missing
        if not enhanced.lower().startswith(('hello', 'hi', 'dear', 'greetings')):
            enhanced = f"Dear recipient,\n\n{enhanced}"

        # Ensure proper capitalization
        sentences = enhanced.split('. ')
        enhanced_sentences = []
        for sentence in sentences:
            if sentence and not sentence[0].isupper():
                sentence = sentence[0].upper() + sentence[1:]
            enhanced_sentences.append(sentence)
        enhanced = '. '.join(enhanced_sentences)

        # Add professional closing if missing
        if not any(word in enhanced.lower() for word in ['thank', 'regards', 'sincerely', 'best']):
            enhanced += '\n\nBest regards'

        # Ensure proper punctuation
        if not enhanced.endswith('.'):
            enhanced += '.'

        return enhanced

