from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repository import Repository
from app.schemas.repository import RepositoryCreate
from app.models.repository_file import RepositoryFile


class RepositoryCRUD:
    def create(
        self,
        db: Session,
        repository_in: RepositoryCreate,
        **extra_fields,
    ) -> Repository:
        db_repository = Repository(
            **repository_in.model_dump(),
            **extra_fields,
        )

        db.add(db_repository)
        db.commit()
        db.refresh(db_repository)

        return db_repository

    def get(
        self,
        db: Session,
        repository_id: int,
    ) -> Repository | None:
        return db.get(Repository, repository_id)

    def get_by_github_url(
        self,
        db: Session,
        github_url: str,
    ) -> Repository | None:
        stmt = (
            select(Repository)
            .where(Repository.github_url == github_url)
        )

        return db.scalar(stmt)

    def get_by_owner(
        self,
        db: Session,
        owner_id: int,
    ) -> list[Repository]:
        stmt = (
            select(Repository)
            .where(Repository.owner_id == owner_id)
            .order_by(Repository.created_at.desc())
        )

        return list(db.scalars(stmt))

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
            .order_by(
                RepositoryFile.relative_path
            )
        )

        return list(db.scalars(stmt))

    def update(
        self,
        db: Session,
        repository: Repository,
        **fields,
    ) -> Repository:
        for key, value in fields.items():
            setattr(repository, key, value)

        db.commit()
        db.refresh(repository)

        return repository

    def delete(
        self,
        db: Session,
        repository: Repository,
    ) -> None:
        db.delete(repository)
        db.commit()


repository_crud = RepositoryCRUD()