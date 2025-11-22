#!/usr/bin/env python3
"""
Midjourney Task Monitoring Agent - Real-time KG modification example
"""
import asyncio
import uuid
from datetime import datetime
from kg.models.graph_manager import KnowledgeGraphManager

class MidjourneyMonitoringAgent:
    """Agent that monitors Midjourney tasks and updates knowledge graph in real-time"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.kg = KnowledgeGraphManager(persistent_storage=True)
        self.agent_uri = f"http://example.org/agent/{agent_id}"
    
    async def initialize_agent(self):
        """Agent registers itself in the knowledge graph"""
        print(f"🔧 Agent {self.agent_id[:8]} initializing...")
        
        # Register agent capabilities
        await self.kg.add_triple(
            self.agent_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/core#Agent"
        )
        await self.kg.add_triple(
            self.agent_uri,
            "http://example.org/core#agentType",
            "midjourney_monitor"
        )
        await self.kg.add_triple(
            self.agent_uri,
            "http://example.org/core#status",
            "active"
        )
        await self.kg.add_triple(
            self.agent_uri,
            "http://example.org/core#specialization",
            "task_progress_monitoring"
        )
        
        # Register monitoring session
        session_uri = f"http://example.org/session/{self.agent_id}"
        await self.kg.add_triple(
            session_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/core#MonitoringSession"
        )
        await self.kg.add_triple(
            session_uri,
            "http://example.org/core#agent",
            self.agent_uri
        )
        await self.kg.add_triple(
            session_uri,
            "http://example.org/core#startTime",
            datetime.now().isoformat()
        )
        
        print(f"✅ Agent {self.agent_id[:8]} registered in KG")
        return session_uri
    
    async def analyze_existing_tasks(self):
        """Agent queries existing Midjourney tasks"""
        print(f"🔍 Agent {self.agent_id[:8]} analyzing existing tasks...")
        
        # Query for all Midjourney tool calls
        task_query = '''
        PREFIX : <http://example.org/core#>
        PREFIX ns1: <http://example.org/midjourney#>
        
        SELECT ?taskId ?status ?timestamp WHERE {
          ?toolCall :relatedTo ?task ;
                   :name "mj.import_job" ;
                   :timestamp ?timestamp .
          ?task :status ?status .
          BIND(REPLACE(STR(?task), ".*Task/", "") AS ?taskId)
        }
        ORDER BY DESC(?timestamp)
        '''
        
        results = await self.kg.query_graph(task_query)
        print(f"✅ Found {len(results)} existing tasks")
        
        # Analyze task distribution
        status_counts = {}
        for result in results:
            status = result.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("📊 Task Status Distribution:")
        for status, count in status_counts.items():
            print(f"   • {status}: {count} tasks")
        
        return results, status_counts
    
    async def make_monitoring_decision(self, task_results, status_counts):
        """Agent makes decisions based on analysis"""
        print(f"🤔 Agent {self.agent_id[:8]} making monitoring decisions...")
        
        # Decision 1: Identify high-priority monitoring targets
        priority_tasks = [r for r in task_results if r.get('status') == 'created'][:3]
        
        # Decision 2: Determine monitoring frequency based on task volume
        total_tasks = len(task_results)
        if total_tasks > 50:
            monitoring_freq = "high_frequency"
            interval = "30_seconds"
        elif total_tasks > 20:
            monitoring_freq = "medium_frequency"  
            interval = "2_minutes"
        else:
            monitoring_freq = "low_frequency"
            interval = "5_minutes"
        
        # Decision 3: Set alert thresholds
        if status_counts.get('created', 0) > 10:
            alert_level = "high_priority"
        else:
            alert_level = "normal"
        
        print(f"🎯 Monitoring Decisions:")
        print(f"   • Priority tasks to monitor: {len(priority_tasks)}")
        print(f"   • Monitoring frequency: {monitoring_freq}")
        print(f"   • Check interval: {interval}")
        print(f"   • Alert level: {alert_level}")
        
        return priority_tasks, monitoring_freq, interval, alert_level
    
    async def update_knowledge_graph(self, decisions):
        """Agent updates KG with monitoring decisions and insights"""
        print(f"📝 Agent {self.agent_id[:8]} updating knowledge graph...")
        
        priority_tasks, monitoring_freq, interval, alert_level = decisions
        
        # Store monitoring strategy
        strategy_uri = f"http://example.org/strategy/{self.agent_id}"
        await self.kg.add_triple(
            strategy_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/core#MonitoringStrategy"
        )
        await self.kg.add_triple(
            strategy_uri,
            "http://example.org/core#createdBy",
            self.agent_uri
        )
        await self.kg.add_triple(
            strategy_uri,
            "http://example.org/core#frequency",
            monitoring_freq
        )
        await self.kg.add_triple(
            strategy_uri,
            "http://example.org/core#checkInterval",
            interval
        )
        await self.kg.add_triple(
            strategy_uri,
            "http://example.org/core#alertLevel",
            alert_level
        )
        
        # Store priority task list
        for i, task in enumerate(priority_tasks, 1):
            priority_uri = f"http://example.org/priority/{self.agent_id}/task_{i}"
            await self.kg.add_triple(
                priority_uri,
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                "http://example.org/core#PriorityTask"
            )
            await self.kg.add_triple(
                priority_uri,
                "http://example.org/core#taskId",
                task.get('taskId', 'unknown')
            )
            await self.kg.add_triple(
                priority_uri,
                "http://example.org/core#priorityLevel",
                "high"
            )
            await self.kg.add_triple(
                priority_uri,
                "http://example.org/core#assignedBy",
                self.agent_uri
            )
        
        # Store insights for other agents
        insights_uri = f"http://example.org/insights/{self.agent_id}"
        await self.kg.add_triple(
            insights_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/core#AgentInsights"
        )
        await self.kg.add_triple(
            insights_uri,
            "http://example.org/core#createdBy",
            self.agent_uri
        )
        await self.kg.add_triple(
            insights_uri,
            "http://example.org/core#insightType",
            "system_optimization"
        )
        await self.kg.add_triple(
            insights_uri,
            "http://example.org/core#content",
            f"Monitoring {len(priority_tasks)} high-priority tasks with {monitoring_freq} monitoring"
        )
        await self.kg.add_triple(
            insights_uri,
            "http://example.org/core#recommendation",
            f"Set monitoring interval to {interval} and alert level to {alert_level}"
        )
        
        print("✅ Knowledge graph updated with:")
        print(f"   • Monitoring strategy: {monitoring_freq}")
        print(f"   • Priority tasks: {len(priority_tasks)}")
        print(f"   • Agent insights: system optimization")
        print(f"   • Recommendations: {alert_level} alert level")
    
    async def verify_changes(self):
        """Agent verifies its modifications persisted"""
        print(f"🔍 Agent {self.agent_id[:8]} verifying changes...")
        
        # Verify strategy was stored
        strategy_query = f'''
        PREFIX core: <http://example.org/core#>
        
        SELECT ?frequency ?alertLevel WHERE {{
          ?strategy a core:MonitoringStrategy ;
                   core:createdBy <{self.agent_uri}> ;
                   core:frequency ?frequency ;
                   core:alertLevel ?alertLevel .
        }}
        '''
        
        strategy_results = await self.kg.query_graph(strategy_query)
        if strategy_results:
            print("✅ Monitoring strategy verified:")
            for result in strategy_results:
                print(f"   • Frequency: {result.get('frequency', 'unknown')}")
                print(f"   • Alert Level: {result.get('alertLevel', 'unknown')}")
        else:
            print("❌ Strategy not found")
        
        # Verify insights were stored
        insights_query = f'''
        PREFIX core: <http://example.org/core#>
        
        SELECT ?content ?recommendation WHERE {{
          ?insights a core:AgentInsights ;
                   core:createdBy <{self.agent_uri}> ;
                   core:content ?content ;
                   core:recommendation ?recommendation .
        }}
        '''
        
        insights_results = await self.kg.query_graph(insights_query)
        if insights_results:
            print("✅ Agent insights verified:")
            for result in insights_results:
                print(f"   • Content: {result.get('content', 'unknown')[:50]}...")
                print(f"   • Recommendation: {result.get('recommendation', 'unknown')}")
        else:
            print("❌ Insights not found")
        
        # Count total modifications made by this agent
        mod_count_query = f'''
        PREFIX core: <http://example.org/core#>
        
        SELECT (COUNT(?s) AS ?modCount) WHERE {{
          ?s ?p ?o .
          FILTER(CONTAINS(STR(?s), "{self.agent_id}"))
        }}
        '''
        
        count_results = await self.kg.query_graph(mod_count_query)
        if count_results:
            mod_count = count_results[0].get('modCount', 0)
            print(f"✅ Total modifications by this agent: {mod_count} triples")
    
    async def run_monitoring_cycle(self):
        """Complete monitoring cycle with on-the-fly KG modifications"""
        print(f"🚀 Agent {self.agent_id[:8]} starting monitoring cycle...")
        
        # Phase 1: Initialize and register
        session_uri = await self.initialize_agent()
        print()
        
        # Phase 2: Analyze existing data
        task_results, status_counts = await self.analyze_existing_tasks()
        print()
        
        # Phase 3: Make decisions
        decisions = await self.make_monitoring_decision(task_results, status_counts)
        print()
        
        # Phase 4: Update KG with decisions
        await self.update_knowledge_graph(decisions)
        print()
        
        # Phase 5: Verify changes
        await self.verify_changes()
        print()
        
        return len(task_results), len(status_counts), sum(status_counts.values())

async def main():
    print("🎯 MIDJOURNEY MONITORING AGENT - ON-THE-FLY KG MODIFICATION")
    print("=" * 65)
    
    # Create monitoring agent
    agent = MidjourneyMonitoringAgent("midjourney-monitor-2025")
    
    # Run complete monitoring cycle
    task_count, status_types, total_tasks = await agent.run_monitoring_cycle()
    
    print("🎉 MONITORING CYCLE COMPLETE!")
    print("📊 SUMMARY:")
    print(f"   • Analyzed {task_count} tasks")
    print(f"   • Found {status_types} different status types")
    print(f"   • Total tasks in system: {total_tasks}")
    print("   • All modifications persisted to KG")
    print("   • Ready for other agents to query and use")
    print()
    print("🔄 NEXT CYCLE: Agent can run again to monitor changes")
    print("📈 TREND ANALYSIS: Agent can compare with previous cycles")
    print("🤝 COLLABORATION: Other agents can query these insights")

if __name__ == "__main__":
    asyncio.run(main())
