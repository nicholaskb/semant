#!/usr/bin/env python3
"""
Script to set up email credentials in .env file.

Usage:
    python scripts/tools/setup_email.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv, set_key, find_dotenv
import getpass

def setup_email_credentials():
    """Set up email credentials in .env file."""
    env_path = Path('.env')
    
    if not env_path.exists():
        print("❌ .env file not found. Creating new .env file...")
        env_path.touch()
    
    # Load existing .env
    load_dotenv()
    
    print("=" * 60)
    print("📧 Email Setup for Semant Agents")
    print("=" * 60)
    print()
    
    # Show current settings
    current_email = os.getenv('EMAIL_SENDER')
    if current_email:
        print(f"Current EMAIL_SENDER: {current_email}")
    else:
        print("EMAIL_SENDER: Not set")
    print()
    
    # Get email address
    print("Enter your email address (Gmail recommended):")
    email = input("Email: ").strip()
    
    if not email:
        print("❌ Email address is required")
        sys.exit(1)
    
    # Validate email format (basic check)
    if '@' not in email or '.' not in email.split('@')[1]:
        print("⚠️  Warning: Email format looks invalid")
        response = input("Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            print("❌ Setup cancelled")
            sys.exit(1)
    
    # Get password
    print()
    print("Enter your email password:")
    print("   For Gmail: Use an App Password (not your regular password)")
    print("   Get one at: https://myaccount.google.com/apppasswords")
    print()
    password = getpass.getpass("Password/App Password: ").strip()
    
    if not password:
        print("❌ Password is required")
        sys.exit(1)
    
    # Update the .env file
    try:
        env_file = find_dotenv()
        if env_file:
            set_key(env_file, 'EMAIL_SENDER', email)
            set_key(env_file, 'EMAIL_PASSWORD', password)
            print()
            print(f"✅ Successfully configured email!")
            print(f"   EMAIL_SENDER: {email}")
            print(f"   EMAIL_PASSWORD: {'*' * len(password)}")
            print()
            print("💡 Test email sending with:")
            print("   python -c \"from agents.utils.email_integration import send_email; send_email(recipient_id='your@email.com', subject='Test', body='Hello', force_real=True)\"")
            return True
        else:
            print("❌ Could not find .env file")
            return False
    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return False

def show_gmail_instructions():
    """Show Gmail App Password setup instructions."""
    print()
    print("=" * 60)
    print("📋 GMAIL APP PASSWORD SETUP")
    print("=" * 60)
    print()
    print("To use Gmail with Semant, you need an App Password:")
    print()
    print("1. Go to: https://myaccount.google.com/security")
    print()
    print("2. Enable 2-Step Verification (if not already enabled)")
    print()
    print("3. Go to App Passwords:")
    print("   https://myaccount.google.com/apppasswords")
    print()
    print("4. Select:")
    print("   - App: Mail")
    print("   - Device: Other (Custom name)")
    print("   - Name: Semant")
    print()
    print("5. Click 'Generate'")
    print()
    print("6. Copy the 16-character password (spaces don't matter)")
    print()
    print("7. Use that password (not your regular Gmail password)")
    print()
    print("=" * 60)
    print()

def main():
    """Main function."""
    print()
    print("Choose an option:")
    print("  1. Set up email credentials")
    print("  2. Show Gmail App Password instructions")
    print("  3. Exit")
    print()
    
    choice = input("Choice (1-3): ").strip()
    
    if choice == "1":
        success = setup_email_credentials()
        sys.exit(0 if success else 1)
    elif choice == "2":
        show_gmail_instructions()
        print()
        retry = input("Set up credentials now? (y/n): ").strip().lower()
        if retry == 'y':
            success = setup_email_credentials()
            sys.exit(0 if success else 1)
    else:
        print("Exiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()

