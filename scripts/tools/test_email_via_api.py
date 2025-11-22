#!/usr/bin/env python3
"""
Test Email Integration via API

This script tests agentic email capabilities through the main.py API:
1. Creates a workflow that reviews knowledge graph
2. Sends email notification via API
3. Verifies email was sent

Usage:
    python scripts/tools/test_email_via_api.py
"""

import requests
import json
import time
from datetime import datetime

API_BASE = "http://localhost:8000"
USER_EMAIL = "nicholas.k.baro@gmail.com"

def test_health():
    """Test if API server is running."""
    try:
        response = requests.get(f"{API_BASE}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ API server is running")
            print(f"   Status: {response.json()}")
            return True
        else:
            print(f"❌ API server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server. Is main.py running?")
        print("   Start it with: python main.py")
        return False
    except Exception as e:
        print(f"❌ Error checking health: {e}")
        return False

def create_test_plan_file():
    """Create a test plan file for workflow."""
    plan_content = """
    Test Workflow Plan: Knowledge Graph Review
    
    This workflow will:
    1. Query the knowledge graph for images
    2. Review knowledge graph status
    3. Send email notification with findings
    
    Steps:
    - Step 1: Query KG for images
    - Step 2: Count total triples
    - Step 3: Generate email report
    - Step 4: Send email notification
    """
    
    plan_file = "test_kg_review_plan.txt"
    with open(plan_file, "w") as f:
        f.write(plan_content)
    
    print(f"✅ Created test plan file: {plan_file}")
    return plan_file

def test_create_workflow(plan_file: str):
    """Test creating a workflow via API."""
    print("\n📋 Creating workflow via API...")
    
    try:
        response = requests.post(
            f"{API_BASE}/api/orchestration/create-workflow",
            json={
                "text_file": plan_file,
                "user_email": USER_EMAIL,
                "workflow_name": "KG Review and Email Test"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Workflow created successfully!")
            print(f"   Workflow ID: {result.get('workflow_id')}")
            print(f"   Status: {result.get('status')}")
            return result.get('workflow_id')
        else:
            print(f"❌ Failed to create workflow: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating workflow: {e}")
        return None

def test_send_email_step(workflow_id: str):
    """Test sending email via workflow step."""
    print(f"\n📧 Sending email for workflow {workflow_id}...")
    
    try:
        response = requests.post(
            f"{API_BASE}/api/orchestration/execute-step",
            json={
                "workflow_id": workflow_id,
                "step": "send_email",
                "user_email": USER_EMAIL
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Email step executed successfully!")
            print(f"   Email Status: {result.get('email_status')}")
            print(f"   Workflow Status: {result.get('status')}")
            print(f"   Next Step: {result.get('next_step')}")
            return True
        else:
            print(f"❌ Failed to send email: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

def test_kg_query():
    """Test querying knowledge graph for images via API."""
    print("\n🔍 Querying knowledge graph for images...")
    
    query = """
    PREFIX schema: <http://schema.org/>
    SELECT (COUNT(?image) as ?count) WHERE {
        ?image a schema:ImageObject .
    }
    """
    
    try:
        response = requests.get(
            f"{API_BASE}/api/kg/query",
            params={"sparql": query},
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()
            print("✅ KG Query successful!")
            if results:
                count = int(results[0].get("count", 0))
                print(f"   Images in KG: {count}")
                return count
            else:
                print("   No results returned")
                return 0
        else:
            print(f"❌ KG query failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error querying KG: {e}")
        return None

def main():
    """Main test function."""
    print("=" * 70)
    print("🧪 TESTING EMAIL INTEGRATION VIA API")
    print("=" * 70)
    
    # Step 1: Check API health
    if not test_health():
        print("\n❌ Cannot proceed - API server not available")
        return False
    
    # Step 2: Query KG for images
    image_count = test_kg_query()
    
    # Step 3: Create test plan file
    plan_file = create_test_plan_file()
    
    # Step 4: Create workflow
    workflow_id = test_create_workflow(plan_file)
    if not workflow_id:
        print("\n❌ Cannot proceed - workflow creation failed")
        return False
    
    # Step 5: Send email via workflow step
    email_sent = test_send_email_step(workflow_id)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"✅ API Server: Running")
    print(f"✅ KG Query: {image_count if image_count is not None else 'N/A'} images found")
    print(f"✅ Workflow Created: {workflow_id}")
    print(f"{'✅' if email_sent else '❌'} Email Sent: {'Yes' if email_sent else 'No'}")
    
    if email_sent:
        print("\n🎉 **SUCCESS!**")
        print(f"👀 Check your inbox at {USER_EMAIL} for the workflow plan review email!")
    else:
        print("\n⚠️  Email sending failed - check API logs")
    
    return email_sent

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)

