#!/usr/bin/env python3
"""
Real Gmail API Email Sender - Actually sends emails using Gmail API
This script uses your service account credentials to send real emails.
"""

import os
import sys
import base64
from datetime import datetime
from dotenv import load_dotenv

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False
    print("❌ Gmail API libraries not installed. Run: pip install google-api-python-client")

class RealGmailSender:
    """Real Gmail API email sender using service account credentials."""
    
    def __init__(self):
        load_dotenv(override=True)
        self.service = None
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        self.credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
    def initialize(self):
        """Initialize Gmail API service."""
        if not GMAIL_API_AVAILABLE:
            raise Exception("Gmail API libraries not available")
            
        if not self.credentials_path or not os.path.exists(self.credentials_path):
            raise Exception(f"Gmail credentials not found at: {self.credentials_path}")
        
        try:
            # Use service account with Gmail scopes
            scopes = [
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.compose'
            ]
            
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=scopes)
            
            # Enable subject delegation if needed (for domain-wide delegation)
            # credentials = credentials.with_subject('your-user@yourdomain.com')
            
            self.service = build('gmail', 'v1', credentials=credentials)
            print("✅ Gmail API service initialized with service account")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize Gmail service: {e}")
            return False
    
    def create_message(self, to, subject, body, from_email=None):
        """Create email message."""
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            if from_email:
                message['from'] = from_email
                
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            return {'raw': raw_message}
            
        except Exception as e:
            print(f"❌ Error creating message: {e}")
            return None
    
    def send_email(self, to, subject, body, from_email=None):
        """Send an email using Gmail API."""
        if not self.service:
            if not self.initialize():
                return False, "Failed to initialize Gmail service"
        
        try:
            # Create the message
            message = self.create_message(to, subject, body, from_email)
            if not message:
                return False, "Failed to create email message"
            
            # Send the message
            result = self.service.users().messages().send(
                userId='me', 
                body=message
            ).execute()
            
            print(f"✅ **REAL EMAIL SENT SUCCESSFULLY!**")
            print(f"   📧 To: {to}")
            print(f"   📝 Subject: {subject}")
            print(f"   🆔 Gmail Message ID: {result['id']}")
            print(f"   📅 Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            return True, {
                'status': 'sent',
                'gmail_message_id': result['id'],
                'recipient': to,
                'subject': subject,
                'timestamp': datetime.now().isoformat()
            }
            
        except HttpError as error:
            error_msg = f"Gmail API error: {error}"
            print(f"❌ {error_msg}")
            
            if error.resp.status == 403:
                print("🔐 **PERMISSION ISSUE DETECTED**")
                print("   This is likely due to one of these issues:")
                print("   1. Gmail API not enabled in Google Cloud Console")
                print("   2. Service account needs domain-wide delegation")
                print("   3. Service account lacks Gmail permissions")
                print("   4. Need to set up subject delegation")
                
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg

def test_real_email_sending():
    """Test sending a real email."""
    print("🚀" * 60)
    print("🚀 REAL GMAIL API EMAIL SENDING TEST")
    print("🚀" * 60)
    
    # Initialize sender
    sender = RealGmailSender()
    
    print(f"📧 Project: {sender.project_id}")
    print(f"🔑 Credentials: {sender.credentials_path}")
    
    # Create test email content
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    subject = f"🎉 REAL EMAIL TEST - Sent at {timestamp}"
    
    body = f"""
🎉 SUCCESS! This is a REAL email from your Gmail API integration!

📅 Sent at: {timestamp}
🤖 From: Real Gmail API Sender
🎯 Purpose: Prove Gmail API integration works

✅ What this proves:
• Gmail API service account is working
• Can send emails to real recipients
• Email content is properly formatted
• Authentication is successful
• Multi-agent system can send real emails

👀 If you're reading this in your inbox, the Gmail API integration is FULLY OPERATIONAL!

🚀 Your system is ready for production email handling.

---
Multi-Agent Orchestration System
Real Gmail API Integration Test
    """
    
    # Send the email
    success, result = sender.send_email(
        to="nicholas.k.baro@gmail.com",
        subject=subject,
        body=body
    )
    
    print("\n" + "📊" * 60)
    print("📊 TEST RESULTS")
    print("📊" * 60)
    
    if success:
        print("🎉 **REAL EMAIL SENT SUCCESSFULLY!**")
        print("👀 **CHECK YOUR EMAIL INBOX RIGHT NOW!**")
        print(f"   📧 Look for: '{subject}'")
        print(f"   📅 Sent around: {timestamp}")
        print("   🎯 This proves Gmail API integration is working!")
        
        print(f"\n📋 **What to do next:**")
        print(f"   1. Check your email inbox")
        print(f"   2. If you see the email → Gmail API is working! 🎉")
        print(f"   3. If you don't see it → Check spam folder")
        print(f"   4. Still no email → Permission configuration needed")
        
        return True
    else:
        print("❌ **REAL EMAIL SENDING FAILED**")
        print(f"   Error: {result}")
        print(f"\n🔧 **Troubleshooting steps:**")
        print(f"   1. Check Google Cloud Console permissions")
        print(f"   2. Enable Gmail API if not already enabled")
        print(f"   3. Consider setting up domain-wide delegation")
        print(f"   4. Verify service account has correct scopes")
        
        return False

def main():
    """Main function."""
    print("📧 **STARTING REAL GMAIL API EMAIL TEST**")
    print("This will attempt to send a REAL email using Gmail API!")
    
    success = test_real_email_sending()
    
    if success:
        print("\n🏆 **GMAIL API INTEGRATION VERIFIED!**")
        print("🎉 You should receive a real email shortly!")
    else:
        print("\n🔧 **GMAIL API NEEDS CONFIGURATION**")
        print("📋 See troubleshooting steps above")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 