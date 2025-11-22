#!/usr/bin/env python3
"""
Agent Conversation Viewer - Shows multi-agent interactions step by step
"""
import asyncio
from datetime import datetime
from kg.models.graph_manager import KnowledgeGraphManager
import json

class AgentConversationViewer:
    """Shows step-by-step agent conversations and interactions"""
    
    def __init__(self):
        self.kg = KnowledgeGraphManager(persistent_storage=True)
        
    async def show_agent_initialization(self):
        """Show how agents initialize and register"""
        print("🎯 STEP 1: AGENT INITIALIZATION")
        print("=" * 50)
        
        # Query for agent registration
        query = '''
        PREFIX : <http://example.org/core#>
        
        SELECT ?agent ?agentType ?authority ?status ?timestamp WHERE {
          ?agent a :Agent .
          OPTIONAL { ?agent :agentType ?agentType }
          OPTIONAL { ?agent :authority ?authority }
          OPTIONAL { ?agent :status ?status }
          ?agent :timestamp ?timestamp .
        }
        ORDER BY ?timestamp
        '''
        
        results = await self.kg.query_graph(query)
        if results:
            print("✅ AGENTS REGISTERED:")
            for result in results:
                agent_name = result.get('agent', 'unknown').split('/')[-1][:20]
                agent_type = result.get('agentType', 'unknown')
                authority = result.get('authority', 'SUPREME')
                status = result.get('status', 'unknown')
                timestamp = result.get('timestamp', 'unknown')[:19]
                print(f"   📝 {timestamp} - Agent '{agent_name}' ({agent_type})")
                print(f"      Authority: {authority} | Status: {status}")
        else:
            print("❌ No agents found - this is the initialization phase")
        
        print()
    
    async def show_planning_conversations(self):
        """Show planning phase conversations"""
        print("🎯 STEP 2: PLANNING CONVERSATIONS")
        print("=" * 50)
        
        # Query for plans and decisions
        plan_query = '''
        PREFIX : <http://example.org/core#>
        
        SELECT ?plan ?mission ?commander ?status ?created WHERE {
          ?plan a :FlyerCreationPlan ;
               :mission ?mission .
          OPTIONAL { ?plan :commander ?commander }
          OPTIONAL { ?plan :status ?status }
          OPTIONAL { ?plan :created ?created }
        }
        ORDER BY DESC(?created)
        '''
        
        plans = await self.kg.query_graph(plan_query)
        if plans:
            print("✅ PLANNING PHASE:")
            for result in plans:
                plan_id = result.get('plan', 'unknown').split('/')[-1][:20]
                mission = result.get('mission', 'unknown')
                commander = result.get('commander', 'unknown').split('/')[-1][:20]
                status = result.get('status', 'unknown')
                created = result.get('created', 'unknown')[:19]
                print(f"   📋 {created} - Plan '{plan_id}' created")
                print(f"      Mission: {mission}")
                print(f"      Commander: {commander}")
                print(f"      Status: {status}")
        else:
            print("❌ No plans found yet - planning phase in progress")
        
        print()
    
    async def show_execution_conversations(self):
        """Show execution phase conversations"""
        print("🎯 STEP 3: EXECUTION CONVERSATIONS")
        print("=" * 50)
        
        # Query for image generation and task execution
        execution_query = '''
        PREFIX : <http://example.org/core#>
        
        SELECT ?image ?prompt ?purpose ?taskId WHERE {
          ?image a :GeneratedImage .
          OPTIONAL { ?image :prompt ?prompt }
          OPTIONAL { ?image :purpose ?purpose }
          OPTIONAL { ?image :taskId ?taskId }
        }
        ORDER BY ?taskId
        '''
        
        executions = await self.kg.query_graph(execution_query)
        if executions:
            print("✅ EXECUTION PHASE:")
            for result in executions:
                image_id = result.get('image', 'unknown').split('/')[-1][:20]
                prompt = result.get('prompt', 'unknown')[:60] + '...'
                purpose = result.get('purpose', 'unknown')
                task_id = result.get('taskId', 'unknown')
                print(f"   🎨 Image '{image_id}' - Task: {task_id}")
                print(f"      Purpose: {purpose}")
                print(f"      Prompt: {prompt}")
        else:
            print("❌ No executions found - execution phase in progress")
        
        print()
    
    async def show_validation_conversations(self):
        """Show validation phase conversations"""
        print("🎯 STEP 4: VALIDATION CONVERSATIONS")
        print("=" * 50)
        
        # Query for decisions and validation
        validation_query = '''
        PREFIX : <http://example.org/core#>
        
        SELECT ?decision ?conclusion ?madeBy ?timestamp WHERE {
          ?decision a :AgentDecision .
          OPTIONAL { ?decision :conclusion ?conclusion }
          OPTIONAL { ?decision :madeBy ?madeBy }
          OPTIONAL { ?decision :timestamp ?timestamp }
        }
        ORDER BY DESC(?timestamp)
        '''
        
        validations = await self.kg.query_graph(validation_query)
        if validations:
            print("✅ VALIDATION PHASE:")
            for result in validations:
                decision_id = result.get('decision', 'unknown').split('/')[-1][:20]
                conclusion = result.get('conclusion', 'unknown')
                made_by = result.get('madeBy', 'unknown').split('/')[-1][:20]
                timestamp = result.get('timestamp', 'unknown')[:19]
                print(f"   ✅ {timestamp} - Decision '{decision_id}'")
                print(f"      Conclusion: {conclusion}")
                print(f"      Made by: {made_by}")
        else:
            print("❌ No validations found - validation phase in progress")
        
        print()
    
    async def show_knowledge_sharing(self):
        """Show knowledge sharing between agents"""
        print("🎯 STEP 5: KNOWLEDGE SHARING")
        print("=" * 50)
        
        # Query for knowledge shared between agents
        knowledge_query = '''
        PREFIX : <http://example.org/core#>
        
        SELECT ?knowledge ?content ?createdBy ?timestamp WHERE {
          ?knowledge a :Knowledge .
          OPTIONAL { ?knowledge :content ?content }
          OPTIONAL { ?knowledge :createdBy ?createdBy }
          OPTIONAL { ?knowledge :timestamp ?timestamp }
        }
        ORDER BY DESC(?timestamp)
        LIMIT 5
        '''
        
        knowledge_items = await self.kg.query_graph(knowledge_query)
        if knowledge_items:
            print("✅ KNOWLEDGE SHARED:")
            for result in knowledge_items:
                knowledge_id = result.get('knowledge', 'unknown').split('/')[-1][:20]
                content = result.get('content', 'unknown')[:50] + '...'
                created_by = result.get('createdBy', 'unknown').split('/')[-1][:15]
                timestamp = result.get('timestamp', 'unknown')[:19]
                print(f"   📚 {timestamp} - Knowledge '{knowledge_id}'")
                print(f"      Content: {content}")
                print(f"      Shared by: {created_by}")
        else:
            print("❌ No knowledge sharing found - knowledge phase in progress")
        
        print()
    
    async def run_conversation_analysis(self):
        """Complete analysis of multi-agent conversations"""
        print("🎯 MULTI-AGENT CONVERSATION ANALYSIS")
        print("=" * 60)
        
        await self.show_agent_initialization()
        await self.show_planning_conversations()
        await self.show_execution_conversations()
        await self.show_validation_conversations()
        await self.show_knowledge_sharing()
        
        print("🎉 CONVERSATION ANALYSIS COMPLETE!")
        print()
        print("🚀 TO SEE VISUAL REPRESENTATION:")
        print("   1. Open: http://localhost:8000/static/workflow_visualizer.html")
        print("   2. Enter: hot-dog-flyer-{timestamp}")
        print("   3. View: Interactive graph of all agent conversations")
        print()
        print("🔍 TO QUERY SPECIFIC CONVERSATIONS:")
        print("   1. Use SPARQL queries to drill down")
        print("   2. Filter by agent, time, or topic")
        print("   3. Trace conversation chains")

async def main():
    print("🎯 AGENT CONVERSATION VIEWER")
    print("=" * 50)
    
    viewer = AgentConversationViewer()
    await viewer.run_conversation_analysis()

if __name__ == "__main__":
    asyncio.run(main())
