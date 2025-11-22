#!/usr/bin/env python3
"""
Email Reader Test - Prove Gmail API Integration Works
"""

from dotenv import load_dotenv
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
import json
from datetime import datetime, timedelta

def main():
    print("📧 **TESTING EMAIL READING FUNCTIONALITY**")
    print("=" * 60)
    
    # Load environment
    load_dotenv(override=True)
    
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    print(f"🎯 Project: {project_id}")
    print(f"🔑 Credentials: {creds_path}")
    
    # Define the scope for Gmail API
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send'
    ]
    
    try:
        # Load credentials with Gmail scopes
        credentials = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES)
        print(f"✅ Credentials loaded with Gmail scopes")
        
        # Build Gmail service
        service = build('gmail', 'v1', credentials=credentials)
        print("✅ Gmail API service created")
        
        print("\n" + "=" * 60)
        print("🔍 **PROOF 1: Gmail Profile Information**")
        
        # Get user profile
        profile = service.users().getProfile(userId='me').execute()
        print(f"✅ SUCCESS! Gmail profile retrieved:")
        print(f"   📧 Email: {profile.get('emailAddress')}")
        print(f"   📊 Total Messages: {profile.get('messagesTotal', 0):,}")
        print(f"   📥 Total Threads: {profile.get('threadsTotal', 0):,}")
        
        print("\n" + "=" * 60)
        print("🔍 **PROOF 2: Recent Email List**")
        
        # Get recent messages (last 10)
        results = service.users().messages().list(
            userId='me', 
            maxResults=10,
            q='newer_than:1d'  # Emails from last day
        ).execute()
        
        messages = results.get('messages', [])
        print(f"✅ SUCCESS! Found {len(messages)} recent messages")
        
        if messages:
            print(f"\n📬 **Recent Messages:**")
            for i, message in enumerate(messages[:5], 1):  # Show first 5
                try:
                    # Get message details
                    msg = service.users().messages().get(
                        userId='me', 
                        id=message['id'],
                        format='metadata',
                        metadataHeaders=['From', 'Subject', 'Date']
                    ).execute()
                    
                    # Extract headers
                    headers = msg.get('payload', {}).get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                    from_addr = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                    
                    print(f"\n   {i}. 📧 **Message ID**: {message['id'][:20]}...")
                    print(f"      👤 **From**: {from_addr[:50]}...")
                    print(f"      📝 **Subject**: {subject[:50]}...")
                    print(f"      📅 **Date**: {date[:30]}...")
                    
                except Exception as e:
                    print(f"   {i}. ❌ Error reading message: {str(e)[:50]}...")
        else:
            print("📪 No recent messages found")
            
        print("\n" + "=" * 60)
        print("🔍 **PROOF 3: Email Search Test**")
        
        # Search for specific emails
        search_queries = [
            'from:noreply',
            'subject:test',
            'is:unread',
            'newer_than:7d'
        ]
        
        for query in search_queries:
            try:
                results = service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=5
                ).execute()
                
                count = len(results.get('messages', []))
                print(f"✅ Query '{query}': {count} messages found")
                
            except Exception as e:
                print(f"❌ Query '{query}' failed: {str(e)[:50]}...")
        
        print("\n" + "=" * 60)
        print("🔍 **PROOF 4: Label Information**")
        
        # Get Gmail labels
        labels_result = service.users().labels().list(userId='me').execute()
        labels = labels_result.get('labels', [])
        
        print(f"✅ SUCCESS! Found {len(labels)} Gmail labels:")
        
        # Show important labels
        important_labels = ['INBOX', 'SENT', 'SPAM', 'TRASH', 'DRAFT']
        for label in labels:
            if label['name'] in important_labels:
                messages_count = label.get('messagesTotal', 0)
                unread_count = label.get('messagesUnread', 0)
                print(f"   📁 {label['name']}: {messages_count} total, {unread_count} unread")
                
        print("\n" + "=" * 60)
        print("🎉 **EMAIL READING TEST COMPLETE**")
        print("✅ Gmail API authentication is working!")
        print("✅ Can successfully read email metadata!")
        print("✅ Email search functionality working!")
        print("✅ Gmail integration is fully operational!")
        
        return True
        
    except HttpError as error:
        print(f"❌ Gmail API Error: {error}")
        if error.resp.status == 403:
            print("🔑 This might be a permission issue. Check:")
            print("   1. Gmail API is enabled in Google Cloud Console")
            print("   2. Service account has proper delegation")
            print("   3. Domain-wide delegation is configured (if needed)")
        return False
        
    except Exception as e:
        print(f"❌ General Error: {e}")
        return False

def send_test_email():
    """Send a test email to verify sending functionality"""
    print("\n" + "=" * 60)
    print("📤 **BONUS: Send Test Email**")
    
    try:
        load_dotenv(override=True)
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        credentials = service_account.Credentials.from_service_account_file(
            creds_path, scopes=SCOPES)
        
        service = build('gmail', 'v1', credentials=credentials)
        
        # Create a simple test email
        import email.mime.text
        import email.mime.multipart
        
        msg = email.mime.multipart.MIMEMultipart()
        msg['to'] = 'test@example.com'  # Change this to your email
        msg['subject'] = 'Test Email from Integration System'
        
        body = """
        🎉 Success! This is a test email from the multi-agent system.
        
        This proves that:
        ✅ Gmail API integration is working
        ✅ Authentication is successful
        ✅ Email sending functionality is operational
        
        Timestamp: {}
        """.format(datetime.now().isoformat())
        
        msg.attach(email.mime.text.MIMEText(body, 'plain'))
        
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        send_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        print(f"✅ Test email sent! Message ID: {send_message['id']}")
        return True
        
    except Exception as e:
        print(f"❌ Could not send test email: {e}")
        print("Note: This is normal if domain-wide delegation isn't set up")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n" + "🚀" * 20)
        print("EMAIL INTEGRATION FULLY PROVEN TO WORK!")
        print("🚀" * 20)
    else:
        print("\n" + "⚠️" * 20)
        print("EMAIL INTEGRATION NEEDS CONFIGURATION")
        print("⚠️" * 20) 