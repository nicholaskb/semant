"""Extension to PlannerAgent for creating and storing plans in the Knowledge Graph."""

from typing import Dict, Any, List
from datetime import datetime
import json
from agents.core.message_types import AgentMessage
from rdflib import URIRef, Literal, RDF, RDFS

async def create_and_store_plan(planner_agent, theme: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a comprehensive plan for a theme and store it in the Knowledge Graph.
    
    Args:
        planner_agent: The PlannerAgent instance
        theme: The theme or goal for the plan
        context: Additional context (image_urls, requirements, etc.)
    
    Returns:
        Dict containing the plan ID and structure
    """
    plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    plan_uri = f"http://example.org/plan/{plan_id}"
    
    # Create the plan structure
    plan = {
        "id": plan_id,
        "theme": theme,
        "created_at": datetime.now().isoformat(),
        "created_by": planner_agent.agent_id,
        "context": context,
        "steps": [],
        "resources": context.get("image_urls", []),
        "status": "created"
    }
    
    # Generate plan steps based on theme
    if "midjourney" in theme.lower() or "image" in theme.lower():
        # Image generation plan
        plan["steps"] = [
            {
                "step": 1,
                "action": "analyze_theme",
                "description": f"Analyze the theme '{theme}' to identify key visual elements",
                "agent": "planner",
                "output": "theme_analysis"
            },
            {
                "step": 2,
                "action": "generate_prompts",
                "description": f"Generate {context.get('count', 5)} diverse prompts for the theme",
                "agent": "synthesis_agent",
                "input": "theme_analysis",
                "output": "base_prompts"
            },
            {
                "step": 3,
                "action": "refine_prompts",
                "description": "Refine each prompt for clarity and artistic quality",
                "agent": "planner",
                "input": "base_prompts",
                "output": "refined_prompts"
            },
            {
                "step": 4,
                "action": "critique_prompts",
                "description": "Evaluate prompts for theme adherence and quality",
                "agent": "critic_agent",
                "input": "refined_prompts",
                "output": "critiques"
            },
            {
                "step": 5,
                "action": "finalize_prompts",
                "description": "Select and finalize the best prompts",
                "agent": "judge_agent",
                "input": ["refined_prompts", "critiques"],
                "output": "final_prompts"
            },
            {
                "step": 6,
                "action": "submit_jobs",
                "description": "Submit image generation jobs to Midjourney",
                "agent": "midjourney_client",
                "input": "final_prompts",
                "output": "job_ids"
            }
        ]
    elif "research" in theme.lower():
        # Research plan
        plan["steps"] = [
            {
                "step": 1,
                "action": "define_scope",
                "description": f"Define research scope for '{theme}'",
                "agent": "planner",
                "output": "research_scope"
            },
            {
                "step": 2,
                "action": "gather_information",
                "description": "Collect relevant information and sources",
                "agent": "research_agent",
                "input": "research_scope",
                "output": "raw_data"
            },
            {
                "step": 3,
                "action": "analyze_data",
                "description": "Analyze and synthesize collected information",
                "agent": "synthesis_agent",
                "input": "raw_data",
                "output": "analysis"
            },
            {
                "step": 4,
                "action": "create_report",
                "description": "Create comprehensive research report",
                "agent": "planner",
                "input": "analysis",
                "output": "research_report"
            }
        ]
    else:
        # Generic workflow plan
        plan["steps"] = [
            {
                "step": 1,
                "action": "analyze_requirements",
                "description": f"Analyze requirements for '{theme}'",
                "agent": "planner",
                "output": "requirements"
            },
            {
                "step": 2,
                "action": "design_solution",
                "description": "Design solution approach",
                "agent": "planner",
                "input": "requirements",
                "output": "solution_design"
            },
            {
                "step": 3,
                "action": "implement",
                "description": "Implement the solution",
                "agent": "execution_agent",
                "input": "solution_design",
                "output": "implementation"
            },
            {
                "step": 4,
                "action": "review",
                "description": "Review and validate implementation",
                "agent": "critic_agent",
                "input": "implementation",
                "output": "review"
            },
            {
                "step": 5,
                "action": "finalize",
                "description": "Finalize and approve",
                "agent": "judge_agent",
                "input": ["implementation", "review"],
                "output": "final_result"
            }
        ]
    
    # Store plan in Knowledge Graph if available
    if planner_agent.knowledge_graph:
        try:
            kg = planner_agent.knowledge_graph
            
            # Add main plan node
            await kg.add_triple(
                plan_uri,
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                "http://example.org/ontology#Plan"
            )
            await kg.add_triple(
                plan_uri,
                "http://example.org/ontology#hasTheme",
                theme
            )
            await kg.add_triple(
                plan_uri,
                "http://example.org/ontology#createdBy",
                f"http://example.org/agent/{planner_agent.agent_id}"
            )
            await kg.add_triple(
                plan_uri,
                "http://example.org/ontology#createdAt",
                plan["created_at"]
            )
            await kg.add_triple(
                plan_uri,
                "http://example.org/ontology#status",
                "created"
            )
            
            # Store full plan as JSON
            await kg.add_triple(
                plan_uri,
                "http://example.org/ontology#planData",
                json.dumps(plan)
            )
            
            # Add steps as separate triples for querying
            for step in plan["steps"]:
                step_uri = f"{plan_uri}/step/{step['step']}"
                await kg.add_triple(
                    step_uri,
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                    "http://example.org/ontology#PlanStep"
                )
                await kg.add_triple(
                    step_uri,
                    "http://example.org/ontology#belongsToPlan",
                    plan_uri
                )
                await kg.add_triple(
                    step_uri,
                    "http://example.org/ontology#stepNumber",
                    str(step["step"])
                )
                await kg.add_triple(
                    step_uri,
                    "http://example.org/ontology#action",
                    step["action"]
                )
                await kg.add_triple(
                    step_uri,
                    "http://example.org/ontology#description",
                    step["description"]
                )
                await kg.add_triple(
                    step_uri,
                    "http://example.org/ontology#assignedAgent",
                    step["agent"]
                )
            
            planner_agent.logger.info(f"Plan {plan_id} stored in Knowledge Graph")
            plan["kg_stored"] = True
            
        except Exception as e:
            planner_agent.logger.error(f"Error storing plan in KG: {e}")
            plan["kg_stored"] = False
    
    return plan

async def retrieve_plan(planner_agent, plan_id: str) -> Dict[str, Any]:
    """
    Retrieve a plan from the Knowledge Graph.
    
    Args:
        planner_agent: The PlannerAgent instance
        plan_id: The plan ID to retrieve
    
    Returns:
        Dict containing the plan data
    """
    if not planner_agent.knowledge_graph:
        return {"error": "Knowledge Graph not available"}
    
    try:
        plan_uri = f"http://example.org/plan/{plan_id}"
        
        # Query for plan data
        sparql_query = f"""
        SELECT ?predicate ?object
        WHERE {{
            <{plan_uri}> ?predicate ?object .
        }}
        """
        
        results = await planner_agent.knowledge_graph.query_graph(sparql_query)
        
        # Look for the planData JSON
        for result in results:
            if result.get("predicate") == "http://example.org/ontology#planData":
                plan_json = result.get("object")
                if plan_json:
                    return json.loads(plan_json)
        
        return {"error": f"Plan {plan_id} not found"}
        
    except Exception as e:
        planner_agent.logger.error(f"Error retrieving plan from KG: {e}")
        return {"error": str(e)}

async def list_plans(planner_agent, theme_filter: str = None) -> List[Dict[str, Any]]:
    """
    List all plans in the Knowledge Graph, optionally filtered by theme.
    
    Args:
        planner_agent: The PlannerAgent instance
        theme_filter: Optional theme to filter plans
    
    Returns:
        List of plan summaries
    """
    if not planner_agent.knowledge_graph:
        return []
    
    try:
        # Build SPARQL query
        if theme_filter:
            sparql_query = f"""
            SELECT ?plan ?theme ?createdAt ?status
            WHERE {{
                ?plan a <http://example.org/ontology#Plan> .
                ?plan <http://example.org/ontology#hasTheme> ?theme .
                ?plan <http://example.org/ontology#createdAt> ?createdAt .
                ?plan <http://example.org/ontology#status> ?status .
                FILTER(CONTAINS(LCASE(?theme), LCASE("{theme_filter}")))
            }}
            ORDER BY DESC(?createdAt)
            LIMIT 20
            """
        else:
            sparql_query = """
            SELECT ?plan ?theme ?createdAt ?status
            WHERE {
                ?plan a <http://example.org/ontology#Plan> .
                ?plan <http://example.org/ontology#hasTheme> ?theme .
                ?plan <http://example.org/ontology#createdAt> ?createdAt .
                ?plan <http://example.org/ontology#status> ?status .
            }
            ORDER BY DESC(?createdAt)
            LIMIT 20
            """
        
        results = await planner_agent.knowledge_graph.query_graph(sparql_query)
        
        # Format results
        plans = []
        for result in results:
            plan_uri = result.get("plan", "")
            plan_id = plan_uri.split("/")[-1] if plan_uri else "unknown"
            plans.append({
                "id": plan_id,
                "theme": result.get("theme", ""),
                "created_at": result.get("createdAt", ""),
                "status": result.get("status", "")
            })
        
        return plans
        
    except Exception as e:
        planner_agent.logger.error(f"Error listing plans from KG: {e}")
        return []

async def execute_plan_step(planner_agent, plan_id: str, step_number: int) -> Dict[str, Any]:
    """
    Execute a specific step from a stored plan.
    
    Args:
        planner_agent: The PlannerAgent instance
        plan_id: The plan ID
        step_number: The step number to execute
    
    Returns:
        Dict containing execution results
    """
    # Retrieve the plan
    plan = await retrieve_plan(planner_agent, plan_id)
    
    if "error" in plan:
        return plan
    
    # Find the step
    step_data = None
    for step in plan.get("steps", []):
        if step["step"] == step_number:
            step_data = step
            break
    
    if not step_data:
        return {"error": f"Step {step_number} not found in plan {plan_id}"}
    
    # Execute based on the assigned agent
    try:
        agent_id = step_data["agent"]
        action = step_data["action"]
        
        # Create a message for the agent
        message = AgentMessage(
            sender_id=planner_agent.agent_id,
            recipient_id=agent_id,
            content={
                "action": action,
                "description": step_data["description"],
                "plan_id": plan_id,
                "step": step_number
            },
            message_type="plan_execution"
        )
        
        # For now, just log the execution request
        # In a real system, you'd route this to the appropriate agent
        planner_agent.logger.info(f"Executing plan {plan_id} step {step_number}: {action}")
        
        # Update step status in KG
        step_uri = f"http://example.org/plan/{plan_id}/step/{step_number}"
        await planner_agent.knowledge_graph.add_triple(
            step_uri,
            "http://example.org/ontology#executedAt",
            datetime.now().isoformat()
        )
        
        return {
            "plan_id": plan_id,
            "step": step_number,
            "action": action,
            "status": "executed",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": f"Error executing step: {str(e)}"}

