from __future__ import annotations

from app.services.parsers.models.base import ParserBaseModel

from dataclasses import field

class GrammarConfig(ParserBaseModel):
    """
    Describes how a Tree-sitter grammar maps to RepoIntel's
    semantic parser.

    GrammarConfig contains only grammar metadata
    (node names and field names).

    It must never contain parsing logic.
    """

    # ==========================================================
    # Node Types
    # ==========================================================

    namespace_node: str | None = None

    class_node: str | None = None

    interface_node: str | None = None

    enum_node: str | None = None

    function_node: str | None = None

    constructor_node: str | None = None

    annotation_node: str | None = None

    decorated_definition_node: str | None = None

    async_node: str | None = None

    generator_node: str | None = None

    # ==========================================================
    # Field Names
    # ==========================================================

    class_name_field: str = "name"

    function_name_field: str = "name"

    constructor_name_field: str = "name"

    superclass_field: str | None = None

    interfaces_field: str | None = None

    parameter_field: str | None = None

    return_type_field: str | None = None

    variable_left_field: str | None = None

    variable_right_field: str | None = None
    
    modifiers_field: str | None = None

    modifier_node: str | None = "modifiers"

    function_expression_nodes: set[str] = field(
        default_factory=set
    )
