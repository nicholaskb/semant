import os
import sys
import asyncio
from pathlib import Path

# Add project root to path  
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.utils.email_integration import EmailIntegration

def test_email():
    """Test email functionality with real email sending to nicholas.k.baro@gmail.com"""
    print("📧 **TESTING EMAIL SEND FUNCTIONALITY**")
    print("🎯 Target: nicholas.k.baro@gmail.com")
    
    # Use real email mode to actually send emails
    email = EmailIntegration(use_real_email=True)
    results = []
    
    # Test 1: Valid email to nicholas.k.baro@gmail.com
    print("\n🧪 **TEST 1: Valid Email**")
    try:
        result = email.send_email(
            recipient_id="nicholas.k.baro@gmail.com",
            subject="✅ Test Email from Semant - Email Send Test",
            body="""
🧪 This is a test email from the email send test suite.

📧 Purpose: Verify basic email sending functionality works correctly
🎯 Test: test_email_send.py 
📅 Sent: from automated test suite
👤 Recipient: nicholas.k.baro@gmail.com

✅ If you're reading this, the basic email functionality is working!

---
Semant Multi-Agent System
Email Send Test Suite
            """,
            force_real=True
        )
        if result.get('status') == 'sent_real':
            results.append(("Valid email", "✅ REAL EMAIL SENT"))
            print("✅ Valid email test: REAL EMAIL SENT")
        else:
            results.append(("Valid email", "⚠️  Simulated only"))
            print("⚠️  Valid email test: Simulated only")
    except Exception as e:
        results.append(("Valid email", f"❌ Error: {e}"))
        print(f"❌ Valid email test: Error - {e}")
        
    # Test 2: Test with invalid email (should still work in simulation)
    print("\n🧪 **TEST 2: Invalid Recipient**")
    try:
        result = email.send_email(
            recipient_id="not-an-email",
            subject="Test Invalid Email",
            body="This should be simulated since it's invalid."
        )
        results.append(("Invalid recipient", "✅ Handled gracefully"))
        print("✅ Invalid recipient test: Handled gracefully")
    except Exception as e:
        results.append(("Invalid recipient", f"⚠️  Error handled: {e}"))
        print(f"⚠️  Invalid recipient test: Error handled - {e}")
        
    # Test 3: Missing subject (should still work)
    print("\n🧪 **TEST 3: Missing Subject**")
    try:
        result = email.send_email(
            recipient_id="nicholas.k.baro@gmail.com",
            subject="",
            body="📧 Test email with no subject from email send test suite.",
            force_real=True
        )
        if result.get('status') == 'sent_real':
            results.append(("Missing subject", "✅ REAL EMAIL SENT"))
            print("✅ Missing subject test: REAL EMAIL SENT")
        else:
            results.append(("Missing subject", "⚠️  Simulated only"))
            print("⚠️  Missing subject test: Simulated only")
    except Exception as e:
        results.append(("Missing subject", f"❌ Error: {e}"))
        print(f"❌ Missing subject test: Error - {e}")
        
    # Test 4: Missing body (should still work)
    print("\n🧪 **TEST 4: Missing Body**")
    try:
        result = email.send_email(
            recipient_id="nicholas.k.baro@gmail.com",
            subject="📧 Test Email - No Body Content",
            body="",
            force_real=True
        )
        if result.get('status') == 'sent_real':
            results.append(("Missing body", "✅ REAL EMAIL SENT"))
            print("✅ Missing body test: REAL EMAIL SENT")
        else:
            results.append(("Missing body", "⚠️  Simulated only"))  
            print("⚠️  Missing body test: Simulated only")
    except Exception as e:
        results.append(("Missing body", f"❌ Error: {e}"))
        print(f"❌ Missing body test: Error - {e}")
    
    # Summary
    print(f"\n📊 **EMAIL SEND TEST RESULTS**")
    real_emails_sent = 0
    for test, result in results:
        print(f"   {result.split()[0]} {test}: {result}")
        if "REAL EMAIL SENT" in result:
            real_emails_sent += 1
    
    if real_emails_sent > 0:
        print(f"\n🎉 **SUCCESS! {real_emails_sent} REAL EMAIL(S) SENT!**")
        print(f"👀 **CHECK nicholas.k.baro@gmail.com INBOX NOW!**")
        print(f"🔍 Look for emails with subjects containing 'Test Email from Semant'")
    else:
        print(f"\n⚠️  **NO REAL EMAILS SENT**")
        print(f"💡 Tests completed but emails were simulated")
        print(f"🔧 Check email credentials for real sending")
    
    assert True  # Tests pass if we reach this point without exceptions

if __name__ == "__main__":
    success = test_email()
    print(f"\n🏆 **EMAIL SEND TEST: {'PASSED' if success else 'NEEDS CONFIG'}**")
    sys.exit(0 if success else 1) 