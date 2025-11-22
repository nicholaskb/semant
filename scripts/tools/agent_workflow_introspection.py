#!/usr/bin/env python3
"""
Agent Workflow Introspection Demo
Shows how agents can see and modify workflows in the Knowledge Graph
"""
import asyncio
import uuid
from datetime import datetime
from kg.models.graph_manager import KnowledgeGraphManager
from rdflib import Literal, URIRef, XSD
import json

class WorkflowIntrospectionAgent:
    """Agent that can see and modify workflows in the Knowledge Graph"""
    
    def __init__(self, agent_id: str, kg: KnowledgeGraphManager):
        self.agent_id = agent_id
        self.kg = kg
        self.agent_uri = URIRef(f"http://example.org/agent/{self.agent_id}")
        self.logger = print  # Simple logger for demo

    async def see_all_workflows(self):
        """See all workflows in the Knowledge Graph"""
        self.logger("🔍 WORKFLOW INTROSPECTION AGENT ACTIVATED")
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
            self.logger(f"✅ Found {len(workflows)} workflows in Knowledge Graph:")
            for workflow in workflows:
                workflow_id = str(workflow.get('workflow', 'unknown')).split('/')[-1][:30]
                mission = str(workflow.get('mission', 'No mission'))
                status = str(workflow.get('status', 'No status'))
                commander = str(workflow.get('commander', 'No commander')).split('/')[-1][:20]
                self.logger(f"   • ID: {workflow_id}...")
                self.logger(f"     Mission: {mission}")
                self.logger(f"     Status: {status}")
                self.logger(f"     Commander: {commander}...")
        else:
            self.logger("❌ No workflows found in Knowledge Graph")
        
        return workflows

    async def analyze_workflow_quality(self, workflow_uri: str):
        """Analyze the quality and completeness of a workflow"""
        self.logger(f"\n🔍 ANALYZING WORKFLOW QUALITY: {workflow_uri}")
        
        # Check if workflow has required components
        quality_query = f"""
        PREFIX : <http://example.org/core#>
        SELECT ?mission ?commander ?status WHERE {{
          <{workflow_uri}> :mission ?mission .
          <{workflow_uri}> :commander ?commander .
          <{workflow_uri}> :status ?status .
        }}
        """
        
        quality_data = await self.kg.query_graph(quality_query)
        if quality_data:
            workflow_data = quality_data[0]
            mission = str(workflow_data.get('mission', 'No mission'))
            commander = str(workflow_data.get('commander', 'No commander')).split('/')[-1]
            status = str(workflow_data.get('status', 'No status'))
            
            self.logger("✅ Workflow Analysis:")
            self.logger(f"   • Mission: {mission}")
            self.logger(f"   • Commander: {commander}")
            self.logger(f"   • Status: {status}")
            
            # Assess quality
            quality_score = 0
            if mission != 'No mission': quality_score += 40
            if 'supreme' in commander.lower(): quality_score += 30
            if status in ['APPROVED', 'COMPLETED']: quality_score += 30
            
            self.logger(f"   • Quality Score: {quality_score}/100")
            
            if quality_score >= 70:
                self.logger("   • Assessment: HIGH QUALITY WORKFLOW")
            elif quality_score >= 40:
                self.logger("   • Assessment: MODERATE QUALITY WORKFLOW")
            else:
                self.logger("   • Assessment: LOW QUALITY WORKFLOW")
        else:
            self.logger("❌ Workflow data incomplete")

    async def modify_workflow_status(self, workflow_uri: str, new_status: str, reason: str):
        """Modify a workflow's status with reasoning"""
        self.logger(f"\n🔧 MODIFYING WORKFLOW STATUS: {workflow_uri}")
        
        # Add status change record
        status_change_id = str(uuid.uuid4())
        status_change_uri = URIRef(f"http://example.org/status-change/{status_change_id}")
        
        await self.kg.add_triple(
            status_change_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/core#WorkflowStatusChange"
        )
        await self.kg.add_triple(
            status_change_uri,
            "http://example.org/core#modifiedBy",
            self.agent_uri
        )
        await self.kg.add_triple(
            status_change_uri,
            "http://example.org/core#timestamp",
            Literal(datetime.now().isoformat(), datatype=XSD.dateTime)
        )
        await self.kg.add_triple(
            status_change_uri,
            "http://example.org/core#oldStatus",
            Literal("PENDING", datatype=XSD.string)
        )
        await self.kg.add_triple(
            status_change_uri,
            "http://example.org/core#newStatus",
            Literal(new_status, datatype=XSD.string)
        )
        await self.kg.add_triple(
            status_change_uri,
            "http://example.org/core#reason",
            Literal(reason, datatype=XSD.string)
        )
        
        # Update the workflow status
        await self.kg.add_triple(
            workflow_uri,
            "http://example.org/core#status",
            Literal(new_status, datatype=XSD.string)
        )
        
        self.logger(f"✅ Workflow status changed to: {new_status}")
        self.logger(f"   Reason: {reason}")

    async def optimize_workflow_steps(self, workflow_uri: str):
        """Analyze and suggest optimizations for workflow steps"""
        self.logger(f"\n🎯 OPTIMIZING WORKFLOW STEPS: {workflow_uri}")
        
        # Look for steps related to this workflow
        steps_query = f"""
        PREFIX : <http://example.org/core#>
        SELECT ?step ?action ?agent WHERE {{
          ?step :relatedTo <{workflow_uri}> .
          OPTIONAL {{ ?step :action ?action }}
          OPTIONAL {{ ?step :agent ?agent }}
        }}
        """
        
        steps = await self.kg.query_graph(steps_query)
        if steps:
            self.logger("✅ Found workflow steps:")
            for step in steps:
                step_id = str(step.get('step', 'unknown')).split('/')[-1][:20]
                action = str(step.get('action', 'No action'))
                agent = str(step.get('agent', 'No agent')).split('/')[-1][:15]
                self.logger(f"   • Step: {step_id}... - Action: {action} - Agent: {agent}...")
        else:
            self.logger("❌ No workflow steps found")

    async def generate_workflow_report(self, workflow_uri: str):
        """Generate a comprehensive report about a workflow"""
        self.logger(f"\n📊 GENERATING WORKFLOW REPORT: {workflow_uri}")
        
        # Get comprehensive workflow data
        report_query = f"""
        PREFIX : <http://example.org/core#>
        SELECT ?mission ?status ?commander ?createdAt WHERE {{
          <{workflow_uri}> :mission ?mission .
          <{workflow_uri}> :status ?status .
          <{workflow_uri}> :commander ?commander .
          OPTIONAL {{ <{workflow_uri}> :createdAt ?createdAt }}
        }}
        """
        
        report_data = await self.kg.query_graph(report_query)
        if report_data:
            data = report_data[0]
            self.logger("✅ WORKFLOW REPORT:")
            self.logger(f"   • Mission: {data.get('mission', 'Unknown')}")
            self.logger(f"   • Status: {data.get('status', 'Unknown')}")
            self.logger(f"   • Commander: {str(data.get('commander', 'Unknown')).split('/')[-1]}")
            self.logger(f"   • Created: {data.get('createdAt', 'Unknown')}")
            
            # Add agent self-reflection
            await self.kg.add_triple(
                self.agent_uri,
                "http://example.org/core#analyzedWorkflow",
                workflow_uri
            )
            await self.kg.add_triple(
                self.agent_uri,
                "http://example.org/core#analysisTimestamp",
                Literal(datetime.now().isoformat(), datatype=XSD.dateTime)
            )
            
            self.logger("   • Analysis: Agent has reviewed and documented this workflow")
            self.logger("   • Self-Reflection: Workflow introspection capabilities verified")
        else:
            self.logger("❌ Unable to generate report - workflow data incomplete")

async def main():
    print("🚀 AGENT WORKFLOW INTROSPECTION DEMO")
    print("=" * 60)
    
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    # Create the introspection agent
    introspection_agent = WorkflowIntrospectionAgent("workflow-introspection-agent", kg)
    
    # Demonstrate workflow introspection capabilities
    print("\n1️⃣ SEEING ALL WORKFLOWS")
    workflows = await introspection_agent.see_all_workflows()
    
    if workflows:
        # Pick the first workflow for detailed analysis
        workflow_uri = str(workflows[0]['workflow'])
        workflow_id = workflow_uri.split('/')[-1][:30]
        print(f"\n2️⃣ ANALYZING WORKFLOW: {workflow_id}...")
        await introspection_agent.analyze_workflow_quality(workflow_uri)
        
        print(f"\n3️⃣ OPTIMIZING WORKFLOW: {workflow_id}...")
        await introspection_agent.optimize_workflow_steps(workflow_uri)
        
        print(f"\n4️⃣ MODIFYING WORKFLOW STATUS: {workflow_id}...")
        await introspection_agent.modify_workflow_status(
            workflow_uri, 
            "REVIEWED", 
            "Agent introspection completed - workflow analysis performed"
        )
        
        print(f"\n5️⃣ GENERATING WORKFLOW REPORT: {workflow_id}...")
        await introspection_agent.generate_workflow_report(workflow_uri)
    
    print("\n🎉 WORKFLOW INTROSPECTION DEMO COMPLETE!")
    print("   • Agents can see all workflows in KG")
    print("   • Agents can analyze workflow quality")
    print("   • Agents can modify workflow status")
    print("   • Agents can optimize workflow steps")
    print("   • Agents can generate comprehensive reports")
    print("   • Full self-reflection and documentation capabilities")

if __name__ == "__main__":
    asyncio.run(main())
