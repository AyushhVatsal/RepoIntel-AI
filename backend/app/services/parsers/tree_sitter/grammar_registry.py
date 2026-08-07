from __future__ import annotations

from .grammar_config import GrammarConfig


class GrammarRegistry:
    """
    Registry containing Tree-sitter grammar mappings.

    Only languages that use the Tree-sitter parser are registered here.
    """

    _registry: dict[str, GrammarConfig] = {

        "python": GrammarConfig(

            class_node="class_definition",
            function_node="function_definition",
            constructor_node=None,
            function_expression_nodes=set(),
            namespace_node=None,

            annotation_node="decorator",
            decorated_definition_node="decorated_definition",

            async_node="async",
            generator_node="yield",

            class_name_field="name",
            function_name_field="name",

            parameter_field="parameters",
            return_type_field="return_type",

            superclass_field="superclasses",

            variable_left_field="left",
            variable_right_field="right",
        ),

        "java": GrammarConfig(

            class_node="class_declaration",

            function_node="method_declaration",

            constructor_node="constructor_declaration",

            function_expression_nodes=set(),

            namespace_node="package_declaration",

            annotation_node="annotation",

            decorated_definition_node=None,

            class_name_field="name",

            function_name_field="name",

            parameter_field="formal_parameters",

            return_type_field="type",

            superclass_field="superclass",

            variable_left_field="declarator",

            variable_right_field="value",
            async_node=None,
            generator_node=None,
        ),

        "javascript": GrammarConfig(

            class_node="class_declaration",

            interface_node=None,

            enum_node=None,

            function_node="method_definition",

            constructor_node="method_definition",

            function_expression_nodes={
                "function_expression",
                "arrow_function",
            },

            namespace_node=None,

            annotation_node=None,

            decorated_definition_node=None,

            async_node="async",

            generator_node="generator_function",

            class_name_field="name",

            function_name_field="name",

            constructor_name_field="name",

            parameter_field="parameters",

            return_type_field=None,

            superclass_field=None,

            interfaces_field=None,

            variable_left_field="name",

            variable_right_field="value",
        ),

        "typescript": GrammarConfig(

            class_node="class_declaration",

            interface_node="interface_declaration",

            enum_node="enum_declaration",

            function_node="function_declaration",

            constructor_node="constructor",

            function_expression_nodes={
                "function_expression",
                "arrow_function",
            },

            namespace_node=None,

            annotation_node="decorator",

            decorated_definition_node=None,

            class_name_field="name",

            function_name_field="name",

            constructor_name_field="name",

            parameter_field="parameters",

            return_type_field="return_type",

            superclass_field="class_heritage",

            interfaces_field="implements_clause",

            variable_left_field="left",

            variable_right_field="right",
            async_node=None,
            generator_node=None,
        ),
    }

    @classmethod
    def get(
        cls,
        language: str,
    ) -> GrammarConfig:

        try:
            return cls._registry[language.lower()]

        except KeyError:

            raise ValueError(
                f"No grammar registered for '{language}'."
            )

    @classmethod
    def is_registered(
        cls,
        language: str,
    ) -> bool:
        return language.lower() in cls._registry

    @classmethod
    def supported_languages(cls) -> list[str]:
        return sorted(cls._registry.keys())