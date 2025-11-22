# Google Cloud Integration Guide

## Overview

The Semant system integrates with Google Cloud Platform (GCP) services to provide advanced AI capabilities, cloud storage, and email functionality. This guide covers the setup, configuration, and usage of Google Cloud integrations.

## Supported Services

### Vertex AI
- **Models**: Gemini Pro, Gemini Flash, PaLM 2, Codey
- **Features**: Text generation, vision analysis, batch processing, cost optimization
- **Use Cases**: Content generation, code assistance, image analysis

### Cloud Storage (GCS)
- **Features**: File upload/download, bucket management
- **Integration**: Children's book image storage, model artifacts
- **Security**: Service account authentication, bucket permissions

### Gmail API
- **Features**: Email reading, sending, enhancement
- **Integration**: Agent communication, notifications
- **Security**: OAuth 2.0, domain-wide delegation

## Prerequisites

### Google Cloud Project Setup

1. **Create a Google Cloud Project**
   ```bash
   gcloud projects create your-project-id
   gcloud config set project your-project-id
   ```

2. **Enable Required APIs**
   ```bash
   # Vertex AI API
   gcloud services enable aiplatform.googleapis.com

   # Cloud Storage API
   gcloud services enable storage.googleapis.com

   # Gmail API
   gcloud services enable gmail.googleapis.com
   ```

3. **Create Service Account**
   ```bash
   gcloud iam service-accounts create semant-sa \
     --description="Semant AI System Service Account" \
     --display-name="Semant Service Account"
   ```

4. **Generate Service Account Key**
   ```bash
   gcloud iam service-accounts keys create key.json \
     --iam-account=semant-sa@your-project-id.iam.gserviceaccount.com
   ```

### IAM Permissions

Grant the following roles to your service account:

```bash
# Vertex AI permissions
gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:semant-sa@your-project-id.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Cloud Storage permissions
gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:semant-sa@your-project-id.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Gmail permissions (if using Gmail integration)
gcloud projects add-iam-policy-binding your-project-id \
  --member="serviceAccount:semant-sa@your-project-id.iam.gserviceaccount.com" \
  --role="roles/gmail.send"
```

## Configuration

### Environment Variables

Set the following environment variables:

```bash
# Google Cloud Project
export GOOGLE_PROJECT_ID="your-project-id"
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Service Account Credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"

# Optional: Custom GCS bucket
export GCS_BUCKET_NAME="your-custom-bucket"

# Optional: Vertex AI location
export VERTEX_AI_LOCATION="us-central1"
```

### Python Configuration

```python
from integrations.google_cloud_auth import initialize_google_cloud

# Initialize Google Cloud integration
auth_manager = await initialize_google_cloud()

# Validate setup
validation = await auth_manager.validate_credentials()
print(f"Setup status: {validation['overall_status']}")
```

## Vertex AI Integration

### Basic Text Generation

```python
from integrations.vertex_ai_client import get_vertex_client, VertexAIModel

async def generate_text():
    client = await get_vertex_client()

    response = await client.generate_text(
        prompt="Explain quantum computing in simple terms",
        model=VertexAIModel.GEMINI_FLASH,
        temperature=0.7,
        max_output_tokens=500
    )

    if response.success:
        print(response.content)
    else:
        print(f"Error: {response.error_message}")
```

### Vision Analysis

```python
async def analyze_image():
    client = await get_vertex_client()

    # Read image file
    with open("image.jpg", "rb") as f:
        image_data = f.read()

    response = await client.generate_with_images(
        prompt="Describe this image in detail",
        images=[image_data],
        model=VertexAIModel.GEMINI_PRO_VISION
    )

    print(response.content)
```

### Batch Processing

```python
async def batch_generate():
    client = await get_vertex_client()

    prompts = [
        "Write a haiku about AI",
        "Explain machine learning",
        "What is the future of robotics?"
    ]

    responses = []
    for prompt in prompts:
        response = await client.generate_text(
            prompt=prompt,
            model=VertexAIModel.GEMINI_FLASH
        )
        responses.append(response)

    return responses
```

### Cost Optimization

```python
# Use cheaper model for simple tasks
response = await client.generate_text(
    prompt="Summarize this article",
    model=VertexAIModel.GEMINI_FLASH,  # Cheaper than GEMINI_PRO
    max_output_tokens=200  # Limit output to control costs
)
```

## Cloud Storage Integration

### File Upload

```python
from integrations.google_cloud_auth import get_gcs_client

async def upload_file():
    client = await get_gcs_client()
    bucket = client.bucket("your-bucket-name")

    blob = bucket.blob("path/to/remote/file.jpg")
    blob.upload_from_filename("local/file.jpg")

    print(f"File uploaded to: gs://{bucket.name}/{blob.name}")
```

### File Download

```python
async def download_file():
    client = await get_gcs_client()
    bucket = client.bucket("your-bucket-name")

    blob = bucket.blob("path/to/remote/file.jpg")
    blob.download_to_filename("local/downloaded.jpg")

    print("File downloaded successfully")
```

### Batch Operations

```python
async def upload_multiple_files():
    client = await get_gcs_client()
    bucket = client.bucket("your-bucket-name")

    files_to_upload = [
        ("local/image1.jpg", "images/image1.jpg"),
        ("local/image2.jpg", "images/image2.jpg"),
        ("local/image3.jpg", "images/image3.jpg")
    ]

    for local_path, remote_path in files_to_upload:
        blob = bucket.blob(remote_path)
        blob.upload_from_filename(local_path)
        print(f"Uploaded: {remote_path}")
```

## Gmail Integration

### Send Email

```python
from integrations.google_cloud_auth import get_gmail_service

async def send_email():
    service = await get_gmail_service()

    message = {
        'raw': base64.urlsafe_b64encode(
            f"To: recipient@example.com\n"
            f"Subject: Test Email\n\n"
            f"This is a test email sent via Gmail API."
        ).decode()
    }

    sent_message = service.users().messages().send(
        userId='me',
        body=message
    ).execute()

    print(f"Email sent: {sent_message['id']}")
```

### Enhanced Email with Vertex AI

```python
from agents.domain.vertex_email_agent import VertexEmailAgent

async def send_enhanced_email():
    agent = VertexEmailAgent("email_agent")
    await agent.initialize()

    # Enhance content with AI
    original_content = "Meeting tomorrow at 2pm"
    enhanced_content = await agent.enhance_email_content(original_content)

    # Send enhanced email
    message = AgentMessage(
        sender_id="user",
        recipient_id="email_agent",
        content={
            "recipient": "colleague@example.com",
            "subject": "Meeting Reminder",
            "body": enhanced_content
        },
        message_type="send_email"
    )

    response = await agent.process_message(message)
    print(f"Email sent: {response.content}")
```

## Agent Integration

### Vertex Email Agent

```python
from agents.domain.vertex_email_agent import VertexEmailAgent

# Initialize agent
agent = VertexEmailAgent("email_assistant")
await agent.initialize()

# Send AI-enhanced email
message = AgentMessage(
    sender_id="user",
    recipient_id="email_assistant",
    content={
        "recipient": "recipient@example.com",
        "subject": "Project Update",
        "body": "The project is progressing well."
    },
    message_type="send_email"
)

response = await agent.process_message(message)
```

### Image Ingestion Agent

```python
from agents.domain.image_ingestion_agent import ImageIngestionAgent

# Initialize agent
agent = ImageIngestionAgent("image_processor")
await agent.initialize()

# Process images from GCS
message = AgentMessage(
    sender_id="user",
    recipient_id="image_processor",
    content={
        "action": "process_batch",
        "gcs_prefix": "images/to-process/",
        "batch_size": 10
    },
    message_type="process_images"
)

response = await agent.process_message(message)
```

## Monitoring and Health Checks

### System Health

```python
from integrations.google_cloud_auth import validate_google_cloud_setup

# Check overall health
validation = await validate_google_cloud_setup()
print(f"Overall status: {validation['overall_status']}")

for service, status in validation['services'].items():
    print(f"{service}: {status.get('valid', 'unknown')}")
```

### Vertex AI Metrics

```python
client = await get_vertex_client()
metrics = client.get_metrics()

print(f"Total requests: {metrics['total_requests']}")
print(f"Success rate: {metrics['success_rate']:.1%}")
print(f"Average latency: {metrics['average_latency_ms']:.2f}ms")
print(f"Average batch size: {metrics['average_batch_size']:.1f}")
```

### Cost Tracking

```python
# Monitor API usage and costs
health = await client.health_check()
if 'cost_estimate' in health:
    print(f"Estimated cost: ${health['cost_estimate']:.4f}")
```

## Error Handling and Retries

### Automatic Retries

The system automatically handles temporary failures:

```python
# Vertex AI client automatically retries on transient errors
response = await client.generate_text(
    prompt="Generate content",
    model=VertexAIModel.GEMINI_FLASH
)
# Automatic retry on rate limits, network issues, etc.
```

### Error Types

- **AuthenticationError**: Invalid credentials
- **QuotaExceededError**: API quota exceeded
- **NetworkError**: Connectivity issues
- **ValidationError**: Invalid input parameters

### Custom Error Handling

```python
from integrations.google_cloud_auth import GoogleCloudAuthError

try:
    client = await get_vertex_client()
    response = await client.generate_text("Test prompt")
except GoogleCloudAuthError as e:
    print(f"Authentication failed: {e}")
    # Handle auth failure (refresh credentials, etc.)
except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle other errors
```

## Security Best Practices

### Credential Management

1. **Never commit credentials** to version control
2. **Use service accounts** instead of user accounts
3. **Rotate keys regularly** (recommended: monthly)
4. **Limit service account permissions** to minimum required

### Network Security

1. **Use VPC** for internal services
2. **Enable Cloud Armor** for web applications
3. **Configure firewall rules** appropriately
4. **Use private endpoints** when available

### Data Protection

1. **Enable encryption** at rest and in transit
2. **Use customer-managed encryption keys** for sensitive data
3. **Implement access logging** and monitoring
4. **Regular security audits** and compliance checks

## Performance Optimization

### Vertex AI Optimization

```python
# Use appropriate model for task complexity
model_choice = {
    "simple": VertexAIModel.GEMINI_FLASH,      # Fast, cheap
    "complex": VertexAIModel.GEMINI_PRO,       # Better quality
    "vision": VertexAIModel.GEMINI_PRO_VISION, # Image analysis
    "code": VertexAIModel.CODEY                # Code generation
}

# Optimize parameters
optimized_params = {
    "temperature": 0.7,      # Creativity vs consistency
    "max_output_tokens": 256, # Limit output length
    "top_p": 0.8,           # Nucleus sampling
    "top_k": 40             # Top-k sampling
}
```

### Batching Strategies

```python
# Batch similar requests together
batch_requests = [
    {"prompt": "Summarize article 1", "priority": 1},
    {"prompt": "Summarize article 2", "priority": 1},
    {"prompt": "Summarize article 3", "priority": 2},  # Higher priority
]

# Sort by priority for optimal processing
batch_requests.sort(key=lambda x: x.get('priority', 1), reverse=True)
```

### Caching Strategies

```python
# Cache frequently used embeddings
embedding_cache = {}

async def get_cached_embedding(text: str):
    if text in embedding_cache:
        return embedding_cache[text]

    embedding = await service.embed_text(text)
    embedding_cache[text] = embedding
    return embedding
```

## Troubleshooting

### Common Issues

#### Authentication Failures

```bash
# Check credentials file
cat $GOOGLE_APPLICATION_CREDENTIALS | jq '.client_email'

# Test authentication
python -c "
from integrations.google_cloud_auth import validate_google_cloud_setup
import asyncio
result = asyncio.run(validate_google_cloud_setup())
print(result)
"
```

#### API Quota Exceeded

```bash
# Check quotas in Google Cloud Console
# https://console.cloud.google.com/iam-admin/quotas

# Monitor usage
client = await get_vertex_client()
metrics = client.get_metrics()
print(f"Requests this hour: {metrics['total_requests']}")
```

#### Network Connectivity

```bash
# Test connectivity to Google APIs
curl -I https://aiplatform.googleapis.com/v1/projects

# Check DNS resolution
nslookup aiplatform.googleapis.com
```

### Debug Logging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or set environment variable
export LOG_LEVEL=DEBUG
```

### Health Check Endpoint

```bash
curl http://localhost:8000/api/health
# Should show Google Cloud services status
```

## Cost Management

### Monitoring Usage

```python
# Track API usage
client = await get_vertex_client()
metrics = client.get_metrics()

# Estimate costs (rough approximation)
input_tokens = sum(r.get('token_usage', {}).get('input_tokens', 0)
                   for r in recent_requests)
output_tokens = sum(r.get('token_usage', {}).get('output_tokens', 0)
                    for r in recent_requests)

# Gemini Flash pricing (approximate)
input_cost = (input_tokens / 1000) * 0.00001875
output_cost = (output_tokens / 1000) * 0.000075
total_cost = input_cost + output_cost

print(f"Estimated cost: ${total_cost:.4f}")
```

### Cost Optimization Tips

1. **Use appropriate models**: Flash for simple tasks, Pro for complex
2. **Limit output tokens**: Set reasonable maximums
3. **Batch requests**: Reduce API call overhead
4. **Cache results**: Avoid duplicate requests
5. **Monitor usage**: Set up alerts for unexpected costs

## Migration Guide

### From Local to Cloud

1. **Set up Google Cloud project** (see Prerequisites)
2. **Configure service accounts** and permissions
3. **Update environment variables** in production
4. **Test authentication** and API access
5. **Gradually migrate workloads** to cloud services

### Version Upgrades

```python
# Check current versions
from integrations.vertex_ai_client import VertexAIModel
print("Available models:", [m.value for m in VertexAIModel])

# Update to latest model versions
latest_models = {
    "text": VertexAIModel.GEMINI_FLASH,      # Latest text model
    "vision": VertexAIModel.GEMINI_PRO_VISION,  # Latest vision model
    "code": VertexAIModel.CODEY              # Latest code model
}
```

## Support and Resources

### Documentation Links

- [Google Cloud Vertex AI](https://cloud.google.com/vertex-ai/docs)
- [Google Cloud Storage](https://cloud.google.com/storage/docs)
- [Gmail API](https://developers.google.com/gmail/api)
- [Google Cloud Authentication](https://cloud.google.com/docs/authentication)

### Community Resources

- **Stack Overflow**: Tag questions with `google-cloud-vertex-ai`
- **GitHub Issues**: Report bugs and request features
- **Google Cloud Community**: Forums and user groups

### Professional Support

- **Google Cloud Support**: Enterprise support plans
- **Managed Services**: GCP partners for implementation
- **Consulting**: Architecture review and optimization

---

*This documentation is automatically updated with system changes. Last updated: January 11, 2025*
