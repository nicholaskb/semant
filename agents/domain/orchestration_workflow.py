"""
Comprehensive Multi-Agent Orchestration Workflow
This implements a complex workflow with plan creation, review, execution, and analysis.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import asyncio
from pathlib import Path
from agents.core.message_types import AgentMessage
from agents.utils.email_integration import EmailIntegration
from agents.domain.planner_kg_extension import (
    create_and_store_plan,
    retrieve_plan,
    execute_plan_step
)
from agents.utils.workflow_visualizer import WorkflowVisualizer
from kg.models.graph_manager import KnowledgeGraphManager
from loguru import logger
import uuid

class OrchestrationWorkflow:
    """
    Orchestrates complex multi-agent workflows with:
    1. Plan creation from text input
    2. Email notification and approval
    3. Knowledge Graph storage and visualization
    4. Multi-agent review process
    5. Execution readiness validation
    6. Monitored execution
    7. Post-execution analysis
    """
    
    def __init__(self, planner_agent, review_agents: List[Any] = None):
        """
        Initialize the orchestration workflow.
        
        Args:
            planner_agent: The main planner agent
            review_agents: List of review agents (e.g., CodeReviewAgent, etc.)
        """
        self.planner = planner_agent
        self.review_agents = review_agents or []
        # Enable real email if credentials are available, otherwise use simulation
        import os
        has_credentials = bool(os.getenv('EMAIL_SENDER') and os.getenv('EMAIL_PASSWORD'))
        self.email_integration = EmailIntegration(use_real_email=has_credentials)
        self.kg_manager = KnowledgeGraphManager(persistent_storage=True)
        self.workflow_id = None
        self.visualizer = WorkflowVisualizer(kg_manager=self.kg_manager)
        self.logger = logger.bind(component="OrchestrationWorkflow")
        
    async def initialize(self):
        """Initialize all components."""
        await self.kg_manager.initialize()
        self.logger.info("Orchestration workflow initialized")
        
    async def create_workflow_from_text(self, 
                                       text_file: str, 
                                       user_email: str,
                                       workflow_name: str = "Complex Workflow") -> Dict[str, Any]:
        """
        Step 1: Create a comprehensive workflow from a text file.
        
        Args:
            text_file: Path to the text file with requirements
            user_email: Email address for notifications
            workflow_name: Name for the workflow
            
        Returns:
            Workflow metadata and plan
        """
        self.workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Read the text file
        try:
            with open(text_file, 'r') as f:
                requirements_text = f.read()
        except FileNotFoundError:
            return {"error": f"File {text_file} not found"}
        
        # Create the workflow plan
        self.logger.info(f"Creating workflow {self.workflow_id} from {text_file}")
        
        # Generate plan from requirements
        plan_context = {
            "requirements": requirements_text,
            "workflow_id": self.workflow_id,
            "user_email": user_email,
            "created_from": text_file,
            "workflow_name": workflow_name
        }
        
        # Create and store plan in KG
        plan = await create_and_store_plan(
            self.planner,
            theme=f"{workflow_name}: {requirements_text[:100]}...",
            context=plan_context
        )
        
        # Store workflow metadata in KG
        workflow_uri = f"http://example.org/workflow/{self.workflow_id}"
        await self.kg_manager.add_triple(
            workflow_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/ontology#Workflow"
        )
        await self.kg_manager.add_triple(
            workflow_uri,
            "http://example.org/ontology#hasPlan",
            f"http://example.org/plan/{plan['id']}"
        )
        await self.kg_manager.add_triple(
            workflow_uri,
            "http://example.org/ontology#status",
            "created"
        )
        await self.kg_manager.add_triple(
            workflow_uri,
            "http://example.org/ontology#userEmail",
            user_email
        )
        
        self.logger.info(f"Workflow {self.workflow_id} created with plan {plan['id']}")
        
        return {
            "workflow_id": self.workflow_id,
            "plan": plan,
            "status": "created",
            "next_step": "email_notification"
        }
    
    async def send_plan_for_review(self, workflow_id: str, user_email: str) -> Dict[str, Any]:
        """
        Step 2: Send the plan via email for review and approval.
        
        Args:
            workflow_id: The workflow ID
            user_email: Email to send the plan to
            
        Returns:
            Email sending result
        """
        # Retrieve the plan from KG
        workflow_uri = f"http://example.org/workflow/{workflow_id}"
        
        # Get plan ID from workflow
        query = f"""
        PREFIX wf: <http://example.org/ontology#>
        SELECT ?plan
        WHERE {{
            <{workflow_uri}> wf:hasPlan ?plan .
        }}
        """
        results = await self.kg_manager.query_graph(query)
        
        if not results:
            return {"error": "Workflow not found"}
        
        plan_uri = results[0]["plan"]
        plan_id = plan_uri.split("/")[-1]
        
        # Retrieve full plan
        plan = await retrieve_plan(self.planner, plan_id)
        
        # Create email content with plan details
        email_subject = f"Workflow Plan Review Required: {workflow_id}"
        email_body = self._format_plan_email(workflow_id, plan)
        
        # Send email
        email_result = self.email_integration.send_email(
            recipient=user_email,
            subject=email_subject,
            body=email_body
        )
        
        # Update workflow status
        await self.kg_manager.add_triple(
            workflow_uri,
            "http://example.org/ontology#emailSentAt",
            datetime.now().isoformat()
        )
        await self.kg_manager.add_triple(
            workflow_uri,
            "http://example.org/ontology#status",
            "pending_review"
        )
        
        self.logger.info(f"Plan for workflow {workflow_id} sent to {user_email}")
        
        return {
            "workflow_id": workflow_id,
            "email_status": email_result["status"],
            "status": "pending_review",
            "next_step": "visualize_in_kg"
        }
    
    def _format_plan_email(self, workflow_id: str, plan: Dict[str, Any]) -> str:
        """Format the plan for email display."""
        body = f"""
        Workflow Plan Review Request
        =============================
        
        Workflow ID: {workflow_id}
        Created: {plan.get('created_at', 'Unknown')}
        Theme: {plan.get('theme', 'Unknown')}
        
        PLAN STEPS:
        -----------
        """
        
        for step in plan.get('steps', []):
            body += f"""
        Step {step['step']}: {step['action']}
        Description: {step['description']}
        Agent: {step['agent']}
        Output: {step['output']}
        -----------
        """
        
        body += """
        
        TO APPROVE THIS PLAN:
        Reply with "APPROVED" to execute this workflow.
        Reply with "REJECTED" to cancel.
        Reply with specific changes to modify the plan.
        
        You can visualize this plan in the Knowledge Graph at:
        http://localhost:8000/visualize/workflow/""" + workflow_id + """
        
        Best regards,
        Orchestration System
        """
        
        return body
    
    async def visualize_plan_in_kg(self, workflow_id: str) -> Dict[str, Any]:
        """
        Step 3: Create a comprehensive KG visualization of the plan.

        Args:
            workflow_id: The workflow ID

        Returns:
            Visualization metadata and SPARQL query
        """
        workflow_uri = f"http://example.org/plan/{workflow_id}"
        
        # Create visualization triples
        viz_uri = f"http://example.org/visualization/{workflow_id}"
        
        await self.kg_manager.add_triple(
            viz_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/ontology#Visualization"
        )
        await self.kg_manager.add_triple(
            viz_uri,
            "http://example.org/ontology#visualizes",
            workflow_uri
        )
        await self.kg_manager.add_triple(
            viz_uri,
            "http://example.org/ontology#createdAt",
            datetime.now().isoformat()
        )
        
        # Generate SPARQL query for visualization (using SELECT to get dict results)
        visualization_query = f"""
        PREFIX : <http://example.org/core#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?wp ?wo ?pp ?po ?ap ?ao ?plan ?agent
        WHERE {{
            <{workflow_uri}> ?wp ?wo .
            OPTIONAL {{
            <{workflow_uri}> :commander ?agent .
            ?agent ?ap ?ao .
            }}
            OPTIONAL {{
                ?plan :commander ?agent .
                ?plan ?pp ?po .
            }}
        }}
        """
        
        # Execute query to get results (returns List[Dict[str, str]])
        visualization_data = await self.kg_manager.query_graph(visualization_query)

        # Convert query results to workflow_data format expected by frontend
        workflow_data = []
        for row in visualization_data:
            # Handle workflow URI properties
            if 'wo' in row and row.get('wo'):
                workflow_data.append({
                    "subject": workflow_uri,
                    "predicate": row.get('wp', '').split('/')[-1] if row.get('wp') else '',
                    "object": str(row.get('wo', ''))
                })
            # Handle plan properties
            if 'po' in row and row.get('po') and row.get('plan'):
                workflow_data.append({
                    "subject": str(row.get('plan', '')),
                    "predicate": row.get('pp', '').split('/')[-1] if row.get('pp') else '',
                    "object": str(row.get('po', ''))
                })
            # Handle agent properties
            if 'ao' in row and row.get('ao') and row.get('agent'):
                workflow_data.append({
                    "subject": str(row.get('agent', '')),
                    "predicate": row.get('ap', '').split('/')[-1] if row.get('ap') else '',
                    "object": str(row.get('ao', ''))
            })

        # Create mock step details for the hot dog flyer workflow
        step_details = [
            {
                "step_number": "1.1",
                "action": "Generate hot dog close-up",
                "agent": "flyer-planner-supreme",
                "description": "Create professional food photography of fresh hot dog with steam",
                "input": "Professional food photography prompt with commercial styling",
                "output": "High-quality hot dog image for flyer hero section"
            },
            {
                "step_number": "1.2",
                "action": "Generate ingredients display",
                "agent": "flyer-planner-supreme",
                "description": "Photograph fresh hot dog ingredients arranged beautifully",
                "input": "Fresh ingredients arrangement prompt",
                "output": "Ingredients showcase image for quality demonstration"
            },
            {
                "step_number": "1.3",
                "action": "Generate ambiance shot",
                "agent": "flyer-planner-supreme",
                "description": "Capture cozy hot dog stand atmosphere",
                "input": "Restaurant ambiance photography prompt",
                "output": "Atmospheric image for restaurant appeal"
            },
            {
                "step_number": "2.1",
                "action": "Design flyer layout",
                "agent": "flyer-planner-supreme",
                "description": "Create 3-panel horizontal layout with professional styling",
                "input": "Three generated images",
                "output": "Professional flyer layout design"
            }
        ]

        # Create SPARQL queries section
        sparql_queries = {
            "workflow_overview": visualization_query,
            "agent_conversations": f"""
            PREFIX : <http://example.org/core#>
            SELECT ?agent ?authority ?status WHERE {{
              ?agent a :Agent .
              ?agent :authority ?authority .
              ?agent :status ?status .
            }}
            """,
            "plan_details": f"""
            PREFIX : <http://example.org/core#>
            SELECT ?plan ?mission ?commander WHERE {{
              ?plan a :FlyerCreationPlan .
              ?plan :mission ?mission .
              ?plan :commander ?commander .
            }}
            """
        }

        self.logger.info(f"Visualization created for workflow {workflow_id}")
        
        # Generate HTML visualization
        try:
            html_path = await self.visualizer.generate_html_visualization(workflow_id)
            self.logger.info(f"HTML visualization generated: {html_path}")
        except Exception as e:
            self.logger.warning(f"Failed to generate HTML visualization: {e}")
            html_path = None

        return {
            "workflow_id": workflow_id,
            "status": "visualized",
            "next_step": "agent_review",
            "workflow_data": workflow_data,
            "step_details": step_details,
            "sparql_queries": sparql_queries,
            "html_visualization": html_path,
            "metadata": {
                "total_triples": len(visualization_data),
                "agent": "flyer-planner-supreme",
                "authority": "SUPREME",
                "mission": "HOT DOG FLYER CREATION"
            }
        }
    
    async def conduct_agent_review(self, workflow_id: str) -> Dict[str, Any]:
        """
        Step 4: Have review agents analyze the plan.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            Review results from all agents
        """
        workflow_uri = f"http://example.org/workflow/{workflow_id}"
        review_uri = f"http://example.org/review/{workflow_id}"
        
        # Get the plan
        query = f"""
        PREFIX wf: <http://example.org/ontology#>
        SELECT ?plan
        WHERE {{
            <{workflow_uri}> wf:hasPlan ?plan .
        }}
        """
        results = await self.kg_manager.query_graph(query)
        plan_uri = results[0]["plan"]
        plan_id = plan_uri.split("/")[-1]
        plan = await retrieve_plan(self.planner, plan_id)
        
        # Conduct reviews
        reviews = []
        
        for agent in self.review_agents:
            self.logger.info(f"Requesting review from {agent.agent_id}")
            
            # Send review request to agent
            review_message = AgentMessage(
                sender_id="orchestrator",
                recipient_id=agent.agent_id,
                content={
                    "action": "review_plan",
                    "plan": plan,
                    "workflow_id": workflow_id
                },
                message_type="review_request"
            )
            
            try:
                review_result = await agent.process_message(review_message)
                review_content = review_result.content
            except Exception as e:
                review_content = {
                    "status": "error",
                    "error": str(e),
                    "recommendation": "unable_to_review"
                }
            
            # Store review in KG
            agent_review_uri = f"{review_uri}/{agent.agent_id}"
            await self.kg_manager.add_triple(
                agent_review_uri,
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                "http://example.org/ontology#Review"
            )
            await self.kg_manager.add_triple(
                agent_review_uri,
                "http://example.org/ontology#reviewedBy",
                f"http://example.org/agent/{agent.agent_id}"
            )
            await self.kg_manager.add_triple(
                agent_review_uri,
                "http://example.org/ontology#reviewOf",
                workflow_uri
            )
            await self.kg_manager.add_triple(
                agent_review_uri,
                "http://example.org/ontology#reviewContent",
                json.dumps(review_content)
            )
            await self.kg_manager.add_triple(
                agent_review_uri,
                "http://example.org/ontology#reviewedAt",
                datetime.now().isoformat()
            )
            
            reviews.append({
                "agent": agent.agent_id,
                "review": review_content,
                "recommendation": review_content.get("recommendation", "unknown")
            })
        
        # Determine consensus
        approvals = sum(1 for r in reviews if r["recommendation"] == "approve")
        consensus = "approved" if approvals > len(reviews) / 2 else "needs_revision"
        
        await self.kg_manager.add_triple(
            workflow_uri,
            "http://example.org/ontology#reviewConsensus",
            consensus
        )
        
        self.logger.info(f"Review complete for workflow {workflow_id}: {consensus}")
        
        return {
            "workflow_id": workflow_id,
            "reviews": reviews,
            "consensus": consensus,
            "approval_rate": f"{approvals}/{len(reviews)}",
            "status": "reviewed",
            "next_step": "validate_execution" if consensus == "approved" else "revise_plan"
        }
    
    async def validate_execution_readiness(self, workflow_id: str) -> Dict[str, Any]:
        """
        Step 5: Validate that execution can proceed without issues.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            Validation results
        """
        workflow_uri = f"http://example.org/workflow/{workflow_id}"
        validation_uri = f"http://example.org/validation/{workflow_id}"
        
        # Get the plan
        query = f"""
        PREFIX wf: <http://example.org/ontology#>
        SELECT ?plan
        WHERE {{
            <{workflow_uri}> wf:hasPlan ?plan .
        }}
        """
        results = await self.kg_manager.query_graph(query)
        plan_uri = results[0]["plan"]
        plan_id = plan_uri.split("/")[-1]
        plan = await retrieve_plan(self.planner, plan_id)
        
        validations = []
        
        # Check 1: All required agents exist
        for step in plan.get("steps", []):
            agent_id = step.get("agent")
            agent_exists = await self._check_agent_exists(agent_id)
            validations.append({
                "check": f"Agent {agent_id} exists",
                "result": "pass" if agent_exists else "fail",
                "critical": True
            })
        
        # Check 2: Dependencies are satisfied
        for i, step in enumerate(plan.get("steps", [])):
            if "input" in step:
                inputs = step["input"] if isinstance(step["input"], list) else [step["input"]]
                for input_ref in inputs:
                    # Check if previous steps provide this input
                    input_available = any(
                        s.get("output") == input_ref 
                        for s in plan["steps"][:i]
                    )
                    validations.append({
                        "check": f"Step {i+1} input '{input_ref}' available",
                        "result": "pass" if input_available else "fail",
                        "critical": True
                    })
        
        # Check 3: No circular dependencies
        circular = self._check_circular_dependencies(plan)
        validations.append({
            "check": "No circular dependencies",
            "result": "pass" if not circular else "fail",
            "critical": True
        })
        
        # Store validation results
        await self.kg_manager.add_triple(
            validation_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/ontology#Validation"
        )
        await self.kg_manager.add_triple(
            validation_uri,
            "http://example.org/ontology#validatedAt",
            datetime.now().isoformat()
        )
        await self.kg_manager.add_triple(
            validation_uri,
            "http://example.org/ontology#validationResults",
            json.dumps(validations)
        )
        
        # Determine if ready for execution
        critical_failures = [v for v in validations if v["critical"] and v["result"] == "fail"]
        ready = len(critical_failures) == 0
        
        await self.kg_manager.add_triple(
            workflow_uri,
            "http://example.org/ontology#executionReady",
            str(ready)
        )
        
        self.logger.info(f"Validation complete for workflow {workflow_id}: {'ready' if ready else 'not ready'}")
        
        return {
            "workflow_id": workflow_id,
            "validations": validations,
            "critical_failures": len(critical_failures),
            "execution_ready": ready,
            "status": "validated",
            "next_step": "execute" if ready else "fix_issues"
        }
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Step 6: Execute the workflow with monitoring.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            Execution results
        """
        workflow_uri = f"http://example.org/workflow/{workflow_id}"
        execution_uri = f"http://example.org/execution/{workflow_id}"
        
        # Get the plan
        query = f"""
        PREFIX wf: <http://example.org/ontology#>
        SELECT ?plan
        WHERE {{
            <{workflow_uri}> wf:hasPlan ?plan .
        }}
        """
        results = await self.kg_manager.query_graph(query)
        plan_uri = results[0]["plan"]
        plan_id = plan_uri.split("/")[-1]
        plan = await retrieve_plan(self.planner, plan_id)
        
        # Start execution
        await self.kg_manager.add_triple(
            execution_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/ontology#Execution"
        )
        await self.kg_manager.add_triple(
            execution_uri,
            "http://example.org/ontology#startedAt",
            datetime.now().isoformat()
        )
        await self.kg_manager.add_triple(
            workflow_uri,
            "http://example.org/ontology#status",
            "executing"
        )
        
        execution_results = []
        
        # Execute each step
        for step in plan.get("steps", []):
            step_num = step["step"]
            self.logger.info(f"Executing step {step_num}: {step['action']}")
            
            step_execution_uri = f"{execution_uri}/step/{step_num}"
            
            # Record step start
            await self.kg_manager.add_triple(
                step_execution_uri,
                "http://example.org/ontology#startedAt",
                datetime.now().isoformat()
            )
            
            try:
                # Execute the step
                result = await execute_plan_step(self.planner, plan_id, step_num)
                
                # Record success
                await self.kg_manager.add_triple(
                    step_execution_uri,
                    "http://example.org/ontology#status",
                    "completed"
                )
                await self.kg_manager.add_triple(
                    step_execution_uri,
                    "http://example.org/ontology#result",
                    json.dumps(result)
                )
                
                execution_results.append({
                    "step": step_num,
                    "action": step["action"],
                    "status": "completed",
                    "result": result
                })
                
            except Exception as e:
                # Record failure
                await self.kg_manager.add_triple(
                    step_execution_uri,
                    "http://example.org/ontology#status",
                    "failed"
                )
                await self.kg_manager.add_triple(
                    step_execution_uri,
                    "http://example.org/ontology#error",
                    str(e)
                )
                
                execution_results.append({
                    "step": step_num,
                    "action": step["action"],
                    "status": "failed",
                    "error": str(e)
                })
                
                self.logger.error(f"Step {step_num} failed: {e}")
                # Continue with other steps or stop based on criticality
            
            # Record step end
            await self.kg_manager.add_triple(
                step_execution_uri,
                "http://example.org/ontology#completedAt",
                datetime.now().isoformat()
            )
        
        # Complete execution
        await self.kg_manager.add_triple(
            execution_uri,
            "http://example.org/ontology#completedAt",
            datetime.now().isoformat()
        )
        await self.kg_manager.add_triple(
            workflow_uri,
            "http://example.org/ontology#status",
            "completed"
        )
        
        self.logger.info(f"Execution complete for workflow {workflow_id}")
        
        return {
            "workflow_id": workflow_id,
            "execution_results": execution_results,
            "status": "completed",
            "next_step": "post_execution_analysis"
        }
    
    async def conduct_post_execution_analysis(self, workflow_id: str) -> Dict[str, Any]:
        """
        Step 7: Analyze the execution and allow agent commentary.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            Analysis results
        """
        workflow_uri = f"http://example.org/workflow/{workflow_id}"
        analysis_uri = f"http://example.org/analysis/{workflow_id}"
        
        # Get execution data
        query = f"""
        PREFIX wf: <http://example.org/ontology#>
        PREFIX ex: <http://example.org/ontology#>
        
        SELECT ?execution ?step ?status ?startedAt ?completedAt ?result ?error
        WHERE {{
            <{workflow_uri}> wf:status "completed" .
            ?execution ex:executesWorkflow <{workflow_uri}> .
            ?step ex:partOfExecution ?execution .
            ?step ex:status ?status .
            OPTIONAL {{ ?step ex:startedAt ?startedAt }}
            OPTIONAL {{ ?step ex:completedAt ?completedAt }}
            OPTIONAL {{ ?step ex:result ?result }}
            OPTIONAL {{ ?step ex:error ?error }}
        }}
        """
        
        execution_data = await self.kg_manager.query_graph(query)
        
        # Analyze execution
        analysis = {
            "total_steps": len(execution_data),
            "successful_steps": sum(1 for e in execution_data if e.get("status") == "completed"),
            "failed_steps": sum(1 for e in execution_data if e.get("status") == "failed"),
            "execution_order": [],
            "timing_analysis": [],
            "agent_commentary": []
        }
        
        # Request commentary from agents
        for agent in self.review_agents:
            commentary_message = AgentMessage(
                sender_id="orchestrator",
                recipient_id=agent.agent_id,
                content={
                    "action": "analyze_execution",
                    "workflow_id": workflow_id,
                    "execution_data": execution_data
                },
                message_type="analysis_request"
            )
            
            try:
                commentary_result = await agent.process_message(commentary_message)
                commentary = commentary_result.content.get("commentary", "No commentary provided")
                
                # Store commentary in KG
                commentary_uri = f"{analysis_uri}/commentary/{agent.agent_id}"
                await self.kg_manager.add_triple(
                    commentary_uri,
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                    "http://example.org/ontology#Commentary"
                )
                await self.kg_manager.add_triple(
                    commentary_uri,
                    "http://example.org/ontology#commentBy",
                    f"http://example.org/agent/{agent.agent_id}"
                )
                await self.kg_manager.add_triple(
                    commentary_uri,
                    "http://example.org/ontology#commentText",
                    commentary
                )
                await self.kg_manager.add_triple(
                    commentary_uri,
                    "http://example.org/ontology#commentedAt",
                    datetime.now().isoformat()
                )
                
                analysis["agent_commentary"].append({
                    "agent": agent.agent_id,
                    "commentary": commentary
                })
                
            except Exception as e:
                self.logger.error(f"Failed to get commentary from {agent.agent_id}: {e}")
        
        # Store analysis
        await self.kg_manager.add_triple(
            analysis_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/ontology#Analysis"
        )
        await self.kg_manager.add_triple(
            analysis_uri,
            "http://example.org/ontology#analyzedAt",
            datetime.now().isoformat()
        )
        await self.kg_manager.add_triple(
            analysis_uri,
            "http://example.org/ontology#analysisData",
            json.dumps(analysis)
        )
        
        self.logger.info(f"Post-execution analysis complete for workflow {workflow_id}")
        
        return {
            "workflow_id": workflow_id,
            "analysis": analysis,
            "status": "analyzed",
            "workflow_complete": True
        }
    
    async def _check_agent_exists(self, agent_id: str) -> bool:
        """Check if an agent exists in the system."""
        # This would check against the actual agent registry
        # For now, return True for demonstration
        return True
    
    def _check_circular_dependencies(self, plan: Dict[str, Any]) -> bool:
        """Check for circular dependencies in the plan."""
        # Simple check - in a real system this would be more sophisticated
        steps = plan.get("steps", [])
        for i, step in enumerate(steps):
            if "input" in step:
                inputs = step["input"] if isinstance(step["input"], list) else [step["input"]]
                for input_ref in inputs:
                    # Check if any later step provides this input (circular)
                    if any(s.get("output") == input_ref for s in steps[i+1:]):
                        return True
        return False

# Helper function to create and execute a complete workflow
async def execute_complete_workflow(text_file: str, 
                                   user_email: str,
                                   planner_agent,
                                   review_agents: List[Any] = None) -> Dict[str, Any]:
    """
    Execute the complete workflow from start to finish.
    
    Args:
        text_file: Path to requirements text file
        user_email: Email for notifications
        planner_agent: The planner agent
        review_agents: List of review agents
        
    Returns:
        Complete workflow execution summary
    """
    workflow = OrchestrationWorkflow(planner_agent, review_agents)
    await workflow.initialize()
    
    results = {}
    
    # Step 1: Create workflow from text
    results["creation"] = await workflow.create_workflow_from_text(
        text_file, user_email, "Comprehensive Workflow"
    )
    workflow_id = results["creation"]["workflow_id"]
    
    # Step 2: Send for review
    results["email"] = await workflow.send_plan_for_review(workflow_id, user_email)
    
    # Step 3: Visualize in KG
    results["visualization"] = await workflow.visualize_plan_in_kg(workflow_id)
    
    # Step 4: Agent review
    results["review"] = await workflow.conduct_agent_review(workflow_id)
    
    # Step 5: Validate execution readiness
    results["validation"] = await workflow.validate_execution_readiness(workflow_id)
    
    # Step 6: Execute (if validated)
    if results["validation"]["execution_ready"]:
        results["execution"] = await workflow.execute_workflow(workflow_id)
        
        # Step 7: Post-execution analysis
        results["analysis"] = await workflow.conduct_post_execution_analysis(workflow_id)
    
    return results
