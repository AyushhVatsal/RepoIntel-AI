from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import urlparse

from git import GitCommandError, Repo

from app.services.repository.constants import (
    CLONE_DIRECTORY,
    SUPPORTED_GIT_HOSTS,
)
from app.exceptions.repository import (
    InvalidRepositoryUrlError,
    RepositoryCloneError,
    UnsupportedGitProviderError
)


class CloneService:
    """Service responsible for cloning Git repositories."""

    def __init__(self) -> None:
        CLONE_DIRECTORY.mkdir(parents=True, exist_ok=True)

    def validate_url(self, github_url: str) -> None:
        """Validate that the URL belongs to a supported Git provider."""

        parsed = urlparse(github_url)

        if parsed.scheme not in {"http", "https"}:
            raise InvalidRepositoryUrlError(
                "Repository URL must use HTTP or HTTPS."
            )

        if parsed.netloc not in SUPPORTED_GIT_HOSTS:
            raise UnsupportedGitProviderError(
                f"Git provider '{parsed.netloc}' is not supported."
            )

    def get_repository_name(
        self,
        github_url: str,
    ) -> str:
        """
        Extract the repository name from a Git URL.
        """

        self.validate_url(github_url)

        return Path(
            urlparse(github_url).path
        ).stem
        
    def get_default_branch(
        self,
        repository_path: Path,
    ) -> str:
        """
        Get the default branch of a cloned repository.
        """

        repository = Repo(repository_path)

        return repository.active_branch.name
    
    def clone(
        self,
        github_url: str,
        repository_name: str,
    ) -> Path:
        """
        Clone a Git repository.

        Returns
        -------
        Path
            Local path of the cloned repository.
        """

        self.validate_url(github_url)

        clone_path = CLONE_DIRECTORY / repository_name

        if clone_path.exists():
            shutil.rmtree(clone_path)

        try:
            Repo.clone_from(
                github_url,
                clone_path,
            )

            return clone_path

        except GitCommandError as exc:
            if clone_path.exists():
                shutil.rmtree(clone_path)

            raise RepositoryCloneError(
                "Failed to clone repository."
            ) from exc


clone_service = CloneService()