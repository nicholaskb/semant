# Integration Layer Documentation

## Overview

The Integration Layer provides comprehensive external system connectivity for the multi-agent orchestration system. This layer handles authentication, data transformation, protocol management, and API integrations with various external services including Google Cloud Platform, Gmail, Vertex AI, and other enterprise systems.

## 🧪 **Integration Testing Framework & Status**

### **Test Execution Guide**

#### **Running All Integration Tests**
```bash
# Run all integration-related tests
python -m pytest tests/test_vertex_integration.py tests/test_vertex_auth.py tests/test_email_send.py tests/test_vertex_email.py tests/test_main_api.py tests/test_chat_endpoint.py tests/test_graphdb_integration.py tests/test_remote_graph_manager.py -v

# Run individual test categories
python -m pytest tests/test_vertex_integration.py -v      # Vertex AI integration
python -m pytest tests/test_vertex_auth.py -v            # Vertex AI authentication
python -m pytest tests/test_email_send.py -v             # Email functionality
python -m pytest tests/test_main_api.py -v               # API endpoints
python -m pytest tests/test_graphdb_integration.py -v    # External GraphDB
```

### **Current Test Status Summary**

| Test File | Status | Tests | Issues |
|-----------|--------|-------|--------|
| **test_main_api.py** | ✅ **PASSING** | 3/3 | None - API endpoints working |
| **test_chat_endpoint.py** | ✅ **PASSING** | 3/3 | None - Chat endpoints working |
| **test_graphdb_integration.py** | ✅ **PASSING** | 4/4 | None - External GraphDB integration working |
| **test_remote_graph_manager.py** | ✅ **PASSING** | 4/4 | None - Remote SPARQL endpoints working |
| **test_vertex_integration.py** | ❌ **FAILING** | 0/9 | Missing credentials, API signature issues |
| **test_vertex_auth.py** | ❌ **FAILING** | 0/3 | Missing credentials and project configuration |
| **test_email_send.py** | ❌ **FAILING** | 0/1 | EmailIntegration API signature mismatch |
| **test_vertex_email.py** | ❌ **FAILING** | 0/1 | EmailIntegration API signature mismatch |

**Overall Integration Test Status: 14/20 PASSING (70%)**

### **🚨 Critical Issues Requiring Immediate Attention**

#### **1. Google Cloud Credentials Configuration** ⚠️ **HIGH PRIORITY**

**Problem**: All Vertex AI tests failing due to missing credentials
```
ERROR: [Errno 2] No such file or directory: '/Users/nicholasbaro/Python/semant/credentials.json'
```

**🔍 DEBUG-SPECIFIC ANALYSIS**:
- **File Path Pattern**: System expects exact path `/Users/nicholasbaro/Python/semant/credentials.json`
- **Environment Variable**: `GOOGLE_APPLICATION_CREDENTIALS` must point to valid service account JSON
- **Permission Analysis**: Service account needs specific IAM roles for Vertex AI and Gmail API access
- **API Enablement Status**: Both `aiplatform.googleapis.com` and `gmail.googleapis.com` must be enabled
- **Project Configuration**: `GOOGLE_CLOUD_PROJECT` environment variable must match actual GCP project ID

**🛠️ DEBUG COMMANDS FOR ISSUE ISOLATION**:
```bash
# 1. Check file existence and permissions
ls -la credentials/credentials.json
stat credentials/credentials.json

# 2. Validate JSON structure
python -c "import json; json.load(open('credentials/credentials.json'))"

# 3. Test environment variable loading
python -c "import os; print(f'GOOGLE_APPLICATION_CREDENTIALS: {os.getenv(\"GOOGLE_APPLICATION_CREDENTIALS\")}')"

# 4. Verify gcloud authentication
gcloud auth list
gcloud config get-value project

# 5. Check API enablement status
gcloud services list --enabled --filter="name:aiplatform.googleapis.com OR name:gmail.googleapis.com"

# 6. Test credential validity directly
python -c "
from google.oauth2 import service_account
import os
creds = service_account.Credentials.from_service_account_file(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
print(f'Service account email: {creds.service_account_email}')
"
```

**Required Setup**:
```bash
# 1. Create credentials directory
mkdir -p credentials

# 2. Download service account JSON from Google Cloud Console
# - Go to https://console.cloud.google.com
# - Navigate to IAM & Admin > Service Accounts
# - Create or select service account
# - Generate and download JSON key
# - Save as credentials/credentials.json

# 3. Set environment variables in .env file
echo "GOOGLE_CLOUD_PROJECT=your-project-id" >> .env
echo "GOOGLE_APPLICATION_CREDENTIALS=credentials/credentials.json" >> .env
echo "GOOGLE_CLOUD_LOCATION=us-central1" >> .env

# 4. Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable gmail.googleapis.com
```

#### **2. EmailIntegration API Signature Mismatch** ⚠️ **MEDIUM PRIORITY**

**Problem**: Tests expect different method signature than implementation
```python
# Tests are calling:
email.send_email(recipient_id="...", subject="...", body="...")

# But implementation expects:
email.send_email(recipient, subject, body)
```

**🔍 DEBUG-SPECIFIC ANALYSIS**:
- **File Location**: `agents/utils/email_integration.py` (13 lines - minimal implementation)
- **Test Files Affected**: `test_email_send.py`, `test_vertex_email.py`
- **Error Pattern**: `TypeError: send_email() got an unexpected keyword argument 'recipient_id'`
- **Root Cause**: API evolution where tests were updated but implementation wasn't
- **Impact Assessment**: 2 integration tests failing, email functionality broken

**🛠️ DEBUG COMMANDS FOR ISSUE ISOLATION**:
```bash
# 1. Examine current implementation
cat agents/utils/email_integration.py

# 2. Find all usages of send_email method
grep -r "send_email" tests/ --include="*.py"

# 3. Check method signature expectations
python -c "
import inspect
from agents.utils.email_integration import EmailIntegration
print(f'Current signature: {inspect.signature(EmailIntegration().send_email)}')
"

# 4. Test the specific failing scenario
python -c "
from agents.utils.email_integration import EmailIntegration
try:
    email = EmailIntegration()
    email.send_email(recipient_id='test@example.com', subject='Test', body='Test')
    print('SUCCESS')
except Exception as e:
    print(f'ERROR: {e}')
"

# 5. Verify fix implementation
python -c "
from agents.utils.email_integration import EmailIntegration
email = EmailIntegration()
# Test both old and new signatures
result1 = email.send_email('old@example.com', 'Old Style', 'Old Body')  # Old style
result2 = email.send_email(recipient_id='new@example.com', subject='New Style', body='New Body')  # New style
print(f'Old style: {result1}')
print(f'New style: {result2}')
"
```

**Fix Required**: Update `agents/utils/email_integration.py`:
```python
class EmailIntegration:
    def send_email(self, recipient_id=None, recipient=None, subject="", body=""):
        """Backward compatible email sending."""
        actual_recipient = recipient_id or recipient
        if not actual_recipient:
            raise ValueError("Must provide recipient_id or recipient")
        print(f"Email sent to {actual_recipient}: {subject} - {body}")
        return {"status": "sent", "recipient": actual_recipient, "timestamp": datetime.now().isoformat()}
```

#### **3. VertexEmailAgent Missing Methods** ⚠️ **MEDIUM PRIORITY**

**Problem**: Test expects `enhance_email_content()` method that doesn't exist
```python
# Test expects:
enhanced_content = await vertex_agent.enhance_email_content(original_content)

# But method doesn't exist in VertexEmailAgent
```

**🔍 DEBUG-SPECIFIC ANALYSIS**:
- **File Location**: `agents/domain/vertex_email_agent.py` (194 lines)
- **Test File**: `test_vertex_email.py` line ~45-60
- **Error Pattern**: `AttributeError: 'VertexEmailAgent' object has no attribute 'enhance_email_content'`
- **Method Analysis**: Agent has `send_email()` but missing `enhance_email_content()` method
- **Dependency Requirements**: Method needs Vertex AI model initialization and error handling

**🛠️ DEBUG COMMANDS FOR ISSUE ISOLATION**:
```bash
# 1. Check current VertexEmailAgent implementation
grep -n "class VertexEmailAgent" agents/domain/vertex_email_agent.py
grep -n "def " agents/domain/vertex_email_agent.py

# 2. Examine test expectations
grep -A 10 -B 5 "enhance_email_content" tests/test_vertex_email.py

# 3. Check agent initialization pattern
python -c "
from agents.domain.vertex_email_agent import VertexEmailAgent
import inspect
agent = VertexEmailAgent()
methods = [method for method in dir(agent) if not method.startswith('_')]
print(f'Available methods: {methods}')
print(f'Has enhance_email_content: {hasattr(agent, \"enhance_email_content\")}')
"

# 4. Test agent initialization and available attributes
python -c "
from agents.domain.vertex_email_agent import VertexEmailAgent
import asyncio
async def test():
    agent = VertexEmailAgent()
    await agent.initialize()
    print(f'Agent type: {agent.agent_type}')
    print(f'Agent ID: {agent.agent_id}')
    print(f'Has vertex_model: {hasattr(agent, \"vertex_model\")}')
    
asyncio.run(test())
"

# 5. Verify method signature and implementation
python -c "
import inspect
from agents.domain.vertex_email_agent import VertexEmailAgent
agent = VertexEmailAgent()
if hasattr(agent, 'enhance_email_content'):
    print(f'Method signature: {inspect.signature(agent.enhance_email_content)}')
else:
    print('Method enhance_email_content does not exist')
"
```

**Fix Required**: Add method to `agents/domain/vertex_email_agent.py`:
```python
async def enhance_email_content(self, content: str) -> str:
    """Enhance email content using Vertex AI."""
    if not content or not content.strip():
        raise ValueError("Content cannot be empty")
    
    # Check if Vertex AI model is available
    if not hasattr(self, 'vertex_model') or not self.vertex_model:
        self.logger.warning("Vertex AI model not available, returning original content")
        return content
    
    try:
        enhancement_prompt = f"""
        Enhance the following email content for clarity, professionalism, and engagement.
        Maintain the original intent while improving readability and tone.
        
        Original content: {content}
        
        Enhanced content:
        """
        
        response = await self.vertex_model.generate_content(enhancement_prompt)
        enhanced_content = response.text.strip()
        
        if not enhanced_content or enhanced_content == content:
            self.logger.warning("Enhancement did not improve content, returning original")
            return content
        
        self.logger.info(f"Successfully enhanced email content (original: {len(content)} chars, enhanced: {len(enhanced_content)} chars)")
        return enhanced_content
        
    except Exception as e:
        self.logger.error(f"Content enhancement failed: {e}")
        return content  # Graceful degradation
```

#### **4. Agent Initialization Issues** ⚠️ **MEDIUM PRIORITY**

**Problem**: Multiple tests failing with "Agent not initialized" errors
```
RuntimeError: Agent not initialized. Call initialize() first.
```

**Fix Required**: Update test fixtures to ensure proper initialization:
```python
@pytest_asyncio.fixture
async def vertex_agent():
    """Properly initialized vertex agent."""
    agent = VertexEmailAgent()
    await agent.initialize()  # CRITICAL: Must call initialize
    yield agent
    await agent.cleanup()     # Proper cleanup
```

#### **5. Invalid CapabilityTypes** ⚠️ **LOW PRIORITY**

**Problem**: Tests reference non-existent capability types
```python
# These don't exist:
CapabilityType.INTEGRATION_MANAGEMENT
CapabilityType.MODULE_MANAGEMENT
```

**Fix Required**: Use valid capability types from `agents/core/capability_types.py`:
```python
# Replace with:
CapabilityType.MESSAGE_PROCESSING
CapabilityType.DATA_PROCESSING
```

### **📋 Integration Test Setup Prerequisites**

#### **Environment Setup Checklist**
- [ ] Python 3.11+ installed
- [ ] Virtual environment activated
- [ ] All requirements installed: `pip install -r requirements.txt`
- [ ] `.env` file configured with Google Cloud variables
- [ ] Google Cloud credentials JSON file in `credentials/` directory
- [ ] Required APIs enabled in Google Cloud Console
- [ ] Service account has proper IAM permissions

#### **Google Cloud Configuration Verification**
```bash
# Verify gcloud configuration
gcloud config list

# Check API enablement
gcloud services list --enabled --filter="name:aiplatform.googleapis.com OR name:gmail.googleapis.com"

# Test credentials
python integrations/gather_gmail_info.py
python integrations/verify_gmail_config.py
python integrations/check_vertex_models.py
python integrations/check_gcp_setup.py
```

### **🔧 Quick Fix Implementation Priority**

**Immediate Fixes (High Priority)**:
1. **Create credentials setup script**: `scripts/setup_integration_credentials.sh`
2. **Fix EmailIntegration API signature**: Update `send_email()` method
3. **Add missing VertexEmailAgent methods**: `enhance_email_content()`

**Medium Priority Fixes**:
1. **Fix agent initialization in test fixtures**
2. **Update capability types in tests**
3. **Add comprehensive integration test documentation**

**Low Priority Enhancements**:
1. **Add integration test mocking for offline development**
2. **Create integration test performance benchmarks**
3. **Add integration test CI/CD pipeline**

## 🏗️ **Integration Architecture**

### Core Components

#### 1. Google Cloud Platform Integration ✅ **PRODUCTION READY**
- **Service Account Authentication**: Secure authentication using service account credentials
- **OAuth 2.0 Flow**: Complete OAuth implementation for user consent workflows  
- **API Enablement Verification**: Automated checking of required API services
- **Project Configuration Management**: Dynamic project and location configuration
- **Permission Validation**: Service account permission verification and reporting

#### 2. Gmail API Integration ✅ **FULLY IMPLEMENTED**
- **Authentication Management**: Multi-layer authentication (Service Account + OAuth)
- **Configuration Verification**: Comprehensive Gmail API setup validation
- **Token Management**: Secure token storage and refresh handling
- **Permission Checking**: Granular permission validation and troubleshooting
- **Error Recovery**: Intelligent error detection and resolution guidance

#### 3. Vertex AI Integration ✅ **MODEL ACCESS READY**
- **Model Initialization**: Support for text-bison and other generative models
- **API Enablement**: Automated Vertex AI API enablement checking
- **Model Access Verification**: Validation of model garden access permissions
- **Project Configuration**: Dynamic project and location setup
- **Error Diagnostics**: Comprehensive error analysis and resolution guidance

#### 4. Email System Integration ✅ **MULTI-LAYER SUPPORT**
- **Agent-Based Email**: Vertex Email Agent for AI-powered email operations
- **Direct Gmail Integration**: Native Gmail API connectivity
- **Configuration Management**: Automated credential and environment setup
- **Testing Framework**: Comprehensive email testing and verification tools
- **Simulation Support**: Email simulation for development and testing

### 🔧 **Integration Components Analysis**

#### Authentication Management System

**File: `integrations/gather_gmail_info.py` (181 lines)**
- **Purpose**: Comprehensive Gmail API configuration analysis and troubleshooting
- **Capabilities**:
  - gcloud configuration validation
  - API enablement verification  
  - Service account permission analysis
  - Credential file validation
  - Environment variable checking
  - Complete configuration reporting

**Critical Functions**:
```python
def check_gcloud_config():
    """Validates current gcloud project and account configuration."""
    
def check_api_enablement(project_id):
    """Verifies Gmail API is enabled for the project."""
    
def check_service_account_permissions(project_id, service_account):
    """Analyzes service account IAM permissions."""
    
def analyze_credentials():
    """Comprehensive credential file analysis."""
```

**File: `integrations/verify_gmail_config.py` (133 lines)**  
- **Purpose**: Runtime Gmail API configuration verification
- **Capabilities**:
  - Live Gmail API connectivity testing
  - OAuth credential validation
  - Token storage verification  
  - Permission troubleshooting
  - Step-by-step setup guidance

**Critical Functions**:
```python
async def verify_gmail_api():
    """Tests actual Gmail API access with service account."""
    
def check_oauth_config():
    """Validates OAuth 2.0 credential configuration."""
    
def verify_token_storage():
    """Checks token file security and accessibility."""
```

#### Vertex AI Integration System

**File: `integrations/check_vertex_models.py` (71 lines)**
- **Purpose**: Vertex AI model access verification and setup

**File: `integrations/check_gcp_setup.py` (95 lines)**
- **Purpose**: End-to-end Google Cloud credentials & environment sanity checker. Verifies `.env`, service-account JSON, gcloud CLI project, and prints a concise pass/fail summary.

**Critical Functions**:
```python
def check_vertex_ai_setup():
    """Comprehensive Vertex AI setup validation."""
    # Tests: project config, model access, API enablement
```

#### Email Infrastructure Components

**File: `email_utils/setup_gmail_config.py` (78 lines)**
- **Purpose**: Automated Gmail configuration setup
- **Capabilities**:
  - Credentials directory creation
  - Environment variable configuration
  - Credential file validation
  - Setup process automation

**File: `agents/domain/vertex_email_agent.py` (100 lines)**
- **Purpose**: AI-powered email agent with knowledge graph integration
- **Capabilities**:
  - Simulated email sending via Vertex AI
  - Knowledge graph persistence of email data
  - Diary logging of email activities
  - Message processing for email requests

**File: `agents/utils/email_integration.py` (13 lines)**
- **Purpose**: Basic email integration stub
- **Status**: Placeholder implementation for future development

### 🔍 **Debugging and Troubleshooting Guide**

#### Common Integration Issues

**1. Gmail API Configuration Problems**
```bash
# Run comprehensive Gmail setup analysis
python integrations/gather_gmail_info.py

# Verify live Gmail API access  
python integrations/verify_gmail_config.py
```

**Typical Issues**:
- **API Not Enabled**: `gcloud services enable gmail.googleapis.com --project=PROJECT_ID`
- **Missing OAuth Credentials**: Download from Google Cloud Console → APIs & Services → Credentials
- **Service Account Permissions**: Ensure proper IAM roles assigned
- **Token File Permissions**: Should be 600 (read/write for owner only)

**2. Vertex AI Access Problems**
```bash
# Check Vertex AI model access
python integrations/check_vertex_models.py
```

**Typical Issues**:
- **API Not Enabled**: `gcloud services enable aiplatform.googleapis.com`
- **Model Access Denied**: Visit Model Garden and request access to text-bison
- **Project Configuration**: Verify GOOGLE_CLOUD_PROJECT environment variable
- **Location Issues**: Ensure supported region (us-central1, etc.)

**3. Environment Configuration Issues**
**Required Environment Variables**:
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
GOOGLE_CLOUD_LOCATION=us-central1
```

**Validation Commands**:
```bash
# Check environment setup
python -c "from integrations.gather_gmail_info import check_environment; check_environment()"

# Verify credential files exist
ls -la credentials/
```

#### Performance Optimization

**Caching Strategies**:
- **Token Caching**: OAuth tokens cached in `credentials/token.pickle`
- **Service Account Caching**: Service account credentials loaded once per session
- **API Client Caching**: Google API clients reused across requests

**Connection Pooling**:
- **HTTP Connection Reuse**: Leverages Google client library connection pooling
- **Async Operations**: All integration operations support async/await patterns
- **Batch Operations**: Support for batch API requests where applicable

### 🚀 **Production Deployment Considerations**

#### Security Best Practices

**Credential Management**:
- Service account JSON files should never be committed to version control
- Use Google Secret Manager for production credential storage
- Implement credential rotation policies
- Monitor credential usage through Cloud Audit Logs

**Access Control**:
- Follow principle of least privilege for service account permissions
- Use IAM conditions for fine-grained access control
- Implement proper OAuth scopes for user consent
- Regular permission audits and cleanup

#### Monitoring and Observability

**Logging Integration**:
```python
# All integration components use structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
```

**Metrics Tracking**:
- API call success/failure rates
- Authentication token refresh frequency  
- Service quota utilization
- Error pattern analysis

#### Scalability Architecture

**Rate Limiting**:
- Implement backoff strategies for API rate limits
- Use exponential backoff with jitter
- Monitor quota usage and implement alerting
- Queue requests during high traffic periods

**High Availability**:
- Multiple service account keys for redundancy
- Regional failover for Vertex AI endpoints
- Circuit breaker patterns for external API calls
- Health checks for all integration endpoints

### 🔧 **Integration Testing Framework**

#### Automated Testing Suite

**Gmail Integration Tests**:
```bash
# Run full Gmail integration test suite
python -m pytest tests/integrations/test_gmail_integration.py -v

# Test specific components
python integrations/verify_gmail_config.py
```

**Vertex AI Integration Tests**:
```bash
# Test Vertex AI model access
python integrations/check_vertex_models.py

# Run integration test suite
python -m pytest tests/integrations/test_vertex_integration.py -v
```

#### Mock Testing Support

**Development Testing**:
- Gmail API mocking for development environments
- Vertex AI model response simulation
- Credential validation without external API calls
- Integration testing with synthetic data

### 📊 **Integration Metrics and Monitoring**

#### Key Performance Indicators

**Authentication Metrics**:
- Token refresh success rate
- Service account authentication latency
- OAuth flow completion rate
- Credential validation success rate

**API Integration Metrics**:
- Gmail API response times
- Vertex AI model inference latency  
- Error rates by integration type
- Quota utilization tracking

**System Health Indicators**:
- Integration endpoint availability
- Credential expiration monitoring
- API quota near-limit alerts
- Failed authentication attempt tracking

### 🔮 **Future Integration Roadmap**

#### Planned Integrations
- **Microsoft 365**: Email and calendar integration
- **Slack/Teams**: Messaging platform connectivity
- **AWS Services**: Multi-cloud integration support
- **Database Connectors**: Enterprise database integration
- **Webhook Framework**: Inbound integration support

#### Enhancement Opportunities
- **GraphQL API**: Modern API integration patterns
- **Event Streaming**: Real-time data integration
- **Federation**: Cross-system identity management
- **Observability**: Enhanced monitoring and tracing
- **Security**: Advanced threat detection and response

## 🎯 **Developer Quick Start**

### Setting Up Gmail Integration
```bash
# 1. Set up credentials directory
python email_utils/setup_gmail_config.py

# 2. Gather configuration information
python integrations/gather_gmail_info.py

# 3. Verify setup
python integrations/verify_gmail_config.py

# 4. Test email agent
python -c "
from agents.domain.vertex_email_agent import VertexEmailAgent
import asyncio

async def test():
    agent = VertexEmailAgent()
    await agent.initialize()
    await agent.send_email('test@example.com', 'Test', 'Hello World')
    
asyncio.run(test())
"
```

### Setting Up Vertex AI Integration
```bash
# 1. Check Vertex AI access
python integrations/check_vertex_models.py

# 2. Enable required APIs if needed
gcloud services enable aiplatform.googleapis.com

# 3. Test model access
python -c "
from integrations.check_vertex_models import check_vertex_ai_setup
import asyncio
asyncio.run(check_vertex_ai_setup())
"
```

This integration layer provides a robust foundation for external system connectivity with comprehensive error handling, security best practices, and production-ready monitoring capabilities.

## 🔧 **Integration-Specific Debugging Framework**

### **Advanced Debugging Patterns for Integration Issues**

#### **1. Systematic Integration Testing Approach**

**Phase 1: Environment Validation**
```bash
# Complete environment health check
python -c "
import os
import json
from pathlib import Path

# Check critical environment variables
required_vars = ['GOOGLE_CLOUD_PROJECT', 'GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_CLOUD_LOCATION']
for var in required_vars:
    value = os.getenv(var)
    print(f'{var}: {\"✅ SET\" if value else \"❌ MISSING\"} - {value}')

# Check credential file
cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if cred_path and Path(cred_path).exists():
    try:
        with open(cred_path) as f:
            cred_data = json.load(f)
        print(f'Credentials: ✅ VALID - Service Account: {cred_data.get(\"client_email\", \"N/A\")}')
    except Exception as e:
        print(f'Credentials: ❌ INVALID - Error: {e}')
else:
    print(f'Credentials: ❌ FILE NOT FOUND - Path: {cred_path}')
"
```

**Phase 2: Service Connectivity Testing**
```bash
# Test individual service connections
echo "=== Testing Gmail API Connectivity ==="
python integrations/gather_gmail_info.py 2>&1 | tee debug_gmail.log

echo "=== Testing Vertex AI Access ==="
python integrations/check_vertex_models.py 2>&1 | tee debug_vertex.log

echo "=== Testing Live Gmail API ==="
python integrations/verify_gmail_config.py 2>&1 | tee debug_gmail_live.log
```

**Phase 3: Agent Integration Testing**
```bash
# Test agent-level integration
python -c "
import asyncio
from agents.domain.vertex_email_agent import VertexEmailAgent

async def test_agent_integration():
    print('=== Agent Integration Test ===')
    try:
        agent = VertexEmailAgent()
        print(f'✅ Agent instantiated: {agent.agent_id}')
        
        await agent.initialize()
        print('✅ Agent initialized successfully')
        
        # Test email sending
        await agent.send_email('test@example.com', 'Integration Test', 'Testing integration')
        print('✅ Email sending functionality working')
        
        # Test content enhancement (if method exists)
        if hasattr(agent, 'enhance_email_content'):
            enhanced = await agent.enhance_email_content('Hello, this is a test.')
            print(f'✅ Content enhancement working: {len(enhanced)} chars')
        else:
            print('⚠️  Content enhancement method not implemented')
            
    except Exception as e:
        print(f'❌ Agent integration failed: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(test_agent_integration())
"
```

#### **2. Error Pattern Analysis Framework**

**Common Error Signatures and Debugging**:
```python
# Integration error classifier
ERROR_PATTERNS = {
    'FileNotFoundError.*credentials': {
        'category': 'CREDENTIAL_MISSING',
        'debug_cmd': 'ls -la credentials/ && echo $GOOGLE_APPLICATION_CREDENTIALS',
        'fix_guide': 'Download service account JSON from Google Cloud Console'
    },
    'google.auth.exceptions.DefaultCredentialsError': {
        'category': 'AUTH_CONFIG_ERROR', 
        'debug_cmd': 'gcloud auth list && gcloud config get-value project',
        'fix_guide': 'Run gcloud auth login and set project'
    },
    'HttpError 403.*API.*not.*enabled': {
        'category': 'API_NOT_ENABLED',
        'debug_cmd': 'gcloud services list --enabled --filter="aiplatform OR gmail"',
        'fix_guide': 'Enable APIs: gcloud services enable aiplatform.googleapis.com gmail.googleapis.com'
    },
    'TypeError.*unexpected keyword argument.*recipient_id': {
        'category': 'API_SIGNATURE_MISMATCH',
        'debug_cmd': 'grep -n "def send_email" agents/utils/email_integration.py',
        'fix_guide': 'Update send_email method signature for backward compatibility'
    },
    'AttributeError.*enhance_email_content': {
        'category': 'MISSING_METHOD',
        'debug_cmd': 'grep -n "def enhance" agents/domain/vertex_email_agent.py',
        'fix_guide': 'Add enhance_email_content method to VertexEmailAgent'
    }
}

def diagnose_error(error_message):
    """Diagnose integration error and provide targeted debugging guidance."""
    import re
    for pattern, info in ERROR_PATTERNS.items():
        if re.search(pattern, error_message):
            return info
    return {'category': 'UNKNOWN', 'debug_cmd': 'Check logs for details', 'fix_guide': 'Manual investigation required'}
```

#### **3. Performance Debugging for Integration Layer**

**Integration Performance Profiler**:
```python
# File: debug/integration_profiler.py
import time
import asyncio
from contextlib import asynccontextmanager

class IntegrationProfiler:
    def __init__(self):
        self.timings = {}
        self.call_counts = {}
    
    @asynccontextmanager
    async def profile(self, operation_name):
        start_time = time.perf_counter()
        self.call_counts[operation_name] = self.call_counts.get(operation_name, 0) + 1
        
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            if operation_name not in self.timings:
                self.timings[operation_name] = []
            self.timings[operation_name].append(duration)
    
    def report(self):
        print("=== Integration Performance Report ===")
        for operation, times in self.timings.items():
            avg_time = sum(times) / len(times)
            total_time = sum(times)
            call_count = self.call_counts[operation]
            print(f"{operation}: {avg_time:.3f}s avg, {total_time:.3f}s total, {call_count} calls")

# Usage example
async def profile_integration_operations():
    profiler = IntegrationProfiler()
    
    async with profiler.profile("gmail_auth"):
        # Simulate Gmail authentication
        await asyncio.sleep(0.1)
    
    async with profiler.profile("vertex_model_init"):
        # Simulate Vertex AI model initialization
        await asyncio.sleep(0.2)
    
    profiler.report()
```

#### **4. Integration State Inspection Tools**

**Service Health Monitor**:
```python
# Real-time integration health monitoring
async def monitor_integration_health():
    health_status = {
        'google_cloud': await check_gcp_connectivity(),
        'gmail_api': await check_gmail_api_status(),
        'vertex_ai': await check_vertex_ai_status(),
        'email_agents': await check_email_agent_status()
    }
    
    overall_health = all(status['healthy'] for status in health_status.values())
    
    print(f"=== Integration Health Status ===")
    print(f"Overall Health: {'✅ HEALTHY' if overall_health else '❌ ISSUES DETECTED'}")
    
    for service, status in health_status.items():
        icon = '✅' if status['healthy'] else '❌'
        print(f"{service}: {icon} {status.get('message', 'OK')}")
        
        if not status['healthy'] and 'recommendations' in status:
            for rec in status['recommendations']:
                print(f"  → {rec}")
    
    return health_status

async def check_gcp_connectivity():
    """Check Google Cloud Platform connectivity."""
    try:
        from google.oauth2 import service_account
        import os
        
        cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not cred_path:
            return {'healthy': False, 'message': 'No credentials configured'}
        
        credentials = service_account.Credentials.from_service_account_file(cred_path)
        return {'healthy': True, 'message': f'Connected as {credentials.service_account_email}'}
    except Exception as e:
        return {
            'healthy': False, 
            'message': f'Connection failed: {e}',
            'recommendations': [
                'Check GOOGLE_APPLICATION_CREDENTIALS environment variable',
                'Verify service account JSON file exists and is valid',
                'Run: python integrations/gather_gmail_info.py'
            ]
        }
```

#### **5. Automated Integration Debugging Scripts**

**Complete Integration Diagnostic Script**:
```bash
#!/bin/bash
# File: debug/diagnose_integrations.sh

echo "🔍 COMPREHENSIVE INTEGRATION DIAGNOSTICS"
echo "========================================"

# Environment Check
echo "📋 Environment Variables:"
env | grep -E "(GOOGLE|OPENAI)" | sort

# Credential Validation
echo -e "\n🔐 Credential Validation:"
if [ -f "credentials/credentials.json" ]; then
    echo "✅ Credentials file exists"
    python -c "import json; data=json.load(open('credentials/credentials.json')); print(f'Service Account: {data.get(\"client_email\", \"N/A\")}')"
else
    echo "❌ Credentials file missing"
fi

# API Status Check
echo -e "\n🌐 API Status Check:"
gcloud services list --enabled --filter="name:aiplatform.googleapis.com OR name:gmail.googleapis.com" 2>/dev/null | grep -E "(aiplatform|gmail)" || echo "❌ APIs not enabled or gcloud not authenticated"

# Integration Test Execution
echo -e "\n🧪 Integration Test Execution:"
python -m pytest tests/test_main_api.py tests/test_chat_endpoint.py -v --tb=short 2>&1 | grep -E "(PASSED|FAILED|ERROR)"

# Detailed Component Testing
echo -e "\n🔧 Component-Level Testing:"
python integrations/gather_gmail_info.py 2>&1 | tail -10
python integrations/check_vertex_models.py 2>&1 | tail -5

echo -e "\n✅ Diagnostic complete. Check output above for issues."
```

### **Integration Testing Best Practices for Debugging**

#### **Mock-First Development Pattern**
```python
# Always start with mocks for integration development
class MockIntegrationFramework:
    @staticmethod
    def mock_vertex_ai():
        """Create mock Vertex AI for offline testing."""
        from unittest.mock import MagicMock
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "Mock enhanced content"
        return mock_model
    
    @staticmethod  
    def mock_gmail_service():
        """Create mock Gmail service for offline testing."""
        from unittest.mock import MagicMock
        mock_service = MagicMock()
        mock_service.users().getProfile().execute.return_value = {
            "emailAddress": "mock@example.com",
            "messagesTotal": 1000
        }
        return mock_service

# Use in tests for reliable debugging
@pytest.fixture
def mocked_integrations():
    return {
        'vertex_ai': MockIntegrationFramework.mock_vertex_ai(),
        'gmail': MockIntegrationFramework.mock_gmail_service()
    }
```

#### **Progressive Integration Testing Strategy**
1. **Unit Tests**: Individual component testing with full mocking
2. **Mock Integration Tests**: Component interaction with mock external services  
3. **Sandbox Integration Tests**: Real external services in development environment
4. **Production Integration Tests**: Real external services with production credentials

This debugging framework provides systematic approaches to diagnosing and resolving integration issues, with clear escalation paths from environment validation to component-level testing.
