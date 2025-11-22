#!/usr/bin/env python3
"""
Send Confirmation Email - Simple test to verify email sending works
Check your inbox after running this script!
"""

import sys
import os
from datetime import datetime

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.utils.email_integration import EmailIntegration

def send_confirmation_email():
    """Send a clear confirmation email that's easy to verify."""
    print("📧 **SENDING CONFIRMATION EMAIL**")
    print("=" * 50)
    
    # Initialize email integration
    email = EmailIntegration()
    
    # Create a clear, easy to spot email
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    subject = "✅ EMAIL SYSTEM WORKING - Sent at " + timestamp
    
    body = f"""
🎉 EMAIL SYSTEM CONFIRMATION

This email confirms that your email integration is working perfectly!

📅 Sent at: {timestamp}
🤖 From: Multi-Agent Email System
🎯 Purpose: Verify email functionality

✅ What this proves:
• Email integration is operational
• Can send emails to real recipients  
• Email content is properly formatted
• System timestamp is working
• Email subject line is clear

👀 If you're reading this in your inbox, everything is working! 

🚀 Your email system is ready for production use.

---
Multi-Agent Orchestration System
Email Integration Test
    """
    
    try:
        result = email.send_email(
            recipient_id="nicholas.k.baro@gmail.com",
            subject=subject,
            body=body
        )
        
        print("🎉 **CONFIRMATION EMAIL SENT!**")
        print(f"   📧 To: {result['recipient']}")
        print(f"   📝 Subject: {result['subject']}")
        print(f"   📅 Timestamp: {result['timestamp']}")
        print(f"   🆔 Message ID: {result['message_id']}")
        
        print("\n" + "👀" * 50)
        print("👀 **CHECK YOUR EMAIL INBOX NOW!**")
        print("👀" * 50)
        
        print("\n📋 **What to look for:**")
        print(f"   📧 Subject: '{subject}'")
        print(f"   📅 Sent around: {timestamp}")
        print(f"   📨 Should arrive within 1-2 minutes")
        
        print("\n✅ **If you see this email in your inbox:**")
        print("   🎉 Email sending is 100% working!")
        print("   🎯 System is ready for production")
        print("   ✅ Multi-agent email coordination is operational")
        
        print("\n❌ **If you don't see the email:**")
        print("   📪 Check spam/junk folder")
        print("   ⏰ Wait a few more minutes")
        print("   🔧 Check email configuration")
        
        return True, result
        
    except Exception as e:
        print(f"❌ **FAILED TO SEND EMAIL**: {e}")
        return False, str(e)

def main():
    """Main function to send confirmation email."""
    print("🚀" * 50)
    print("🚀 EMAIL CONFIRMATION TEST")
    print("🚀" * 50)
    
    print("📧 This will send a confirmation email to nicholas.k.baro@gmail.com")
    print("📧 Check your inbox to verify the email system is working!")
    
    success, result = send_confirmation_email()
    
    if success:
        print("\n" + "🎉" * 50)
        print("🎉 EMAIL SENT SUCCESSFULLY!")
        print("🎉" * 50)
        print("👀 Go check your email inbox right now!")
        print("✅ Email system is fully operational!")
    else:
        print("\n" + "❌" * 50)
        print("❌ EMAIL SENDING FAILED")
        print("❌" * 50)
        print(f"Error: {result}")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 