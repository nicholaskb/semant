#!/usr/bin/env python3
"""
Knowledge Graph Interpretation Agent - Demonstrates agent interpretation tools
"""
import asyncio
import uuid
from datetime import datetime
from kg.models.graph_manager import KnowledgeGraphManager

class KnowledgeGraphInterpreter:
    """Agent with sophisticated KG interpretation capabilities"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.kg = KnowledgeGraphManager(persistent_storage=True)
        self.agent_uri = f"http://example.org/agent/{agent_id}"
    
    async def initialize_interpreter(self):
        """Initialize the interpretation agent"""
        print(f"🔧 Interpreter Agent {self.agent_id[:8]} initializing...")
        
        # Register interpretation capabilities
        await self.kg.add_triple(self.agent_uri, 'type', 'Agent')
        await self.kg.add_triple(self.agent_uri, 'agentType', 'knowledge_interpreter')
        await self.kg.add_triple(self.agent_uri, 'specialization', 'sparql_reasoning')
        await self.kg.add_triple(self.agent_uri, 'interpretationTools', 'sparql_engine')
        await self.kg.add_triple(self.agent_uri, 'interpretationTools', 'pattern_analyzer')
        await self.kg.add_triple(self.agent_uri, 'interpretationTools', 'decision_engine')
        
        print(f"✅ Interpreter Agent {self.agent_id[:8]} registered")
    
    async def basic_sparql_queries(self):
        """Demonstrate basic SPARQL interpretation tools"""
        print("🔍 1. BASIC SPARQL INTERPRETATION")
        print("-" * 40)
        
        # Count total entities by type
        type_query = '''
        SELECT ?type (COUNT(?type) AS ?count) WHERE {
          ?s ?p ?o .
          BIND(DATATYPE(?o) AS ?type)
        }
        GROUP BY ?type
        ORDER BY DESC(?count)
        LIMIT 5
        '''
        
        print("📊 Entity type distribution:")
        results = await self.kg.query_graph(type_query)
        for result in results:
            print(f"   • {result.get('type', 'unknown')}: {result.get('count', 0)} entities")
        
        # Find recent activity
        recent_query = '''
        SELECT ?timestamp ?activityType WHERE {
          ?s ?p ?o .
          ?s <http://example.org/core#timestamp> ?timestamp .
          BIND("data_modification" AS ?activityType)
        }
        ORDER BY DESC(?timestamp)
        LIMIT 3
        '''
        
        print("🕒 Recent activity:")
        recent_results = await self.kg.query_graph(recent_query)
        for result in recent_results:
            print(f"   • {result.get('timestamp', 'unknown')[:19]} - {result.get('activityType', 'unknown')}")
    
    async def pattern_analysis(self):
        """Demonstrate pattern recognition and analysis"""
        print("🔍 2. PATTERN ANALYSIS & REASONING")
        print("-" * 40)
        
        # Analyze agent activity patterns
        pattern_query = '''
        PREFIX core: <http://example.org/core#>
        
        SELECT ?agentType (COUNT(?agent) AS ?agentCount) 
               (GROUP_CONCAT(DISTINCT ?capability; SEPARATOR=", ") AS ?capabilities)
        WHERE {
          ?agent a core:Agent ;
                 core:agentType ?agentType .
          OPTIONAL { ?agent core:hasCapability ?capability }
        }
        GROUP BY ?agentType
        ORDER BY DESC(?agentCount)
        '''
        
        print("🤖 Agent capability patterns:")
        pattern_results = await self.kg.query_graph(pattern_query)
        for result in pattern_results:
            agent_type = result.get('agentType', 'unknown')
            count = result.get('agentCount', 0)
            capabilities = result.get('capabilities', 'none')
            print(f"   • {agent_type}: {count} agents")
            if capabilities != 'none':
                print(f"     Capabilities: {capabilities}")
    
    async def decision_making(self):
        """Demonstrate decision making based on interpreted data"""
        print("🔍 3. DECISION MAKING BASED ON INTERPRETATION")
        print("-" * 40)
        
        # Analyze system health based on multiple factors
        health_query = '''
        PREFIX core: <http://example.org/core#>
        
        SELECT 
          (COUNT(DISTINCT ?agent) AS ?activeAgents)
          (COUNT(DISTINCT ?task) AS ?totalTasks)
          (AVG(?progress) AS ?avgProgress)
        WHERE {
          { ?agent a core:Agent ; core:status "active" . }
          UNION
          { ?task a core:Task ; core:status ?status .
            OPTIONAL { ?task core:hasProgress ?progress } }
        }
        '''
        
        health_results = await self.kg.query_graph(health_query)
        if health_results:
            result = health_results[0]
            active_agents = int(result.get('activeAgents', 0))
            total_tasks = int(result.get('totalTasks', 0))
            avg_progress = float(result.get('avgProgress', 0))
            
            print("📊 System Health Analysis:")
            print(f"   • Active agents: {active_agents}")
            print(f"   • Total tasks: {total_tasks}")
            print(f"   • Average progress: {avg_progress:.1f}%")
            
            # Make interpretation decisions
            if active_agents > 5:
                interpretation = "System has high agent activity"
                recommendation = "Consider load balancing"
            elif active_agents == 0:
                interpretation = "No agents are active"
                recommendation = "Investigate agent failures"
            else:
                interpretation = "Normal agent activity level"
                recommendation = "Continue monitoring"
            
            if avg_progress < 30:
                interpretation += ", but low overall progress"
                recommendation += " and check for bottlenecks"
            elif avg_progress > 80:
                interpretation += " with high progress"
                recommendation += " - system performing well"
            
            print(f"🧠 Interpretation: {interpretation}")
            print(f"🎯 Recommendation: {recommendation}")
    
    async def multi_hop_reasoning(self):
        """Demonstrate complex multi-hop reasoning"""
        print("🔍 4. MULTI-HOP REASONING")
        print("-" * 40)
        
        # Find complex relationships between entities
        reasoning_query = '''
        PREFIX core: <http://example.org/core#>
        
        SELECT ?startEntity ?relationship ?endEntity ?pathLength WHERE {
          ?startEntity ?prop1 ?middle .
          ?middle ?prop2 ?endEntity .
          BIND(CONCAT(STR(?prop1), " -> ", STR(?prop2)) AS ?relationship)
          BIND("2-hop" AS ?pathLength)
          FILTER(?startEntity != ?endEntity)
        }
        ORDER BY ?startEntity
        LIMIT 5
        '''
        
        print("🔗 Multi-hop relationship analysis:")
        reasoning_results = await self.kg.query_graph(reasoning_query)
        for result in reasoning_results:
            start = result.get('startEntity', 'unknown').split('/')[-1][:12]
            relationship = result.get('relationship', 'unknown')
            end = result.get('endEntity', 'unknown').split('/')[-1][:12]
            path_length = result.get('pathLength', 'unknown')
            print(f"   • {start}... {relationship} {end}... ({path_length})")
    
    async def temporal_analysis(self):
        """Demonstrate temporal interpretation and trend analysis"""
        print("🔍 5. TEMPORAL ANALYSIS & TRENDING")
        print("-" * 40)
        
        # Analyze temporal patterns
        temporal_query = '''
        PREFIX core: <http://example.org/core#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        SELECT 
          (COUNT(?timestamp) AS ?activityCount)
          (MIN(?timestamp) AS ?earliestActivity)
          (MAX(?timestamp) AS ?latestActivity)
        WHERE {
          ?s ?p ?o .
          ?s core:timestamp ?timestamp .
          FILTER(DATATYPE(?timestamp) = xsd:dateTime)
        }
        '''
        
        temporal_results = await self.kg.query_graph(temporal_query)
        if temporal_results:
            result = temporal_results[0]
            activity_count = int(result.get('activityCount', 0))
            earliest = result.get('earliestActivity', 'unknown')
            latest = result.get('latestActivity', 'unknown')
            
            print("📈 Temporal Activity Analysis:")
            print(f"   • Total activities: {activity_count}")
            print(f"   • Earliest activity: {earliest[:19]}")
            print(f"   • Latest activity: {latest[:19]}")
            
            # Make trend interpretation
            if activity_count > 100:
                trend = "High activity system"
                insight = "Knowledge graph is actively growing"
            elif activity_count > 50:
                trend = "Moderate activity system"
                insight = "Steady knowledge accumulation"
            else:
                trend = "Low activity system"
                insight = "Knowledge graph in early stages"
            
            print(f"📊 Trend: {trend}")
            print(f"🔍 Insight: {insight}")
    
    async def run_interpretation_cycle(self):
        """Complete interpretation cycle demonstrating all tools"""
        print(f"🚀 Interpreter Agent {self.agent_id[:8]} starting analysis...")
        
        # Initialize
        await self.initialize_interpreter()
        print()
        
        # Basic SPARQL queries
        await self.basic_sparql_queries()
        print()
        
        # Pattern analysis
        await self.pattern_analysis()
        print()
        
        # Decision making
        await self.decision_making()
        print()
        
        # Multi-hop reasoning
        await self.multi_hop_reasoning()
        print()
        
        # Temporal analysis
        await self.temporal_analysis()
        print()
        
        print("🎉 INTERPRETATION CYCLE COMPLETE!")
        print("   • Demonstrated 5 different interpretation tools")
        print("   • Analyzed data patterns and relationships")
        print("   • Made intelligent decisions based on KG content")
        print("   • Performed multi-hop reasoning")
        print("   • Analyzed temporal trends")

async def main():
    print("🎯 KNOWLEDGE GRAPH INTERPRETATION AGENT")
    print("=" * 50)
    
    # Create interpretation agent
    interpreter = KnowledgeGraphInterpreter("kg-interpreter-2025")
    
    # Run complete interpretation cycle
    await interpreter.run_interpretation_cycle()
    
    print()
    print("🚀 AGENT INTERPRETATION TOOLS DEMONSTRATED!")
    print("   • SPARQL Query Engine")
    print("   • Pattern Recognition")
    print("   • Decision Making Engine")
    print("   • Multi-hop Reasoning")
    print("   • Temporal Analysis")
    print("   • Statistical Processing")

if __name__ == "__main__":
    asyncio.run(main())
