import os

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
TG_SESSION = os.getenv("TG_SESSION")  # leave empty the first run – we’ll print it

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")  # e.g. https://my‑n8n/webhook/telegram‑in

API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "CHANGE_ME")

LISTEN_HOST = os.getenv("HOST", "0.0.0.0")
LISTEN_PORT = int(os.getenv("PORT", "8000"))
