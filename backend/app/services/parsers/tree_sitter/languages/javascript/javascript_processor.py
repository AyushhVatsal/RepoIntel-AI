from __future__ import annotations

from ..base_processor import BaseLanguageProcessor


class JavaScriptProcessor(BaseLanguageProcessor):
    """
    JavaScript-specific symbol enhancements.
    """

    @classmethod
    def process(
        cls,
        symbols: list,
        grouped: dict,
        source_code: str,
    ) -> list:

        cls._process_function_expressions(
            symbols,
            grouped,
            source_code,
        )

        cls._process_object_functions(
            symbols,
            grouped,
            source_code,
        )

        cls._process_async(
            symbols,
            grouped,
        )

        cls._process_generators(
            symbols,
            grouped,
        )

        cls._process_exports(
            symbols,
            grouped,
        )

        return symbols

    @classmethod
    def _process_function_expressions(
        cls,
        symbols: list,
        grouped: dict,
        source_code: str,
    ) -> None:
        """
        Handle arrow functions and function expressions assigned to variables.
        Example: const myFunc = () => {}

        These are captured as variables but should be marked as functions.
        """
        from app.services.parsers.models.enums import SymbolType

        for symbol in symbols:
            if symbol.type == SymbolType.VARIABLE:
                # Check if variable value looks like a function (arrow or function expression)
                if symbol.value and isinstance(symbol.value, str):
                    value_stripped = symbol.value.strip()
                    # Arrow function patterns: () => {}, (a, b) => {}, x => {}
                    # Function expression: function() {}, function name() {}
                    if ('=>' in value_stripped or
                        value_stripped.startswith('function') or
                        value_stripped.startswith('async')):
                        # Keep as variable but add metadata indicating it's a function
                        if 'function_like' not in symbol.modifiers:
                            symbol.modifiers.add('function_like')

    @classmethod
    def _process_object_functions(
        cls,
        symbols: list,
        grouped: dict,
        source_code: str,
    ) -> None:
        """
        Handle methods defined in object literals.
        Example: const obj = { method() {}, asyncMethod() {} }

        These are typically captured as variables but contain function definitions.
        """
        # Note: Most object methods are already captured by method_definition in queries
        # This is a placeholder for edge cases if needed
        pass

    @classmethod
    def _process_async(
        cls,
        symbols: list,
        grouped: dict,
    ) -> None:
        """
        Mark functions as async based on their source code.
        Example: async function fetchData() {}

        Tree-sitter should capture this, but this ensures consistency.
        """
        from app.services.parsers.models.enums import SymbolType

        for symbol in symbols:
            if symbol.type in (SymbolType.FUNCTION, SymbolType.METHOD):
                # Check if 'async' modifier exists or add it
                if 'async' in symbol.modifiers:
                    symbol.is_async = True

    @classmethod
    def _process_generators(
        cls,
        symbols: list,
        grouped: dict,
    ) -> None:
        """
        Mark functions as generators based on their source code.
        Example: function* generator() {}

        Generators have function* syntax in JavaScript.
        """
        from app.services.parsers.models.enums import SymbolType

        for symbol in symbols:
            if symbol.type in (SymbolType.FUNCTION, SymbolType.METHOD):
                # Check if 'generator' modifier exists or add it
                if 'generator' in symbol.modifiers or '*' in symbol.modifiers:
                    symbol.is_generator = True

    @classmethod
    def _process_exports(
        cls,
        symbols: list,
        grouped: dict,
    ) -> None:
        """
        Mark symbols as exported for ES6 export statements.
        Example: export const value = 42; export default MyClass;

        Adds 'exported' or 'default_export' to modifiers.
        """
        # Check if symbols have 'export' keyword in modifiers
        for symbol in symbols:
            if 'export' in symbol.modifiers:
                symbol.modifiers.add('exported')
            if 'default' in symbol.modifiers:
                symbol.modifiers.add('default_export')