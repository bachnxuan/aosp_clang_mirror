import pytest
import requests

from src.aosp import (
    archive_url,
    clang_key,
    fetch_file_content,
    fetch_gitiles_tree,
    fetch_metadata,
    fetch_tree_from_branches,
    find_clang_revs,
)
from src.error import GitilesError, GitilesFormatError, GitilesHTTPError
from src.models import GitilesEntry, GitilesTree


def test_clang_key_orders_lettered_revisions_after_base_revision() -> None:
    revisions = ["clang-r100b", "clang-r101", "clang-r100", "clang-r100a"]

    assert sorted(revisions, key=clang_key) == [
        "clang-r100",
        "clang-r100a",
        "clang-r100b",
        "clang-r101",
    ]

def test_find_clang_revs_ignores_files_and_unrelated_directories() -> None:
    tree = GitilesTree(
        id="root",
        entries=[
            GitilesEntry(mode=16384, type="tree", id="1", name="clang-r100"),
            GitilesEntry(mode=16384, type="tree", id="2", name="clang-r101a"),
            GitilesEntry(mode=16384, type="tree", id="3", name="llvm"),
            GitilesEntry(mode=33188, type="blob", id="4", name="clang-r999"),
        ],
    )

    assert find_clang_revs(tree) == ["clang-r100", "clang-r101a"]

def test_fetch_tree_falls_back_after_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    tree = GitilesTree(id="root", entries=[])
    responses = iter(
        [
            GitilesHTTPError("missing", status_code=404),
            tree,
        ]
    )

    def fake_fetch_gitiles_tree(_url: str) -> GitilesTree:
        result = next(responses)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr("src.aosp.fetch_gitiles_tree", fake_fetch_gitiles_tree)

    branch, result = fetch_tree_from_branches(["first", "second"])

    assert branch == "second"
    assert result is tree


def test_archive_url_uses_gitiles_archive_endpoint() -> None:
    assert archive_url("main", "clang-r123") == (
        "https://android.googlesource.com/platform/prebuilts/clang/host/"
        "linux-x86/+archive/main/clang-r123.tar.gz"
    )


def test_fetch_gitiles_tree_wraps_http_status(monkeypatch: pytest.MonkeyPatch) -> None:
    response = requests.Response()
    response.status_code = 404

    def fake_get(_url: str, *, timeout: int) -> object:
        request = requests.Request("GET", "https://example.invalid/tree").prepare()
        raise requests.exceptions.HTTPError("missing", response=response, request=request)

    monkeypatch.setattr("src.aosp.requests.get", fake_get)

    with pytest.raises(GitilesHTTPError, match="HTTP 404 returned") as exc_info:
        fetch_gitiles_tree("https://example.invalid/tree")

    assert exc_info.value.status_code == 404


def test_fetch_gitiles_tree_rejects_missing_xssi_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        text = '{"id":"root","entries":[]}'

        @staticmethod
        def raise_for_status() -> None:
            return None

    monkeypatch.setattr("src.aosp.requests.get", lambda _url, *, timeout: FakeResponse())

    with pytest.raises(GitilesFormatError, match="expected Gitiles safety prefix"):
        fetch_gitiles_tree("https://example.invalid/tree")


def test_fetch_file_content_rejects_invalid_base64(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        text = "%%%not-base64%%%"

        @staticmethod
        def raise_for_status() -> None:
            return None

    monkeypatch.setattr("src.aosp.requests.get", lambda _url, *, timeout: FakeResponse())

    with pytest.raises(GitilesFormatError, match="Invalid encoded content"):
        fetch_file_content("main", "clang-r123", "BUILD_INFO")


def test_fetch_file_content_wraps_request_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(_url: str, *, timeout: int) -> object:
        raise requests.exceptions.Timeout("timed out")

    monkeypatch.setattr("src.aosp.requests.get", fake_get)

    with pytest.raises(GitilesError, match="Failed to fetch BUILD_INFO"):
        fetch_file_content("main", "clang-r123", "BUILD_INFO")


def test_fetch_metadata_rejects_invalid_build_info(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter(['{"bid": ""}', "Android clang version"])

    def fake_fetch_file_content(_branch: str, _latest_clang: str, _filename: str) -> str:
        return next(responses)

    monkeypatch.setattr("src.aosp.fetch_file_content", fake_fetch_file_content)

    with pytest.raises(GitilesFormatError, match="BUILD_INFO is not valid build metadata"):
        fetch_metadata("main", "clang-r123")


def test_fetch_metadata_rejects_empty_version_file(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter(['{"bid": "123"}', ""])

    def fake_fetch_file_content(_branch: str, _latest_clang: str, _filename: str) -> str:
        return next(responses)

    monkeypatch.setattr("src.aosp.fetch_file_content", fake_fetch_file_content)

    with pytest.raises(GitilesFormatError, match="does not contain a version"):
        fetch_metadata("main", "clang-r123")
