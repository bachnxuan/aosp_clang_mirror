import os
import subprocess
from pathlib import Path

from src.error import ConfigError
from src.logger import LOGGER as logger


def tag_exists(tag: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "tag", "--list", tag],
            capture_output=True,
            text=True,
            check=True,
        )
        return bool(result.stdout.strip())
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError("Failed to inspect local Git tags") from error


def github_repo_url() -> str:
    repo_url = os.getenv("GITHUB_REPO_URL", "").strip().rstrip("/")

    if not repo_url:
        raise ConfigError("GITHUB_REPO_URL is required")

    return repo_url


def create_github_release(tag_name: str, file_path: Path) -> None:
    logger.info("Creating GitHub release for tag %s...", tag_name)
    try:
        subprocess.run(
            [
                "gh",
                "release",
                "create",
                tag_name,
                str(file_path),
                "--title",
                f"Clang prebuilts {tag_name}",
                "--notes",
                "Automated release asset",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Successfully created GitHub release and uploaded asset.")
    except OSError as error:
        raise RuntimeError("Failed to execute gh release create") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or str(error)
        raise RuntimeError(f"gh release create failed: {detail}") from error
