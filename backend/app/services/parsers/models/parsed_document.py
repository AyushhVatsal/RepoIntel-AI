from __future__ import annotations

from typing import Any

from pydantic import Field

from app.models.repository_file import RepositoryFile

from .base import ParserBaseModel
from .symbols import BaseSymbol, SourceLocation


class Diagnostic(ParserBaseModel):
    """
    Represents a parser warning or error.
    """

    message: str

    location: SourceLocation | None = None


class ParsedDocument(ParserBaseModel):
    """
    Intermediate Representation (IR) of a parsed source file.
    """

    repository_file: RepositoryFile

    source_code: str

    symbols: list[BaseSymbol] = Field(default_factory=list)

    diagnostics: list[Diagnostic] = Field(default_factory=list)

    metadata: dict[str, Any] = Field(default_factory=dict)