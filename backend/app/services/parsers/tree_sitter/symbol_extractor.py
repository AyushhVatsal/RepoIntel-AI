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
from .grammar_config import GrammarConfig

from app.services.parsers.models.symbols import Visibility

from app.services.parsers.tree_sitter.languages.javascript.javascript_processor import (
    JavaScriptProcessor,
)


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
        grammar_config: GrammarConfig,
    ) -> list[BaseSymbol]:

        grouped = cls._group_captures(captures)

        namespace = cls._extract_namespace(
            grouped,
            source_code,
        )

        imports = cls._extract_imports(
            grouped,
            source_code,
            language_config,
        )

        classes, class_node_map = cls._extract_classes(
            grammar_config,
            grouped,
            source_code,
            language_config,
            namespace,
        )

        functions = cls._extract_functions(
            grouped,
            source_code,
            language_config,
            grammar_config,
            class_node_map,
            namespace
        )

        variables = cls._extract_variables(
            grouped,
            source_code,
            grammar_config,
            language_config,
            namespace,
            class_node_map,
        )

        cls._extract_constructors(
            grouped,
            source_code,
            language_config,
            grammar_config,
            class_node_map,
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

        return symbols, grouped

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
        field: str | None,
    ) -> Node | None:
        if field is None:
            return None

        return node.child_by_field_name(field)

    @classmethod
    def _find_parent_class(
        cls,
        node: Node,
        grammar: GrammarConfig,
    ) -> Node | None:

        current = node.parent

        while current is not None:

            supported_nodes = {
                grammar.class_node,
                grammar.interface_node,
                grammar.enum_node,
            }
            supported_nodes.discard(None)

            if current.type in supported_nodes:
                return current

            current = current.parent

        return None

    @classmethod
    def _is_async(
        cls,
        function_node: Node,
        grammar_config: GrammarConfig,
    ) -> bool:

        return cls._has_child(
            function_node,
            grammar_config.async_node,
        )

    @classmethod
    def _has_child(
        cls,
        node: Node,
        node_type: str | None,
    ) -> bool:

        if node_type is None:
            return False

        return any(
            child.type == node_type
            for child in node.children
        )

    @classmethod
    def _capture(
        cls,
        grouped: dict[str, list[Node]],
        capture: str,
    ) -> Node | None:

        nodes = grouped.get(capture)

        if not nodes:
            return None

        return nodes[0]

    @classmethod
    def _find_nodes(
        cls,
        node: Node,
        node_type: str | None,
    ) -> list[Node]:

        if node_type is None:
            return []

        nodes: list[Node] = []

        if node.type == node_type:
            nodes.append(node)

        for child in node.named_children:
            nodes.extend(
                cls._find_nodes(
                    child,
                    node_type,
                )
            )

        return nodes

    @classmethod
    def _modifier_nodes(
        cls,
        node: Node,
        grammar_config: GrammarConfig,
    ) -> list[Node]:

        if grammar_config.modifier_node is None:
            return []

        return cls._find_nodes(
            node,
            grammar_config.modifier_node,
        )

    @classmethod
    def _extract_visibility(
        cls,
        node: Node,
        grammar_config: GrammarConfig,
    ) -> Visibility | None:

        for modifier_node in cls._modifier_nodes(
            node,
            grammar_config,
        ):

            for child in modifier_node.named_children:

                match child.type:

                    case "public":
                        return Visibility.PUBLIC

                    case "private":
                        return Visibility.PRIVATE

                    case "protected":
                        return Visibility.PROTECTED

        return None

    @classmethod
    def _extract_modifiers(
        cls,
        node: Node,
        grammar_config: GrammarConfig,
    ) -> set[str]:

        modifiers: set[str] = set()

        for modifier_node in cls._modifier_nodes(
            node,
            grammar_config,
        ):

            for child in modifier_node.named_children:

                if child.type in (
                    "marker_annotation",
                    "annotation",
                    "decorator",
                ):
                    continue

                modifiers.add(child.type)

        return modifiers

    @classmethod
    def _extract_namespace(
        cls,
        grouped: dict[str, list[Node]],
        source_code: str,
    ) -> str | None:
        """
        Extracts the module / package namespace for the current file.
        """

        namespace_node = cls._capture(
            grouped,
            CaptureNames.NAMESPACE_NAME,
        )

        if namespace_node is None:
            return None

        return cls._text(
            namespace_node,
            source_code,
        )

    @classmethod
    def _is_function_value(
        cls,
        value_node: Node | None,
        grammar_config: GrammarConfig,
    ) -> bool:

        if value_node is None:
            return False

        return (
            value_node.type
            in grammar_config.function_expression_nodes
        )

    @classmethod
    def _create_function_symbol(
        cls,
        function_node: Node,
        function_name: str,
        source_code: str,
        language_config: LanguageConfig,
        grammar_config: GrammarConfig,
        parent_class_symbol: ClassSymbol | None,
    ) -> FunctionSymbol:

        parameters = cls._extract_parameters(
            function_node,
            grammar_config,
            source_code,
        )

        decorators = cls._extract_annotations(
            grammar_config,
            function_node,
            source_code,
        )

        modifiers = cls._extract_modifiers(
            function_node,
            grammar_config,
        )

        documentation = cls._extract_documentation(
            function_node,
            source_code,
        )

        return_type = cls._extract_return_type(
            function_node,
            grammar_config,
            source_code,
        )

        visibility = cls._extract_visibility(
            modifiers,
        )

        symbol_type = (
            SymbolType.METHOD
            if parent_class_symbol is not None
            else SymbolType.FUNCTION
        )

        return FunctionSymbol(
            symbol_id=cls._symbol_id(
                language_config.language,
                function_name,
            ),
            name=function_name,
            qualified_name=(
                f"{parent_class_symbol.qualified_name}.{function_name}"
                if parent_class_symbol is not None
                else function_name
            ),
            type=symbol_type,
            language=language_config.language,
            location=cls._location(function_node),
            documentation=documentation,
            modifiers=modifiers,
            visibility=visibility,
            parent_symbol=(
                parent_class_symbol.symbol_id
                if parent_class_symbol is not None
                else None
            ),
            parameters=parameters,
            return_type=return_type,
            decorators=decorators,
            is_async=cls._is_async(
                function_node,
                grammar_config,
            ),
            is_generator=cls._is_generator(
                function_node,
                grammar_config,
            ),
        )
        
    # ==========================================================
    # Classes
    # ==========================================================

    @classmethod
    def _extract_classes(
        cls,
        grammar_config: GrammarConfig,
        grouped: dict[str, list[Node]],
        source_code: str,
        language_config: LanguageConfig,
        namespace: str | None,
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
                grammar_config.class_name_field,
            )

            if name_node is None:
                continue

            class_name = cls._text(
                name_node,
                source_code,
            )

            qualified_name = class_name

            base_types: list[str] = []

            interfaces: list[str] = []

            superclasses = cls._child_by_field_name(
                class_node,
                grammar_config.superclass_field,
            )

            if superclasses is not None:
                for child in cls._children(superclasses):
                    base_types.append(cls._text(child, source_code))

            interfaces_node = (
                cls._child_by_field_name(
                    class_node,
                    grammar_config.interfaces_field,
                )
                if grammar_config.interfaces_field is not None
                else None
            )

            if interfaces_node is not None:
                for child in cls._children(interfaces_node):
                    interfaces.append(
                        cls._text(child, source_code)
                    )

            documentation = cls._extract_documentation(
                class_node,
                grouped.get(
                    CaptureNames.CLASS_DOCUMENTATION,
                    [],
                ),
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
                interfaces=interfaces,
                namespace=namespace,
                methods=[],
                fields=[],
                is_abstract=False,
                parent_symbol=None,
            )

            classes.append(class_symbol)
            class_node_map[class_node] = class_symbol

        return classes, class_node_map

    @classmethod
    def _extract_documentation(
        cls,
        parent: Node,
        documentation_nodes: list[Node],
        source_code: str,
    ) -> str | None:

        for node in documentation_nodes:

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
        grammar_config: GrammarConfig,
        class_node_map: dict[Node, ClassSymbol],
        namespace: str | None,
    ) -> list[FunctionSymbol]:

        functions: list[FunctionSymbol] = []

        definitions = grouped.get(
            CaptureNames.FUNCTION_DEFINITION,
            [],
        )

        for function_node in definitions:

            name_node = cls._child_by_field_name(
                function_node,
                grammar_config.function_name_field,
            )

            if name_node is None:
                continue

            function_name = cls._text(name_node, source_code)

            parent_class_node = cls._find_parent_class(function_node, grammar_config)
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
                grammar_config,
                source_code,
            )

            annotations = cls._extract_annotations(
                grammar_config,
                function_node,
                source_code,
            )

            return_type = None
            return_node = cls._child_by_field_name(
                function_node,
                grammar_config.return_type_field,
            )
            if return_node is not None:
                return_type = cls._text(return_node, source_code)

            documentation = cls._extract_documentation(
                function_node,
                grouped.get(
                    CaptureNames.FUNCTION_DOCUMENTATION,
                    [],
                ),
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
                    decorators=annotations,
                    return_type=return_type,
                    is_async=cls._is_async(function_node, grammar_config),
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
    # Constructors
    # ==========================================================

    @classmethod
    def _extract_constructors(
        cls,
        grouped: dict[str, list[Node]],
        source_code: str,
        language_config: LanguageConfig,
        grammar_config: GrammarConfig,
        class_node_map: dict[Node, ClassSymbol],
    ) -> list[FunctionSymbol]:
        constructors: list[FunctionSymbol] = []
        
        definitions = grouped.get(
            CaptureNames.CONSTRUCTOR_DEFINITION,
            [],
        )

        for constructor_node in definitions:
                    
                    name_node = cls._child_by_field_name(
                        constructor_node,
                        grammar_config.constructor_name_field,
                    )

                    if name_node is None:
                        continue

                    constructor_name = cls._text(
                        name_node,
                        source_code,
                    )            
                    parent_class_node = cls._find_parent_class(
                        constructor_node,
                        grammar_config,
                    )

                    parent_class_symbol = (
                        class_node_map.get(parent_class_node)
                        if parent_class_node is not None
                        else None
                    )

                    if parent_class_symbol is None:
                        continue

                    parameters = cls._extract_parameters(
                        constructor_node,
                        grammar_config,
                        source_code,
                    )

                    decorators = cls._extract_annotations(
                        grammar_config,
                        constructor_node,
                        source_code,
                    )

                    constructor_symbol = FunctionSymbol(
                        symbol_id=cls._symbol_id(
                            language_config.language,
                            f"{parent_class_symbol.qualified_name}.{constructor_name}",
                        ),
                        name=constructor_name,
                        qualified_name=f"{parent_class_symbol.qualified_name}.{constructor_name}",
                        type=SymbolType.CONSTRUCTOR,
                        language=language_config.language,
                        location=cls._location(constructor_node),
                        documentation=None,
                        parameters=parameters,
                        decorators=decorators,
                        return_type=None,
                        is_async=False,
                        is_generator=False,
                        parent_symbol=parent_class_symbol.symbol_id,
                    )

                    parent_class_symbol.methods.append(
                        constructor_symbol
                    )

                    constructors.append(
                        constructor_symbol
                    )

        return constructors
    
    # ==========================================================
    # Parameters
    # ==========================================================

    @classmethod
    def _extract_parameters(
        cls,
        function_node: Node,
        grammar_config: GrammarConfig,
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
            grammar_config.parameter_field,
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
                identifier = (
                    node.named_children[0]
                    if node.named_children
                    else None
                )

            else:
                identifier = (
                    node.child_by_field_name("name")
                    or next(
                        (
                            child
                            for child in node.named_children
                            if child.type == "identifier"
                        ),
                        None,
                    )
                )

                type_node = node.child_by_field_name("type")
                if type_node is not None:
                    type_hint = cls._text(type_node, source_code)

                value_node = node.child_by_field_name("value")
                if value_node is not None:
                    default_value = cls._text(value_node, source_code)

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
    def _extract_annotations(
        cls,
        grammar_config: GrammarConfig,
        function_node: Node,
        source_code: str,
    ) -> list[str]:
        """
        Extracts decorator names without call arguments, e.g.
        `@router.get("/")` -> "router.get", not `router.get("/")`.
        """

        annotations: list[str] = []

        search_node = function_node

        if (
            grammar_config.decorated_definition_node
            and function_node.parent is not None
            and function_node.parent.type == grammar_config.decorated_definition_node
        ):
            search_node = function_node.parent

        for child in cls._find_nodes(
            search_node,
            grammar_config.annotation_node,
        ):
            if child.type != grammar_config.annotation_node:
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

            annotations.append(
                cls._text(target, source_code)
            )

        return annotations

    # ==========================================================
    # Variables
    # ==========================================================

    @classmethod
    def _extract_variables(
        cls,
        grouped,
        source_code,
        grammar_config,
        language_config,
        namespace,
        class_node_map: dict[Node, ClassSymbol],
    ) -> list[VariableSymbol]:

        variables: list[VariableSymbol] = []

        definitions = grouped.get(
            CaptureNames.VARIABLE_DEFINITION,
            [],
        )

        for variable_node in definitions:

            name_node = cls._child_by_field_name(variable_node, grammar_config.variable_left_field,)

            # If the grammar returns a declarator node instead of the
            # identifier directly (Java/JS/TS), descend once.

            if (
                name_node is not None
                and name_node.child_by_field_name("name") is not None
            ):
                name_node = name_node.child_by_field_name("name")

            if name_node is None:
                for child in variable_node.named_children:
                    if child.type == "identifier":
                        name_node = child
                        break

            if name_node is None:
                continue

            variable_name = cls._text(name_node, source_code)

            type_hint = None

            for node in grouped.get(
                CaptureNames.VARIABLE_TYPE,
                [],
            ):
                if (
                    node.start_byte >= variable_node.start_byte
                    and node.end_byte <= variable_node.end_byte
                ):
                    type_hint = cls._text(node, source_code)
                    break

            value_parent = cls._child_by_field_name(
                variable_node,
                grammar_config.variable_left_field,
            )

            if (
                value_parent is not None
                and value_parent.child_by_field_name(
                    grammar_config.variable_right_field
                ) is not None
            ):
                value_node = value_parent.child_by_field_name(
                    grammar_config.variable_right_field
                )
            else:
                value_node = cls._child_by_field_name(
                    variable_node,
                    grammar_config.variable_right_field,
                )

            if cls._is_function_value(
                value_node,
                grammar_config,
            ):
                print("Function Value:", variable_name)    

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

            parent_class_node = cls._find_parent_class(
                variable_node,
                grammar_config,
            )

            parent_class_symbol = (
                class_node_map.get(parent_class_node)
                if parent_class_node is not None
                else None
            )

            variable_symbol = VariableSymbol(
            symbol_id=cls._symbol_id(
                language_config.language,
                variable_name,
            ),
            name=variable_name,
            qualified_name=variable_name,
            type=SymbolType.VARIABLE,
            language=language_config.language,
            location=cls._location(variable_node),
            type_hint=type_hint,
            value=value,
            is_constant=is_constant,
            parent_symbol=(
                parent_class_symbol.symbol_id
                if parent_class_symbol is not None
                else None
            ),
        )

        if parent_class_symbol is not None:
            parent_class_symbol.fields.append(
                variable_symbol
            )
        else:
            variables.append(variable_symbol)

        return variables