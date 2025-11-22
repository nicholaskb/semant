#!/usr/bin/env python3
"""
SIMPLE DEMO: See Proposed Plans in Knowledge Graph
🎯 This shows exactly how to visualize workflows and plans
"""

import asyncio
import json

async def demo_kg_visualization():
    """Demonstrate how to see plans in the Knowledge Graph."""

    print("🎯 SIMPLE DEMO: Knowledge Graph Workflow Visualization")
    print("=" * 65)

    # Step 1: Initialize Knowledge Graph
    print("\n📥 INITIALIZING KNOWLEDGE GRAPH...")
    from kg.models.graph_manager import KnowledgeGraphManager
    kg = KnowledgeGraphManager()
    await kg.initialize()
    print("✅ Knowledge Graph ready")

    # Step 2: Query for all workflows
    print("\n🔍 QUERYING ALL WORKFLOWS...")

    query_all_workflows = """
    PREFIX ex: <http://example.org/ontology#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?workflow ?theme ?createdAt ?status ?workflowName
    WHERE {
        ?workflow a ex:Workflow .
        ?workflow ex:hasTheme ?theme .
        ?workflow ex:createdAt ?createdAt .
        ?workflow ex:status ?status .
        OPTIONAL { ?workflow ex:workflowName ?workflowName . }
    }
    ORDER BY DESC(?createdAt)
    """

    workflows = await kg.query_graph(query_all_workflows)

    if not workflows:
        print("❌ No workflows found. Let's create one first!")

        # Create a simple workflow
        print("\n🚀 CREATING A DEMO WORKFLOW...")

        # Create workflow URI and triples
        workflow_id = "demo_workflow_001"
        workflow_uri = f"http://example.org/workflow/{workflow_id}"

        # Add workflow metadata
        await kg.add_triple(workflow_uri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/ontology#Workflow")
        await kg.add_triple(workflow_uri, "http://example.org/ontology#hasTheme", "Children's Book Creation Demo")
        await kg.add_triple(workflow_uri, "http://example.org/ontology#createdAt", "2025-09-23T16:00:00")
        await kg.add_triple(workflow_uri, "http://example.org/ontology#status", "created")
        await kg.add_triple(workflow_uri, "http://example.org/ontology#workflowName", "Book Creation Demo")

        # Create plan
        plan_uri = f"http://example.org/plan/{workflow_id}_plan"
        await kg.add_triple(workflow_uri, "http://example.org/ontology#hasPlan", plan_uri)
        await kg.add_triple(plan_uri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/ontology#Plan")
        await kg.add_triple(plan_uri, "http://example.org/ontology#planData", json.dumps({
            "id": f"{workflow_id}_plan",
            "theme": "Children's Book Creation Demo",
            "steps": [
                {"step": 1, "action": "analyze_requirements", "agent": "planner", "description": "Analyze book requirements"},
                {"step": 2, "action": "generate_prompts", "agent": "synthesis_agent", "description": "Create image prompts"},
                {"step": 3, "action": "create_book", "agent": "execution_agent", "description": "Generate the book"}
            ]
        }))

        # Add plan steps
        steps = [
            {"step": 1, "action": "analyze_requirements", "agent": "planner", "description": "Analyze book requirements"},
            {"step": 2, "action": "generate_prompts", "agent": "synthesis_agent", "description": "Create image prompts"},
            {"step": 3, "action": "create_book", "agent": "execution_agent", "description": "Generate the book"}
        ]

        for step in steps:
            step_uri = f"{plan_uri}/step/{step['step']}"
            await kg.add_triple(step_uri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/ontology#PlanStep")
            await kg.add_triple(step_uri, "http://example.org/ontology#belongsToPlan", plan_uri)
            await kg.add_triple(step_uri, "http://example.org/ontology#stepNumber", str(step["step"]))
            await kg.add_triple(step_uri, "http://example.org/ontology#action", step["action"])
            await kg.add_triple(step_uri, "http://example.org/ontology#assignedAgent", step["agent"])
            await kg.add_triple(step_uri, "http://example.org/ontology#description", step["description"])

        print(f"✅ Created demo workflow: {workflow_id}")

        # Re-query to see the new workflow
        workflows = await kg.query_graph(query_all_workflows)

    print(f"\n📋 FOUND {len(workflows)} WORKFLOWS:")
    print("-" * 50)

    for i, workflow in enumerate(workflows, 1):
        print(f"\n{i}. WORKFLOW: {workflow.get('workflow', 'Unknown')}")
        print(f"   Theme: {workflow.get('theme', 'No theme')}")
        print(f"   Status: {workflow.get('status', 'Unknown')}")
        print(f"   Created: {workflow.get('createdAt', 'Unknown')}")
        if workflow.get('workflowName'):
            print(f"   Name: {workflow.get('workflowName')}")

    # Step 3: Get detailed plan for the first workflow
    if workflows:
        print("\n🔍 DETAILED PLAN ANALYSIS:")
        print("=" * 50)

        first_workflow = workflows[0]
        workflow_uri = first_workflow.get('workflow')

        # Get plan steps
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

        plan_steps = await kg.query_graph(plan_query)

        print(f"\n📋 PLAN STEPS for: {workflow.get('theme', 'Unknown')}")
        print("-" * 40)

        for step in plan_steps:
            print(f"\nStep {step.get('stepNumber', '?')}: {step.get('action', 'unknown')}")
            print(f"  Agent: {step.get('agent', 'unknown')}")
            print(f"  Description: {step.get('description', 'no description')}")

        # Step 4: Show the SPARQL queries used
        print("\n🔧 SPARQL QUERIES USED:")
        print("=" * 30)
        print("1. Find all workflows:")
        print(query_all_workflows.strip())
        print("\n2. Get plan details:")
        print(plan_query.strip())

    # Step 5: Show web interface access
    print("\n🌐 WEB VISUALIZER:")
    print("=" * 25)
    print("1. Start the server: python3 main.py")
    print("2. Open: http://localhost:8000/static/workflow_visualizer.html")
    print("3. Enter workflow ID from above")
    print("4. Click 'Visualize' to see the full plan!")

    # Clean up
    await kg.shutdown()

    return {
        "workflows_found": len(workflows),
        "workflows": workflows,
        "plan_steps": plan_steps if 'plan_steps' in locals() else []
    }

async def main():
    """Run the demo."""
    try:
        result = await demo_kg_visualization()

        print("\n🎉 DEMO COMPLETE!")
        print("=" * 20)
        print(f"✅ Found {result['workflows_found']} workflows in Knowledge Graph")
        print(f"✅ Demonstrated SPARQL queries for visualization")
        print(f"✅ Showed web interface access")
        print("\n📊 WHAT YOU CAN DO NOW:")
        print("  • Use the web visualizer to explore workflows")
        print("  • Query the Knowledge Graph directly with SPARQL")
        print("  • Create new workflows with the planner agent")
        print("  • Execute and monitor workflow steps")
        print("\n🔥 NEXT STEPS:")
        print("  1. Start server: python3 main.py")
        print("  2. Open: http://localhost:8000/static/workflow_visualizer.html")
        print("  3. Explore your workflows!")

    except Exception as e:
        print(f"❌ Demo error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
