from __future__ import annotations

import hashlib
from collections import defaultdict

from tree_sitter import Node

from app.services.parsers.models.enums import SymbolType
from app.services.parsers.models.symbols import (
    BaseSymbol,
    ClassSymbol,
    FunctionSymbol,
    ImportSymbol,
    Parameter,
    SourceLocation,
    VariableSymbol,
)

from .capture_names import CaptureNames
from .language_config import LanguageConfig


class SymbolExtractor:
    """
    Converts Tree-sitter captures into parser symbols.
    """

    @classmethod
    def extract(
        cls,
        captures: list[tuple[Node, str]],
        source_code: str,
        language_config: LanguageConfig,
    ) -> list[BaseSymbol]:

        grouped = cls._group_captures(captures)

        imports = cls._extract_imports(
            grouped,
            source_code,
            language_config,
        )

        classes, class_node_map = cls._extract_classes(
            grouped,
            source_code,
            language_config,
        )

        functions = cls._extract_functions(
            grouped,
            source_code,
            language_config,
            class_node_map,
        )

        variables = cls._extract_variables(
            grouped,
            source_code,
            language_config,
        )

        cls._attach_methods(
            class_node_map,
            functions,
        )

        symbols: list[BaseSymbol] = []

        symbols.extend(imports)
        symbols.extend(classes)

        # Only top-level functions should be returned.
        symbols.extend(
            function
            for function in functions
            if function.type == SymbolType.FUNCTION
        )

        symbols.extend(variables)

        return symbols

    # ==========================================================
    # Grouping
    # ==========================================================

    @staticmethod
    def _group_captures(
        captures: list[tuple[Node, str]],
    ) -> dict[str, list[Node]]:

        grouped: dict[str, list[Node]] = defaultdict(list)

        for node, capture in captures:
            grouped[capture].append(node)

        return grouped

    # ==========================================================
    # Imports
    # ==========================================================

    @classmethod
    def _extract_imports(
        cls,
        grouped: dict[str, list[Node]],
        source_code: str,
        language_config: LanguageConfig,
    ) -> list[ImportSymbol]:

        imports: list[ImportSymbol] = []

        import_statements = grouped.get(
            CaptureNames.IMPORT_STATEMENT,
            [],
        )

        if not import_statements:

            return cls._extract_imports_by_index_pairing(
                grouped,
                source_code,
                language_config,
            )

        for statement in import_statements:

            module = None
            symbol = None
            alias = None

            # ------------------------------------------------------
            # import x
            # import x as y
            # ------------------------------------------------------

            if statement.type == "import_statement":

                for child in statement.named_children:

                    if child.type == "dotted_name":

                        module = cls._text(
                            child,
                            source_code,
                        )

                    elif child.type == "aliased_import":

                        for grandchild in child.named_children:

                            if grandchild.type == "dotted_name":

                                module = cls._text(
                                    grandchild,
                                    source_code,
                                )

                            elif grandchild.type == "identifier":

                                alias = cls._text(
                                    grandchild,
                                    source_code,
                                )

            # ------------------------------------------------------
            # from x import y
            # from x import y as z
            # ------------------------------------------------------

            elif statement.type == "import_from_statement":

                module_node = statement.child_by_field_name(
                    "module_name",
                )

                if module_node is not None:

                    module = cls._text(
                        module_node,
                        source_code,
                    )

                for child in statement.named_children:

                    if child.type == "dotted_name":

                        if module is None:

                            module = cls._text(
                                child,
                                source_code,
                            )

                        else:

                            symbol = cls._text(
                                child,
                                source_code,
                            )

                    elif child.type == "aliased_import":

                        for grandchild in child.named_children:

                            if grandchild.type == "dotted_name":

                                symbol = cls._text(
                                    grandchild,
                                    source_code,
                                )

                            elif grandchild.type == "identifier":

                                alias = cls._text(
                                    grandchild,
                                    source_code,
                                )

            if module is None:
                continue

            qualified_name = (
                f"{module}.{symbol}"
                if symbol is not None
                else module
            )

            imports.append(

                ImportSymbol(

                    symbol_id=cls._symbol_id(
                        language_config.language,
                        qualified_name,
                    ),

                    name=(
                        symbol
                        if symbol is not None
                        else module.split(".")[-1]
                    ),

                    qualified_name=qualified_name,

                    type=SymbolType.IMPORT,

                    location=cls._location(
                        statement,
                    ),

                    language=language_config.language,

                    module=module,

                    symbol=symbol,

                    alias=alias,
                )
            )

        return imports

# TODO:
#! Remove this fallback once every supported language emits
#! IMPORT_STATEMENT captures in its Tree-sitter query.

    @classmethod
    def _extract_imports_by_index_pairing(
        cls,
        grouped: dict[str, list[Node]],
        source_code: str,
        language_config: LanguageConfig,
    ) -> list[ImportSymbol]:
        """
        Legacy fallback: pairs IMPORT_MODULE / IMPORT_ALIAS captures
        by index. Kept only for languages whose query doesn't yet
        emit a single IMPORT_STATEMENT capture. Prefer wiring
        IMPORT_STATEMENT in the language config's .scm query instead
        of relying on this.
        """


        imports: list[ImportSymbol] = []

        modules = grouped.get(CaptureNames.IMPORT_MODULE, [])
        aliases = grouped.get(CaptureNames.IMPORT_ALIAS, [])

        for index, module_node in enumerate(modules):

            module = cls._text(module_node, source_code)

            alias = None
            if index < len(aliases):
                alias = cls._text(aliases[index], source_code)

            imports.append(
                ImportSymbol(
                    symbol_id=cls._symbol_id(
                        language_config.language,
                        module,
                    ),
                    name=module.split(".")[-1],
                    qualified_name=module,
                    type=SymbolType.IMPORT,
                    location=cls._location(module_node),
                    language=language_config.language,
                    module=module,
                    alias=alias,
                )
            )

        return imports

    # ==========================================================
    # Helpers
    # ==========================================================

    @staticmethod
    def _text(
        node: Node,
        source_code: str,
    ) -> str:

        return source_code[
            node.start_byte: node.end_byte
        ]

    @staticmethod
    def _location(
        node: Node,
    ) -> SourceLocation:

        return SourceLocation(
            start_line=node.start_point.row + 1,
            start_column=node.start_point.column + 1,
            end_line=node.end_point.row + 1,
            end_column=node.end_point.column + 1,
        )

    @staticmethod
    def _symbol_id(
        language: str,
        qualified_name: str,
    ) -> str:

        return hashlib.sha1(
            f"{language}:{qualified_name}".encode()
        ).hexdigest()

    @staticmethod
    def _children(
        node: Node,
    ):

        return node.named_children

    @staticmethod
    def _child_by_field_name(
        node: Node,
        field: str,
    ) -> Node | None:

        return node.child_by_field_name(field)

    @classmethod
    def _find_parent_class(
        cls,
        node: Node,
    ) -> Node | None:

        current = node.parent

        while current is not None:

            if current.type == "class_definition":
                return current

            current = current.parent

        return None

    @classmethod
    def _is_async(
        cls,
        function_node: Node,
    ) -> bool:

        return (
            function_node.prev_named_sibling is not None
            and function_node.prev_named_sibling.type == "async"
        )

    # ==========================================================
    # Classes
    # ==========================================================

    @classmethod
    def _extract_classes(
        cls,
        grouped: dict[str, list[Node]],
        source_code: str,
        language_config: LanguageConfig,
    ) -> tuple[list[ClassSymbol], dict[Node, ClassSymbol]]:

        classes: list[ClassSymbol] = []

        # Maps Tree-sitter class nodes to their corresponding
        # ClassSymbol instances so methods can be attached later.

        class_node_map: dict[Node, ClassSymbol] = {}

        definitions = grouped.get(
            CaptureNames.CLASS_DEFINITION,
            [],
        )

        for class_node in definitions:

            name_node = cls._child_by_field_name(
                class_node,
                "name",
            )

            if name_node is None:
                continue

            class_name = cls._text(
                name_node,
                source_code,
            )

            qualified_name = class_name

            base_types: list[str] = []

            superclasses = cls._child_by_field_name(
                class_node,
                "superclasses",
            )

            if superclasses is not None:
                for child in cls._children(superclasses):
                    base_types.append(cls._text(child, source_code))

            documentation = cls._extract_docstring(
                class_node,
                grouped.get(CaptureNames.CLASS_DOCSTRING, []),
                source_code,
            )

            class_symbol = ClassSymbol(
                symbol_id=cls._symbol_id(
                    language_config.language,
                    qualified_name,
                ),
                name=class_name,
                qualified_name=qualified_name,
                type=SymbolType.CLASS,
                language=language_config.language,
                location=cls._location(class_node),
                documentation=documentation,
                base_types=base_types,
                interfaces=[],
                namespace=None,
                methods=[],
                fields=[],
                is_abstract=False,
                parent_symbol=None,
            )

            classes.append(class_symbol)
            class_node_map[class_node] = class_symbol

        return classes, class_node_map

    @classmethod
    def _extract_docstring(
        cls,
        parent: Node,
        docstring_nodes: list[Node],
        source_code: str,
    ) -> str | None:

        for node in docstring_nodes:

            if (
                node.start_byte >= parent.start_byte
                and node.end_byte <= parent.end_byte
            ):
                return cls._text(node, source_code).strip("\"'")

        return None

    # ==========================================================
    # Functions
    # ==========================================================

    @classmethod
    def _extract_functions(
        cls,
        grouped: dict[str, list[Node]],
        source_code: str,
        language_config: LanguageConfig,
        class_node_map: dict[Node, ClassSymbol],
    ) -> list[FunctionSymbol]:

        functions: list[FunctionSymbol] = []

        definitions = grouped.get(
            CaptureNames.FUNCTION_DEFINITION,
            [],
        )

        for function_node in definitions:

            name_node = cls._child_by_field_name(
                function_node,
                "name",
            )

            if name_node is None:
                continue

            function_name = cls._text(name_node, source_code)

            parent_class_node = cls._find_parent_class(function_node)
            parent_class_symbol = (
                class_node_map.get(parent_class_node)
                if parent_class_node is not None
                else None
            )

            symbol_type = (
                SymbolType.METHOD
                if parent_class_symbol is not None
                else SymbolType.FUNCTION
            )

            qualified_name = (
                f"{parent_class_symbol.qualified_name}.{function_name}"
                if parent_class_symbol is not None
                else function_name
            )

            parameters = cls._extract_parameters(
                function_node,
                source_code,
            )

            decorators = cls._extract_decorators(
                function_node,
                source_code,
            )

            return_type = None
            return_node = cls._child_by_field_name(
                function_node,
                "return_type",
            )
            if return_node is not None:
                return_type = cls._text(return_node, source_code)

            documentation = cls._extract_docstring(
                function_node,
                grouped.get(CaptureNames.FUNCTION_DOCSTRING, []),
                source_code,
            )

            functions.append(
                FunctionSymbol(
                    symbol_id=cls._symbol_id(
                        language_config.language,
                        qualified_name,
                    ),
                    name=function_name,
                    qualified_name=qualified_name,
                    type=symbol_type,
                    language=language_config.language,
                    location=cls._location(function_node),
                    documentation=documentation,
                    parameters=parameters,
                    decorators=decorators,
                    return_type=return_type,
                    is_async=cls._is_async(function_node),
                    is_generator=False,
                    parent_symbol=(
                        parent_class_symbol.symbol_id
                        if parent_class_symbol is not None
                        else None
                    ),
                )
            )

        return functions

    @classmethod
    def _attach_methods(
        cls,
        class_node_map: dict[Node, ClassSymbol],
        functions: list[FunctionSymbol],
    ) -> None:
        """
        Links METHOD-type functions back onto their owning
        ClassSymbol.methods list. Must run after both classes and
        functions have been extracted.
        """

        class_by_symbol_id = {
            class_symbol.symbol_id: class_symbol
            for class_symbol in class_node_map.values()
        }

        for function in functions:

            if function.type != SymbolType.METHOD:
                continue

            if function.parent_symbol is None:
                continue

            owning_class = class_by_symbol_id.get(function.parent_symbol)

            if owning_class is not None:
                owning_class.methods.append(function)

    # ==========================================================
    # Parameters
    # ==========================================================

    @classmethod
    def _extract_parameters(
        cls,
        function_node: Node,
        source_code: str,
    ) -> list[Parameter]:
        """
        Extracts parameters with type hint / default value /
        variadic / keyword-only metadata.

        NOTE: field names below (name/type/value) match the
        tree-sitter-python grammar as of the versions this was
        written against. If parameters come back empty for a
        grammar version bump, check the exact node/field names in
        the tree-sitter playground before assuming the extraction
        logic itself is wrong.
        """

        parameters: list[Parameter] = []

        parameter_list = cls._child_by_field_name(
            function_node,
            "parameters",
        )

        if parameter_list is None:
            return parameters

        for node in parameter_list.named_children:

            is_variadic = False
            is_keyword_only = False
            type_hint = None
            default_value = None

            if node.type == "identifier":
                identifier = node

            elif node.type == "list_splat_pattern":
                is_variadic = True
                identifier = node.named_children[0] if node.named_children else None

            elif node.type == "dictionary_splat_pattern":
                is_keyword_only = True
                identifier = node.named_children[0] if node.named_children else None

            elif node.type in (
                "typed_parameter",
                "default_parameter",
                "typed_default_parameter",
            ):
                identifier = (
                    node.child_by_field_name("name")
                    or next(
                        (c for c in node.named_children if c.type == "identifier"),
                        None,
                    )
                )

                type_node = node.child_by_field_name("type")
                if type_node is not None:
                    type_hint = cls._text(type_node, source_code)

                value_node = node.child_by_field_name("value")
                if value_node is not None:
                    default_value = cls._text(value_node, source_code)

            else:
                identifier = node.child_by_field_name("name")

                if identifier is None:
                    for child in node.named_children:
                        if child.type == "identifier":
                            identifier = child
                            break

            if identifier is None:
                continue

            parameters.append(
                Parameter(
                    name=cls._text(identifier, source_code),
                    type_hint=type_hint,
                    default_value=default_value,
                    is_variadic=is_variadic,
                    is_keyword_only=is_keyword_only,
                )
            )

        return parameters

    # ==========================================================
    # Decorators
    # ==========================================================

    @classmethod
    def _extract_decorators(
        cls,
        function_node: Node,
        source_code: str,
    ) -> list[str]:
        """
        Extracts decorator names without call arguments, e.g.
        `@router.get("/")` -> "router.get", not `router.get("/")`.
        """

        parent = function_node.parent

        if parent is None:
            return []

        if parent.type != "decorated_definition":
            return []

        decorators: list[str] = []

        for child in parent.named_children:

            if child.type != "decorator":
                continue

            named = child.named_children

            if not named:
                continue

            expression = named[-1]

            if expression.type == "call":
                target = (
                    expression.child_by_field_name("function")
                    or expression
                )
            else:
                target = expression

            decorators.append(
                cls._text(target, source_code)
            )

        return decorators

    # ==========================================================
    # Variables
    # ==========================================================

    @classmethod
    def _extract_variables(
        cls,
        grouped: dict[str, list[Node]],
        source_code: str,
        language_config: LanguageConfig,
    ) -> list[VariableSymbol]:

        variables: list[VariableSymbol] = []

        definitions = grouped.get(
            CaptureNames.VARIABLE_DEFINITION,
            [],
        )

        for variable_node in definitions:

            name_node = cls._child_by_field_name(variable_node, "left")

            if name_node is None:
                for child in variable_node.named_children:
                    if child.type == "identifier":
                        name_node = child
                        break

            if name_node is None:
                continue

            variable_name = cls._text(name_node, source_code)

            value_node = cls._child_by_field_name(variable_node, "right")
            value = (
                cls._text(value_node, source_code)
                if value_node is not None
                else None
            )

            is_constant = (
                variable_name.isupper()
                or (
                    variable_name.startswith("__")
                    and variable_name.endswith("__")
                )
            )

            variables.append(
                VariableSymbol(
                    symbol_id=cls._symbol_id(
                        language_config.language,
                        variable_name,
                    ),
                    name=variable_name,
                    qualified_name=variable_name,
                    type=SymbolType.VARIABLE,
                    language=language_config.language,
                    location=cls._location(variable_node),
                    type_hint=None,
                    value=value,
                    is_constant=is_constant,
                )
            )

        return variables