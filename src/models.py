from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class GitilesEntry(BaseModel):
    """File or directory entry in a Gitiles tree listing."""

    model_config = ConfigDict(extra="ignore")

    mode: int
    type: Literal["blob", "tree"]
    id: str
    name: str


class GitilesTree(BaseModel):
    """Gitiles tree listing response."""

    model_config = ConfigDict(extra="ignore")

    id: str
    entries: list[GitilesEntry]


class BuildInfo(BaseModel):
    """Key information parsed from Android prebuilts BUILD_INFO."""

    model_config = ConfigDict(extra="ignore")

    bid: str

    @field_validator("bid", mode="before")
    @classmethod
    def normalize_bid(cls, value: object) -> str:
        if value is None or not str(value).strip():
            raise ValueError("bid must not be empty")
        return str(value)


class ClangMetadata(BaseModel):
    """Metadata of the fetched Clang toolchain revision."""

    latest_clang: str
    build_id: str
    clang_version: str
    new_tag: str
    exists: bool
    branch: str


class TelegramRequest(BaseModel):
    """Telegram Bot API payload for sendMessage."""

    chat_id: str
    parse_mode: Literal["Markdown"] = "Markdown"
    disable_web_page_preview: bool = True
    text: str


class TelegramResponse(BaseModel):
    """Minimal Telegram Bot API response shape."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    description: str | None = None
