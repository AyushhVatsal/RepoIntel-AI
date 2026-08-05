from __future__ import annotations

from app.models.repository_file import RepositoryFile

from .base import ParserBaseModel


class FileContent(ParserBaseModel):
    """
    Input object shared across the parsing pipeline.

    Repository Module reads the file once and passes the
    content to all downstream services.
    """

    repository_file: RepositoryFile

    content: bytes