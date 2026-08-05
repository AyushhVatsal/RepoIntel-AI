from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import ParserBaseModel
from .enums import SymbolType, Visibility


class SourceLocation(ParserBaseModel):
    """
    Represents the location of a symbol within a source file.
    """

    start_line: int
    start_column: int

    end_line: int
    end_column: int


class Parameter(ParserBaseModel):
    """
    Represents a function or method parameter.

    Parameters are value objects and not standalone symbols.
    """

    name: str

    type_hint: str | None = None

    default_value: Any | None = None

    is_variadic: bool = False

    is_keyword_only: bool = False


class Field(ParserBaseModel):
    """
    Represents a class field.

    Fields are owned by a class and are not standalone symbols.
    """

    name: str

    type_hint: str | None = None

    default_value: Any | None = None


class BaseSymbol(ParserBaseModel):
    """
    Base class for every top-level symbol extracted by the parser.
    """

    symbol_id: str

    name: str

    qualified_name: str

    type: SymbolType

    location: SourceLocation

    documentation: str | None = None

    modifiers: set[str] = Field(default_factory=set)

    visibility: Visibility | None = None

    language: str | None = None

    parent_symbol: str | None = None


class ImportSymbol(BaseSymbol):
    """
    Represents an import statement.
    """

    module: str

    symbol: str | None = None

    alias: str | None = None

    is_relative: bool = False


class FunctionSymbol(BaseSymbol):
    """
    Represents a function or method.
    """

    parameters: list[Parameter] = Field(default_factory=list)

    return_type: str | None = None

    decorators: list[str] = Field(default_factory=list)

    is_async: bool = False

    is_generator: bool = False


class ClassSymbol(BaseSymbol):
    """
    Represents a type declaration.

    Depending on SymbolType this may represent:

    - Class
    - Struct
    - Interface
    - Enum
    """

    base_types: list[str] = Field(default_factory=list)

    interfaces: list[str] = Field(default_factory=list)

    namespace: str | None = None

    methods: list[FunctionSymbol] = Field(default_factory=list)

    fields: list[Field] = Field(default_factory=list)

    is_abstract: bool = False


class VariableSymbol(BaseSymbol):
    """
    Represents a module-level or global variable.
    """

    type_hint: str | None = None

    value: Any | None = None

    is_constant: bool = False