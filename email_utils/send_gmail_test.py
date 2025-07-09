import os
import pickle
import base64
from email.mime.text import MIMEText
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Added readonly scope so the same OAuth token can list and fetch messages
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def get_gmail_service():
    creds = None
    token_path = 'credentials/token.pickle'
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

def send_email(service, to, subject, body):
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    message = {'raw': raw}
    sent = service.users().messages().send(userId='me', body=message).execute()
    print(f"Message Id: {sent['id']}")

# ---------------------------------------------------------------------------
# 🌐  READ-ONLY HELPERS
# ---------------------------------------------------------------------------

def list_message_ids(service, query: str = "", max_results: int = 10):
    """Return a list of Gmail message IDs matching `query`."""
    response = service.users().messages().list(
        userId='me', q=query, maxResults=max_results
    ).execute()
    return [msg['id'] for msg in response.get('messages', [])]


def get_message_body(service, msg_id: str) -> str:
    """Fetch plain-text body of a Gmail message by ID (best-effort)."""
    import base64, email

    msg = service.users().messages().get(
        userId='me', id=msg_id, format='full'
    ).execute()

    # Walk the payload to find text/plain part
    def _extract(parts):
        for p in parts:
            mime = p.get('mimeType')
            if mime == 'text/plain' and 'data' in p.get('body', {}):
                return base64.urlsafe_b64decode(p['body']['data']).decode()
            elif p.get('parts'):
                inner = _extract(p['parts'])
                if inner:
                    return inner
        return ""

    payload = msg.get('payload', {})
    if 'body' in payload and payload.get('body', {}).get('data'):
        return base64.urlsafe_b64decode(payload['body']['data']).decode()
    if payload.get('parts'):
        return _extract(payload['parts'])
    return ""


if __name__ == '__main__':
    service = get_gmail_service()
    send_email(service, 'nicholas.k.baro@gmail.com', 'Test Email from Gmail API', 'Hello from your Gmail API integration!') 