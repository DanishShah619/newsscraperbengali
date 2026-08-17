import os
import requests


def _get_bot_token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")
    return token


def _get_chat_id() -> str:
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID environment variable is not set")
    return chat_id


def _redact(text: str, token: str) -> str:
    """Remove the bot token from strings before they appear in logs (SEC-5)."""
    if token and token in text:
        return text.replace(token, "<REDACTED>")
    return text


def send_telegram_digest(text: str) -> None:
    token = _get_bot_token()
    chat_id = _get_chat_id()
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Split on article/paragraph boundaries, not raw character count - blind
    # slicing can cut a markdown entity (e.g. *bold*) in half and cause a 400.
    blocks = text.split("\n\n")
    chunks, current = [], ""
    for block in blocks:
        if len(current) + len(block) + 2 > 3500:
            chunks.append(current)
            current = block
        else:
            current += ("\n\n" if current else "") + block
    if current:
        chunks.append(current)

    for chunk in chunks:
        try:
            resp = requests.post(api_url, json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
            })
            if not resp.ok:
                print(f"[telegram] markdown send failed ({resp.status_code}), retrying as plain text")
                resp2 = requests.post(api_url, json={
                    "chat_id": chat_id,
                    "text": chunk,
                })
                resp2.raise_for_status()
        except Exception as e:
            # Ensure the bot token never appears in logged exception messages
            raise RuntimeError(_redact(str(e), token)) from None

    print("Digest sent to Telegram.")
