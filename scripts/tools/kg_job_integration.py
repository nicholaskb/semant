#!/usr/bin/env python3
"""
KG Job Integration System
Shows how future jobs automatically integrate with the ontology-based KG
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD
import json

# Namespaces
AG = Namespace("http://example.org/agentKG#")
EX = Namespace("http://example.org/")
MISSION = Namespace("http://example.org/mission/")
AGENT = Namespace("http://example.org/agent/")
TASK = Namespace("http://example.org/task/")
DECISION = Namespace("http://example.org/decision/")
PROV = Namespace("http://www.w3.org/ns/prov#")

class KGJobIntegrator:
    """
    Automatically integrates any job with the KG using the ontology
    This would be used by agents when starting new missions
    """
    
    def __init__(self, kg_manager):
        self.kg = kg_manager
        self.graph = Graph()
        self.bind_namespaces()
        
    def bind_namespaces(self):
        """Bind all namespaces for clean output"""
        self.graph.bind("ag", AG)
        self.graph.bind("ex", EX)
        self.graph.bind("mission", MISSION)
        self.graph.bind("agent", AGENT)
        self.graph.bind("task", TASK)
        self.graph.bind("decision", DECISION)
        self.graph.bind("prov", PROV)
        
    async def start_new_job(self, job_config: Dict[str, Any]) -> str:
        """
        Start a new job and automatically integrate it with the KG
        
        Args:
            job_config: Configuration for the new job
                - job_type: Type of job (e.g., "image_generation", "document_creation")
                - agent_id: ID of the agent executing the job
                - objective: What the job aims to achieve
                - parameters: Job-specific parameters
        
        Returns:
            mission_id: The ID of the created mission
        """
        print(f"\n🚀 STARTING NEW JOB: {job_config.get('job_type', 'Unknown')}")
        print("=" * 60)
        
        # Generate mission ID
        mission_id = str(uuid.uuid4())
        mission_uri = MISSION[mission_id]
        
        # Create mission in KG with ontology types
        await self.kg.add_triple(
            str(mission_uri),
            str(RDF.type),
            str(AG.Mission)
        )
        await self.kg.add_triple(
            str(mission_uri),
            str(RDF.type),
            str(AG.WorkflowExecution)
        )
        await self.kg.add_triple(
            str(mission_uri),
            str(RDFS.label),
            job_config.get('objective', 'Mission')
        )
        await self.kg.add_triple(
            str(mission_uri),
            str(AG.status),
            "initialized"
        )
        await self.kg.add_triple(
            str(mission_uri),
            str(AG.jobType),
            job_config.get('job_type', 'generic')
        )
        await self.kg.add_triple(
            str(mission_uri),
            str(PROV.startedAtTime),
            datetime.now().isoformat()
        )
        
        # Link to agent
        agent_id = job_config.get('agent_id', 'default-agent')
        agent_uri = AGENT[agent_id]
        
        await self.kg.add_triple(
            str(mission_uri),
            str(AG.executedBy),
            str(agent_uri)
        )
        await self.kg.add_triple(
            str(agent_uri),
            str(AG.executedMission),
            str(mission_uri)
        )
        
        # Store parameters as metadata
        if 'parameters' in job_config:
            await self.kg.add_triple(
                str(mission_uri),
                str(AG.hasParameters),
                json.dumps(job_config['parameters'])
            )
        
        print(f"✅ Created mission: {mission_id}")
        print(f"   Type: {job_config.get('job_type')}")
        print(f"   Agent: {agent_id}")
        print(f"   Objective: {job_config.get('objective')}")
        
        return mission_id
    
    async def add_task_to_job(self, mission_id: str, task_config: Dict[str, Any]) -> str:
        """
        Add a task to an existing job
        
        Args:
            mission_id: The mission this task belongs to
            task_config: Task configuration
                - task_type: Type of task
                - description: What the task does
                - dependencies: List of task IDs this depends on
        
        Returns:
            task_id: The created task ID
        """
        task_id = str(uuid.uuid4())
        task_uri = TASK[task_id]
        mission_uri = MISSION[mission_id]
        
        # Create task with ontology types
        await self.kg.add_triple(
            str(task_uri),
            str(RDF.type),
            str(AG.Task)
        )
        await self.kg.add_triple(
            str(task_uri),
            str(RDF.type),
            str(PROV.Activity)
        )
        await self.kg.add_triple(
            str(task_uri),
            str(RDFS.label),
            task_config.get('description', 'Task')
        )
        await self.kg.add_triple(
            str(task_uri),
            str(AG.taskType),
            task_config.get('task_type', 'generic')
        )
        await self.kg.add_triple(
            str(task_uri),
            str(AG.status),
            "pending"
        )
        
        # Link to mission
        await self.kg.add_triple(
            str(task_uri),
            str(AG.partOfMission),
            str(mission_uri)
        )
        await self.kg.add_triple(
            str(mission_uri),
            str(AG.hasTask),
            str(task_uri)
        )
        
        # Add dependencies
        for dep_id in task_config.get('dependencies', []):
            dep_uri = TASK[dep_id]
            await self.kg.add_triple(
                str(task_uri),
                str(AG.dependsOn),
                str(dep_uri)
            )
        
        print(f"   📌 Added task: {task_config.get('description')}")
        
        return task_id
    
    async def record_decision(self, mission_id: str, decision_data: Dict[str, Any]) -> str:
        """
        Record a decision made during job execution
        
        Args:
            mission_id: The mission this decision belongs to
            decision_data: Decision information
                - context: What the decision is about
                - options: Available options
                - selected: The chosen option
                - reasoning: Why this was chosen
        
        Returns:
            decision_id: The created decision ID
        """
        decision_id = str(uuid.uuid4())
        decision_uri = DECISION[decision_id]
        mission_uri = MISSION[mission_id]
        
        # Create decision with ontology types
        await self.kg.add_triple(
            str(decision_uri),
            str(RDF.type),
            str(AG.Decision)
        )
        await self.kg.add_triple(
            str(decision_uri),
            str(RDF.type),
            str(PROV.Activity)
        )
        await self.kg.add_triple(
            str(decision_uri),
            str(AG.decisionContext),
            decision_data.get('context', 'Decision')
        )
        await self.kg.add_triple(
            str(decision_uri),
            str(AG.selectedChoice),
            decision_data.get('selected', 'Unknown')
        )
        
        if 'reasoning' in decision_data:
            await self.kg.add_triple(
                str(decision_uri),
                str(AG.reasoning),
                decision_data['reasoning']
            )
        
        # Link to mission
        await self.kg.add_triple(
            str(decision_uri),
            str(AG.partOfMission),
            str(mission_uri)
        )
        await self.kg.add_triple(
            str(mission_uri),
            str(AG.hasDecision),
            str(decision_uri)
        )
        
        # Add timestamp
        await self.kg.add_triple(
            str(decision_uri),
            str(PROV.atTime),
            datetime.now().isoformat()
        )
        
        print(f"   🤔 Recorded decision: {decision_data.get('context')} → {decision_data.get('selected')}")
        
        return decision_id
    
    async def query_similar_jobs(self, job_type: str) -> List[Dict[str, Any]]:
        """
        Query the KG for similar past jobs to learn from
        
        Args:
            job_type: Type of job to search for
            
        Returns:
            List of similar jobs with their outcomes
        """
        query = f"""
        PREFIX ag: <http://example.org/agentKG#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?mission ?objective ?status ?decision ?choice WHERE {{
            ?mission a ag:Mission ;
                    ag:jobType "{job_type}" ;
                    ag:status ?status ;
                    rdfs:label ?objective .
            OPTIONAL {{
                ?decision ag:partOfMission ?mission ;
                         ag:selectedChoice ?choice .
            }}
        }}
        LIMIT 10
        """
        
        results = await self.kg.query_graph(query)
        
        print(f"\n📚 Found {len(results)} similar past jobs")
        for r in results[:3]:
            print(f"   • {r.get('objective', 'Unknown')}: {r.get('status', 'Unknown')}")
            if r.get('choice'):
                print(f"     Decision: {r.get('choice')}")
        
        return results
    
    async def complete_job(self, mission_id: str, outcome: Dict[str, Any]):
        """
        Mark a job as complete and record outcomes
        
        Args:
            mission_id: The mission to complete
            outcome: Outcome information
                - status: Final status (success, failure, partial)
                - artifacts: List of produced artifacts
                - metrics: Performance metrics
        """
        mission_uri = MISSION[mission_id]
        
        # Update status
        await self.kg.add_triple(
            str(mission_uri),
            str(AG.status),
            outcome.get('status', 'completed')
        )
        
        # Add completion time
        await self.kg.add_triple(
            str(mission_uri),
            str(PROV.endedAtTime),
            datetime.now().isoformat()
        )
        
        # Record artifacts
        for artifact in outcome.get('artifacts', []):
            artifact_uri = EX[f"artifact/{uuid.uuid4()}"]
            await self.kg.add_triple(
                str(artifact_uri),
                str(RDF.type),
                str(AG.Artifact)
            )
            await self.kg.add_triple(
                str(artifact_uri),
                str(RDFS.label),
                artifact.get('name', 'Artifact')
            )
            await self.kg.add_triple(
                str(mission_uri),
                str(AG.produced),
                str(artifact_uri)
            )
        
        # Record metrics
        if 'metrics' in outcome:
            for metric, value in outcome['metrics'].items():
                await self.kg.add_triple(
                    str(mission_uri),
                    str(AG[metric]),
                    str(value)
                )
        
        print(f"\n✅ Job completed: {outcome.get('status')}")
        print(f"   Artifacts: {len(outcome.get('artifacts', []))}")
        print(f"   Metrics: {outcome.get('metrics', {})}")


# Example of how future jobs would use this system
async def demo_future_job_integration():
    """
    Demonstrate how a future job (e.g., creating a restaurant menu) 
    would automatically integrate with the KG
    """
    print("\n" + "=" * 70)
    print("🔮 DEMONSTRATING FUTURE JOB INTEGRATION")
    print("=" * 70)
    
    # Mock KG manager (in reality, this would be the actual KG)
    class MockKG:
        async def add_triple(self, s, p, o):
            pass  # In reality, this adds to the actual KG
        
        async def query_graph(self, query):
            # Mock return of similar past jobs
            return [
                {'objective': 'Hot Dog Flier', 'status': 'completed', 'choice': 'Professional Style'},
                {'objective': 'Pizza Menu', 'status': 'completed', 'choice': 'Casual Style'}
            ]
    
    kg = MockKG()
    integrator = KGJobIntegrator(kg)
    
    # ============================================================
    # SCENARIO: New Restaurant Menu Creation Job
    # ============================================================
    print("\n📋 SCENARIO: Creating a Restaurant Menu")
    
    # 1. Start the job
    job_config = {
        'job_type': 'menu_creation',
        'agent_id': 'menu-designer-agent',
        'objective': 'Create Italian Restaurant Menu',
        'parameters': {
            'cuisine': 'Italian',
            'style': 'elegant',
            'sections': ['appetizers', 'mains', 'desserts', 'wines']
        }
    }
    
    mission_id = await integrator.start_new_job(job_config)
    
    # 2. Query similar past jobs to learn from them
    similar_jobs = await integrator.query_similar_jobs('menu_creation')
    
    # 3. Add tasks
    tasks = [
        {'task_type': 'design', 'description': 'Design menu layout'},
        {'task_type': 'image_generation', 'description': 'Generate food images', 'dependencies': []},
        {'task_type': 'text_generation', 'description': 'Write dish descriptions', 'dependencies': []},
        {'task_type': 'composition', 'description': 'Compose final menu', 'dependencies': []}
    ]
    
    task_ids = []
    for task in tasks:
        task_id = await integrator.add_task_to_job(mission_id, task)
        task_ids.append(task_id)
    
    # 4. Record decisions made during execution
    decisions = [
        {
            'context': 'Choose menu style',
            'options': ['Modern', 'Classic', 'Rustic'],
            'selected': 'Classic',
            'reasoning': 'Matches restaurant ambiance'
        },
        {
            'context': 'Select color scheme',
            'options': ['Warm', 'Cool', 'Neutral'],
            'selected': 'Warm',
            'reasoning': 'Italian restaurants traditionally use warm colors'
        }
    ]
    
    for decision in decisions:
        await integrator.record_decision(mission_id, decision)
    
    # 5. Complete the job
    outcome = {
        'status': 'success',
        'artifacts': [
            {'name': 'menu.pdf', 'type': 'document'},
            {'name': 'menu_images.zip', 'type': 'image_collection'}
        ],
        'metrics': {
            'quality_score': 0.92,
            'generation_time': '8m',
            'decisions_made': 2,
            'images_generated': 12
        }
    }
    
    await integrator.complete_job(mission_id, outcome)
    
    # ============================================================
    # HOW THIS INTEGRATES WITH THE EXISTING KG
    # ============================================================
    print("\n🔗 INTEGRATION WITH EXISTING KG:")
    print("-" * 50)
    print("1. ✅ Uses same ontology classes (ag:Mission, ag:Task, ag:Decision)")
    print("2. ✅ Follows same relationship patterns (partOfMission, dependsOn)")
    print("3. ✅ Can query past jobs for learning (found hot dog flier patterns)")
    print("4. ✅ Decisions are chained and linked to missions")
    print("5. ✅ Metrics and artifacts are tracked consistently")
    
    print("\n📊 SPARQL QUERIES THAT WORK ACROSS ALL JOBS:")
    print("-" * 50)
    
    queries = [
        ("Find all successful image generation jobs", """
            PREFIX ag: <http://example.org/agentKG#>
            SELECT ?mission ?objective WHERE {
                ?mission ag:jobType ?type ;
                        ag:status "success" ;
                        rdfs:label ?objective .
                FILTER(CONTAINS(?type, "image") || CONTAINS(?type, "menu"))
            }
        """),
        ("Compare decision patterns across jobs", """
            PREFIX ag: <http://example.org/agentKG#>
            SELECT ?context (COUNT(?decision) as ?count) WHERE {
                ?decision a ag:Decision ;
                         ag:decisionContext ?context .
            }
            GROUP BY ?context
        """),
        ("Find best performing agents", """
            PREFIX ag: <http://example.org/agentKG#>
            SELECT ?agent (AVG(?score) as ?avg_quality) WHERE {
                ?mission ag:executedBy ?agent ;
                        ag:quality_score ?score .
            }
            GROUP BY ?agent
            ORDER BY DESC(?avg_quality)
        """)
    ]
    
    for title, query in queries:
        print(f"\n📍 {title}:")
        print(f"   {query[:100]}...")
    
    print("\n" + "=" * 70)
    print("🎯 KEY BENEFITS OF THIS INTEGRATION:")
    print("=" * 70)
    print("1. 📚 LEARNING: New jobs can query past similar jobs")
    print("2. 🔄 CONSISTENCY: All jobs use same ontology structure")
    print("3. 📊 ANALYTICS: Can analyze patterns across all jobs")
    print("4. 🤝 INTEROPERABILITY: Any agent can understand any job")
    print("5. 🔍 DISCOVERY: Agents can find and reuse successful patterns")
    print("6. 📈 IMPROVEMENT: Track metrics to improve over time")

if __name__ == "__main__":
    asyncio.run(demo_future_job_integration())
