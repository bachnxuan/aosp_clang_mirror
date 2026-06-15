import subprocess
from pathlib import Path

import pytest

from src.error import ConfigError
from src.github import create_github_release, github_repo_url, tag_exists


def test_tag_exists_does_not_treat_git_failure_as_missing_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> object:
        raise subprocess.CalledProcessError(128, ["git", "tag"])

    monkeypatch.setattr("src.github.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="inspect local Git tags"):
        tag_exists("clang-r123-456")


def test_tag_exists_wraps_os_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> object:
        raise FileNotFoundError("git not found")

    monkeypatch.setattr("src.github.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="inspect local Git tags"):
        tag_exists("clang-r123-456")


def test_create_github_release_wraps_os_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> object:
        raise FileNotFoundError("gh not found")

    monkeypatch.setattr("src.github.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="execute gh release create"):
        create_github_release("clang-r123-456", Path("toolchain/clang-r123.tar.gz"))


def test_github_repo_url_trims_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_REPO_URL", "https://github.com/example/repo/")

    assert github_repo_url() == "https://github.com/example/repo"


def test_github_repo_url_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_REPO_URL", raising=False)

    with pytest.raises(ConfigError, match="GITHUB_REPO_URL is required"):
        github_repo_url()
