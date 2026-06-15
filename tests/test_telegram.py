from unittest.mock import Mock

import pytest
import requests

from src.telegram import send_message


def test_send_message_rejects_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Mock()
    response.json.side_effect = requests.JSONDecodeError("bad json", "", 0)

    monkeypatch.setenv("TG_BOT_TOKEN", "token")
    monkeypatch.setenv("TG_CHAT_ID", "chat")
    monkeypatch.setattr("src.telegram.requests.post", lambda *_args, **_kwargs: response)

    with pytest.raises(RuntimeError, match="sendMessage request failed"):
        send_message("hello")


def test_send_message_rejects_telegram_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Mock()
    response.json.return_value = {"ok": False, "description": "chat not found"}

    monkeypatch.setenv("TG_BOT_TOKEN", "token")
    monkeypatch.setenv("TG_CHAT_ID", "chat")
    monkeypatch.setattr("src.telegram.requests.post", lambda *_args, **_kwargs: response)

    with pytest.raises(RuntimeError, match="chat not found"):
        send_message("hello")


def test_send_message_posts_validated_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Mock()
    response.json.return_value = {"ok": True}
    captured: dict[str, object] = {}

    def fake_post(url: str, *, json: dict[str, object], timeout: int) -> Mock:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return response

    monkeypatch.setenv("TG_BOT_TOKEN", "token")
    monkeypatch.setenv("TG_CHAT_ID", "chat")
    monkeypatch.setattr("src.telegram.requests.post", fake_post)

    send_message("hello")

    assert captured == {
        "url": "https://api.telegram.org/bottoken/sendMessage",
        "json": {
            "chat_id": "chat",
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "text": "hello",
        },
        "timeout": 30,
    }
