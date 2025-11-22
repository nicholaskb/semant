from typing import Dict, Any, List, Optional, Set
from agents.core.scientific_swarm_agent import ScientificSwarmAgent
from agents.core.capability_types import Capability, CapabilityType
from agents.core.message_types import AgentMessage
from loguru import logger
import ast
import re
import uuid
from datetime import datetime

class CodeReviewAgent(ScientificSwarmAgent):
    """
    Specialized agent for code review and analysis.
    Capabilities:
    - Code review
    - Static analysis
    - Code quality assessment
    - Code smell detection
    - Pattern analysis
    """
    
    def __init__(
        self,
        agent_id: str = "code_review_agent",
        knowledge_graph: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        capabilities = {
            Capability(CapabilityType.CODE_REVIEW, "1.0"),
            Capability(CapabilityType.STATIC_ANALYSIS, "1.0"),
            Capability(CapabilityType.CODE_QUALITY, "1.0"),
            Capability(CapabilityType.CODE_SMELL_DETECTION, "1.0"),
            Capability(CapabilityType.PATTERN_ANALYSIS, "1.0")
        }
        super().__init__(
            agent_id=agent_id,
            agent_type="code_review",
            capabilities=capabilities,
            knowledge_graph=knowledge_graph,
            config=config
        )
        self.review_patterns = {
            'complexity': re.compile(r'if.*if.*if|for.*for.*for|while.*while'),
            'naming': re.compile(r'[a-z][A-Z]|[A-Z]{2,}'),
            'docstring': re.compile(r'""".*?"""', re.DOTALL),
            'type_hint': re.compile(r':\s*[A-Za-z_][A-Za-z0-9_]*(\[.*?\])?'),
            'error_handling': re.compile(r'try:|except:|finally:'),
            'logging': re.compile(r'logger\.|logging\.'),
            'test': re.compile(r'def test_|class Test')
        }
        
    async def initialize(self) -> None:
        """Initialize the code review agent."""
        await super().initialize()
        self.logger.info("Code Review Agent initialized")
        
        # Register agent in knowledge graph
        if self.knowledge_graph:
            await self.knowledge_graph.update_graph({
                f"agent:{self.agent_id}": {
                    "rdf:type": "swarm:CodeReviewAgent",
                    "swarm:hasStatus": "swarm:Active",
                    "swarm:hasCapability": [
                        "swarm:CodeReviewCapability",
                        "swarm:StaticAnalysisCapability",
                        "swarm:CodeQualityCapability",
                        "swarm:CodeSmellDetectionCapability",
                        "swarm:PatternAnalysisCapability"
                    ]
                }
            })
            
    async def _perform_review(self, code_artifact: Dict[str, Any]) -> Dict[str, Any]:
        """Perform detailed code review."""
        try:
            code = code_artifact.get('code', '')
            review_id = code_artifact.get('id', 'unknown')
            if not code:
                raise ValueError("No code provided for review")
                
            # Parse code into AST
            try:
                tree = ast.parse(code)
            except SyntaxError as e:
                review_result = {
                    'status': 'error',
                    'error': f'Syntax error: {str(e)}',
                    'findings': [],
                    'recommendations': ['Fix syntax errors before proceeding with review']
                }
                # Write error result to knowledge graph
                if self.knowledge_graph:
                    await self.knowledge_graph.update_graph({
                        f"review:{review_id}": {
                            "rdf:type": "review:CodeReview",
                            "review:reviewedBy": f"agent:{self.agent_id}",
                            "review:timestamp": datetime.now().isoformat(),
                            "review:status": "error",
                            "review:error": review_result['error']
                        }
                    })
                return review_result
                
            # Perform various analyses
            findings = []
            recommendations = []
            
            # Complexity analysis
            complexity_findings = await self._analyze_complexity(tree)
            findings.extend(complexity_findings)
            
            # Code quality analysis
            quality_findings = await self._analyze_code_quality(code)
            findings.extend(quality_findings)
            
            # Pattern analysis
            pattern_findings = await self._analyze_patterns(code)
            findings.extend(pattern_findings)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(findings)
            
            review_result = {
                'status': 'completed',
                'timestamp': datetime.now().isoformat(),
                'findings': findings,
                'recommendations': recommendations,
                'metrics': {
                    'complexity_score': await self._calculate_complexity_score(tree),
                    'quality_score': await self._calculate_quality_score(findings),
                    'maintainability_score': await self._calculate_maintainability_score(findings)
                }
            }
            
            # Update knowledge graph with review results
            if self.knowledge_graph:
                await self.knowledge_graph.update_graph({
                    f"review:{review_id}": {
                        "rdf:type": "review:CodeReview",
                        "review:reviewedBy": f"agent:{self.agent_id}",
                        "review:timestamp": review_result['timestamp'],
                        "review:status": review_result['status'],
                        "review:complexityScore": str(review_result['metrics']['complexity_score']),
                        "review:qualityScore": str(review_result['metrics']['quality_score']),
                        "review:maintainabilityScore": str(review_result['metrics']['maintainability_score'])
                    }
                })
            
            # Send SMS notification on review completion
            try:
                quality_score = review_result['metrics']['quality_score']
                findings_count = len(review_result['findings'])
                sms_msg = f"Code review complete: {review_id[:12]}... | Quality: {quality_score:.1f}/100 | Findings: {findings_count}"
                await self.send_sms_notification(sms_msg)
            except Exception as sms_err:
                self.logger.warning(f"SMS notification failed: {sms_err}")
            
            return review_result
            
        except Exception as e:
            self.logger.error(f"Error performing code review: {str(e)}")
            # Write error to knowledge graph if possible
            if self.knowledge_graph:
                await self.knowledge_graph.update_graph({
                    f"review:{code_artifact.get('id', 'unknown')}": {
                        "rdf:type": "review:CodeReview",
                        "review:reviewedBy": f"agent:{self.agent_id}",
                        "review:timestamp": datetime.now().isoformat(),
                        "review:status": "error",
                        "review:error": str(e)
                    }
                })
            raise
            
    async def _analyze_complexity(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Analyze code complexity using AST."""
        findings = []
        
        # Analyze function complexity
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = await self._calculate_function_complexity(node)
                if complexity > 3:  # Lowered threshold for complex functions
                    findings.append({
                        'type': 'complexity',
                        'severity': 'warning',
                        'location': f'Function: {node.name}',
                        'message': f'Function complexity ({complexity}) exceeds threshold',
                        'recommendation': 'Consider breaking down into smaller functions'
                    })
                    
        return findings
        
    async def _analyze_code_quality(self, code: str) -> List[Dict[str, Any]]:
        """Analyze code quality using pattern matching and AST."""
        findings = []
        import ast
        try:
            tree = ast.parse(code)
        except Exception:
            tree = None
        # Check for docstrings
        if not self.review_patterns['docstring'].search(code):
            findings.append({
                'type': 'documentation',
                'severity': 'info',
                'location': 'File level',
                'message': 'Missing module docstring',
                'recommendation': 'Add module-level documentation'
            })
        # Check for type hints using AST
        missing_type_hints = False
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check arguments
                    for arg in node.args.args:
                        if arg.arg != 'self' and arg.annotation is None:
                            missing_type_hints = True
                    # Check return type
                    if node.returns is None:
                        missing_type_hints = True
        if missing_type_hints:
            findings.append({
                'type': 'type_safety',
                'severity': 'warning',
                'location': 'File level',
                'message': 'Missing type hints',
                'recommendation': 'Add type hints to function parameters and return values'
            })
        # Check for error handling, but suppress for trivial functions (single return statement)
        if not self.review_patterns['error_handling'].search(code):
            if tree:
                trivial = True
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        stmts = [n for n in node.body if not isinstance(n, ast.Expr)]
                        if not (len(stmts) == 1 and isinstance(stmts[0], ast.Return)):
                            trivial = False
                if not trivial:
                    findings.append({
                        'type': 'error_handling',
                        'severity': 'warning',
                        'location': 'File level',
                        'message': 'No error handling found',
                        'recommendation': 'Add try-except blocks for error handling'
                    })
            else:
                findings.append({
                    'type': 'error_handling',
                    'severity': 'warning',
                    'location': 'File level',
                    'message': 'No error handling found',
                    'recommendation': 'Add try-except blocks for error handling'
                })
        return findings
        
    async def _analyze_patterns(self, code: str) -> List[Dict[str, Any]]:
        """Analyze code patterns and anti-patterns using AST for nested ifs."""
        findings = []
        
        try:
            tree = ast.parse(code)
        except Exception:
            tree = None
        # Check for complex nested conditions using AST
        if tree:
            def count_nested_ifs(node, depth=0):
                max_depth = depth
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, ast.If):
                        max_depth = max(max_depth, count_nested_ifs(child, depth+1))
                    else:
                        max_depth = max(max_depth, count_nested_ifs(child, depth))
                return max_depth
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if count_nested_ifs(node) >= 3:
                        findings.append({
                            'type': 'pattern',
                            'severity': 'warning',
                            'location': f'Function: {node.name}',
                            'message': 'Complex nested conditions detected',
                            'recommendation': 'Consider simplifying logic or extracting to helper functions'
                        })
        # Check for naming conventions (keep regex)
        if self.review_patterns['naming'].search(code):
            findings.append({
                'type': 'naming',
                'severity': 'info',
                'location': 'Variable/Function names',
                'message': 'Inconsistent naming convention detected',
                'recommendation': 'Follow PEP 8 naming conventions'
            })
        return findings
        
    async def _generate_recommendations(self, findings: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on findings."""
        recommendations = set()
        
        for finding in findings:
            if 'recommendation' in finding:
                recommendations.add(finding['recommendation'])
                
        return list(recommendations)
        
    async def _calculate_function_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, ast.ExceptHandler)):
                complexity += 1
                
        return complexity
        
    async def _calculate_complexity_score(self, tree: ast.AST) -> float:
        """Calculate overall complexity score."""
        total_complexity = 0
        function_count = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                total_complexity += await self._calculate_function_complexity(node)
                function_count += 1
                
        return total_complexity / max(function_count, 1)
        
    async def _calculate_quality_score(self, findings: List[Dict[str, Any]]) -> float:
        """Calculate code quality score based on findings."""
        severity_weights = {
            'error': 1.0,
            'warning': 0.7,
            'info': 0.3
        }
        
        total_weight = 0
        for finding in findings:
            total_weight += severity_weights.get(finding.get('severity', 'info'), 0)
            
        # Convert to a 0-100 scale
        return max(0, 100 - (total_weight * 10))
        
    async def _calculate_maintainability_score(self, findings: List[Dict[str, Any]]) -> float:
        """Calculate maintainability score based on findings."""
        # Similar to quality score but with different weights
        severity_weights = {
            'error': 1.0,
            'warning': 0.5,
            'info': 0.2
        }
        
        total_weight = 0
        for finding in findings:
            total_weight += severity_weights.get(finding.get('severity', 'info'), 0)
            
        # Convert to a 0-100 scale
        return max(0, 100 - (total_weight * 8))

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages - REQUIRED IMPLEMENTATION."""
        try:
            # Process code review requests
            if hasattr(message, 'content') and isinstance(message.content, dict):
                if message.content.get('type') == 'review_request':
                    # Perform code review
                    review_result = await self._perform_review(message.content)
                    response_content = {
                        'type': 'review_response',
                        'review': review_result
                    }
                else:
                    response_content = f"Code Review Agent {self.agent_id} processed: {message.content}"
            else:
                response_content = f"Code Review Agent {self.agent_id} processed: {message.content}"
            
            return AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=response_content,
                message_type=getattr(message, 'message_type', 'response'),
                timestamp=datetime.now()
            )
        except Exception as e:
            # Error handling
            return AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=f"Error processing message: {str(e)}",
                message_type="error",
                timestamp=datetime.now()
            ) 