#!/usr/bin/env python3
"""
Test: Agents Querying Knowledge Graph and Emailing Results

This demonstrates that agents can:
1. Query the knowledge graph directly from within their code
2. Extract information from KG queries
3. Generate email reports based on KG findings
4. Send emails automatically

Usage:
    python scripts/tools/test_kg_query_agent_email.py
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.domain.vertex_email_agent import VertexEmailAgent
from agents.core.base_agent import AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
from agents.utils.email_integration import EmailIntegration

USER_EMAIL = os.getenv("EMAIL_SENDER", "nicholas.k.baro@gmail.com")

def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"🔬 {title}")
    print("=" * 70)

class KGQueryEmailAgent(VertexEmailAgent):
    """An agent that queries the knowledge graph and emails results."""
    
    def __init__(self, agent_id: str = "kg_query_email_agent"):
        super().__init__(agent_id)
        self.kg_manager = None
    
    async def initialize(self) -> None:
        """Initialize the agent with knowledge graph access."""
        await super().initialize()
        
        # Initialize knowledge graph manager
        self.kg_manager = KnowledgeGraphManager(persistent_storage=True)
        await self.kg_manager.initialize()
        
        # Set the agent's knowledge graph reference
        self.knowledge_graph = self.kg_manager
        
        self.logger.info("KG Query Email Agent initialized with KG access")
    
    async def query_and_email_kg_findings(self, query_type: str = "all") -> bool:
        """Query the knowledge graph and email findings."""
        
        print_section(f"Querying Knowledge Graph ({query_type})")
        
        # Build SPARQL query based on type
        if query_type == "agents":
            sparql_query = """
            PREFIX agent: <http://example.org/demo/agent/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?agent ?type
            WHERE {
                ?agent rdf:type ?type .
                FILTER(STRSTARTS(STR(?type), "http://example.org/demo/"))
            }
            LIMIT 20
            """
        elif query_type == "engagements":
            sparql_query = """
            PREFIX consulting: <http://example.org/demo/consulting/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?engagement ?client ?scope ?budget
            WHERE {
                ?engagement rdf:type consulting:Engagement .
                OPTIONAL { ?engagement consulting:hasClient ?client . }
                OPTIONAL { ?engagement consulting:hasScope ?scope . }
                OPTIONAL { ?engagement consulting:hasBudget ?budget . }
            }
            LIMIT 10
            """
        else:  # all
            sparql_query = """
            SELECT ?subject ?predicate ?object
            WHERE {
                ?subject ?predicate ?object .
                FILTER(
                    STRSTARTS(STR(?subject), "agent:") ||
                    STRSTARTS(STR(?subject), "engagement:") ||
                    STRSTARTS(STR(?subject), "strategy:") ||
                    STRSTARTS(STR(?subject), "workflow:")
                )
            }
            LIMIT 50
            """
        
        try:
            print(f"   Executing SPARQL query...")
            print(f"   Query: {sparql_query[:100]}...")
            
            # Query the knowledge graph
            results = await self.query_knowledge_graph({"sparql": sparql_query})
            
            if not results:
                print("   ⚠️  No results found in knowledge graph")
                results = []
            elif isinstance(results, dict) and 'results' in results:
                results = results['results']
            elif not isinstance(results, list):
                results = [results] if results else []
            
            print(f"   ✅ Found {len(results)} result(s)")
            
            # Generate email report
            email_body = self._generate_email_report(results, query_type)
            
            # Send email using the agent's email capability
            print_section("Sending Email Report")
            print(f"   Recipient: {USER_EMAIL}")
            print(f"   Subject: Knowledge Graph Query Report - {query_type}")
            
            await self.send_email(
                recipient=USER_EMAIL,
                subject=f"Knowledge Graph Query Report - {query_type}",
                body=email_body
            )
            
            print("   ✅ Email sent successfully!")
            return True
            
        except Exception as e:
            print(f"   ❌ Error querying KG or sending email: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _generate_email_report(self, results: list, query_type: str) -> str:
        """Generate email report from query results."""
        
        report = f"""
KNOWLEDGE GRAPH QUERY REPORT
=============================

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Query Type: {query_type}
Results Found: {len(results)}

This email was generated by an agent querying the knowledge graph directly
from within its code. The agent discovered this information autonomously and
is now sharing it with you via email.

QUERY RESULTS
-------------
"""
        
        if not results:
            report += "\nNo results found in the knowledge graph for this query.\n"
        else:
            report += f"\nFound {len(results)} result(s):\n\n"
            
            for i, result in enumerate(results[:20], 1):  # Limit to 20 results
                report += f"{i}. "
                
                if isinstance(result, dict):
                    # Format dict results nicely
                    for key, value in result.items():
                        if value:
                            report += f"{key}: {value} | "
                    report = report.rstrip(" | ")
                else:
                    report += str(result)
                
                report += "\n"
        
        report += f"""

HOW THIS WORKS
--------------
1. Agent queries the knowledge graph using SPARQL
2. Agent extracts relevant information from query results
3. Agent formats the data into a readable report
4. Agent sends email automatically using EmailIntegration

This demonstrates that agents can:
- Access the knowledge graph independently
- Query for stored information
- Process and format results
- Send emails based on KG findings

---
Report generated by KG Query Email Agent
Knowledge Graph: {self.kg_manager.__class__.__name__ if self.kg_manager else 'N/A'}
"""
        
        return report

async def main():
    """Main test function."""
    print("\n" + "=" * 70)
    print("🚀 AGENT QUERYING KNOWLEDGE GRAPH + EMAIL TEST")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"User Email: {USER_EMAIL}")
    
    # Initialize the agent
    print_section("Initializing KG Query Email Agent")
    
    try:
        agent = KGQueryEmailAgent()
        await agent.initialize()
        print("   ✅ Agent initialized with KG access")
    except Exception as e:
        print(f"   ❌ Failed to initialize agent: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test querying and emailing
    success = await agent.query_and_email_kg_findings(query_type="all")
    
    if success:
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print("✅ Agent Initialized: With KG access")
        print("✅ Knowledge Graph: Queried successfully")
        print("✅ Email Report: Generated and sent")
        print(f"📧 Check your inbox at {USER_EMAIL}!")
        print("\n🎉 **SUCCESS!** Agents can query the KG and email you from inside!")
    else:
        print("\n❌ Test failed - check errors above")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

