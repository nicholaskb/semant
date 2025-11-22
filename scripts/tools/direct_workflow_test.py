#!/usr/bin/env python3
"""
Direct Workflow Data Access - Bypassing the API for testing
"""
import asyncio
from kg.models.graph_manager import KnowledgeGraphManager
import json

class DirectWorkflowViewer:
    """Direct access to workflow data for testing"""
    
    def __init__(self):
        self.kg = KnowledgeGraphManager(persistent_storage=True)
        
    async def show_workflow_data(self, workflow_id):
        """Show all data related to a workflow"""
        print(f"🎯 SEARCHING FOR WORKFLOW: {workflow_id}")
        print("=" * 60)
        
        await self.kg.initialize()
        
        # Find the workflow entity
        workflow_uri = f"http://example.org/plan/{workflow_id}"
        print(f"🔍 Looking for workflow URI: {workflow_uri}")
        
        # Query for workflow data without namespace prefixes
        workflow_query = f'''
        SELECT ?p ?o WHERE {{
          <{workflow_uri}> ?p ?o .
        }}
        '''
        
        results = await self.kg.query_graph(workflow_query)
        if results:
            print("✅ WORKFLOW DATA FOUND:")
            for result in results:
                p = str(result.get('p', 'unknown')).split('/')[-1]
                o = str(result.get('o', 'unknown'))
                print(f"   • {p}: {o}")
        else:
            print("❌ No workflow data found")
        
        print()
        
        # Find the agent that created the workflow
        agent_query = f'''
        SELECT ?agent ?p ?o WHERE {{
          ?agent ?p ?o .
          FILTER(CONTAINS(STR(?agent), 'flyer-planner'))
        }}
        '''
        
        agent_results = await self.kg.query_graph(agent_query)
        if agent_results:
            print("✅ AGENT DATA FOUND:")
            for result in agent_results:
                agent = str(result.get('agent', 'unknown')).split('/')[-1]
                p = str(result.get('p', 'unknown')).split('/')[-1]
                o = str(result.get('o', 'unknown'))
                print(f"   • Agent: {agent} - {p}: {o}")
        
        print()
        
        # Find all related data
        related_query = f'''
        SELECT ?s ?p ?o WHERE {{
          ?s ?p ?o .
          FILTER(CONTAINS(STR(?s), '{workflow_id}') || CONTAINS(STR(?o), '{workflow_id}'))
        }}
        '''
        
        related_results = await self.kg.query_graph(related_query)
        if related_results:
            print("✅ ALL WORKFLOW-RELATED DATA:")
            for result in related_results:
                s = str(result.get('s', 'unknown')).split('/')[-1][:30]
                p = str(result.get('p', 'unknown')).split('/')[-1][:20]
                o = str(result.get('o', 'unknown'))[:40]
                print(f"   • {s}... → {p}... → {o}...")

async def main():
    print("🎯 DIRECT WORKFLOW DATA ACCESS")
    print("=" * 50)
    
    viewer = DirectWorkflowViewer()
    
    # Test with the workflow ID from our run
    workflow_id = "hot-dog-flyer-1758823969"
    await viewer.show_workflow_data(workflow_id)
    
    print()
    print("🚀 TO VIEW IN BROWSER:")
    print("   1. Open: http://localhost:8000/static/workflow_visualizer.html")
    print(f"   2. Enter: {workflow_id}")
    print("   3. Click: Visualize")

if __name__ == "__main__":
    asyncio.run(main())
