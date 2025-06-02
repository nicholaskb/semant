from typing import Dict, Any, List, Optional
from agents.core.scientific_swarm_agent import ScientificSwarmAgent
from agents.core.capability_types import Capability, CapabilityType
from agents.domain.code_review_agent import CodeReviewAgent
from loguru import logger
import asyncio
import os
import json
from datetime import datetime

class TestSwarmCoordinator(ScientificSwarmAgent):
    """
    Coordinates test fixes across the swarm.
    Capabilities:
    - Test analysis
    - Test fix coordination
    - Progress tracking
    - Peer review management
    """
    
    def __init__(
        self,
        agent_id: str = "test_swarm_coordinator",
        config: Optional[Dict[str, Any]] = None
    ):
        capabilities = {
            Capability(CapabilityType.TEST_ANALYSIS, "1.0"),
            Capability(CapabilityType.COORDINATION, "1.0"),
            Capability(CapabilityType.PROGRESS_TRACKING, "1.0"),
            Capability(CapabilityType.PEER_REVIEW, "1.0")
        }
        super().__init__(agent_id, "test_coordinator", capabilities, config)
        self.code_review_agent = CodeReviewAgent(config=config)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
            
    async def initialize(self) -> None:
        """Initialize the test swarm coordinator."""
        await super().initialize()
        await self.code_review_agent.initialize()
        self.logger.info("Test Swarm Coordinator initialized")
        
        # Register in knowledge graph
        if self.knowledge_graph:
            await self.knowledge_graph.update_graph({
                f"agent:{self.agent_id}": {
                    "rdf:type": "swarm:TestSwarmCoordinator",
                    "swarm:hasStatus": "swarm:Active",
                    "swarm:hasCapability": [
                        "swarm:TestAnalysisCapability",
                        "swarm:CoordinationCapability",
                        "swarm:ProgressTrackingCapability",
                        "swarm:PeerReviewCapability"
                    ]
                }
            })
            
    async def fix_all_tests(self, test_dir: str) -> Dict[str, Any]:
        """Coordinate fixing all tests in the given directory."""
        try:
            # Find all test files
            test_files = await self._find_test_files(test_dir)
            total_tests = len(test_files)
            
            # Initialize progress tracking
            progress = {
                'total_tests': total_tests,
                'fixed_tests': 0,
                'failed_tests': 0,
                'in_progress': 0,
                'start_time': datetime.now().isoformat()
            }
            
            # Update knowledge graph with initial progress
            if self.knowledge_graph:
                await self.knowledge_graph.update_graph({
                    "swarm:test_fix_progress": {
                        "rdf:type": "swarm:TestFixProgress",
                        "swarm:totalTests": str(total_tests),
                        "swarm:fixedTests": "0",
                        "swarm:failedTests": "0",
                        "swarm:inProgress": "0",
                        "swarm:startTime": progress['start_time']
                    }
                })
            
            # Process tests in parallel
            tasks = []
            for test_file in test_files:
                task = asyncio.create_task(self._process_test_file(test_file, progress))
                tasks.append(task)
                
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update final progress
            progress['end_time'] = datetime.now().isoformat()
            if self.knowledge_graph:
                await self.knowledge_graph.update_graph({
                    "swarm:test_fix_progress": {
                        "swarm:endTime": progress['end_time'],
                        "swarm:status": "completed"
                    }
                })
                
            return {
                'status': 'completed',
                'progress': progress,
                'results': results
            }
            
        except Exception as e:
            self.logger.error(f"Error fixing tests: {str(e)}")
            if self.knowledge_graph:
                await self.knowledge_graph.update_graph({
                    "swarm:test_fix_progress": {
                        "swarm:status": "error",
                        "swarm:error": str(e)
                    }
                })
            raise
            
    async def _find_test_files(self, test_dir: str) -> List[str]:
        """Find all test files in the given directory."""
        test_files = []
        for root, _, files in os.walk(test_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(os.path.join(root, file))
        return test_files
        
    async def _process_test_file(self, test_file: str, progress: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single test file."""
        try:
            # Read test file
            with open(test_file, 'r') as f:
                test_code = f.read()
                
            # Review test code
            review_result = await self.code_review_agent.process_message({
                'type': 'review_request',
                'code': test_code,
                'file': test_file
            })
            
            if review_result['status'] == 'error':
                # Test has syntax errors, try to fix
                fixed_code = await self._fix_test_with_openai(test_file, test_code, review_result)
                if fixed_code:
                    # Write fixed code back to file
                    with open(test_file, 'w') as f:
                        f.write(fixed_code)
                    progress['fixed_tests'] += 1
                else:
                    progress['failed_tests'] += 1
            else:
                # Test passed review
                progress['fixed_tests'] += 1
                
            # Update progress in knowledge graph
            if self.knowledge_graph:
                await self.knowledge_graph.update_graph({
                    "swarm:test_fix_progress": {
                        "swarm:fixedTests": str(progress['fixed_tests']),
                        "swarm:failedTests": str(progress['failed_tests']),
                        "swarm:inProgress": str(progress['total_tests'] - progress['fixed_tests'] - progress['failed_tests'])
                    }
                })
                
            return {
                'file': test_file,
                'status': 'fixed' if review_result['status'] == 'completed' else 'needs_fix',
                'review': review_result
            }
            
        except Exception as e:
            self.logger.error(f"Error processing test file {test_file}: {str(e)}")
            progress['failed_tests'] += 1
            return {
                'file': test_file,
                'status': 'error',
                'error': str(e)
            }
            
    async def _fix_test_with_openai(self, test_file: str, test_code: str, review_result: Dict[str, Any]) -> Optional[str]:
        """Use OpenAI to fix a test file."""
        try:
            import openai
            
            # Prepare prompt for OpenAI
            prompt = f"""Fix the following Python test file based on these findings:

            File: {test_file}
            
            Findings:
            {json.dumps(review_result['findings'], indent=2)}
            
            Original code:
            {test_code}
            
            Please provide the fixed code that addresses all findings.
            """
            
            # Call OpenAI API
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a Python test expert. Fix the test code provided."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            # Extract fixed code from response
            fixed_code = response.choices[0].message.content.strip()
            
            # Verify the fix
            try:
                compile(fixed_code, '<string>', 'exec')
                return fixed_code
            except SyntaxError:
                return None
                
        except Exception as e:
            self.logger.error(f"Error fixing test with OpenAI: {str(e)}")
            return None 