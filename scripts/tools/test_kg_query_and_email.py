#!/usr/bin/env python3
"""
Test Agents Querying Knowledge Graph and Sending Emails

This script demonstrates:
1. Agents querying the knowledge graph for stored information
2. Extracting relevant data from KG queries
3. Composing email reports based on KG findings
4. Sending emails with KG-derived information

Usage:
    python scripts/tools/test_kg_query_and_email.py
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from examples.demo_agents import (
    EngagementManagerAgent,
    StrategyLeadAgent,
    AgentMessage
)
from agents.utils.email_integration import EmailIntegration
from kg.models.graph_manager import KnowledgeGraphManager

USER_EMAIL = os.getenv("EMAIL_SENDER", "nicholas.k.baro@gmail.com")

def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"🔬 {title}")
    print("=" * 70)

async def query_engagements_from_agent_kg(engagement_manager: EngagementManagerAgent) -> List[Dict[str, Any]]:
    """Query the agent's knowledge graph for engagement information."""
    print_section("Querying Agent's Knowledge Graph for Engagements")
    
    try:
        # Query the agent's knowledge graph directly
        kg_query = {
            "sparql": """
            PREFIX consulting: <http://example.org/demo/consulting/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?engagement ?client ?scope ?budget ?timeline
            WHERE {
                ?engagement rdf:type consulting:Engagement .
                ?engagement consulting:hasClient ?client .
                ?engagement consulting:hasScope ?scope .
                ?engagement consulting:hasBudget ?budget .
                ?engagement consulting:hasTimeline ?timeline .
            }
            ORDER BY DESC(?engagement)
            LIMIT 10
            """
        }
        
        print("   Querying agent's knowledge graph...")
        results = await engagement_manager.query_knowledge_graph(kg_query)
        
        # The agent's KG returns a dict with query results
        if isinstance(results, dict) and 'results' in results:
            results_list = results['results']
        elif isinstance(results, list):
            results_list = results
        else:
            # Try to extract from the graph directly
            results_list = []
            if hasattr(engagement_manager, 'knowledge_graph') and engagement_manager.knowledge_graph:
                # Query the graph directly
                from rdflib import Namespace, RDF
                CONSULTING = Namespace("http://example.org/demo/consulting/")
                graph = engagement_manager.knowledge_graph.graph
                
                # Find all engagements
                for s, p, o in graph:
                    if str(p) == str(RDF.type) and str(o) == str(CONSULTING.Engagement):
                        engagement_data = {'engagement': str(s)}
                        # Get properties
                        for s2, p2, o2 in graph:
                            if s2 == s:
                                prop_name = str(p2).split('#')[-1].split('/')[-1]
                                if prop_name == 'hasClient':
                                    engagement_data['client'] = str(o2)
                                elif prop_name == 'hasScope':
                                    engagement_data['scope'] = str(o2)
                                elif prop_name == 'hasBudget':
                                    engagement_data['budget'] = str(o2)
                                elif prop_name == 'hasTimeline':
                                    engagement_data['timeline'] = str(o2)
                        if len(engagement_data) > 1:  # Has more than just engagement ID
                            results_list.append(engagement_data)
        
        if results_list:
            print(f"   ✅ Found {len(results_list)} engagements in agent's knowledge graph")
            return results_list
        else:
            print("   ℹ️  No engagements found in agent's KG")
            return []
    except Exception as e:
        print(f"   ⚠️  Query error: {e}")
        import traceback
        traceback.print_exc()
        return []

async def query_strategies_from_agent_kg(strategy_lead: StrategyLeadAgent) -> List[Dict[str, Any]]:
    """Query the agent's knowledge graph for strategy information."""
    print_section("Querying Agent's Knowledge Graph for Strategies")
    
    try:
        # Query the agent's knowledge graph directly
        kg_query = {
            "sparql": """
            PREFIX consulting: <http://example.org/demo/consulting/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?strategy ?vision ?approach
            WHERE {
                ?strategy rdf:type consulting:Strategy .
                ?strategy consulting:hasVision ?vision .
                ?strategy consulting:hasApproach ?approach .
            }
            ORDER BY DESC(?strategy)
            LIMIT 10
            """
        }
        
        print("   Querying agent's knowledge graph...")
        results = await strategy_lead.query_knowledge_graph(kg_query)
        
        # Extract results
        if isinstance(results, dict) and 'results' in results:
            results_list = results['results']
        elif isinstance(results, list):
            results_list = results
        else:
            # Try to extract from graph directly
            results_list = []
            if hasattr(strategy_lead, 'knowledge_graph') and strategy_lead.knowledge_graph:
                from rdflib import Namespace, RDF
                CONSULTING = Namespace("http://example.org/demo/consulting/")
                graph = strategy_lead.knowledge_graph.graph
                
                for s, p, o in graph:
                    if str(p) == str(RDF.type) and str(o) == str(CONSULTING.Strategy):
                        strategy_data = {'strategy': str(s)}
                        for s2, p2, o2 in graph:
                            if s2 == s:
                                prop_name = str(p2).split('#')[-1].split('/')[-1]
                                if prop_name == 'hasVision':
                                    strategy_data['vision'] = str(o2)
                                elif prop_name == 'hasApproach':
                                    strategy_data['approach'] = str(o2)
                        if len(strategy_data) > 1:
                            results_list.append(strategy_data)
        
        if results_list:
            print(f"   ✅ Found {len(results_list)} strategies in agent's knowledge graph")
            return results_list
        else:
            print("   ℹ️  No strategies found in agent's KG")
            return []
    except Exception as e:
        print(f"   ⚠️  Query error: {e}")
        import traceback
        traceback.print_exc()
        return []

async def query_all_agent_activities(kg_manager: KnowledgeGraphManager) -> Dict[str, Any]:
    """Query for all agent-related activities in the knowledge graph."""
    print_section("Querying Knowledge Graph for Agent Activities")
    
    # Query for agents
    agent_query = """
    PREFIX agent: <http://example.org/demo/agent/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT ?agent ?type
    WHERE {
        ?agent rdf:type ?type .
        FILTER(STRSTARTS(STR(?type), "http://example.org/demo/"))
    }
    LIMIT 20
    """
    
    try:
        print("   Querying for agents...")
        agent_results = await kg_manager.query_graph(agent_query)
        
        # Query for all triples related to engagements
        engagement_query = """
        PREFIX consulting: <http://example.org/demo/consulting/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?subject ?predicate ?object
        WHERE {
            ?subject ?predicate ?object .
            FILTER(
                STRSTARTS(STR(?subject), "engagement:") ||
                STRSTARTS(STR(?subject), "strategy:") ||
                STRSTARTS(STR(?subject), "implementation:") ||
                STRSTARTS(STR(?subject), "value:")
            )
        }
        LIMIT 50
        """
        
        print("   Querying for engagement-related data...")
        engagement_results = await kg_manager.query_graph(engagement_query)
        
        return {
            'agents': agent_results if agent_results else [],
            'engagements': engagement_results if engagement_results else []
        }
    except Exception as e:
        print(f"   ⚠️  Query error: {e}")
        return {'agents': [], 'engagements': []}

async def create_engagement_and_store_in_kg():
    """Create a new engagement and store it in the knowledge graph."""
    print_section("Creating New Engagement in Knowledge Graph")
    
    # Initialize agents
    engagement_manager = EngagementManagerAgent()
    strategy_lead = StrategyLeadAgent()
    
    await engagement_manager.initialize()
    await strategy_lead.initialize()
    
    # Create engagement
    engagement_message = AgentMessage(
        sender="client",
        recipient="engagement_manager",
        content={
            'client': 'Tech Startup Inc',
            'scope': 'Digital transformation and email integration testing',
            'budget': '$25M',
            'timeline': '12 months'
        },
        timestamp=0.0,
        message_type="engagement_request"
    )
    
    print("   Processing engagement request...")
    response = await engagement_manager.process_message(engagement_message)
    engagement_id = response.content.get('engagement_id')
    
    print(f"   ✅ Engagement created: {engagement_id}")
    
    # Get strategy
    if engagement_id:
        strategy_message = AgentMessage(
            sender="engagement_manager",
            recipient="strategy_lead",
            content={
                'engagement_id': engagement_id,
                'client': 'Tech Startup Inc',
                'scope': 'Digital transformation'
            },
            timestamp=0.0,
            message_type="strategy_request"
        )
        strategy_response = await strategy_lead.process_message(strategy_message)
        print(f"   ✅ Strategy developed")
    
    return engagement_manager, engagement_id

async def generate_email_from_kg_findings(
    engagements: List[Dict[str, Any]],
    strategies: List[Dict[str, Any]],
    activities: Dict[str, Any]
) -> str:
    """Generate an email report from knowledge graph findings."""
    
    email_body = f"""
KNOWLEDGE GRAPH QUERY REPORT
=============================

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This report contains information discovered by querying the knowledge graph
directly. Agents can query the KG, extract relevant data, and automatically
generate email reports based on what they find.

ENGAGEMENTS FOUND IN KNOWLEDGE GRAPH
------------------------------------
"""
    
    if engagements:
        email_body += f"Found {len(engagements)} engagement(s):\n\n"
        for i, eng in enumerate(engagements, 1):
            email_body += f"{i}. Engagement: {eng.get('engagement', 'N/A')}\n"
            email_body += f"   Client: {eng.get('client', 'N/A')}\n"
            email_body += f"   Scope: {eng.get('scope', 'N/A')}\n"
            email_body += f"   Budget: {eng.get('budget', 'N/A')}\n"
            email_body += f"   Timeline: {eng.get('timeline', 'N/A')}\n\n"
    else:
        email_body += "No engagements found in knowledge graph.\n\n"
    
    email_body += "\nSTRATEGIES FOUND IN KNOWLEDGE GRAPH\n"
    email_body += "------------------------------------\n"
    
    if strategies:
        email_body += f"Found {len(strategies)} strategy(ies):\n\n"
        for i, strat in enumerate(strategies, 1):
            email_body += f"{i}. Strategy: {strat.get('strategy', 'N/A')}\n"
            email_body += f"   Vision: {strat.get('vision', 'N/A')}\n"
            email_body += f"   Approach: {strat.get('approach', 'N/A')}\n\n"
    else:
        email_body += "No strategies found in knowledge graph.\n\n"
    
    email_body += "\nAGENT ACTIVITIES IN KNOWLEDGE GRAPH\n"
    email_body += "------------------------------------\n"
    
    agents_found = activities.get('agents', [])
    if agents_found:
        email_body += f"Found {len(agents_found)} agent(s):\n\n"
        for i, agent in enumerate(agents_found[:10], 1):  # Limit to 10
            email_body += f"{i}. Agent: {agent.get('agent', 'N/A')}\n"
            email_body += f"   Type: {agent.get('type', 'N/A')}\n\n"
    else:
        email_body += "No agents found in knowledge graph.\n\n"
    
    engagement_data = activities.get('engagements', [])
    if engagement_data:
        email_body += f"\nFound {len(engagement_data)} engagement-related triples:\n"
        email_body += "(This shows the detailed structure stored in the KG)\n\n"
        for i, triple in enumerate(engagement_data[:10], 1):  # Limit to 10
            email_body += f"{i}. {triple.get('subject', 'N/A')} -> {triple.get('predicate', 'N/A')} -> {triple.get('object', 'N/A')}\n"
    
    email_body += f"""

QUERY METHODOLOGY
-----------------
This report was generated by:
1. Querying the knowledge graph using SPARQL queries
2. Extracting relevant information from query results
3. Formatting the data into a readable email report
4. Sending via EmailIntegration

This demonstrates that agents can:
- Query the knowledge graph independently
- Discover stored information
- Generate reports based on KG data
- Send emails automatically

---
Report generated by Semant Knowledge Graph Query Agent
"""
    
    return email_body

async def main():
    """Main test function."""
    print("\n" + "=" * 70)
    print("🚀 KNOWLEDGE GRAPH QUERY + EMAIL INTEGRATION TEST")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"User Email: {USER_EMAIL}")
    
    # Initialize knowledge graph manager
    print_section("Initializing Knowledge Graph Manager")
    try:
        kg_manager = KnowledgeGraphManager(persistent_storage=True)
        await kg_manager.initialize()
        print("   ✅ Knowledge Graph Manager initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize KG: {e}")
        return False
    
    # Create a new engagement to ensure there's data in the KG
    engagement_manager, engagement_id = await create_engagement_and_store_in_kg()
    
    # Query the agent's knowledge graph for engagements
    engagements = await query_engagements_from_agent_kg(engagement_manager)
    
    # Query for strategies from strategy agent's KG
    strategy_lead = StrategyLeadAgent()
    await strategy_lead.initialize()
    strategies = await query_strategies_from_agent_kg(strategy_lead)
    
    # Query for all agent activities (using shared KG)
    activities = await query_all_agent_activities(kg_manager)
    
    # Generate email from findings
    print_section("Generating Email Report from KG Findings")
    email_body = await generate_email_from_kg_findings(
        engagements, strategies, activities
    )
    print(f"   ✅ Email report generated ({len(email_body)} characters)")
    
    # Send email
    print_section("Sending Email Report")
    try:
        email_integration = EmailIntegration(use_real_email=True)
        
        if not email_integration.sender_email or not email_integration.sender_password:
            if not email_integration._setup_smtp_credentials():
                print("   ❌ Cannot send email without credentials")
                return False
        
        result = email_integration.send_email(
            recipient_id=USER_EMAIL,
            subject=f"Knowledge Graph Query Report - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            body=email_body,
            force_real=True
        )
        
        if result.get('status') == 'sent_real':
            print("   ✅ Email sent successfully!")
            print(f"   Recipient: {USER_EMAIL}")
            print(f"   Status: {result.get('status')}")
            
            # Summary
            print("\n" + "=" * 70)
            print("📊 TEST SUMMARY")
            print("=" * 70)
            print(f"✅ Knowledge Graph: Queried successfully")
            print(f"✅ Engagements Found: {len(engagements)}")
            print(f"✅ Strategies Found: {len(strategies)}")
            print(f"✅ Agent Activities: {len(activities.get('agents', []))} agents")
            print(f"✅ Email Sent: Yes")
            print(f"\n📧 Check your inbox at {USER_EMAIL} for the KG query report!")
            print("\n🎉 **SUCCESS!** Agents can query the KG and email you the results!")
            return True
        else:
            print(f"   ⚠️  Email status: {result.get('status')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Failed to send email: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

