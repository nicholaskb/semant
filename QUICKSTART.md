# 🚀 Quick Start Guide

Get Semant running in 5 minutes.

---

## Prerequisites

- Python 3.11+
- pip
- (Optional) Docker for Qdrant vector database

---

## Installation

```bash
# 1. Clone repository
git clone <repo-url>
cd semant

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
cp .env.example .env
# Edit .env and add your API keys:
# OPENAI_API_KEY=your-key-here
```

---

## Start the Server

```bash
# Start API server
python main.py

# Server runs on http://localhost:8000
# API docs: http://localhost:8000/docs
```

---

## Try It Out

### 1. Health Check
```bash
curl http://localhost:8000/api/health
```

### 2. Create an Agent
```bash
curl -X POST http://localhost:8000/api/agents/create \
  -H "Content-Type: application/json" \
  -d '{"agent_type": "simple", "agent_id": "test_agent"}'
```

### 3. Query Knowledge Graph
```bash
curl -X GET "http://localhost:8000/api/kg/query?query=SELECT%20*%20WHERE%20%7B%20%3Fs%20%3Fp%20%3Fo%20%7D%20LIMIT%2010"
```

---

## Example: Image Similarity Search

```bash
# 1. Start Qdrant (requires Docker)
docker run -d -p 6333:6333 qdrant/qdrant:latest

# 2. Upload an image
curl -X POST http://localhost:8000/api/images/search-similar \
  -F "image_file=@path/to/image.jpg" \
  -F "limit=5"

# 3. View results in browser
# Open: http://localhost:8000/static/frontend_image_search_example.html
```

---

## Example: Children's Book Generation

```bash
# Generate a children's book
python scripts/generate_childrens_book.py \
  --bucket your-gcs-bucket \
  --input-prefix input_images/ \
  --output-prefix generated_images/
```

---

## Troubleshooting

**Port already in use?**
```bash
# Use different port
python main.py --port 8001
```

**Missing API keys?**
- Check `.env` file exists
- Verify environment variables are loaded
- See `docs/troubleshooting_guide.md`

**Tests failing?**
```bash
# Run test suite
pytest tests/ -v

# Check specific test
pytest tests/test_agent_factory.py -v
```

---

## Next Steps

- **Read**: `INVESTOR_README.md` for business overview
- **Explore**: `docs/developer_guide.md` for technical details
- **Try**: `scripts/demos/` for working examples
- **API**: Visit `http://localhost:8000/docs` for interactive API docs

---

**Need Help?** See `docs/troubleshooting_guide.md`

