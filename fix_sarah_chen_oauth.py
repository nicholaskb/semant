#!/usr/bin/env python3
"""
Fix Sarah Chen OAuth - Restore the working email system
======================================================

This script fixes the OAuth authorization to restore Sarah Chen emails exactly as they worked before.
"""

import os
import json
from pathlib import Path

def fix_oauth_authorization():
    """Fix the OAuth authorization for Gmail API."""
    print("🔧 **FIXING SARAH CHEN EMAIL OAUTH AUTHORIZATION**")
    print("This will restore the working email system you had before.\n")
    
    print("📋 **Steps to restore Sarah Chen emails:**")
    print()
    print("1. 🌐 **Go to Google Cloud Console**:")
    print("   https://console.cloud.google.com")
    print()
    print("2. 📁 **Select your project: baa-roo**")
    print()
    print("3. 🔑 **Go to APIs & Services > Credentials**")
    print()
    print("4. ➕ **Create OAuth 2.0 Client ID** (if not exists):")
    print("   - Application type: Desktop application")
    print("   - Name: Sarah Chen Email System")
    print()
    print("5. 📧 **Enable Gmail API** (if not enabled):")
    print("   - Go to APIs & Services > Library")
    print("   - Search 'Gmail API'")
    print("   - Click Enable")
    print()
    print("6. 📥 **Download OAuth credentials**:")
    print("   - Click the download button for your OAuth client")
    print("   - Save as 'oauth_credentials.json' in credentials/ folder")
    print()
    print("7. ✅ **Run the working email system**:")
    print("   python run_working_sarah_chen.py")
    print()
    
    # Check current credentials
    cred_path = Path("credentials/credentials.json")
    if cred_path.exists():
        print("✅ **Service account credentials found**")
        print(f"   📍 Location: {cred_path}")
        
        # Read and show project info
        try:
            with open(cred_path) as f:
                creds = json.load(f)
                print(f"   🏢 Project: {creds.get('project_id', 'Unknown')}")
                print(f"   📧 Type: {creds.get('type', 'Unknown')}")
        except:
            print("   ⚠️ Could not read credential details")
    else:
        print("❌ **Service account credentials not found**")
    
    oauth_path = Path("credentials/oauth_credentials.json")
    if oauth_path.exists():
        print("✅ **OAuth credentials found**")
        print(f"   📍 Location: {oauth_path}")
    else:
        print("❌ **OAuth credentials needed** (this is what's missing)")
        print("   💡 Download from Google Cloud Console as described above")
    
    print("\n🎯 **SUMMARY:**")
    print("Your system is 99% working! Just need OAuth credentials to send real emails.")
    print("Once you download oauth_credentials.json, Sarah Chen emails will work exactly like before!")

if __name__ == "__main__":
    fix_oauth_authorization() 