from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.repository_file import RepositoryFile
from app.schemas.repository_file import RepositoryFileCreate


class RepositoryFileCRUD:
    def create(
        self,
        db: Session,
        file_in: RepositoryFileCreate,
    ) -> RepositoryFile:
        db_file = RepositoryFile(**file_in.model_dump())

        db.add(db_file)
        db.commit()
        db.refresh(db_file)

        return db_file

    def create_many(
        self,
        db: Session,
        files: list[RepositoryFileCreate],
    ) -> list[RepositoryFile]:
        db_files = [
            RepositoryFile(**file.model_dump())
            for file in files
        ]

        db.add_all(db_files)
        db.commit()

        return db_files

    def get(
        self,
        db: Session,
        file_id: int,
    ) -> RepositoryFile | None:
        return db.get(RepositoryFile, file_id)

    def get_by_repository(
        self,
        db: Session,
        repository_id: int,
    ) -> list[RepositoryFile]:
        stmt = (
            select(RepositoryFile)
            .where(
                RepositoryFile.repository_id == repository_id
            )
            .order_by(RepositoryFile.relative_path)
        )

        return list(db.scalars(stmt))

    def delete(
        self,
        db: Session,
        file_id: int,
    ) -> None:
        file = self.get(db, file_id)

        if file:
            db.delete(file)
            db.commit()

    def delete_by_repository(
        self,
        db: Session,
        repository_id: int,
    ) -> None:
        stmt = (
            delete(RepositoryFile)
            .where(
                RepositoryFile.repository_id == repository_id
            )
        )

        db.execute(stmt)
        db.commit()


repository_file_crud = RepositoryFileCRUD()