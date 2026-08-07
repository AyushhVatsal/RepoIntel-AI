from __future__ import annotations


class CaptureNames:
    """
    Standardized semantic Tree-sitter capture names.

    These names form the contract between

        *.scm Queries
                ↓
        QueryExtractor
                ↓
        SymbolExtractor

    Every Tier 1 language must emit these semantic capture
    names regardless of its underlying grammar.
    """


    # ==========================================================
    # Interfaces
    # ==========================================================

    INTERFACE_DEFINITION = "interface.definition"

    INTERFACE_NAME = "interface.name"

    # ==========================================================
    # Enums
    # ==========================================================

    ENUM_DEFINITION = "enum.definition"

    ENUM_NAME = "enum.name"

    # ==========================================================
    # Constructors
    # ==========================================================

    CONSTRUCTOR_DEFINITION = "constructor.definition"

    CONSTRUCTOR_NAME = "constructor.name"

    # ==========================================================
    # Namespace
    # ==========================================================

    NAMESPACE_NAME = "namespace.name"

    # ==========================================================
    # Imports
    # ==========================================================

    IMPORT_STATEMENT = "import.statement"

    IMPORT_MODULE = "import.module"

    IMPORT_FROM = "import.from"

    IMPORT_NAME = "import.name"

    IMPORT_ALIAS = "import.alias"

    IMPORT_STATIC = "import.static"

    # ==========================================================
    # Classes / Types
    # ==========================================================

    CLASS_DEFINITION = "class.definition"

    CLASS_NAME = "class.name"

    CLASS_BASE = "class.base"

    # ==========================================================
    # Functions / Methods
    # ==========================================================

    FUNCTION_DEFINITION = "function.definition"

    FUNCTION_NAME = "function.name"

    FUNCTION_RETURN_TYPE = "function.return_type"

    FUNCTION_ASYNC = "function.async"

    FUNCTION_GENERATOR = "function.generator"

    # ==========================================================
    # Parameters
    # ==========================================================

    PARAMETER_NAME = "parameter.name"

    PARAMETER_TYPE = "parameter.type"

    PARAMETER_DEFAULT = "parameter.default"

    # ==========================================================
    # Annotations
    # ==========================================================

    ANNOTATION_NAME = "annotation.name"

    # ==========================================================
    # Variables / Fields
    # ==========================================================

    VARIABLE_DEFINITION = "variable.definition"

    VARIABLE_NAME = "variable.name"

    VARIABLE_TYPE = "variable.type"

    VARIABLE_VALUE = "variable.value"

    # ==========================================================
    # Documentation
    # ==========================================================

    MODULE_DOCUMENTATION = "documentation.module"

    CLASS_DOCUMENTATION = "documentation.class"

    FUNCTION_DOCUMENTATION = "documentation.function"