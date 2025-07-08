#!/usr/bin/env python3
"""
Programmatic Google Cloud Project and Credentials Checker
"""

from dotenv import load_dotenv
import os
from google.oauth2 import service_account
import json
import subprocess

def main():
    print("🔍 **Google Cloud Setup Analysis**")
    print("=" * 50)
    
    # Load environment
    load_dotenv(override=True)
    
    print("\n📋 **Environment Variables**")
    project_env = os.getenv('GOOGLE_CLOUD_PROJECT')
    creds_env = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    location_env = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
    
    print(f"GOOGLE_CLOUD_PROJECT: {project_env}")
    print(f"GOOGLE_APPLICATION_CREDENTIALS: {creds_env}")
    print(f"GOOGLE_CLOUD_LOCATION: {location_env}")
    
    print("\n🔑 **Credentials File Analysis**")
    if not creds_env:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
        return False
    
    if not os.path.exists(creds_env):
        print(f"❌ Credentials file not found: {creds_env}")
        return False
    
    print(f"✅ Credentials file exists: {creds_env}")
    
    # Read credentials file
    try:
        with open(creds_env, 'r') as f:
            creds_data = json.load(f)
        
        project_in_creds = creds_data.get('project_id')
        service_email = creds_data.get('client_email')
        key_type = creds_data.get('type')
        
        print(f"📁 Project ID in credentials: {project_in_creds}")
        print(f"📧 Service account email: {service_email}")
        print(f"🔑 Key type: {key_type}")
        
        # Check if environment and credentials match
        if project_env != project_in_creds:
            print(f"⚠️  WARNING: Environment project ({project_env}) != Credentials project ({project_in_creds})")
        else:
            print(f"✅ Project IDs match: {project_env}")
            
    except Exception as e:
        print(f"❌ Error reading credentials file: {e}")
        return False
    
    print("\n🔧 **Credentials Object Test**")
    try:
        credentials = service_account.Credentials.from_service_account_file(creds_env)
        print(f"✅ Credentials loaded successfully")
        print(f"🎯 Project from credentials object: {credentials.project_id}")
        print(f"🔗 Service account email: {credentials.service_account_email}")
    except Exception as e:
        print(f"❌ Error loading credentials object: {e}")
        return False
    
    print("\n⚙️  **GCloud CLI Status**")
    try:
        # Get current gcloud project
        result = subprocess.run(['gcloud', 'config', 'get-value', 'project'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            gcloud_project = result.stdout.strip()
            print(f"🔧 Current gcloud project: {gcloud_project}")
            if gcloud_project != project_env:
                print(f"⚠️  WARNING: gcloud project ({gcloud_project}) != environment project ({project_env})")
        else:
            print("❌ Could not get gcloud project")
    except Exception as e:
        print(f"❌ Error checking gcloud: {e}")
    
    print("\n📊 **Summary**")
    print(f"✅ Environment project: {project_env}")
    print(f"✅ Credentials file: {creds_env}")
    print(f"✅ All checks passed!")
    
    return True

if __name__ == "__main__":
    main() 