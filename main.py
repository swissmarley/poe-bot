# main.py
# Poe Server Bot (Modal) -> triggers n8n webhook and forwards n8n's { "reply": "..." } back to Poe.

from __future__ import annotations

import os
from typing import AsyncIterable, Dict, Any, Optional

import httpx
import fastapi_poe as fp
import modal


# ----------------------------
# Modal image + app
# ----------------------------
REQUIREMENTS = [
    "fastapi-poe==0.0.63",
    "httpx==0.27.2",
]

image = modal.Image.debian_slim().pip_install(*REQUIREMENTS)
app = modal.App("poe-n8n-trigger-bot")


# ----------------------------
# Helpers
# ----------------------------
def must_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing required env var: {name}")
    return v.strip()


def extract_reply(data: Any) -> Optional[str]:
    """
    n8n may return:
      - dict: { "reply": "..." }
      - list of dict items: [{...}, {..., "reply": "..."}]
    """
    if isinstance(data, dict):
        v = data.get("reply")
        return v if isinstance(v, str) and v.strip() else None

    if isinstance(data, list) and data:
        last = data[-1]
        if isinstance(last, dict):
            v = last.get("reply")
            return v if isinstance(v, str) and v.strip() else None

    return None


# ----------------------------
# Bot implementation
# ----------------------------
class N8NTriggerBot(fp.PoeBot):
    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            introduction_message=(
                "Send me a note/task/reminder. I forward it to n8n.\n\n"
                "Examples:\n"
                "- “Remind me to call mom”\n"
                "- “Task: submit expenses by Friday”\n"
                "- “Idea: build a habit tracker app”"
            )
        )

    async def get_response(self, request: fp.QueryRequest) -> AsyncIterable[fp.PartialResponse]:
        """
        1) Acknowledge quickly
        2) POST to n8n webhook
        3) Forward n8n {reply} back to Poe
        4) Never let exceptions escape (otherwise Poe shows 'unexpected issue')
        """
        try:
            user_text = (request.query[-1].content or "").strip()
            if not user_text:
                yield fp.PartialResponse(text="Send me a message and I’ll file it.")
                return

            # quick UX ack
            yield fp.PartialResponse(text="Got it — sending to n8n…\n")

            # read env at runtime (prevents import-time crashes)
            n8n_url = must_env("N8N_WEBHOOK_URL")
            shared_secret = must_env("POE_N8N_SHARED_SECRET")

            payload: Dict[str, Any] = {
    		"text": user_text,
    		"conversation_id": getattr(request, "conversation_id", None),
    		"message_id": getattr(request, "message_id", None),
    		"user_id": getattr(request, "user_id", None),
    		"timestamp": getattr(request, "timestamp", None),  # optional; may be None
	    }


            headers = {
                "Content-Type": "application/json",
                "x-poe-n8n-secret": shared_secret,
            }

            async with httpx.AsyncClient(timeout=25.0) as client:
                r = await client.post(n8n_url, json=payload, headers=headers)

            # If n8n returns non-2xx, return the info instead of throwing
            if r.status_code < 200 or r.status_code >= 300:
                body_preview = (r.text or "")[:400]
                yield fp.PartialResponse(text=f"⚠️ n8n HTTP {r.status_code}: {body_preview}")
                return

            # Parse JSON (if possible)
            try:
                data = r.json()
            except Exception:
                yield fp.PartialResponse(text=f"⚠️ n8n returned non-JSON response: {(r.text or '')[:400]}")
                return

            reply = extract_reply(data)
            yield fp.PartialResponse(text=reply or "✅ Done (no 'reply' returned from n8n).")

        except httpx.ConnectError:
            yield fp.PartialResponse(text="⚠️ Cannot connect to n8n (DNS/network). Check N8N_WEBHOOK_URL.")
            return
        except httpx.ReadTimeout:
            yield fp.PartialResponse(text="⚠️ n8n timed out. Check connectivity and webhook response mode.")
            return
        except Exception as e:
            # critical: never crash the bot
            msg = str(e)[:250]
            yield fp.PartialResponse(text=f"⚠️ Modal error: {type(e).__name__}: {msg}")
            return


# ----------------------------
# Modal ASGI app
# ----------------------------
@app.function(
    image=image,
    # Create this secret in the SAME Modal environment (e.g., "main")
    # It must contain:
    #   POE_ACCESS_KEY, POE_BOT_NAME, N8N_WEBHOOK_URL, POE_N8N_SHARED_SECRET
    secrets=[modal.Secret.from_name("poe-n8n-bot")],
)
@modal.asgi_app()
def fastapi_app():
    poe_access_key = must_env("POE_ACCESS_KEY")
    poe_bot_name = must_env("POE_BOT_NAME")

    bot = N8NTriggerBot()

    # make_app validates Poe requests using the access key you configured in Poe
    return fp.make_app(bot, access_key=poe_access_key, bot_name=poe_bot_name)
