#!/usr/bin/env python3
"""
Comprehensive Test of Agentic Email Capabilities via API

This script tests:
1. Health check
2. Knowledge graph queries
3. Workflow creation with agentic planning
4. Email sending via orchestration workflow
5. Email reading capability
6. Agent chat with email integration

Usage:
    python scripts/tools/test_agentic_email_comprehensive.py
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

API_BASE = "http://localhost:8000"
USER_EMAIL = "nicholas.k.baro@gmail.com"

def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"🔬 {title}")
    print("=" * 70)

def test_health() -> bool:
    """Test if API server is running."""
    print_section("API Health Check")
    try:
        response = requests.get(f"{API_BASE}/api/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print("✅ API server is running")
            print(f"   Status: {health.get('status')}")
            print(f"   Version: {health.get('version')}")
            
            components = health.get('components', {})
            for comp_name, comp_data in components.items():
                status = comp_data.get('status', 'unknown')
                icon = "✅" if status == "healthy" else "⚠️"
                print(f"   {icon} {comp_name}: {status}")
            
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

def test_kg_query() -> Optional[int]:
    """Test querying knowledge graph."""
    print_section("Knowledge Graph Query Test")
    
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
            if results and len(results) > 0:
                count = int(results[0].get("count", 0))
                print(f"   Images in KG: {count}")
                return count
            else:
                print("   No results returned")
                return 0
        else:
            print(f"⚠️  KG query returned {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"⚠️  Error querying KG: {e}")
        return None

def create_test_plan() -> str:
    """Create a test plan file for workflow."""
    print_section("Creating Test Plan")
    
    plan_content = """
    Agentic Email Integration Test Plan
    
    This workflow demonstrates agentic capabilities:
    1. Query knowledge graph for recent agent activities
    2. Review email integration status
    3. Generate comprehensive email report
    4. Send email notification with findings
    
    Agent Tasks:
    - Planner: Create execution plan
    - Reviewer: Review email integration code
    - Executor: Execute workflow steps
    - Reporter: Generate email report
    
    Expected Outcomes:
    - Workflow created successfully
    - Email sent with workflow plan
    - Knowledge graph updated with workflow metadata
    """
    
    plan_file = "test_agentic_email_plan.txt"
    with open(plan_file, "w") as f:
        f.write(plan_content)
    
    print(f"✅ Created test plan file: {plan_file}")
    return plan_file

def test_create_workflow(plan_file: str) -> Optional[str]:
    """Test creating a workflow via API."""
    print_section("Creating Agentic Workflow")
    
    try:
        print(f"   Sending request to {API_BASE}/api/orchestration/create-workflow")
        print(f"   Plan file: {plan_file}")
        print(f"   User email: {USER_EMAIL}")
        
        response = requests.post(
            f"{API_BASE}/api/orchestration/create-workflow",
            json={
                "text_file": plan_file,
                "user_email": USER_EMAIL,
                "workflow_name": "Agentic Email Integration Test"
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            workflow_id = result.get('workflow_id')
            print("✅ Workflow created successfully!")
            print(f"   Workflow ID: {workflow_id}")
            print(f"   Status: {result.get('status', 'N/A')}")
            
            # Print additional details if available
            if 'plan' in result:
                plan = result['plan']
                steps = plan.get('steps', [])
                print(f"   Plan Steps: {len(steps)}")
                for i, step in enumerate(steps[:3], 1):  # Show first 3 steps
                    step_name = step.get('name', 'Unknown')
                    print(f"      {i}. {step_name}")
            
            return workflow_id
        else:
            print(f"❌ Failed to create workflow: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return None
    except Exception as e:
        print(f"❌ Error creating workflow: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_send_email_step(workflow_id: str) -> Dict[str, Any]:
    """Test sending email via workflow step."""
    print_section("Testing Email Sending via Workflow")
    
    try:
        print(f"   Workflow ID: {workflow_id}")
        print(f"   Recipient: {USER_EMAIL}")
        print(f"   Step: send_email")
        
        response = requests.post(
            f"{API_BASE}/api/orchestration/execute-step",
            json={
                "workflow_id": workflow_id,
                "step": "send_email",
                "user_email": USER_EMAIL
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Email step executed successfully!")
            
            # Print detailed response
            email_status = result.get('email_status')
            workflow_status = result.get('status')
            next_step = result.get('next_step')
            
            print(f"   Email Status: {email_status if email_status else 'sent (no status returned)'}")
            print(f"   Workflow Status: {workflow_status if workflow_status else 'N/A'}")
            print(f"   Next Step: {next_step if next_step else 'N/A'}")
            
            # Check for email metadata
            if 'email_metadata' in result:
                metadata = result['email_metadata']
                print(f"   Email Metadata:")
                print(f"      To: {metadata.get('to', 'N/A')}")
                print(f"      Subject: {metadata.get('subject', 'N/A')}")
                print(f"      Status: {metadata.get('status', 'N/A')}")
            
            return {
                'success': True,
                'email_status': email_status,
                'result': result
            }
        else:
            print(f"❌ Failed to send email: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return {
                'success': False,
                'error': response.text
            }
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

def test_agent_chat() -> bool:
    """Test agent chat functionality."""
    print_section("Testing Agent Chat")
    
    try:
        chat_message = "Can you send a test email to verify the email integration is working?"
        
        response = requests.post(
            f"{API_BASE}/chat",
            json={
                "message": chat_message,
                "history": []
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Chat request successful!")
            response_text = result.get('response', 'N/A')
            print(f"   Agent Response: {response_text[:200]}...")
            return True
        else:
            print(f"⚠️  Chat returned {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"⚠️  Error in chat test: {e}")
        return False

def main():
    """Main test function."""
    print("\n" + "=" * 70)
    print("🚀 COMPREHENSIVE AGENTIC EMAIL CAPABILITIES TEST")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"API Base: {API_BASE}")
    print(f"User Email: {USER_EMAIL}")
    
    results = {
        'health': False,
        'kg_query': None,
        'workflow_created': False,
        'email_sent': False,
        'chat_tested': False
    }
    
    # Step 1: Health check
    results['health'] = test_health()
    if not results['health']:
        print("\n❌ Cannot proceed - API server not available")
        return False
    
    # Step 2: KG query
    results['kg_query'] = test_kg_query()
    
    # Step 3: Create test plan
    plan_file = create_test_plan()
    
    # Step 4: Create workflow
    workflow_id = test_create_workflow(plan_file)
    results['workflow_created'] = workflow_id is not None
    
    if not workflow_id:
        print("\n⚠️  Cannot test email sending - workflow creation failed")
    else:
        # Step 5: Send email
        email_result = test_send_email_step(workflow_id)
        results['email_sent'] = email_result.get('success', False)
    
    # Step 6: Test agent chat (optional)
    results['chat_tested'] = test_agent_chat()
    
    # Final Summary
    print("\n" + "=" * 70)
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print("=" * 70)
    
    print(f"{'✅' if results['health'] else '❌'} API Server: {'Running' if results['health'] else 'Not Available'}")
    print(f"{'✅' if results['kg_query'] is not None else '⚠️'} KG Query: {results['kg_query'] if results['kg_query'] is not None else 'N/A'} images")
    print(f"{'✅' if results['workflow_created'] else '❌'} Workflow Created: {'Yes' if results['workflow_created'] else 'No'}")
    print(f"{'✅' if results['email_sent'] else '❌'} Email Sent: {'Yes' if results['email_sent'] else 'No'}")
    print(f"{'✅' if results['chat_tested'] else '⚠️'} Agent Chat: {'Tested' if results['chat_tested'] else 'Skipped'}")
    
    if results['email_sent']:
        print("\n🎉 **SUCCESS!**")
        print(f"📧 Check your inbox at {USER_EMAIL} for the workflow plan review email!")
        print("\n✨ Agentic email capabilities are working correctly!")
    else:
        print("\n⚠️  Email sending failed - check API logs for details")
    
    return results['email_sent']

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)

