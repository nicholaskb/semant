# 🔑 Setting Up .env for Real Midjourney Images

## Quick Setup (Copy & Paste)

1. **Create `.env` file in project root** (`/Users/nicholasbaro/Python/semant/.env`)

2. **Add this content:**

```bash
# REQUIRED: Your GoAPI/Midjourney API Token
MIDJOURNEY_API_TOKEN=your-actual-token-here

# GCS Configuration (already set)
GCS_BUCKET_NAME=bahroo_public

# Optional: Path to GCS credentials 
# GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

## Where to Get Your API Token

1. **GoAPI Dashboard**: https://www.theapi.app/
2. Sign up/Login
3. Go to API Keys section
4. Copy your token (starts with `sk-` or similar)
5. Replace `your-actual-token-here` with your actual token

## Test Your Setup

```bash
# Test basic connection
python test_real_midjourney.py

# Create real hot dog flier with Midjourney
python create_real_hot_dog_flier.py
```

## Verify It's Working

When properly configured, you'll see:
```
✅ API Token found: sk-xxxxx...
✅ MidjourneyClient initialized successfully
🎨 Submitting hot dog image generation...
```

## Troubleshooting

- **401 Error**: Invalid or missing API token
- **403 Error**: Token expired or no credits
- **Connection Error**: Check internet/firewall

## Important Notes

- The `.env` file is gitignored for security
- Never commit API tokens to the repository
- Each Midjourney image costs API credits (~700k points)

## Current Status

The server is already running and ready:
- FastAPI on http://0.0.0.0:8000 ✅
- 132 previous Midjourney images generated ✅
- Knowledge Graph integration active ✅

**Just needs your API token in .env to generate new images!**

