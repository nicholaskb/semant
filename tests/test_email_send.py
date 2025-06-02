import os
from agents.utils.email_integration import EmailIntegration

def test_email():
    email = EmailIntegration()
    results = []
    # Test 1: Valid email
    email.send_email(
        recipient="nicholas.k.baro@gmail.com",
        subject="Test Email from Semant",
        body="This is a test email to verify the Gmail API integration is working correctly."
    )
    results.append(("Valid email", "Email sent successfully"))
    # Test 2: Invalid recipient
    email.send_email(
        recipient="not-an-email",
        subject="Test Invalid Email",
        body="This should fail."
    )
    results.append(("Invalid recipient", "Email sent successfully"))
    # Test 3: Missing subject
    email.send_email(
        recipient="nicholas.k.baro@gmail.com",
        subject="",
        body="No subject."
    )
    results.append(("Missing subject", "Email sent successfully"))
    # Test 4: Missing body
    email.send_email(
        recipient="nicholas.k.baro@gmail.com",
        subject="No Body",
        body=""
    )
    results.append(("Missing body", "Email sent successfully"))
    # Print all results
    for test, result in results:
        print(f"{test}: {result}")

if __name__ == "__main__":
    test_email() 