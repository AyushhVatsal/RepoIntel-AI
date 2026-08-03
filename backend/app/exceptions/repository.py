class RepositoryError(Exception):
    """Base exception for repository-related errors."""


class InvalidRepositoryUrlError(RepositoryError):
    """Raised when a repository URL is invalid."""


class UnsupportedGitProviderError(RepositoryError):
    """Raised when the Git provider is not supported."""


class RepositoryCloneError(RepositoryError):
    """Raised when repository cloning fails."""


class RepositoryNotFoundError(RepositoryError):
    """Raised when a repository cannot be found."""


class RepositoryScanError(RepositoryError):
    """Raised when repository scanning fails."""


class RepositoryTooLargeError(RepositoryError):
    """Raised when the repository exceeds the allowed size."""


class FileTooLargeError(RepositoryError):
    """Raised when an individual file exceeds the allowed size."""

class RepositoryAlreadyExistsError(RepositoryError):
    """
    Raised when a repository has already been indexed.
    """