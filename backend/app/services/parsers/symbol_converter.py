from app.schemas.repository_symbol import RepositorySymbolCreate
from app.services.parsers.models.symbols import (
    BaseSymbol,
    ClassSymbol,
    FunctionSymbol,
    ImportSymbol,
    SymbolType,
    VariableSymbol,
)


class SymbolConverter:
    """Convert parser IR symbols to database schemas."""

    @staticmethod
    def to_db_schema(
        symbol: BaseSymbol,
        repository_id: int,
        file_id: int,
    ) -> RepositorySymbolCreate:
        """Convert a parser symbol to database schema."""
        metadata = SymbolConverter._extract_metadata(symbol)

        return RepositorySymbolCreate(
            repository_id=repository_id,
            file_id=file_id,
            symbol_type=symbol.type.value,
            name=symbol.name,
            qualified_name=symbol.qualified_name,
            location={
                "start_line": symbol.location.start_line,
                "end_line": symbol.location.end_line,
                "start_column": symbol.location.start_column,
                "end_column": symbol.location.end_column,
            },
            symbol_metadata=metadata if metadata else None,
        )

    @staticmethod
    def _extract_metadata(symbol: BaseSymbol) -> dict:
        """Extract language-specific metadata from symbol."""
        metadata = {}

        # Add modifiers if present
        if symbol.modifiers:
            metadata["modifiers"] = list(symbol.modifiers)

        # Type-specific metadata
        if isinstance(symbol, FunctionSymbol):
            metadata.update({
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type_annotation,
                        "default_value": p.default_value,
                    }
                    for p in symbol.parameters
                ],
                "return_type": symbol.return_type,
                "decorators": symbol.decorators,
                "is_async": symbol.is_async,
                "is_generator": symbol.is_generator,
            })

        elif isinstance(symbol, ClassSymbol):
            metadata.update({
                "base_types": symbol.base_types,
                "interfaces": symbol.interfaces,
                "decorators": symbol.decorators,
                "method_count": len(symbol.methods),
                "field_count": len(symbol.fields),
            })

        elif isinstance(symbol, VariableSymbol):
            metadata.update({
                "type_annotation": symbol.type_annotation,
                "value": symbol.value,
                "is_constant": symbol.is_constant,
            })

        elif isinstance(symbol, ImportSymbol):
            metadata.update({
                "module": symbol.module,
                "imported_names": symbol.imported_names,
                "alias": symbol.alias,
                "is_from_import": symbol.is_from_import,
            })

        return metadata

    @staticmethod
    def convert_all(
        symbols: list[BaseSymbol],
        repository_id: int,
        file_id: int,
    ) -> list[RepositorySymbolCreate]:
        """Convert all symbols to database schemas."""
        return [
            SymbolConverter.to_db_schema(
                symbol=symbol,
                repository_id=repository_id,
                file_id=file_id,
            )
            for symbol in symbols
        ]
