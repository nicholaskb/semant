#!/usr/bin/env python3
"""
Script to update Twilio phone number in .env file.

Usage:
    python scripts/tools/update_twilio_phone.py +1234567890
    python scripts/tools/update_twilio_phone.py  # Interactive mode
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv, set_key, find_dotenv

def update_twilio_phone(phone_number: str, interactive: bool = True) -> bool:
    """Update TWILIO_PHONE_NUMBER in .env file.
    
    Args:
        phone_number: The phone number to set (should start with +)
        interactive: Whether to prompt for confirmation (default: True)
    """
    env_path = Path('.env')
    
    if not env_path.exists():
        print("❌ .env file not found. Creating new .env file...")
        env_path.touch()
    
    # Load existing .env
    load_dotenv()
    
    # Validate phone number format (basic check)
    if not phone_number.startswith('+'):
        print("⚠️  Warning: Phone number should start with '+' (e.g., +1234567890)")
        if interactive:
            response = input("Continue anyway? (y/n): ").strip().lower()
            if response != 'y':
                print("❌ Update cancelled")
                return False
        else:
            print("⚠️  Continuing anyway (non-interactive mode)")
    
    # Update the .env file
    try:
        env_file = find_dotenv()
        if env_file:
            set_key(env_file, 'TWILIO_PHONE_NUMBER', phone_number)
            print(f"✅ Successfully updated TWILIO_PHONE_NUMBER to: {phone_number}")
            
            # Also update legacy variable if it exists
            current_legacy = os.getenv('TWILIO_ACCOUNT_NUBMER')  # Note: typo in original
            if current_legacy:
                set_key(env_file, 'TWILIO_ACCOUNT_NUBMER', phone_number)
                print(f"✅ Also updated legacy TWILIO_ACCOUNT_NUBMER")
            
            return True
        else:
            print("❌ Could not find .env file")
            return False
    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return False

def show_current_phone():
    """Show current Twilio phone number from .env."""
    load_dotenv()
    phone = os.getenv('TWILIO_PHONE_NUMBER') or os.getenv('TWILIO_ACCOUNT_NUBMER')
    if phone:
        print(f"📱 Current TWILIO_PHONE_NUMBER: {phone}")
    else:
        print("⚠️  No TWILIO_PHONE_NUMBER found in .env file")
    return phone

def main():
    """Main function."""
    print("=" * 60)
    print("📱 Twilio Phone Number Updater")
    print("=" * 60)
    print()
    
    # Show current phone number
    current = show_current_phone()
    print()
    
    # Get new phone number
    interactive_mode = len(sys.argv) <= 1
    if len(sys.argv) > 1:
        new_phone = sys.argv[1]
    else:
        if current:
            print(f"Current: {current}")
        new_phone = input("Enter new phone number (e.g., +1234567890): ").strip()
    
    if not new_phone:
        print("❌ No phone number provided")
        sys.exit(1)
    
    # Update phone number
    if update_twilio_phone(new_phone, interactive=interactive_mode):
        print()
        print("✅ Phone number updated successfully!")
        print("💡 Restart your application for changes to take effect")
        sys.exit(0)
    else:
        print()
        print("❌ Failed to update phone number")
        sys.exit(1)

if __name__ == "__main__":
    main()

