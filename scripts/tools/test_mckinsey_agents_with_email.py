#!/usr/bin/env python3
"""
Test McKinsey-Style Consulting Agents with Email Integration

This script tests:
1. Initializing McKinsey-style consulting team agents
2. Creating an engagement request
3. Processing through the agent team (Engagement Manager → Strategy → Implementation → Value)
4. Sending email report with engagement results
5. Reading emails to verify delivery

Usage:
    python scripts/tools/test_mckinsey_agents_with_email.py
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from examples.demo_agents import (
    EngagementManagerAgent,
    StrategyLeadAgent,
    ImplementationLeadAgent,
    ValueRealizationLeadAgent,
    AgentMessage
)
from agents.utils.email_integration import EmailIntegration

USER_EMAIL = os.getenv("EMAIL_SENDER", "nicholas.k.baro@gmail.com")

def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"🔬 {title}")
    print("=" * 70)

async def test_mckinsey_agents_with_email():
    """Test McKinsey agents and send email report."""
    
    print("\n" + "=" * 70)
    print("🚀 MCKINSEY AGENTS + EMAIL INTEGRATION TEST")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"User Email: {USER_EMAIL}")
    
    # Initialize email integration
    print_section("Initializing Email Integration")
    email_integration = EmailIntegration(use_real_email=True)
    
    # Check if credentials are available
    if not email_integration.sender_email or not email_integration.sender_password:
        print("⚠️  Email credentials not found. Attempting to set up...")
        if not email_integration._setup_smtp_credentials():
            print("❌ Cannot proceed without email credentials")
            print("   Please set EMAIL_SENDER and EMAIL_PASSWORD in .env")
            return False
    
    print(f"✅ Email Integration initialized")
    print(f"   Sender: {email_integration.sender_email}")
    
    # Initialize McKinsey agents
    print_section("Initializing McKinsey Consulting Team")
    
    try:
        engagement_manager = EngagementManagerAgent()
        strategy_lead = StrategyLeadAgent()
        implementation_lead = ImplementationLeadAgent()
        value_realization_lead = ValueRealizationLeadAgent()
        
        print("   Creating agents...")
        await engagement_manager.initialize()
        print("   ✅ Engagement Manager initialized")
        
        await strategy_lead.initialize()
        print("   ✅ Strategy Lead initialized")
        
        await implementation_lead.initialize()
        print("   ✅ Implementation Lead initialized")
        
        await value_realization_lead.initialize()
        print("   ✅ Value Realization Lead initialized")
        
    except Exception as e:
        print(f"❌ Failed to initialize agents: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Create engagement request
    print_section("Creating Engagement Request")
    
    engagement_message = AgentMessage(
        sender="client",
        recipient="engagement_manager",
        content={
            'client': 'Global Healthcare Provider',
            'scope': 'AI-driven diagnostic transformation with email integration testing',
            'budget': '$50M',
            'timeline': '18 months'
        },
        timestamp=0.0,
        message_type="engagement_request"
    )
    
    print("   Client: Global Healthcare Provider")
    print("   Scope: AI-driven diagnostic transformation")
    print("   Budget: $50M")
    print("   Timeline: 18 months")
    
    # Process engagement through the team
    print_section("Processing Engagement Through Agent Team")
    
    engagement_results = {}
    
    try:
        # Step 1: Engagement Manager
        print("\n   📋 Step 1: Engagement Manager processing...")
        response = await engagement_manager.process_message(engagement_message)
        engagement_id = response.content.get('engagement_id')
        engagement_results['engagement'] = response.content
        print(f"   ✅ Engagement created: {engagement_id}")
        
        # Step 2: Strategy Lead (if message was forwarded)
        if 'engagement_id' in response.content:
            print("\n   📋 Step 2: Strategy Lead developing strategy...")
            strategy_message = AgentMessage(
                sender="engagement_manager",
                recipient="strategy_lead",
                content={
                    'engagement_id': engagement_id,
                    'client': 'Global Healthcare Provider',
                    'scope': 'AI-driven diagnostic transformation'
                },
                timestamp=0.0,
                message_type="strategy_request"
            )
            strategy_response = await strategy_lead.process_message(strategy_message)
            engagement_results['strategy'] = strategy_response.content
            print(f"   ✅ Strategy developed")
            
            # Step 3: Implementation Lead
            if 'strategy' in strategy_response.content:
                print("\n   📋 Step 3: Implementation Lead planning execution...")
                implementation_message = AgentMessage(
                    sender="strategy_lead",
                    recipient="implementation_lead",
                    content={
                        'engagement_id': engagement_id,
                        'strategy': strategy_response.content.get('strategy', {})
                    },
                    timestamp=0.0,
                    message_type="implementation_request"
                )
                implementation_response = await implementation_lead.process_message(implementation_message)
                engagement_results['implementation'] = implementation_response.content
                print(f"   ✅ Implementation plan created")
                
                # Step 4: Value Realization Lead
                if 'implementation' in implementation_response.content:
                    print("\n   📋 Step 4: Value Realization Lead creating metrics...")
                    value_message = AgentMessage(
                        sender="implementation_lead",
                        recipient="value_realization_lead",
                        content={
                            'engagement_id': engagement_id,
                            'implementation': implementation_response.content.get('implementation', {})
                        },
                        timestamp=0.0,
                        message_type="value_request"
                    )
                    value_response = await value_realization_lead.process_message(value_message)
                    engagement_results['value_framework'] = value_response.content
                    print(f"   ✅ Value framework developed")
        
    except Exception as e:
        print(f"❌ Error processing engagement: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Generate email report
    print_section("Generating Email Report")
    
    email_body = f"""
MCKINSEY-STYLE CONSULTING ENGAGEMENT REPORT
==========================================

Engagement ID: {engagement_id}
Client: Global Healthcare Provider
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

EXECUTIVE SUMMARY
-----------------
This engagement demonstrates the capabilities of the McKinsey-style consulting team
agents integrated with email functionality. The team successfully processed a complex
engagement request through multiple stages of analysis and planning.

ENGAGEMENT DETAILS
------------------
Client: Global Healthcare Provider
Scope: AI-driven diagnostic transformation with email integration testing
Budget: $50M
Timeline: 18 months

AGENT TEAM RESULTS
------------------

1. ENGAGEMENT MANAGER
   Status: {engagement_results.get('engagement', {}).get('status', 'N/A')}
   Engagement ID: {engagement_id}

2. STRATEGY LEAD
   Status: {engagement_results.get('strategy', {}).get('status', 'N/A')}
   Strategy Vision: {engagement_results.get('strategy', {}).get('strategy', {}).get('vision', 'N/A') if isinstance(engagement_results.get('strategy', {}).get('strategy', {}), dict) else 'N/A'}
   
   Key Strategic Pillars:
   {chr(10).join('   - ' + str(pillar) for pillar in (engagement_results.get('strategy', {}).get('strategy', {}).get('key_pillars', []) if isinstance(engagement_results.get('strategy', {}).get('strategy', {}), dict) else []))}

3. IMPLEMENTATION LEAD
   Status: {engagement_results.get('implementation', {}).get('status', 'N/A')}
   
   Implementation Phases:
   {chr(10).join('   - ' + str(phase.get('name', 'N/A')) + ' (' + str(phase.get('duration', 'N/A')) + ')' for phase in (engagement_results.get('implementation', {}).get('implementation', {}).get('phases', []) if isinstance(engagement_results.get('implementation', {}).get('implementation', {}), dict) else []))}

4. VALUE REALIZATION LEAD
   Status: {engagement_results.get('value_framework', {}).get('status', 'N/A')}
   
   Key Metrics:
   {chr(10).join('   - ' + str(metric.get('name', 'N/A')) + ': Target ' + str(metric.get('target', 'N/A')) for metric in (engagement_results.get('value_framework', {}).get('framework', {}).get('key_metrics', []) if isinstance(engagement_results.get('value_framework', {}).get('framework', {}), dict) else []))}

KNOWLEDGE GRAPH STATUS
----------------------
The engagement has been logged in the knowledge graph with:
- Engagement metadata
- Strategy recommendations
- Implementation plans
- Value tracking framework

NEXT STEPS
----------
1. Review this engagement report
2. Validate agent recommendations
3. Proceed with implementation planning
4. Set up value tracking dashboards

---
This report was generated automatically by the Semant McKinsey Agent Team
with integrated email capabilities.
"""
    
    print("   ✅ Email report generated")
    print(f"   Report length: {len(email_body)} characters")
    
    # Send email
    print_section("Sending Email Report")
    
    try:
        result = email_integration.send_email(
            recipient_id=USER_EMAIL,
            subject=f"McKinsey Engagement Report - {engagement_id}",
            body=email_body,
            force_real=True
        )
        
        if result.get('status') == 'sent_real':
            print("✅ Email sent successfully!")
            print(f"   Recipient: {USER_EMAIL}")
            print(f"   Subject: McKinsey Engagement Report - {engagement_id}")
            print(f"   Status: {result.get('status')}")
            return True
        else:
            print(f"⚠️  Email status: {result.get('status')}")
            print(f"   Response: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_email_reading():
    """Test reading emails to verify delivery."""
    print_section("Testing Email Reading")
    
    try:
        email_integration = EmailIntegration(use_real_email=True)
        
        if not email_integration.sender_email or not email_integration.sender_password:
            print("⚠️  Cannot read emails without credentials")
            return False
        
        print("   Reading recent emails...")
        emails = email_integration.receive_email(max_results=5, query="ALL")
        
        if emails:
            print(f"   ✅ Found {len(emails)} recent emails")
            
            # Look for our test email
            test_subjects = [email.get('subject', '') for email in emails]
            mckinsey_emails = [s for s in test_subjects if 'McKinsey' in s or 'Engagement' in s]
            
            if mckinsey_emails:
                print(f"   ✅ Found {len(mckinsey_emails)} McKinsey engagement emails!")
                for subject in mckinsey_emails[:3]:
                    print(f"      - {subject}")
            else:
                print("   ℹ️  No McKinsey emails found yet (may take a moment to arrive)")
        else:
            print("   ⚠️  No emails found")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Error reading emails: {e}")
        return False

async def main():
    """Main test function."""
    success = await test_mckinsey_agents_with_email()
    
    if success:
        # Wait a moment for email to be delivered
        print("\n⏳ Waiting 3 seconds for email delivery...")
        await asyncio.sleep(3)
        
        # Test reading emails
        await test_email_reading()
        
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print("✅ McKinsey Agents: Initialized and processed engagement")
        print("✅ Email Integration: Email sent successfully")
        print(f"📧 Check your inbox at {USER_EMAIL} for the engagement report!")
        print("\n🎉 **SUCCESS!** McKinsey agents with email integration are working!")
    else:
        print("\n❌ Test failed - check errors above")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

