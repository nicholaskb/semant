import os
from pathlib import Path
import sys

# Ensure repo root is in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from email_utils.send_gmail_test import get_gmail_service, send_email


def test_gmail_api_real_send():
    """Send a real email via Gmail API to verify OAuth credentials work."""
    print("\n📧 **TESTING GMAIL API REAL EMAIL SEND**")
    service = get_gmail_service()
    send_email(
        service,
        "nicholas.k.baro@gmail.com",
        "✅ Gmail API Test Email from pytest",
        "This is an automated test email sent via Gmail API from pytest.\nIf you're reading this, the Gmail API send function works inside the test suite."
    )
    # If no exception, consider test passed
    assert True 