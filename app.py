"""
Telethon ↔ n8n Bridge
=====================
A minimal example showing how to:
1. Sign‑in to Telegram as a *personal* account (not a bot) via Telethon.
2. Forward incoming Telegram messages to an n8n webhook (so n8n can trigger
   downstream automations).
3. Expose a simple HTTP API (FastAPI) that lets n8n send messages *back* to
   Telegram through the same personal account.

Author: ChatGPT example – tailor as you wish ☺
License: MIT
"""

# Auto-install required packages if missing
import sys
import subprocess
import importlib.util

required = [
    "httpx",
    "fastapi",
    "pydantic",
    "telethon",
    "uvicorn"
]

for pkg in required:
    if importlib.util.find_spec(pkg) is None:
        print(f"Installing missing package: {pkg}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

import asyncio
import json
import logging
import os
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from config import (
    API_ID,
    API_HASH,
    TG_SESSION,
    N8N_WEBHOOK_URL,
    API_AUTH_TOKEN,
    LISTEN_HOST,
    LISTEN_PORT,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telethon_n8n_bridge")

# ---------------------------------------------------------------------------
# FastAPI plumbing
# ---------------------------------------------------------------------------
app = FastAPI(title="Telethon ↔ n8n Bridge", version="1.0.0")
telegram_client: Optional[TelegramClient] = None

class SendMessage(BaseModel):
    chat_id: str  # username ("@user"), phone number, or numeric chat ID
    text: str

@app.post("/send", summary="Send a Telegram message via personal account")
async def send(msg: SendMessage, token: str):
    if token != API_AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    if telegram_client is None or not telegram_client.is_connected():
        raise HTTPException(status_code=503, detail="Telegram client not ready")

    try:
        await telegram_client.send_message(msg.chat_id, msg.text)
        return {"ok": True}
    except Exception as exc:
        logger.exception("Failed to send message")
        raise HTTPException(status_code=500, detail=str(exc))

# ---------------------------------------------------------------------------
# Telegram client setup & event routing
# ---------------------------------------------------------------------------
async def bootstrap_telegram() -> TelegramClient:
    """Connect & authenticate. If TG_SESSION is empty we prompt once then print the string."""
    session = StringSession(TG_SESSION) if TG_SESSION else StringSession()
    client = TelegramClient(session, API_ID, API_HASH)

    await client.start()

    if not TG_SESSION:
        # First‑time run – print the new session string so it can be re‑used non‑interactively
        print("★ Your Telegram StringSession → copy & store as TG_SESSION:")
        print(client.session.save())

    # Whenever a new incoming message arrives, forward a JSON payload to n8n.
    @client.on(events.NewMessage(incoming=True))
    async def _(event):
        if not N8N_WEBHOOK_URL:
            return  # nothing configured – skip
        payload = {
            "message_id": event.id,
            "chat_id": event.chat_id,
            "sender_id": event.sender_id,
            "text": event.raw_text,
            "date": event.date.isoformat(),
        }
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                await http.post(N8N_WEBHOOK_URL, json=payload)
        except Exception as exc:
            logger.warning("POST → n8n failed: %s", exc)

    return client

# ---------------------------------------------------------------------------
# Main – run FastAPI + Telethon in the same asyncio loop
# ---------------------------------------------------------------------------
async def _serve():
    global telegram_client
    telegram_client = await bootstrap_telegram()

    import uvicorn

    config = uvicorn.Config(app, host=LISTEN_HOST, port=LISTEN_PORT, loop="asyncio", log_level="info")
    server = uvicorn.Server(config)

    await asyncio.gather(
        telegram_client.run_until_disconnected(),
        server.serve(),
    )

if __name__ == "__main__":
    try:
        asyncio.run(_serve())
    except KeyboardInterrupt:
        print("← shutdown requested – bye!")
    try:
        asyncio.run(_serve())
    except KeyboardInterrupt:
        print("← shutdown requested – bye!")
