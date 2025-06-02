import pytest
from agents.domain.code_review_agent import CodeReviewAgent
from agents.core.capability_types import CapabilityType
import ast

@pytest.fixture
async def code_review_agent():
    agent = CodeReviewAgent()
    await agent.initialize()
    return agent

@pytest.mark.asyncio
async def test_agent_initialization(code_review_agent):
    """Test agent initialization and capabilities."""
    assert code_review_agent.agent_id == "code_review_agent"
    capabilities = await code_review_agent.capabilities
    assert len(capabilities) == 5
    assert any(cap.type == CapabilityType.CODE_REVIEW for cap in capabilities)
    assert any(cap.type == CapabilityType.STATIC_ANALYSIS for cap in capabilities)

@pytest.mark.asyncio
async def test_code_review_simple_function(code_review_agent):
    """Test review of a simple function."""
    code = """
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b
"""
    result = await code_review_agent._perform_review({'code': code, 'id': 'test1'})
    
    assert result['status'] == 'completed'
    assert len(result['findings']) == 0  # No issues in simple function
    assert result['metrics']['complexity_score'] == 1.0  # Base complexity
    assert result['metrics']['quality_score'] == 100  # Perfect score
    assert result['metrics']['maintainability_score'] == 100  # Perfect score

@pytest.mark.asyncio
async def test_code_review_complex_function(code_review_agent):
    """Test review of a complex function with issues."""
    code = """
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            if item % 2 == 0:
                if item < 100:
                    result.append(item)
    return result
"""
    result = await code_review_agent._perform_review({'code': code, 'id': 'test2'})
    
    assert result['status'] == 'completed'
    assert len(result['findings']) > 0  # Should find issues
    assert any(f['type'] == 'complexity' for f in result['findings'])
    assert any(f['type'] == 'type_safety' for f in result['findings'])
    assert result['metrics']['complexity_score'] > 1.0  # Higher complexity
    assert result['metrics']['quality_score'] < 100  # Lower quality score

@pytest.mark.asyncio
async def test_code_review_with_syntax_error(code_review_agent):
    """Test review of code with syntax error."""
    code = """
def broken_function(
    return 42
"""
    result = await code_review_agent._perform_review({'code': code, 'id': 'test3'})
    
    assert result['status'] == 'error'
    assert 'error' in result
    assert 'Syntax error' in result['error']
    assert len(result['findings']) == 0
    assert len(result['recommendations']) == 1

@pytest.mark.asyncio
async def test_complexity_analysis(code_review_agent):
    """Test complexity analysis functionality."""
    code = """
def complex_function(x):
    if x > 0:
        if x < 10:
            if x % 2 == 0:
                return True
    return False
"""
    tree = ast.parse(code)
    findings = await code_review_agent._analyze_complexity(tree)
    
    assert len(findings) > 0
    assert any(f['type'] == 'complexity' for f in findings)
    assert any('exceeds threshold' in f['message'] for f in findings)

@pytest.mark.asyncio
async def test_code_quality_analysis(code_review_agent):
    """Test code quality analysis functionality."""
    code = """
def undocumented_function(x):
    return x * 2
"""
    findings = await code_review_agent._analyze_code_quality(code)
    
    assert len(findings) > 0
    assert any(f['type'] == 'documentation' for f in findings)
    assert any(f['type'] == 'type_safety' for f in findings)

@pytest.mark.asyncio
async def test_pattern_analysis(code_review_agent):
    """Test pattern analysis functionality."""
    code = """
def BadlyNamedFunction():
    if True:
        if False:
            if 1 == 1:
                pass
"""
    findings = await code_review_agent._analyze_patterns(code)
    
    assert len(findings) > 0
    assert any(f['type'] == 'naming' for f in findings)
    assert any(f['type'] == 'pattern' for f in findings)

@pytest.mark.asyncio
async def test_recommendation_generation(code_review_agent):
    """Test recommendation generation."""
    findings = [
        {
            'type': 'complexity',
            'severity': 'warning',
            'message': 'Complex function',
            'recommendation': 'Break down into smaller functions'
        },
        {
            'type': 'documentation',
            'severity': 'info',
            'message': 'Missing docstring',
            'recommendation': 'Add function documentation'
        }
    ]
    
    recommendations = await code_review_agent._generate_recommendations(findings)
    
    assert len(recommendations) == 2
    assert 'Break down into smaller functions' in recommendations
    assert 'Add function documentation' in recommendations

@pytest.mark.asyncio
async def test_scoring_functions(code_review_agent):
    """Test scoring calculation functions."""
    findings = [
        {'severity': 'error', 'type': 'syntax'},
        {'severity': 'warning', 'type': 'complexity'},
        {'severity': 'info', 'type': 'style'}
    ]
    
    quality_score = await code_review_agent._calculate_quality_score(findings)
    maintainability_score = await code_review_agent._calculate_maintainability_score(findings)
    
    assert 0 <= quality_score <= 100
    assert 0 <= maintainability_score <= 100
    assert quality_score < maintainability_score  # Maintainability should be higher due to different weights 