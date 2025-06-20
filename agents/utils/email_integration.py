import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict, Any
import os
import getpass

class EmailIntegration:
    """Email integration functionality with real email sending capability."""

    def __init__(self, use_real_email=False):
        self.use_real_email = use_real_email
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = None
        self.sender_password = None
        
        # Try to get credentials from environment
        self.sender_email = os.getenv('EMAIL_SENDER')
        self.sender_password = os.getenv('EMAIL_PASSWORD')

    def _setup_smtp_credentials(self):
        """Setup SMTP credentials if not already configured."""
        if not self.sender_email:
            print("📧 **SMTP EMAIL SETUP REQUIRED**")
            print("To send real emails, please provide credentials:")
            self.sender_email = input("📧 Enter your Gmail address: ").strip()
            
        if not self.sender_password:
            self.sender_password = getpass.getpass("🔐 Enter your Gmail password (or app password): ")
            
        return bool(self.sender_email and self.sender_password)

    def _send_real_email(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        """Send a real email using SMTP."""
        try:
            if not self._setup_smtp_credentials():
                raise Exception("Failed to setup SMTP credentials")
            
            # Create message
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = recipient
            message["Subject"] = subject
            
            # Add body to email
            message.attach(MIMEText(body, "plain"))
            
            # Create secure connection and send email
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.sender_email, self.sender_password)
                text = message.as_string()
                server.sendmail(self.sender_email, recipient, text)
            
            print(f"✅ **REAL EMAIL SENT!** From {self.sender_email} to {recipient}")
            
            return {
                "status": "sent_real",
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "timestamp": datetime.now().isoformat(),
                "message_id": f"smtp_{hash(recipient + subject)}",
                "method": "SMTP"
            }
            
        except Exception as e:
            print(f"❌ Failed to send real email: {e}")
            # Fall back to simulation
            return self._send_simulated_email(recipient, subject, body)

    def _send_simulated_email(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        """Send a simulated email (original behavior)."""
        print(f"📧 [SIMULATED] Email sent to {recipient}: {subject}")
        
        return {
            "status": "sent_simulated",
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "timestamp": datetime.now().isoformat(),
            "message_id": f"sim_{hash(recipient + subject)}",
            "method": "SIMULATION"
        }

    def send_email(self, recipient_id: Optional[str] = None, recipient: Optional[str] = None, 
                   subject: str = "", body: str = "", force_real: bool = False) -> Dict[str, Any]:
        """
        Send an email with backward compatible parameter support.
        
        Args:
            recipient_id: New parameter name (preferred for tests)
            recipient: Legacy parameter name (backward compatibility)
            subject: Email subject
            body: Email body content
            force_real: Force real email sending even if use_real_email=False
            
        Returns:
            dict: Email sending result with status and metadata
            
        Raises:
            ValueError: If neither recipient_id nor recipient is provided
        """
        # Determine actual recipient from parameters
        actual_recipient = recipient_id or recipient
        if not actual_recipient:
            raise ValueError("Must provide either 'recipient_id' or 'recipient' parameter")
        
        # Decide whether to send real or simulated email
        if self.use_real_email or force_real:
            return self._send_real_email(actual_recipient, subject, body)
        else:
            return self._send_simulated_email(actual_recipient, subject, body)

    def enable_real_email(self):
        """Enable real email sending for this instance."""
        self.use_real_email = True
        print("✅ Real email sending enabled")

    def disable_real_email(self):
        """Disable real email sending (use simulation)."""
        self.use_real_email = False
        print("✅ Email simulation mode enabled")

    def receive_email(self) -> str:
        """Stub method to simulate receiving an email."""
        return "Stub email received." 