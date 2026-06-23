from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from app import app, load_metadata, release_asset, save_metadata
from src.error import ConfigError, TelegramError
from src.models import ClangMetadata

RUNNER = CliRunner()


def test_save_and_load_metadata_round_trip(tmp_path: Path) -> None:
    metadata = ClangMetadata(
        latest_clang="clang-r123",
        build_id="123456",
        clang_version="19.0.0",
        new_tag="clang-r123-123456",
        exists=False,
        branch="main",
    )
    path = tmp_path / "nested" / "metadata.json"

    save_metadata(path, metadata)

    assert load_metadata(path) == metadata


def test_load_metadata_exits_for_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "metadata.json"
    path.write_text("{bad json}\n", encoding="utf-8")

    with pytest.raises(typer.Exit, match="1"):
        load_metadata(path)


def test_release_asset_builds_tarball_path() -> None:
    assert release_asset("clang-r123") == Path("toolchain/clang-r123.tar.gz")


def test_fetch_command_writes_metadata_and_downloads_asset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    metadata_path = tmp_path / "metadata.json"
    download_calls: list[tuple[str, Path]] = []

    monkeypatch.setattr("app.fetch_tree_from_branches", lambda: ("main", object()))
    monkeypatch.setattr("app.find_clang_revs", lambda _tree: ["clang-r100", "clang-r101a"])
    monkeypatch.setattr("app.fetch_metadata", lambda _branch, _clang: ("123456", "19.0.0"))
    monkeypatch.setattr("app.tag_exists", lambda _tag: False)
    monkeypatch.setattr(
        "app.download_tarball",
        lambda url, dest_path: download_calls.append((url, dest_path)),
    )

    result = RUNNER.invoke(app, ["fetch", "--metadata", str(metadata_path)])

    assert result.exit_code == 0
    assert download_calls == [
        (
            "https://android.googlesource.com/platform/prebuilts/clang/host/"
            "linux-x86/+archive/main/clang-r101a.tar.gz",
            Path("toolchain/clang-r101a.tar.gz"),
        )
    ]
    assert load_metadata(metadata_path) == ClangMetadata(
        latest_clang="clang-r101a",
        build_id="123456",
        clang_version="19.0.0",
        new_tag="clang-r101a-123456",
        exists=False,
        branch="main",
    )


def test_release_command_creates_github_release_for_missing_tag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    metadata = ClangMetadata(
        latest_clang="clang-r123",
        build_id="123456",
        clang_version="19.0.0",
        new_tag="clang-r123-123456",
        exists=False,
        branch="main",
    )
    metadata_path = tmp_path / "metadata.json"
    asset = tmp_path / "toolchain" / "clang-r123.tar.gz"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"clang")
    save_metadata(metadata_path, metadata)
    created: list[tuple[str, Path]] = []

    monkeypatch.setattr("app.TOOLCHAIN_DIR", tmp_path / "toolchain")
    monkeypatch.setattr(
        "app.create_github_release",
        lambda tag_name, file_path: created.append((tag_name, file_path)),
    )

    result = RUNNER.invoke(app, ["release", "--metadata", str(metadata_path)])

    assert result.exit_code == 0
    assert created == [("clang-r123-123456", asset)]


def test_release_command_exits_when_asset_is_missing(
    tmp_path: Path,
) -> None:
    metadata = ClangMetadata(
        latest_clang="clang-r123",
        build_id="123456",
        clang_version="19.0.0",
        new_tag="clang-r123-123456",
        exists=False,
        branch="main",
    )
    metadata_path = tmp_path / "metadata.json"
    save_metadata(metadata_path, metadata)

    result = RUNNER.invoke(app, ["release", "--metadata", str(metadata_path)])

    assert result.exit_code == 1


def test_notify_command_sends_both_download_links(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    metadata = ClangMetadata(
        latest_clang="clang-r123",
        build_id="123456",
        clang_version='Android (123456, based on r123) clang version 19.0.0',
        new_tag="clang-r123-123456",
        exists=False,
        branch="main",
    )
    metadata_path = tmp_path / "metadata.json"
    save_metadata(metadata_path, metadata)
    sent_messages: list[str] = []

    monkeypatch.setattr("app.github_repo_url", lambda: "https://github.com/example/repo")
    monkeypatch.setattr("app.send_message", lambda text: sent_messages.append(text))

    result = RUNNER.invoke(app, ["notify", "--metadata", str(metadata_path)])

    assert result.exit_code == 0
    assert sent_messages == [
        "\n".join(
            [
                "*Google Clang Prebuilt Update*",
                "",
                "*Clang Version*: Android (123456, based on r123) clang version 19.0.0 (r123)",
                "*Build ID*: 123456",
                "",
                "*Download tar.gz*:",
                "[Download (GitHub mirror)](https://github.com/example/repo/releases/download/"
                "clang-r123-123456/clang-r123.tar.gz)",
                "[Download (AOSP source)](https://android.googlesource.com/platform/prebuilts/"
                "clang/host/linux-x86/+archive/main/clang-r123.tar.gz)",
            ]
        )
    ]


def test_notify_command_exits_when_github_repo_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    metadata = ClangMetadata(
        latest_clang="clang-r123",
        build_id="123456",
        clang_version="19.0.0",
        new_tag="clang-r123-123456",
        exists=False,
        branch="main",
    )
    metadata_path = tmp_path / "metadata.json"
    save_metadata(metadata_path, metadata)

    monkeypatch.setattr(
        "app.github_repo_url",
        lambda: (_ for _ in ()).throw(
            ConfigError("GITHUB_SERVER_URL and GITHUB_REPOSITORY are required")
        ),
    )

    result = RUNNER.invoke(app, ["notify", "--metadata", str(metadata_path)])

    assert result.exit_code == 1


def test_notify_command_exits_when_telegram_send_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    metadata = ClangMetadata(
        latest_clang="clang-r123",
        build_id="123456",
        clang_version="19.0.0",
        new_tag="clang-r123-123456",
        exists=False,
        branch="main",
    )
    metadata_path = tmp_path / "metadata.json"
    save_metadata(metadata_path, metadata)

    monkeypatch.setattr("app.github_repo_url", lambda: "https://github.com/example/repo")
    monkeypatch.setattr(
        "app.send_message",
        lambda _text: (_ for _ in ()).throw(TelegramError("boom")),
    )

    result = RUNNER.invoke(app, ["notify", "--metadata", str(metadata_path)])

    assert result.exit_code == 1
