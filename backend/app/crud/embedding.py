from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.embedding import Embedding

def get_by_chunk_and_model(
    db: Session,
    chunk_id: int,
    model: str,
) -> Embedding | None:
    stmt = select(Embedding).where(
        Embedding.chunk_id == chunk_id,
        Embedding.model == model,
    )

    return db.scalar(stmt)


def create(
    db: Session,
    chunk_id: int,
    model: str,
    dimensions: int,
    embedding: list[float],
) -> Embedding:
    db_embedding = Embedding(
        chunk_id=chunk_id,
        model=model,
        dimensions=dimensions,
        embedding=embedding,
    )

    db.add(db_embedding)
    db.flush()

    return db_embedding


def upsert(
    db: Session,
    chunk_id: int,
    model: str,
    dimensions: int,
    embedding: list[float],
) -> Embedding:
    stmt = insert(Embedding).values(
        chunk_id=chunk_id,
        model=model,
        dimensions=dimensions,
        embedding=list(embedding),
    )

    stmt = stmt.on_conflict_do_update(
        constraint="uq_embedding_chunk_model",
        set_={
            "dimensions": stmt.excluded.dimensions,
            "embedding": stmt.excluded.embedding,
            "updated_at": func.now(),
        },
    ).returning(Embedding)

    return db.scalar(stmt)


def delete_by_chunk(
    db: Session,
    chunk_id: int,
) -> int:
    stmt = delete(Embedding).where(
        Embedding.chunk_id == chunk_id,
    )

    result = db.execute(stmt)

    return result.rowcount

def delete_by_repository(
    db: Session,
    repository_id: int,
) -> int:
    stmt = delete(Embedding).where(
        Embedding.chunk_id.in_(
            select(Chunk.id).where(
                Chunk.repository_id == repository_id,
            )
        )
    )

    result = db.execute(stmt)

    return result.rowcount