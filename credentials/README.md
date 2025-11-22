# 📂 `credentials/` Directory Guide

This folder **should never be committed with live secrets**. It is
.gitignored except for this README so the structure is clear.

Required at runtime
-------------------
| File | Purpose | How to obtain | Commit? |
|------|---------|---------------|---------|
| `credentials.json` | OAuth 2.0 **Desktop** client for Gmail API (JSON downloaded from Google Cloud → OAuth credentials) | Google Cloud Console → APIs & Services → Credentials → *Create OAuth Client* → Desktop | **NO** |
| `service_account.json` *(name can vary)* | Service-account key used by Vertex SDK or other GCP clients | Google Cloud Console → Service Accounts → *Create Key* | **NO** |
| `token.pickle` | OAuth refresh/access token generated automatically on first run of any Gmail script | Auto-generated; delete to re-authorize with new scopes | **NO** |

Environment variables (.env)
---------------------------
Typical `.env` file at project root:
```ini
GOOGLE_APPLICATION_CREDENTIALS=credentials/service_account.json
GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_CLOUD_LOCATION=us-central1

# Optional – override if credentials.json is not in default path
GMAIL_OAUTH_CREDENTIALS=credentials/credentials.json

# SMTP fallback (only if you still use EmailIntegration SMTP mode)
EMAIL_SENDER=your@gmail.com
EMAIL_PASSWORD=your_app_password  # Google App Password
```

Quick checklist
---------------
1. **Never commit** any of the JSON or pickle files—`.gitignore` covers them.
2. After adding `gmail.readonly` scope, delete `token.pickle` and re-run a Gmail script to refresh permissions.
3. Keep the service-account key only if you use Vertex or other server-side GCP libraries; it is *not* used for Gmail OAuth. 