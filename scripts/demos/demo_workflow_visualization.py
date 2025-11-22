#!/usr/bin/env python3
"""
DEMO: Workflow Visualization in Knowledge Graph
🎯 This script demonstrates how to create and visualize workflows in the Knowledge Graph
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

async def demo_workflow_visualization():
    """Demonstrate workflow creation and visualization."""

    print("🎯 DEMO: Workflow Visualization in Knowledge Graph")
    print("=" * 60)

    # Step 1: Import required components
    print("\n📥 IMPORTING COMPONENTS...")
    from agents.domain.orchestration_workflow import OrchestrationWorkflow
    from agents.domain.planner_agent import PlannerAgent
    from agents.domain.code_review_agent import CodeReviewAgent
    from agents.core.agent_registry import AgentRegistry
    from kg.models.graph_manager import KnowledgeGraphManager

    # Step 2: Initialize registry and agents
    print("🔧 INITIALIZING AGENTS...")
    registry = AgentRegistry(disable_auto_discovery=False)
    await registry.initialize()

    planner = PlannerAgent("planner", registry)

    # Initialize review agents
    review_agents = []
    try:
        review_agent = CodeReviewAgent("code_reviewer")
        review_agents.append(review_agent)
        print("✅ Review agents initialized")
    except Exception as e:
        print(f"⚠️ Review agent not available: {e}")

    # Step 3: Create orchestration workflow
    print("🚀 CREATING ORCHESTRATION WORKFLOW...")
    workflow = OrchestrationWorkflow(planner, review_agents)
    await workflow.initialize()

    # Step 4: Create a workflow from requirements
    print("📝 CREATING WORKFLOW FROM REQUIREMENTS...")
    requirements_file = "demo_requirements.txt"
    user_email = "demo@example.com"
    workflow_name = "Robot Adventure Demo"

    # Read requirements
    with open(requirements_file, 'r') as f:
        requirements_text = f.read()

    print(f"📄 Requirements: {requirements_text}")

    # Create workflow
    result = await workflow.create_workflow_from_text(
        requirements_file,
        user_email,
        workflow_name
    )

    print(f"✅ Workflow created: {result}")

    # Step 5: Extract workflow ID
    workflow_id = result.get("workflow_id")
    if workflow_id:
        print(f"\n🎯 WORKFLOW ID: {workflow_id}")

        # Step 6: Visualize the workflow
        print("🔍 VISUALIZING WORKFLOW IN KNOWLEDGE GRAPH...")
        visualization_result = await workflow.visualize_plan_in_kg(workflow_id)

        print(f"✅ Visualization result: {json.dumps(visualization_result, indent=2)}")

        # Step 7: Query the Knowledge Graph directly
        print("\n📊 DIRECT KNOWLEDGE GRAPH QUERY...")

        # Initialize KG manager
        kg_manager = KnowledgeGraphManager()
        await kg_manager.initialize()

        # Query for workflow data
        workflow_uri = f"http://example.org/workflow/{workflow_id}"
        query = f"""
        PREFIX ex: <http://example.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?predicate ?object
        WHERE {{
            <{workflow_uri}> ?predicate ?object .
        }}
        """

        results = await kg_manager.query_graph(query)
        print("📋 Workflow metadata:")
        for result in results:
            print(f"  • {result.get('predicate', 'unknown')} → {result.get('object', 'unknown')}")

        # Query for plan steps
        plan_query = f"""
        PREFIX ex: <http://example.org/ontology#>

        SELECT ?step ?stepNumber ?action ?agent ?description
        WHERE {{
            <{workflow_uri}> ex:hasPlan ?plan .
            ?step ex:belongsToPlan ?plan .
            ?step ex:stepNumber ?stepNumber .
            ?step ex:action ?action .
            ?step ex:assignedAgent ?agent .
            ?step ex:description ?description .
        }}
        ORDER BY ?stepNumber
        """

        plan_results = await kg_manager.query_graph(plan_query)
        print("\n📋 Plan steps:")
        for step in plan_results:
            print(f"  Step {step.get('stepNumber', '?')}: {step.get('action', 'unknown')} (Agent: {step.get('agent', 'unknown')})")
            print(f"    → {step.get('description', 'no description')}")

        # Step 8: Show SPARQL queries used
        print("\n🔧 SPARQL QUERIES USED:")
        print(f"Workflow Query: {query}")
        print(f"Plan Query: {plan_query}")

        # Clean up
        await kg_manager.shutdown()
        await registry.shutdown()

        return {
            "workflow_id": workflow_id,
            "visualization": visualization_result,
            "workflow_data": results,
            "plan_steps": plan_results
        }

    else:
        print("❌ Failed to create workflow")
        return None

async def main():
    """Main demo function."""
    try:
        result = await demo_workflow_visualization()

        if result:
            print("\n🎉 DEMO COMPLETE!")
            print(f"✅ Workflow ID: {result['workflow_id']}")
            print("\n📊 SUMMARY:")
            print(f"  • Workflow created successfully")
            print(f"  • Stored in Knowledge Graph")
            print(f"  • {len(result['plan_steps'])} plan steps defined")
            print(f"  • Full visualization available")
            print("\n🌐 ACCESS THE WEB VISUALIZER:")
            print(f"  1. Start server: python3 main.py")
            print(f"  2. Open: http://localhost:8000/static/workflow_visualizer.html")
            print(f"  3. Enter workflow ID: {result['workflow_id']}")
            print(f"  4. Click 'Visualize' to see the full plan!")
        else:
            print("❌ Demo failed")

    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
