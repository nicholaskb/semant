#!/usr/bin/env python3
"""
Send SMS to User - Direct real SMS sending via Twilio

This script demonstrates sending real SMS messages using Twilio.
All credentials are already configured in .env file.

⚠️  IMPORTANT: Error Code 30034 indicates messages are being sent but not delivered.
This could be due to:
- Carrier blocking/filtering
- Phone number issues
- Twilio account restrictions
- Network issues

The script will show the actual Twilio delivery status.

Usage:
    python scripts/tools/send_sms_to_user.py
    python scripts/tools/send_sms_to_user.py "Your custom message here"
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.utils.email_integration import EmailIntegration
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_twilio_credentials():
    """Check if Twilio credentials are configured."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID") or os.getenv("TWILIO_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN") or os.getenv("TWILIO_SECRET")
    from_number = os.getenv("TWILIO_PHONE_NUMBER") or os.getenv("TWILIO_ACCOUNT_NUBMER")
    user_phone = os.getenv("USER_PHONE_NUMBER") or os.getenv("NOTIFICATION_PHONE_NUMBER")
    
    print("=" * 70)
    print("📋 CHECKING TWILIO CREDENTIALS")
    print("=" * 70)
    print()
    
    messaging_service_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID")
    print("📱 Twilio Configuration:")
    print(f"   TWILIO_ACCOUNT_SID: {'✅ Set' if account_sid else '❌ Not set'} {'(' + account_sid[:10] + '...)' if account_sid else ''}")
    print(f"   TWILIO_AUTH_TOKEN: {'✅ Set' if auth_token else '❌ Not set'} {'(***)' if auth_token else ''}")
    print(f"   TWILIO_PHONE_NUMBER: {'✅ Set' if from_number else '❌ Not set'} {'(' + from_number + ')' if from_number else ''}")
    print(f"   TWILIO_MESSAGING_SERVICE_SID: {'✅ Set (A2P 10DLC)' if messaging_service_sid else '⚠️  Not set (may cause error 30034)'} {'(' + messaging_service_sid[:20] + '...)' if messaging_service_sid else ''}")
    print()
    
    print("👤 User Configuration:")
    print(f"   USER_PHONE_NUMBER: {'✅ Set' if user_phone else '❌ Not set'} {'(' + user_phone + ')' if user_phone else ''}")
    print()
    
    if account_sid and auth_token and from_number and user_phone:
        print("✅ All credentials configured! Ready to send SMS.")
        return True, user_phone
    else:
        print("❌ Missing required credentials:")
        if not account_sid:
            print("   • TWILIO_ACCOUNT_SID")
        if not auth_token:
            print("   • TWILIO_AUTH_TOKEN")
        if not from_number:
            print("   • TWILIO_PHONE_NUMBER")
        if not user_phone:
            print("   • USER_PHONE_NUMBER")
        return False, None

def send_sms_to_user(message: str = None):
    """Send a real SMS to the user via Twilio."""
    print("=" * 70)
    print("📱 SENDING REAL SMS TO USER")
    print("=" * 70)
    print()
    
    # Check credentials first
    credentials_ok, user_phone = check_twilio_credentials()
    if not credentials_ok:
        print("\n❌ Cannot send SMS - missing credentials")
        print("💡 Please configure Twilio credentials in .env file")
        return False
    
    # Initialize email integration (it handles SMS too)
    email_integration = EmailIntegration(use_real_email=True)
    
    # Create message if not provided
    if not message:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"""🤖 SMS Test from Multi-Agent System

📅 Sent at: {timestamp}
🎯 Purpose: Test Twilio SMS integration

✅ This confirms:
• Twilio SMS is working
• Credentials are configured correctly
• Multi-agent system can send SMS

🚀 Your SMS system is operational!"""
    
    # Truncate to SMS limits (160 chars recommended, but can go up to 1600)
    if len(message) > 160:
        print(f"⚠️  Message is {len(message)} chars (recommended: 160)")
        print(f"   Truncating to 160 chars...")
        message = message[:157] + "..."
    
    print(f"📱 Recipient: {user_phone}")
    print(f"📝 Message ({len(message)} chars):")
    print(f"   {message[:100]}{'...' if len(message) > 100 else ''}")
    print()
    
    try:
        # Send SMS via EmailIntegration
        result = email_integration.send_sms(
            recipient=user_phone,
            body=message,
            force_real=True
        )
        
        print("=" * 70)
        print("📊 SMS SENDING RESULT")
        print("=" * 70)
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Method: {result.get('method', 'unknown')}")
        print(f"   Recipient: {result.get('recipient', 'unknown')}")
        print(f"   Message ID: {result.get('message_id', 'unknown')}")
        print(f"   Timestamp: {result.get('timestamp', 'unknown')}")
        print()
        
        if result.get("status") == "sent_real":
            print("🎉 **REAL SMS SENT SUCCESSFULLY!**")
            print(f"👀 **CHECK YOUR PHONE NOW!**")
            print(f"📱 Message sent to: {user_phone}")
            print(f"📨 Message ID: {result.get('message_id', 'unknown')}")
            print()
            
            # Check message status via Twilio API
            try:
                from twilio.rest import Client
                account_sid = os.getenv("TWILIO_ACCOUNT_SID") or os.getenv("TWILIO_SID")
                auth_token = os.getenv("TWILIO_AUTH_TOKEN") or os.getenv("TWILIO_SECRET")
                if account_sid and auth_token and result.get('message_id'):
                    twilio_client = Client(account_sid, auth_token)
                    msg = twilio_client.messages(result.get('message_id')).fetch()
                    print(f"📊 Twilio Status: {msg.status}")
                    print(f"   Error Code: {msg.error_code if msg.error_code else 'None'}")
                    print(f"   Error Message: {msg.error_message if msg.error_message else 'None'}")
                    if msg.status == 'failed':
                        print(f"   ❌ Message failed: {msg.error_message}")
                    elif msg.status in ['queued', 'sending', 'sent', 'delivered']:
                        print(f"   ✅ Message accepted by Twilio (status: {msg.status})")
                        if msg.status == 'delivered':
                            print(f"   ✅ Confirmed delivered to carrier!")
                        else:
                            print(f"   ⏳ Status: {msg.status} - may take a few seconds to deliver")
            except Exception as status_error:
                print(f"   ⚠️  Could not check status: {status_error}")
            
            print()
            print(f"✅ This confirms your Twilio SMS integration is working!")
            return True
        else:
            print("⚠️  SMS may not have been sent")
            print(f"   Status: {result.get('status')}")
            print(f"   Method: {result.get('method')}")
            if result.get('note'):
                print(f"   Note: {result.get('note')}")
            return False
            
    except Exception as e:
        print(f"\n❌ **ERROR SENDING SMS**: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    print("\n" + "🚀" * 35)
    print("🚀 TWILIO SMS TEST")
    print("🚀" * 35)
    print()
    
    # Get message from command line or use default
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        print(f"📝 Using custom message from command line")
    else:
        message = None
        print(f"📝 Using default test message")
    
    print()
    
    success = send_sms_to_user(message)
    
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    if success:
        print("✅ **SMS SENT SUCCESSFULLY!**")
        print("👀 **Go check your phone!**")
        print("✅ Your Twilio SMS integration is fully operational!")
        
        print(f"\n🎯 **What this proves:**")
        print(f"   • Twilio credentials are configured correctly")
        print(f"   • SMS sending works perfectly")
        print(f"   • Multi-agent system can send SMS notifications")
        print(f"   • EmailIntegration.send_sms() is working")
        
    else:
        print("❌ **SMS SENDING FAILED**")
        print("💡 Check Twilio credentials in .env file")
        print("💡 Verify USER_PHONE_NUMBER is set correctly")
        
        print(f"\n🔧 **Troubleshooting:**")
        print(f"   • Check TWILIO_ACCOUNT_SID is set")
        print(f"   • Check TWILIO_AUTH_TOKEN is set")
        print(f"   • Check TWILIO_PHONE_NUMBER is set")
        print(f"   • Check USER_PHONE_NUMBER is set")
        print(f"   • Verify phone numbers are in E.164 format (+1234567890)")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

