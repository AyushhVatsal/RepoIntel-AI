from __future__ import annotations


class CaptureNames:
    """
    Standardized Tree-sitter capture names.

    These names form the contract between:

        *.scm Queries
                ↓
        QueryExtractor
                ↓
        SymbolExtractor

    Every language-specific query must emit these standardized
    capture names so the SymbolExtractor remains language-agnostic.
    """

    # ==========================================================
    # Imports
    # ==========================================================

    IMPORT_STATEMENT = "import.statement"

    IMPORT_MODULE = "import.module"

    IMPORT_FROM = "import.from"

    IMPORT_NAME = "import.name"

    IMPORT_ALIAS = "import.alias"

    # ==========================================================
    # Classes
    # ==========================================================

    CLASS_DEFINITION = "class.definition"

    CLASS_NAME = "class.name"

    CLASS_BASE = "class.base"

    # ==========================================================
    # Functions
    # ==========================================================

    FUNCTION_DEFINITION = "function.definition"

    FUNCTION_NAME = "function.name"

    FUNCTION_RETURN_TYPE = "function.return_type"

    # ==========================================================
    # Parameters
    # ==========================================================

    PARAMETER_NAME = "parameter.name"

    # ==========================================================
    # Decorators
    # ==========================================================

    DECORATOR_NAME = "decorator.name"

    # ==========================================================
    # Variables
    # ==========================================================

    VARIABLE_DEFINITION = "variable.definition"

    VARIABLE_NAME = "variable.name"

    # ==========================================================
    # Docstrings
    # ==========================================================

    MODULE_DOCSTRING = "docstring.module"

    CLASS_DOCSTRING = "docstring.class"

    FUNCTION_DOCSTRING = "docstring.function"