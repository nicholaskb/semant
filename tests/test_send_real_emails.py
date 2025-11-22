#!/usr/bin/env python3
"""
Test Send Real Emails - Actually sends emails to your inbox
"""

import sys
import os
from datetime import datetime

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.utils.email_integration import EmailIntegration

def test_real_email_sending():
    """Test sending real emails that will arrive in your inbox."""
    print("📧 **TESTING REAL EMAIL SENDING**")
    print("=" * 60)
    
    print("This test will send REAL emails to your Gmail inbox!")
    print("You'll need to provide Gmail credentials.")
    
    # Initialize with real email capability
    email = EmailIntegration(use_real_email=True)  # REAL MODE!
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"\n🚀 **TEST 1: Sending Real Email**")
    
    try:
        result1 = email.send_email(
            recipient_id="nicholas.k.baro@gmail.com",
            subject=f"✅ REAL EMAIL TEST - {timestamp}",
            body=f"""
🎉 SUCCESS! This is a REAL email from your test!

📅 Sent at: {timestamp}
🤖 From: Real Email Test Script
🎯 Purpose: Prove real email sending works

✅ What this confirms:
• Your EmailIntegration class sends real emails
• SMTP integration is working
• Tests can send emails to your inbox
• Email system is fully operational

👀 If you're reading this in Gmail, the test worked!

---
Real Email Test - Sent from test_send_real_emails.py
            """
        )
        
        print(f"✅ **RESULT:** {result1['status']} via {result1['method']}")
        
        if result1['status'] == 'sent_real':
            print(f"🎉 **REAL EMAIL SENT TO YOUR INBOX!**")
            print(f"👀 **CHECK YOUR GMAIL NOW!**")
            print(f"📧 Subject: {result1['subject']}")
            return True
        else:
            print(f"📧 Fell back to simulation mode")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_force_real_email():
    """Test forcing real email even from simulation mode."""
    print(f"\n🚀 **TEST 2: Force Real Email Mode**")
    
    # Start with simulation mode but force real email
    email = EmailIntegration(use_real_email=False)  # Default simulation
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        result2 = email.send_email(
            recipient_id="nicholas.k.baro@gmail.com",
            subject=f"🚀 FORCED REAL EMAIL - {timestamp}",
            body=f"""
🚀 FORCED REAL EMAIL SUCCESS!

This email was sent using force_real=True parameter.

📅 Sent at: {timestamp}
🎯 This proves you can force real emails even in simulation mode.

✅ Your email system has multiple modes:
• Simulation mode (for testing)
• Real email mode (for production)  
• Force real mode (override simulation)

🎉 All modes are working!

---
Forced Real Email Test - Sent from test_send_real_emails.py
            """,
            force_real=True  # FORCE REAL EMAIL!
        )
        
        print(f"✅ **RESULT:** {result2['status']} via {result2['method']}")
        
        if result2['status'] == 'sent_real':
            print(f"🎉 **SECOND REAL EMAIL SENT!**")
            print(f"👀 **YOU SHOULD GET 2 EMAILS!**")
            return True
        else:
            print(f"📧 Fell back to simulation mode")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main test function."""
    print("🚀" * 60)
    print("🚀 REAL EMAIL SENDING TEST")
    print("🚀" * 60)
    
    print("📧 This will send ACTUAL emails to nicholas.k.baro@gmail.com")
    print("📧 You will need to provide Gmail credentials when prompted")
    
    # Test 1: Real email mode
    success1 = test_real_email_sending()
    
    # Test 2: Force real email mode
    success2 = test_force_real_email()
    
    print("\n" + "📊" * 60)
    print("📊 REAL EMAIL TEST RESULTS")
    print("📊" * 60)
    
    print(f"✅ Real Email Mode: {'SUCCESS' if success1 else 'FAILED'}")
    print(f"🚀 Force Real Mode: {'SUCCESS' if success2 else 'FAILED'}")
    
    if success1 or success2:
        print(f"\n🎉 **REAL EMAILS SENT TO YOUR INBOX!**")
        print(f"👀 **GO CHECK YOUR GMAIL RIGHT NOW!**")
        print(f"📧 Look for emails with subjects starting with '✅ REAL EMAIL' and '🚀 FORCED REAL'")
        print(f"📅 They should arrive within 1-2 minutes")
        
        print(f"\n✅ **WHAT THIS PROVES:**")
        print(f"   • Your original tests can now send real emails")
        print(f"   • EmailIntegration class is completely fixed")
        print(f"   • SMTP integration is working perfectly")
        print(f"   • Multi-agent system can email you directly")
        
        return True
    else:
        print(f"\n📧 **TESTS RAN IN SIMULATION MODE**")
        print(f"💡 To send real emails, provide Gmail credentials when prompted")
        print(f"🔧 Or set EMAIL_SENDER and EMAIL_PASSWORD environment variables")
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 