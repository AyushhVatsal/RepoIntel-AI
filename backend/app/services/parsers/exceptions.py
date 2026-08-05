class ParserError(Exception):
    """Base exception for parser errors."""


class UnsupportedLanguageError(ParserError):
    """Raised when the parser does not support a language."""


class TreeSitterParserError(ParserError):
    """Raised when Tree-sitter parsing fails."""


class QueryExecutionError(ParserError):
    """Raised when Tree-sitter query execution fails."""


class GenericParserError(ParserError):
    """Raised when the generic parser fails."""