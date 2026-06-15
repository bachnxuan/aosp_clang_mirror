import os

import requests
from pydantic import ValidationError

from src.error import ConfigError, TelegramError
from src.models import TelegramRequest, TelegramResponse


def env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"{name} environment variable is not set")
    return value


def send_message(text: str) -> None:
    tg_bot_token = env("TG_BOT_TOKEN")
    tg_chat_id = env("TG_CHAT_ID")

    payload = TelegramRequest(chat_id=tg_chat_id, text=text)
    url = f"https://api.telegram.org/bot{tg_bot_token}/sendMessage"
    try:
        response = requests.post(url, json=payload.model_dump(mode="json"), timeout=30)
        response.raise_for_status()
        data = TelegramResponse.model_validate(response.json())
    except (requests.RequestException, ValidationError) as error:
        raise TelegramError("Telegram sendMessage request failed") from error

    if not data.ok:
        description = data.description or "Unknown error"
        raise TelegramError(f"Telegram sendMessage failed: {description}")
