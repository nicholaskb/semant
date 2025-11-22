#!/usr/bin/env python3
"""
Knowledge Graph Review and Email Notification Script

This script demonstrates how agents can:
1. Query the knowledge graph for images
2. Review knowledge graph status
3. Send email notifications about findings

Usage:
    python scripts/tools/kg_review_and_email.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.utils.email_integration import EmailIntegration
from kg.models.graph_manager import KnowledgeGraphManager
from loguru import logger

class KGReviewAgent:
    """Agent that reviews knowledge graph and sends email notifications."""
    
    def __init__(self):
        self.kg_manager = KnowledgeGraphManager(persistent_storage=True)
        self.email = EmailIntegration(use_real_email=True)
        self.logger = logger.bind(agent="KGReviewAgent")
    
    async def initialize(self):
        """Initialize the agent."""
        await self.kg_manager.initialize()
        self.logger.info("KG Review Agent initialized")
    
    async def check_images_in_kg(self) -> Dict[str, Any]:
        """Check if images exist in the knowledge graph."""
        query = """
        PREFIX schema: <http://schema.org/>
        PREFIX kg: <http://example.org/kg#>
        PREFIX book: <http://example.org/childrens-book#>
        
        SELECT (COUNT(?image) as ?count) ?type WHERE {
            ?image a schema:ImageObject .
            OPTIONAL { ?image kg:imageType ?type . }
        }
        GROUP BY ?type
        """
        
        try:
            results = await self.kg_manager.query_graph(query)
            
            # Also get total count
            total_query = """
            PREFIX schema: <http://schema.org/>
            SELECT (COUNT(?image) as ?total) WHERE {
                ?image a schema:ImageObject .
            }
            """
            total_results = await self.kg_manager.query_graph(total_query)
            total_count = int(total_results[0]["total"]) if total_results else 0
            
            # Get sample images
            sample_query = """
            PREFIX schema: <http://schema.org/>
            SELECT ?image ?name ?url WHERE {
                ?image a schema:ImageObject ;
                       schema:name ?name ;
                       schema:contentUrl ?url .
            }
            LIMIT 10
            """
            sample_results = await self.kg_manager.query_graph(sample_query)
            
            return {
                "total_images": total_count,
                "by_type": {r.get("type", "unknown"): int(r["count"]) for r in results} if results else {},
                "sample_images": [
                    {
                        "uri": str(r["image"]),
                        "name": str(r.get("name", "Unknown")),
                        "url": str(r.get("url", ""))
                    }
                    for r in sample_results[:5]
                ],
                "has_images": total_count > 0
            }
        except Exception as e:
            self.logger.error(f"Error checking images: {e}")
            return {"error": str(e), "has_images": False}
    
    async def review_knowledge_graph(self) -> Dict[str, Any]:
        """Review knowledge graph status and return summary."""
        try:
            # Check total triples
            triple_query = """
            SELECT (COUNT(*) as ?count) WHERE {
                ?s ?p ?o .
            }
            """
            triple_results = await self.kg_manager.query_graph(triple_query)
            total_triples = int(triple_results[0]["count"]) if triple_results else 0
            
            # Check for agents
            agent_query = """
            PREFIX core: <http://example.org/core#>
            SELECT (COUNT(?agent) as ?count) WHERE {
                ?agent a core:Agent .
            }
            """
            agent_results = await self.kg_manager.query_graph(agent_query)
            agent_count = int(agent_results[0]["count"]) if agent_results else 0
            
            # Check for workflows
            workflow_query = """
            PREFIX wf: <http://example.org/ontology#>
            SELECT (COUNT(?workflow) as ?count) WHERE {
                ?workflow a wf:Workflow .
            }
            """
            workflow_results = await self.kg_manager.query_graph(workflow_query)
            workflow_count = int(workflow_results[0]["count"]) if workflow_results else 0
            
            # Check images
            image_info = await self.check_images_in_kg()
            
            return {
                "total_triples": total_triples,
                "agent_count": agent_count,
                "workflow_count": workflow_count,
                "image_info": image_info,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error reviewing KG: {e}")
            return {"error": str(e)}
    
    async def send_review_email(self, recipient: str, review_data: Dict[str, Any]) -> bool:
        """Send email with knowledge graph review results."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format email body
        body = f"""Knowledge Graph Review Report
Generated: {timestamp}

📊 KNOWLEDGE GRAPH STATUS
==========================

Total Triples: {review_data.get('total_triples', 0):,}
Agents: {review_data.get('agent_count', 0)}
Workflows: {review_data.get('workflow_count', 0)}

🖼️ IMAGE STATUS
================

"""
        
        image_info = review_data.get('image_info', {})
        if image_info.get('has_images'):
            body += f"✅ Images Found: {image_info.get('total_images', 0)} total\n\n"
            
            if image_info.get('by_type'):
                body += "By Type:\n"
                for img_type, count in image_info['by_type'].items():
                    body += f"  • {img_type}: {count}\n"
                body += "\n"
            
            if image_info.get('sample_images'):
                body += "Sample Images:\n"
                for img in image_info['sample_images'][:5]:
                    body += f"  • {img.get('name', 'Unknown')}: {img.get('url', 'N/A')}\n"
        else:
            body += "❌ No images found in knowledge graph\n"
            if 'error' in image_info:
                body += f"Error: {image_info['error']}\n"
        
        body += f"""

🔍 REVIEW SUMMARY
==================

"""
        
        if review_data.get('total_triples', 0) > 0:
            body += "✅ Knowledge graph is active and contains data\n"
        else:
            body += "⚠️ Knowledge graph appears empty\n"
        
        if image_info.get('has_images'):
            body += "✅ Images are present in the knowledge graph\n"
        else:
            body += "⚠️ No images found in knowledge graph\n"
        
        body += f"""

---
🤖 Automated Knowledge Graph Review
📧 Sent by KG Review Agent
"""
        
        subject = f"Knowledge Graph Review - {timestamp}"
        
        try:
            result = self.email.send_email(
                recipient_id=recipient,
                subject=subject,
                body=body,
                force_real=True
            )
            
            if result.get('status') == 'sent_real':
                self.logger.info(f"Review email sent successfully to {recipient}")
                return True
            else:
                self.logger.warning(f"Email simulated: {result.get('status')}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to send review email: {e}")
            return False

async def main():
    """Main function to run KG review and send email."""
    print("🔍 **KNOWLEDGE GRAPH REVIEW AND EMAIL NOTIFICATION**")
    print("=" * 70)
    
    agent = KGReviewAgent()
    await agent.initialize()
    
    print("\n📊 Reviewing knowledge graph...")
    review_data = await agent.review_knowledge_graph()
    
    print(f"\n✅ Review Complete!")
    print(f"   Total Triples: {review_data.get('total_triples', 0):,}")
    print(f"   Agents: {review_data.get('agent_count', 0)}")
    print(f"   Workflows: {review_data.get('workflow_count', 0)}")
    
    image_info = review_data.get('image_info', {})
    if image_info.get('has_images'):
        print(f"   ✅ Images Found: {image_info.get('total_images', 0)}")
    else:
        print(f"   ⚠️  No images found in knowledge graph")
    
    print("\n📧 Sending email notification...")
    success = await agent.send_review_email(
        recipient="nicholas.k.baro@gmail.com",
        review_data=review_data
    )
    
    if success:
        print("\n🎉 **EMAIL SENT SUCCESSFULLY!**")
        print("👀 Check your inbox for the knowledge graph review report")
    else:
        print("\n⚠️  Email sending failed or was simulated")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

