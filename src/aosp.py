import base64
import binascii
import re
import subprocess
from pathlib import Path
from typing import Final, Sequence

import requests
from pydantic import ValidationError

from src.error import GitilesError, GitilesFormatError, GitilesHTTPError
from src.logger import LOGGER as logger
from src.models import BuildInfo, GitilesTree

AOSP_BASE_URL: Final[str] = (
    "https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+"
)
BRANCHES: Final[list[str]] = ["mirror-goog-main-llvm-toolchain-source", "main"]
XSSI_PREFIX: Final[str] = ")]}'"
REQUEST_TIMEOUT: Final[int] = 60


def archive_url(branch: str, revision: str) -> str:
    archive_base = AOSP_BASE_URL.replace("/+", "/+archive")
    return f"{archive_base}/{branch}/{revision}.tar.gz"


def fetch_gitiles_tree(url: str) -> GitilesTree:
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 0
        raise GitilesHTTPError(
            f"HTTP {status} returned for {url}",
            status_code=status,
        ) from e
    except requests.exceptions.RequestException as e:
        raise GitilesError(f"Connection error requesting {url}") from e

    text = response.text

    if not text.startswith(XSSI_PREFIX):
        raise GitilesFormatError("Response is missing the expected Gitiles safety prefix")

    text = text.removeprefix(XSSI_PREFIX).lstrip()

    try:
        return GitilesTree.model_validate_json(text)
    except ValidationError as e:
        raise GitilesFormatError(
            "Failed to validate Gitiles JSON schema against GitilesTree model"
        ) from e


def fetch_tree_from_branches(
    branches: Sequence[str] = BRANCHES,
) -> tuple[str, GitilesTree]:
    last_error: GitilesError | None = None

    for branch in branches:
        url = f"{AOSP_BASE_URL}/{branch}/?format=JSON"
        logger.info("Fetching tree from AOSP branch: %s", branch)

        try:
            tree = fetch_gitiles_tree(url)
        except GitilesFormatError:
            logger.exception(
                "Gitiles API format change detected on branch %s",
                branch,
            )
            raise
        except GitilesHTTPError as e:
            logger.warning(
                "Branch %s returned HTTP %s. Trying next branch...",
                branch,
                e.status_code,
            )
            last_error = e
        except GitilesError as e:
            logger.warning(
                "Failed to fetch branch %s: %s. Trying next branch...",
                branch,
                e,
            )
            last_error = e
        else:
            logger.info("Successfully fetched tree from branch: %s", branch)
            return branch, tree

    if last_error is not None:
        raise GitilesError("All AOSP branches failed to fetch tree info") from last_error

    raise GitilesError("No AOSP branches configured")


def find_clang_revs(tree: GitilesTree) -> list[str]:
    clang_revs: list[str] = []
    pattern = re.compile(r"^clang-r\d+[a-z]?$")
    for entry in tree.entries:
        if entry.type == "tree" and pattern.match(entry.name):
            clang_revs.append(entry.name)
    if not clang_revs:
        raise GitilesError("No Clang revisions found")
    return clang_revs


def clang_key(name: str) -> tuple[int, str]:
    match = re.fullmatch(r"clang-r(\d+)([a-z]?)", name)
    if match is None:
        raise ValueError(f"Invalid Clang name format: {name}")
    return int(match.group(1)), match.group(2)


def fetch_file_content(branch: str, latest_clang: str, filename: str) -> str:
    url = f"{AOSP_BASE_URL}/{branch}/{latest_clang}/{filename}?format=TEXT"
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return base64.b64decode(response.text, validate=True).decode("utf-8")
    except requests.RequestException as error:
        raise GitilesError(f"Failed to fetch {filename} from {url}") from error
    except (binascii.Error, UnicodeDecodeError) as error:
        raise GitilesFormatError(f"Invalid encoded content returned for {filename}") from error


def fetch_metadata(branch: str, latest_clang: str) -> tuple[str, str]:
    logger.info("Fetching build info for %s...", latest_clang)
    build_info_text = fetch_file_content(branch, latest_clang, "BUILD_INFO")

    try:
        build_info = BuildInfo.model_validate_json(build_info_text)
    except ValidationError as error:
        raise GitilesFormatError("BUILD_INFO is not valid build metadata") from error
    build_id = build_info.bid

    logger.info("Fetching version info for %s...", latest_clang)
    version_text = fetch_file_content(branch, latest_clang, "AndroidVersion.txt")
    version_lines = version_text.splitlines()
    if not version_lines or not (clang_version := version_lines[0].strip()):
        raise GitilesFormatError("AndroidVersion.txt does not contain a version")

    return build_id, clang_version


def download_tarball(url: str, dest_path: Path) -> None:
    logger.info("Downloading tarball from %s...", url)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = dest_path.with_suffix(dest_path.suffix + ".part")
    try:
        subprocess.run(
            [
                "curl",
                "-fL",
                "--retry",
                "5",
                "--retry-delay",
                "5",
                "--retry-all-errors",
                "-o",
                str(partial_path),
                url,
            ],
            check=True,
        )
        partial_path.replace(dest_path)
        logger.info("Successfully downloaded to %s", dest_path)
    except subprocess.CalledProcessError as e:
        partial_path.unlink(missing_ok=True)
        raise RuntimeError(f"curl download failed with exit code {e.returncode}") from e
