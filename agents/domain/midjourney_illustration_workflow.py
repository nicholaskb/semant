"""
Midjourney Illustration Workflow for Children's Book
Integrates image generation with multi-agent evaluation and refinement.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from agents.core.message_types import AgentMessage
from agents.domain.orchestration_workflow import OrchestrationWorkflow
from kg.models.graph_manager import KnowledgeGraphManager
from loguru import logger
import httpx


class IllustrationOrchestrationWorkflow(OrchestrationWorkflow):
    """
    Enhanced workflow that integrates Midjourney for book illustrations.
    Agents can evaluate images, refine prompts, and create alternative versions.
    """
    
    def __init__(self, planner_agent, review_agents: List[Any] = None):
        super().__init__(planner_agent, review_agents)
        self.illustration_nodes = {}  # Track different illustration branches
        self.midjourney_client = None
        self.logger = logger.bind(component="IllustrationWorkflow")
        
    async def initialize(self):
        """Initialize workflow with Midjourney support."""
        await super().initialize()
        self.logger.info("Illustration workflow initialized with Midjourney support")
    
    async def generate_illustration_prompts(self, 
                                           book_content: Dict[str, Any],
                                           workflow_id: str) -> List[Dict[str, Any]]:
        """
        Generate Midjourney prompts for each page of the book.
        
        Args:
            book_content: The book content with pages
            workflow_id: The workflow ID
            
        Returns:
            List of illustration prompts for each page
        """
        prompts = []
        
        for page_num in range(1, 13):  # 12 pages
            # Extract page content and key elements
            page_text = book_content.get(f"page_{page_num}", "")
            
            # Create base prompt for this page
            base_prompt = await self._create_base_illustration_prompt(
                page_num, page_text, book_content.get("character_profile")
            )
            
            # Refine the prompt using the Planner
            refined_prompt = await self._refine_midjourney_prompt(base_prompt)
            
            prompts.append({
                "page": page_num,
                "base_prompt": base_prompt,
                "refined_prompt": refined_prompt,
                "metadata": {
                    "workflow_id": workflow_id,
                    "created_at": datetime.now().isoformat()
                }
            })
            
            # Store prompt in KG
            await self._store_prompt_in_kg(workflow_id, page_num, refined_prompt)
        
        return prompts
    
    async def _create_base_illustration_prompt(self, 
                                              page_num: int,
                                              page_text: str,
                                              character_profile: Dict) -> str:
        """
        Create a base Midjourney prompt for a page.
        
        Args:
            page_num: Page number
            page_text: Text content of the page
            character_profile: Character details
            
        Returns:
            Base Midjourney prompt
        """
        # Key elements for Quacky McWaddles
        if page_num == 1:
            prompt = (
                "Children's book illustration, watercolor style, "
                "cute yellow duckling with oversized orange webbed feet, "
                "one feather sticking up on head, by a sparkly blue pond, "
                "mid-splash action, water droplets in air, bright sunny day, "
                "whimsical, funny expression, age 4-6 appropriate --ar 16:9 --v 6"
            )
        elif page_num == 7:
            prompt = (
                "Children's book illustration, watercolor style, "
                "yellow duckling tangled in green reeds, comically large orange feet, "
                "inventing a hopping dance, motion lines, funny expression, "
                "meadow background with watching bunnies, whimsical and silly, "
                "bright colors --ar 16:9 --v 6"
            )
        elif page_num == 9:
            prompt = (
                "Children's book illustration, watercolor style, "
                "wise old white goose wearing tiny round spectacles, "
                "talking to small yellow duckling with big orange feet, "
                "on top of grassy hill, pond visible below, "
                "warm lighting, storybook quality --ar 16:9 --v 6"
            )
        else:
            # Generic page prompt
            prompt = (
                f"Children's book illustration page {page_num}, watercolor style, "
                "yellow duckling with oversized orange feet, one feather sticking up, "
                "whimsical pond setting, bright cheerful colors, "
                "age 4-6 appropriate, funny and endearing --ar 16:9 --v 6"
            )
        
        return prompt
    
    async def _refine_midjourney_prompt(self, base_prompt: str) -> str:
        """
        Use the Planner agent to refine the Midjourney prompt.
        
        Args:
            base_prompt: Original prompt
            
        Returns:
            Refined prompt
        """
        # Call the refine-prompt endpoint
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/api/midjourney/refine-prompt",
                    json={"prompt": base_prompt}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    refined = result.get("refined_prompt", base_prompt)
                    self.logger.info(f"Prompt refined: {base_prompt[:50]}... -> {refined[:50]}...")
                    return refined
                else:
                    self.logger.warning(f"Refinement failed, using base prompt")
                    return base_prompt
                    
        except Exception as e:
            self.logger.error(f"Error refining prompt: {e}")
            return base_prompt
    
    async def generate_illustrations_with_midjourney(self,
                                                    prompts: List[Dict[str, Any]],
                                                    workflow_id: str) -> Dict[str, Any]:
        """
        Generate illustrations using Midjourney for all prompts.
        
        Args:
            prompts: List of prompts for each page
            workflow_id: The workflow ID
            
        Returns:
            Generated illustrations metadata
        """
        illustrations = []
        
        for prompt_data in prompts[:3]:  # Generate first 3 pages as demo
            page_num = prompt_data["page"]
            refined_prompt = prompt_data["refined_prompt"]
            
            self.logger.info(f"Generating illustration for page {page_num}")
            
            # Call Midjourney API
            result = await self._call_midjourney_imagine(refined_prompt, page_num)
            
            if result["status"] == "success":
                # Store in KG
                await self._store_illustration_in_kg(
                    workflow_id, page_num, result["task_id"], result["image_urls"]
                )
                
                illustrations.append({
                    "page": page_num,
                    "task_id": result["task_id"],
                    "image_urls": result["image_urls"],
                    "prompt": refined_prompt,
                    "status": "generated"
                })
            else:
                illustrations.append({
                    "page": page_num,
                    "status": "failed",
                    "error": result.get("error")
                })
        
        return {
            "workflow_id": workflow_id,
            "illustrations": illustrations,
            "total_pages": len(prompts),
            "generated": len([i for i in illustrations if i["status"] == "generated"])
        }
    
    async def _call_midjourney_imagine(self, prompt: str, page_num: int) -> Dict[str, Any]:
        """
        Call Midjourney imagine endpoint.
        
        Args:
            prompt: The Midjourney prompt
            page_num: Page number for reference
            
        Returns:
            Result with task_id and image URLs
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "http://localhost:8000/api/midjourney/imagine",
                    json={
                        "prompt": prompt,
                        "aspect_ratio": "16:9",
                        "version": "6",
                        "quality": "1",
                        "stylize": "100"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "status": "success",
                        "task_id": result.get("task_id"),
                        "image_urls": result.get("images", []),
                        "page": page_num
                    }
                else:
                    return {
                        "status": "failed",
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "page": page_num
                    }
                    
        except Exception as e:
            self.logger.error(f"Midjourney imagine failed for page {page_num}: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "page": page_num
            }
    
    async def evaluate_illustrations_with_agents(self,
                                                illustrations: List[Dict[str, Any]],
                                                workflow_id: str) -> Dict[str, Any]:
        """
        Have multiple agents evaluate the generated illustrations.
        
        Args:
            illustrations: Generated illustrations
            workflow_id: The workflow ID
            
        Returns:
            Evaluation results with best picks
        """
        evaluation_results = []
        
        for illustration in illustrations:
            if illustration["status"] != "generated":
                continue
            
            page_num = illustration["page"]
            image_urls = illustration["image_urls"]
            
            # Get evaluations from different agents
            evaluations = []
            
            # Art Director Agent evaluation
            art_eval = await self._evaluate_with_agent(
                "ArtDirectorAgent",
                image_urls,
                {
                    "criteria": ["composition", "color_harmony", "visual_appeal"],
                    "target_age": "4-6",
                    "style": "children's book"
                }
            )
            evaluations.append(art_eval)
            
            # Child Psychology Agent evaluation
            psych_eval = await self._evaluate_with_agent(
                "ChildPsychologyAgent",
                image_urls,
                {
                    "criteria": ["age_appropriateness", "emotional_impact", "engagement"],
                    "target_age": "4-6"
                }
            )
            evaluations.append(psych_eval)
            
            # Character Consistency Agent evaluation
            consistency_eval = await self._evaluate_with_agent(
                "CharacterConsistencyAgent",
                image_urls,
                {
                    "character": "Quacky McWaddles",
                    "features": ["yellow duck", "big orange feet", "one feather up"]
                }
            )
            evaluations.append(consistency_eval)
            
            # Determine best image based on consensus
            best_image = self._determine_best_image(evaluations, image_urls)
            
            evaluation_results.append({
                "page": page_num,
                "evaluations": evaluations,
                "best_image": best_image,
                "consensus_score": best_image["score"]
            })
            
            # Store evaluation in KG
            await self._store_evaluation_in_kg(workflow_id, page_num, evaluations, best_image)
        
        return {
            "workflow_id": workflow_id,
            "evaluations": evaluation_results,
            "pages_evaluated": len(evaluation_results)
        }
    
    async def _evaluate_with_agent(self, 
                                  agent_type: str,
                                  image_urls: List[str],
                                  criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Have an agent evaluate images.
        
        Args:
            agent_type: Type of evaluating agent
            image_urls: URLs of images to evaluate
            criteria: Evaluation criteria
            
        Returns:
            Evaluation results
        """
        # Simulate agent evaluation (in real system, would call actual agent)
        scores = []
        for i, url in enumerate(image_urls):
            # Simulate scoring based on criteria
            score = 0.7 + (0.3 * (i / len(image_urls)))  # Mock scoring
            scores.append({
                "image_index": i,
                "url": url,
                "score": score,
                "notes": f"{agent_type} evaluation notes for image {i+1}"
            })
        
        return {
            "agent": agent_type,
            "scores": scores,
            "recommended": max(scores, key=lambda x: x["score"])["image_index"],
            "criteria": criteria
        }
    
    def _determine_best_image(self, 
                             evaluations: List[Dict[str, Any]],
                             image_urls: List[str]) -> Dict[str, Any]:
        """
        Determine best image based on agent consensus.
        
        Args:
            evaluations: All agent evaluations
            image_urls: Image URLs
            
        Returns:
            Best image with consensus score
        """
        # Calculate consensus scores
        image_scores = {}
        for i in range(len(image_urls)):
            total_score = 0
            for eval in evaluations:
                for score_data in eval["scores"]:
                    if score_data["image_index"] == i:
                        total_score += score_data["score"]
            image_scores[i] = total_score / len(evaluations)
        
        # Find best image
        best_index = max(image_scores, key=image_scores.get)
        
        return {
            "index": best_index,
            "url": image_urls[best_index],
            "score": image_scores[best_index],
            "consensus": "strong" if image_scores[best_index] > 0.8 else "moderate"
        }
    
    async def upscale_best_illustrations(self,
                                        evaluation_results: List[Dict[str, Any]],
                                        workflow_id: str) -> Dict[str, Any]:
        """
        Upscale the best illustrations as chosen by agents.
        
        Args:
            evaluation_results: Results from agent evaluations
            workflow_id: The workflow ID
            
        Returns:
            Upscaled images metadata
        """
        upscaled = []
        
        for result in evaluation_results:
            best_image = result["best_image"]
            page_num = result["page"]
            
            self.logger.info(f"Upscaling best image for page {page_num} (index {best_image['index']})")
            
            # Call Midjourney upscale
            upscale_result = await self._call_midjourney_upscale(
                best_image["url"],
                best_image["index"] + 1  # Midjourney uses 1-based indexing
            )
            
            if upscale_result["status"] == "success":
                upscaled.append({
                    "page": page_num,
                    "original_url": best_image["url"],
                    "upscaled_url": upscale_result["url"],
                    "task_id": upscale_result["task_id"]
                })
                
                # Store in KG
                await self._store_upscale_in_kg(workflow_id, page_num, upscale_result)
            else:
                upscaled.append({
                    "page": page_num,
                    "status": "failed",
                    "error": upscale_result.get("error")
                })
        
        return {
            "workflow_id": workflow_id,
            "upscaled": upscaled,
            "success_count": len([u for u in upscaled if "upscaled_url" in u])
        }
    
    async def _call_midjourney_upscale(self, image_url: str, index: int) -> Dict[str, Any]:
        """
        Call Midjourney upscale endpoint.
        
        Args:
            image_url: URL of image to upscale
            index: Image index (1-4)
            
        Returns:
            Upscale result
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "http://localhost:8000/api/midjourney/action",
                    json={
                        "action": "upscale",
                        "index": index,
                        "task_id": "mock_task_id",  # Would come from original generation
                        "message_id": "mock_message_id"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "status": "success",
                        "url": result.get("image_url", image_url + "_upscaled"),
                        "task_id": result.get("task_id")
                    }
                else:
                    return {
                        "status": "failed",
                        "error": f"HTTP {response.status_code}"
                    }
                    
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def create_alternative_illustration_branch(self,
                                                    agent_id: str,
                                                    page_num: int,
                                                    new_prompt: str,
                                                    workflow_id: str,
                                                    reason: str) -> Dict[str, Any]:
        """
        Allow an agent to create an alternative illustration branch.
        
        Args:
            agent_id: ID of the agent proposing alternative
            page_num: Page number for alternative
            new_prompt: New prompt for alternative version
            workflow_id: The workflow ID
            reason: Why the agent thinks this is better
            
        Returns:
            Alternative branch metadata
        """
        branch_id = f"alt_{agent_id}_{page_num}_{uuid.uuid4().hex[:8]}"
        
        self.logger.info(f"Agent {agent_id} creating alternative branch for page {page_num}")
        
        # Generate alternative illustration
        result = await self._call_midjourney_imagine(new_prompt, page_num)
        
        if result["status"] == "success":
            # Create branch node in KG
            branch_uri = f"http://example.org/branch/{branch_id}"
            
            await self.kg_manager.add_triple(
                branch_uri,
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                "http://example.org/ontology#AlternativeBranch"
            )
            await self.kg_manager.add_triple(
                branch_uri,
                "http://example.org/ontology#proposedBy",
                f"http://example.org/agent/{agent_id}"
            )
            await self.kg_manager.add_triple(
                branch_uri,
                "http://example.org/ontology#forPage",
                str(page_num)
            )
            await self.kg_manager.add_triple(
                branch_uri,
                "http://example.org/ontology#reason",
                reason
            )
            await self.kg_manager.add_triple(
                branch_uri,
                "http://example.org/ontology#alternativePrompt",
                new_prompt
            )
            await self.kg_manager.add_triple(
                branch_uri,
                "http://example.org/ontology#resultImages",
                json.dumps(result["image_urls"])
            )
            
            # Link to main workflow
            await self.kg_manager.add_triple(
                branch_uri,
                "http://example.org/ontology#alternativeFor",
                f"http://example.org/workflow/{workflow_id}/page/{page_num}"
            )
            
            return {
                "branch_id": branch_id,
                "agent": agent_id,
                "page": page_num,
                "status": "created",
                "images": result["image_urls"],
                "reason": reason,
                "prompt": new_prompt
            }
        else:
            return {
                "branch_id": branch_id,
                "status": "failed",
                "error": result.get("error")
            }
    
    async def compare_illustration_branches(self,
                                           workflow_id: str,
                                           page_num: int) -> Dict[str, Any]:
        """
        Compare main and alternative illustration branches.
        
        Args:
            workflow_id: The workflow ID
            page_num: Page number to compare
            
        Returns:
            Comparison results
        """
        # Query KG for all branches for this page
        query = f"""
        PREFIX ont: <http://example.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?branch ?agent ?reason ?images
        WHERE {{
            ?branch rdf:type ont:AlternativeBranch .
            ?branch ont:forPage "{page_num}" .
            ?branch ont:alternativeFor <http://example.org/workflow/{workflow_id}/page/{page_num}> .
            ?branch ont:proposedBy ?agent .
            ?branch ont:reason ?reason .
            ?branch ont:resultImages ?images .
        }}
        """
        
        alternatives = await self.kg_manager.query_graph(query)
        
        # Get main branch evaluation
        main_query = f"""
        PREFIX ont: <http://example.org/ontology#>
        
        SELECT ?evaluation ?bestImage
        WHERE {{
            <http://example.org/workflow/{workflow_id}/page/{page_num}> 
                ont:evaluation ?evaluation ;
                ont:bestImage ?bestImage .
        }}
        """
        
        main_result = await self.kg_manager.query_graph(main_query)
        
        return {
            "page": page_num,
            "main_branch": main_result[0] if main_result else None,
            "alternatives": alternatives,
            "alternative_count": len(alternatives),
            "comparison": "Multiple versions available for review"
        }
    
    async def finalize_illustrations(self,
                                   workflow_id: str,
                                   selections: Dict[int, str]) -> Dict[str, Any]:
        """
        Finalize illustration selections for the book.
        
        Args:
            workflow_id: The workflow ID
            selections: Dict of page_num -> selected_image_url
            
        Returns:
            Final illustration set
        """
        final_illustrations = []
        
        for page_num, image_url in selections.items():
            # Store final selection in KG
            final_uri = f"http://example.org/workflow/{workflow_id}/final/page/{page_num}"
            
            await self.kg_manager.add_triple(
                final_uri,
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                "http://example.org/ontology#FinalIllustration"
            )
            await self.kg_manager.add_triple(
                final_uri,
                "http://example.org/ontology#imageUrl",
                image_url
            )
            await self.kg_manager.add_triple(
                final_uri,
                "http://example.org/ontology#finalizedAt",
                datetime.now().isoformat()
            )
            
            final_illustrations.append({
                "page": page_num,
                "final_image": image_url,
                "status": "finalized"
            })
        
        self.logger.info(f"Finalized {len(final_illustrations)} illustrations for workflow {workflow_id}")
        
        return {
            "workflow_id": workflow_id,
            "final_illustrations": final_illustrations,
            "book_ready": len(final_illustrations) == 12
        }
    
    # Helper methods for KG storage
    async def _store_prompt_in_kg(self, workflow_id: str, page_num: int, prompt: str):
        """Store illustration prompt in KG."""
        uri = f"http://example.org/workflow/{workflow_id}/prompt/page/{page_num}"
        await self.kg_manager.add_triple(
            uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/ontology#IllustrationPrompt"
        )
        await self.kg_manager.add_triple(uri, "http://example.org/ontology#promptText", prompt)
    
    async def _store_illustration_in_kg(self, workflow_id: str, page_num: int, task_id: str, urls: List[str]):
        """Store generated illustration in KG."""
        uri = f"http://example.org/workflow/{workflow_id}/illustration/page/{page_num}"
        await self.kg_manager.add_triple(
            uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/ontology#GeneratedIllustration"
        )
        await self.kg_manager.add_triple(uri, "http://example.org/ontology#taskId", task_id)
        await self.kg_manager.add_triple(uri, "http://example.org/ontology#imageUrls", json.dumps(urls))
    
    async def _store_evaluation_in_kg(self, workflow_id: str, page_num: int, evaluations: List, best: Dict):
        """Store evaluation results in KG."""
        uri = f"http://example.org/workflow/{workflow_id}/evaluation/page/{page_num}"
        await self.kg_manager.add_triple(
            uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/ontology#IllustrationEvaluation"
        )
        await self.kg_manager.add_triple(uri, "http://example.org/ontology#evaluations", json.dumps(evaluations))
        await self.kg_manager.add_triple(uri, "http://example.org/ontology#bestImage", json.dumps(best))
    
    async def _store_upscale_in_kg(self, workflow_id: str, page_num: int, upscale_result: Dict):
        """Store upscaled image in KG."""
        uri = f"http://example.org/workflow/{workflow_id}/upscale/page/{page_num}"
        await self.kg_manager.add_triple(
            uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/ontology#UpscaledIllustration"
        )
        await self.kg_manager.add_triple(uri, "http://example.org/ontology#upscaledUrl", upscale_result["url"])
