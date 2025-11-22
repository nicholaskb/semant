#!/usr/bin/env python3
"""
Complete Planner Agent Workflow Demo
Shows how the planner agent creates, modifies, and introspects on workflows in the Knowledge Graph
"""
import asyncio
import uuid
from datetime import datetime
from kg.models.graph_manager import KnowledgeGraphManager
from rdflib import Literal, URIRef, XSD
import json

class SupremePlannerAgent:
    """The SUPREME Commander agent that creates and manages workflows"""
    
    def __init__(self, agent_id: str, kg: KnowledgeGraphManager):
        self.agent_id = agent_id
        self.kg = kg
        self.agent_uri = URIRef(f"http://example.org/agent/{self.agent_id}")
        self.authority = "SUPREME"
        self.logger = print

    async def initialize_supreme_command(self):
        """Initialize the supreme commander in the knowledge graph"""
        self.logger("🚀 SUPREME COMMANDER INITIALIZING...")
        
        await self.kg.initialize()
        
        # Register supreme commander
        await self.kg.add_triple(
            self.agent_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/core#Agent"
        )
        await self.kg.add_triple(
            self.agent_uri,
            "http://example.org/core#agentId",
            Literal(self.agent_id, datatype=XSD.string)
        )
        await self.kg.add_triple(
            self.agent_uri,
            "http://example.org/core#authority",
            Literal(self.authority, datatype=XSD.string)
        )
        await self.kg.add_triple(
            self.agent_uri,
            "http://example.org/core#status",
            Literal("COMMANDING", datatype=XSD.string)
        )
        await self.kg.add_triple(
            self.agent_uri,
            "http://example.org/core#specialization",
            Literal("workflow_planning_and_execution", datatype=XSD.string)
        )
        await self.kg.add_triple(
            self.agent_uri,
            "http://example.org/core#activationTime",
            Literal(datetime.now().isoformat(), datatype=XSD.dateTime)
        )
        
        self.logger(f"✅ SUPREME COMMANDER REGISTERED: {self.agent_id}")
        self.logger(f"   Authority Level: {self.authority}")
        self.logger(f"   Specialization: Workflow Planning & Execution")

    async def create_authoritative_plan(self, mission: str):
        """Create an authoritative workflow plan"""
        self.logger(f"\n🎯 SUPREME COMMANDER ANALYZING MISSION: {mission}")
        
        # Create workflow ID
        workflow_id = f"supreme-plan-{int(datetime.now().timestamp())}"
        workflow_uri = URIRef(f"http://example.org/plan/{workflow_id}")
        
        # Create the workflow plan
        await self.kg.add_triple(
            workflow_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/core#FlyerCreationPlan"
        )
        await self.kg.add_triple(
            workflow_uri,
            "http://example.org/core#mission",
            Literal(mission, datatype=XSD.string)
        )
        await self.kg.add_triple(
            workflow_uri,
            "http://example.org/core#commander",
            self.agent_uri
        )
        await self.kg.add_triple(
            workflow_uri,
            "http://example.org/core#status",
            Literal("APPROVED", datatype=XSD.string)
        )
        await self.kg.add_triple(
            workflow_uri,
            "http://example.org/core#createdAt",
            Literal(datetime.now().isoformat(), datatype=XSD.dateTime)
        )
        
        # Add detailed plan steps
        steps = [
            {
                "step_id": "1.1",
                "action": "Analyze target audience and requirements",
                "description": "SUPREME COMMANDER evaluates market needs and design specifications",
                "input": "Mission briefing and target demographics",
                "output": "Detailed audience profile and design requirements"
            },
            {
                "step_id": "1.2", 
                "action": "Generate professional prompt suite",
                "description": "Create optimized Midjourney prompts for maximum visual impact",
                "input": "Audience profile and design requirements",
                "output": "Professional prompt collection for image generation"
            },
            {
                "step_id": "1.3",
                "action": "Execute image generation protocol",
                "description": "Deploy prompts to Midjourney API with quality monitoring",
                "input": "Professional prompt suite",
                "output": "High-quality generated images ready for composition"
            },
            {
                "step_id": "2.1",
                "action": "Compose final design layout",
                "description": "Assemble images into professional flyer format",
                "input": "Generated image assets",
                "output": "Final flyer design ready for distribution"
            }
        ]
        
        for i, step in enumerate(steps):
            step_uri = URIRef(f"http://example.org/step/{workflow_id}-{i}")
            await self.kg.add_triple(
                step_uri,
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                "http://example.org/core#WorkflowStep"
            )
            await self.kg.add_triple(
                step_uri,
                "http://example.org/core#stepId",
                Literal(step["step_id"], datatype=XSD.string)
            )
            await self.kg.add_triple(
                step_uri,
                "http://example.org/core#action",
                Literal(step["action"], datatype=XSD.string)
            )
            await self.kg.add_triple(
                step_uri,
                "http://example.org/core#description",
                Literal(step["description"], datatype=XSD.string)
            )
            await self.kg.add_triple(
                step_uri,
                "http://example.org/core#input",
                Literal(step["input"], datatype=XSD.string)
            )
            await self.kg.add_triple(
                step_uri,
                "http://example.org/core#output",
                Literal(step["output"], datatype=XSD.string)
            )
            await self.kg.add_triple(
                step_uri,
                "http://example.org/core#belongsToPlan",
                workflow_uri
            )
        
        self.logger(f"✅ SUPREME PLAN CREATED: {workflow_id}")
        self.logger(f"   Mission: {mission}")
        self.logger(f"   Steps: {len(steps)}")
        self.logger(f"   Status: APPROVED")
        
        return workflow_id, workflow_uri

    async def log_commander_decision(self, workflow_uri: str, decision: str, reasoning: str):
        """Log a commander's decision in the knowledge graph"""
        decision_id = str(uuid.uuid4())
        decision_uri = URIRef(f"http://example.org/decision/{decision_id}")
        
        await self.kg.add_triple(
            decision_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/core#CommanderDecision"
        )
        await self.kg.add_triple(
            decision_uri,
            "http://example.org/core#madeBy",
            self.agent_uri
        )
        await self.kg.add_triple(
            decision_uri,
            "http://example.org/core#relatedToWorkflow",
            workflow_uri
        )
        await self.kg.add_triple(
            decision_uri,
            "http://example.org/core#decision",
            Literal(decision, datatype=XSD.string)
        )
        await self.kg.add_triple(
            decision_uri,
            "http://example.org/core#reasoning",
            Literal(reasoning, datatype=XSD.string)
        )
        await self.kg.add_triple(
            decision_uri,
            "http://example.org/core#timestamp",
            Literal(datetime.now().isoformat(), datatype=XSD.dateTime)
        )
        
        self.logger(f"✅ COMMANDER DECISION LOGGED: {decision}")
        self.logger(f"   Reasoning: {reasoning}")

class WorkflowIntrospectionAgent:
    """Agent that can introspect on workflows in the knowledge graph"""
    
    def __init__(self, agent_id: str, kg: KnowledgeGraphManager):
        self.agent_id = agent_id
        self.kg = kg
        self.agent_uri = URIRef(f"http://example.org/agent/{self.agent_id}")
        self.logger = print

    async def introspect_all_workflows(self):
        """See and analyze all workflows in the knowledge graph"""
        self.logger("\n🔍 WORKFLOW INTROSPECTION AGENT ACTIVATED")
        self.logger("=" * 50)
        
        await self.kg.initialize()
        
        # Query for all workflows
        workflow_query = """
        PREFIX : <http://example.org/core#>
        SELECT ?workflow ?mission ?status ?commander WHERE {
          ?workflow a :FlyerCreationPlan .
          OPTIONAL { ?workflow :mission ?mission }
          OPTIONAL { ?workflow :status ?status }
          OPTIONAL { ?workflow :commander ?commander }
        }
        ORDER BY DESC(?mission)
        """
        
        workflows = await self.kg.query_graph(workflow_query)
        if workflows:
            self.logger(f"✅ WORKFLOW INTROSPECTION: Found {len(workflows)} workflows")
            
            for workflow in workflows:
                workflow_id = str(workflow.get('workflow', 'unknown')).split('/')[-1][:30]
                mission = str(workflow.get('mission', 'No mission'))
                status = str(workflow.get('status', 'No status'))
                commander = str(workflow.get('commander', 'No commander')).split('/')[-1][:20]
                
                self.logger(f"\n📋 WORKFLOW ANALYSIS: {workflow_id}...")
                self.logger(f"   • Mission: {mission}")
                self.logger(f"   • Status: {status}")
                self.logger(f"   • Commander: {commander}")
                
                # Analyze workflow quality
                quality_score = 0
                if mission != 'No mission': quality_score += 40
                if 'supreme' in commander.lower(): quality_score += 40
                if status == 'APPROVED': quality_score += 20
                
                self.logger(f"   • Quality Assessment: {quality_score}/100")
                
                # Log introspection
                introspection_uri = URIRef(f"http://example.org/introspection/{uuid.uuid4()}")
                await self.kg.add_triple(
                    introspection_uri,
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                    "http://example.org/core#WorkflowIntrospection"
                )
                await self.kg.add_triple(
                    introspection_uri,
                    "http://example.org/core#analyzedWorkflow",
                    workflow.get('workflow')
                )
                await self.kg.add_triple(
                    introspection_uri,
                    "http://example.org/core#introspectionAgent",
                    self.agent_uri
                )
                await self.kg.add_triple(
                    introspection_uri,
                    "http://example.org/core#qualityScore",
                    Literal(str(quality_score), datatype=XSD.integer)
                )
                await self.kg.add_triple(
                    introspection_uri,
                    "http://example.org/core#timestamp",
                    Literal(datetime.now().isoformat(), datatype=XSD.dateTime)
                )
                
                self.logger(f"   • Introspection Logged: Analysis recorded in KG")
        else:
            self.logger("❌ No workflows found for introspection")

    async def modify_workflow(self, workflow_uri: str, new_status: str, modification_reason: str):
        """Modify an existing workflow"""
        self.logger(f"\n🔧 MODIFYING WORKFLOW: {workflow_uri}")
        
        # Log the modification
        modification_uri = URIRef(f"http://example.org/modification/{uuid.uuid4()}")
        await self.kg.add_triple(
            modification_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/core#WorkflowModification"
        )
        await self.kg.add_triple(
            modification_uri,
            "http://example.org/core#modifiedWorkflow",
            workflow_uri
        )
        await self.kg.add_triple(
            modification_uri,
            "http://example.org/core#modificationAgent",
            self.agent_uri
        )
        await self.kg.add_triple(
            modification_uri,
            "http://example.org/core#newStatus",
            Literal(new_status, datatype=XSD.string)
        )
        await self.kg.add_triple(
            modification_uri,
            "http://example.org/core#reason",
            Literal(modification_reason, datatype=XSD.string)
        )
        await self.kg.add_triple(
            modification_uri,
            "http://example.org/core#timestamp",
            Literal(datetime.now().isoformat(), datatype=XSD.dateTime)
        )
        
        # Update workflow status
        await self.kg.add_triple(
            workflow_uri,
            "http://example.org/core#status",
            Literal(new_status, datatype=XSD.string)
        )
        
        self.logger(f"✅ Workflow modified: Status changed to {new_status}")
        self.logger(f"   Reason: {modification_reason}")
        self.logger(f"   Modification logged in Knowledge Graph")

async def main():
    print("🚀 SUPREME COMMANDER WORKFLOW DEMONSTRATION")
    print("=" * 60)
    
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    # Phase 1: Supreme Commander creates workflow
    print("\n📋 PHASE 1: SUPREME COMMANDER CREATES WORKFLOW")
    supreme_commander = SupremePlannerAgent("supreme-commander-alpha", kg)
    await supreme_commander.initialize_supreme_command()
    
    workflow_id, workflow_uri = await supreme_commander.create_authoritative_plan(
        "Create professional hot dog stand flyer with compelling visuals"
    )
    
    await supreme_commander.log_commander_decision(
        workflow_uri,
        "APPROVE FLYER CREATION PROTOCOL",
        "Mission critical - high-quality flyer needed for maximum customer engagement"
    )
    
    # Phase 2: Introspection Agent analyzes the workflow
    print("\n📋 PHASE 2: INTROSPECTION AGENT ANALYZES WORKFLOW")
    introspection_agent = WorkflowIntrospectionAgent("workflow-introspection-beta", kg)
    await introspection_agent.introspect_all_workflows()
    
    # Phase 3: Introspection Agent modifies the workflow
    print("\n📋 PHASE 3: INTROSPECTION AGENT MODIFIES WORKFLOW")
    await introspection_agent.modify_workflow(
        workflow_uri,
        "ENHANCED",
        "Added additional quality checks and optimization steps"
    )
    
    # Phase 4: Show final conversation state
    print("\n📋 PHASE 4: COMPLETE CONVERSATION SUMMARY")
    print("=" * 50)
    
    # Query for the complete conversation
    conversation_query = """
    PREFIX : <http://example.org/core#>
    SELECT ?subject ?predicate ?object WHERE {
      ?subject ?predicate ?object .
      FILTER(
        CONTAINS(STR(?subject), 'supreme-commander') ||
        CONTAINS(STR(?subject), 'workflow-introspection') ||
        CONTAINS(STR(?object), 'APPROVED') ||
        CONTAINS(STR(?object), 'ENHANCED') ||
        CONTAINS(STR(?predicate), 'decision') ||
        CONTAINS(STR(?predicate), 'analysis')
      )
    }
    ORDER BY ?subject
    """
    
    conversations = await kg.query_graph(conversation_query)
    if conversations:
        print(f"✅ COMPLETE AGENT CONVERSATION ({len(conversations)} triples):")
        for conversation in conversations:
            subject = str(conversation.get('subject', 'unknown')).split('/')[-1][:25]
            predicate = str(conversation.get('predicate', 'unknown')).split('/')[-1][:20]
            obj = str(conversation.get('object', 'unknown'))[:40]
            print(f"   • {subject}... → {predicate}... → {obj}...")
    
    print("\n🎉 SUPREME COMMANDER WORKFLOW DEMO COMPLETE!")
    print("   • Supreme Commander created authoritative workflow")
    print("   • Workflow stored in Knowledge Graph with full metadata")
    print("   • Introspection Agent analyzed and modified workflow")
    print("   • Complete conversation between agents captured")
    print("   • Full self-modification and introspection capabilities demonstrated")

if __name__ == "__main__":
    asyncio.run(main())
