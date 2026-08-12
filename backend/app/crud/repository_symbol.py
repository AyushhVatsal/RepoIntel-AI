
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.repository_symbol import RepositorySymbol
from app.schemas.repository_symbol import RepositorySymbolCreate


class RepositorySymbolCRUD:
    """CRUD operations for repository symbols."""

    def create_many(
        self,
        db: Session,
        symbols: list[RepositorySymbolCreate],
    ) -> list[RepositorySymbol]:
        """Bulk insert symbols for a file."""
        db_symbols = [
            RepositorySymbol(**s.model_dump())
            for s in symbols
        ]
        db.add_all(db_symbols)
        db.commit()
        for symbol in db_symbols:
            db.refresh(symbol)
        return db_symbols

    def get_by_repository(
        self,
        db: Session,
        repository_id: int,
        symbol_type: str | None = None,
    ) -> list[RepositorySymbol]:
        """Get all symbols for a repository, optionally filtered by type."""
        stmt = select(RepositorySymbol).where(
            RepositorySymbol.repository_id == repository_id
        )
        if symbol_type:
            stmt = stmt.where(RepositorySymbol.symbol_type == symbol_type)
        return list(db.scalars(stmt).all())

    def get_by_file(
        self,
        db: Session,
        file_id: int,
    ) -> list[RepositorySymbol]:
        """Get all symbols for a specific file."""
        stmt = select(RepositorySymbol).where(
            RepositorySymbol.file_id == file_id
        )
        return list(db.scalars(stmt).all())

    def delete_by_repository(
        self,
        db: Session,
        repository_id: int,
    ) -> None:
        """Delete all symbols for a repository."""
        stmt = delete(RepositorySymbol).where(
            RepositorySymbol.repository_id == repository_id
        )
        db.execute(stmt)
        db.commit()

    def delete_by_file(
        self,
        db: Session,
        file_id: int,
    ) -> None:
        """Delete all symbols for a file."""
        stmt = delete(RepositorySymbol).where(
            RepositorySymbol.file_id == file_id
        )
        db.execute(stmt)
        db.commit()


# Singleton instance
repository_symbol_crud = RepositorySymbolCRUD()
