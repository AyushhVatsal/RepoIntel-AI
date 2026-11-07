import logging
from time import perf_counter

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_active_user
from app.api.deps.db import get_db
from app.crud.repository_symbol import repository_symbol_crud
from app.exceptions.repository import (
    InvalidRepositoryUrlError,
    RepositoryAlreadyExistsError,
    RepositoryCloneError,
    RepositoryError,
    RepositoryNotFoundError,
    RepositoryScanError,
    RepositoryTooLargeError,
    UnsupportedGitProviderError,
)
from app.models.repository import (
    GraphBuildStatus,
    Repository,
    RepositoryStatus,
)
from app.models.user import User
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryResponse,
)
from app.schemas.repository_file import RepositoryFileResponse
from app.schemas.repository_symbol import RepositorySymbolResponse
from app.services.knowledge_graph.worker import run_repository_graph_build
from app.services.repository.indexing_worker import run_repository_indexing
from app.services.repository.repository_service import (
    get_repository_service,
)

router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"],
)
logger = logging.getLogger(__name__)


@router.post(
    "/",
    response_model=RepositoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_repository(
    repository_in: RepositoryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RepositoryResponse:

    try:
        started = perf_counter()
        repository = get_repository_service().create_indexing_job(
            db=db,
            owner_id=current_user.id,
            repository_in=repository_in,
        )
        background_tasks.add_task(
            run_repository_indexing,
            repository.id,
        )
        logger.info(
            "Repository indexing job queued: repository_id=%s queue_ms=%.1f",
            repository.id,
            (perf_counter() - started) * 1000,
        )
        return repository

    except RepositoryAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except (
        InvalidRepositoryUrlError,
        UnsupportedGitProviderError,
        RepositoryTooLargeError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except (
        RepositoryCloneError,
        RepositoryScanError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    except RepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/",
    response_model=list[RepositoryResponse],
)
def list_repositories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[RepositoryResponse]:

    return get_repository_service().list_repositories(
        db=db,
        owner_id=current_user.id,
    )


@router.get(
    "/{repository_id}",
    response_model=RepositoryResponse,
)
def get_repository(
    repository_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RepositoryResponse:

    try:
        return get_repository_service().get_repository(
            db=db,
            repository_id=repository_id,
            owner_id=current_user.id,
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{repository_id}/graph/rebuild",
    response_model=RepositoryResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def rebuild_repository_graph(
    repository_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RepositoryResponse:
    """Queue an independent graph rebuild for an indexed repository."""
    try:
        repository = get_repository_service().get_repository(
            db=db,
            repository_id=repository_id,
            owner_id=current_user.id,
        )
        if repository.status != RepositoryStatus.INDEXED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Repository must be indexed before graph rebuild.",
            )
        queued = db.execute(
            update(Repository)
            .where(
                Repository.id == repository_id,
                Repository.status == RepositoryStatus.INDEXED,
                Repository.graph_status.not_in(
                    (
                        GraphBuildStatus.QUEUED.value,
                        GraphBuildStatus.BUILDING.value,
                    )
                ),
            )
            .values(
                graph_status=GraphBuildStatus.QUEUED.value,
                graph_error=None,
            )
        )
        if queued.rowcount != 1:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A graph build is already queued or running.",
            )

        db.commit()
        db.refresh(repository)
        background_tasks.add_task(
            run_repository_graph_build,
            repository.id,
        )
        return repository
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

@router.get(
    "/{repository_id}/files",
    response_model=list[RepositoryFileResponse],
)
def list_repository_files(
    repository_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[RepositoryFileResponse]:

    try:
        return get_repository_service().list_repository_files(
            db=db,
            repository_id=repository_id,
            owner_id=current_user.id,
        )

    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/{repository_id}/symbols",
    response_model=list[RepositorySymbolResponse],
)
def list_repository_symbols(
    repository_id: int,
    symbol_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[RepositorySymbolResponse]:
    """
    Get all symbols for a repository.

    Optionally filter by symbol_type (import, class, function, method, variable).
    """
    try:
        # Verify repository ownership
        get_repository_service().get_repository(
            db=db,
            repository_id=repository_id,
            owner_id=current_user.id,
        )

        # Get symbols
        return repository_symbol_crud.get_by_repository(
            db=db,
            repository_id=repository_id,
            symbol_type=symbol_type,
        )

    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.delete(
    "/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_repository(
    repository_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:

    try:
        get_repository_service().delete_repository(
            db=db,
            repository_id=repository_id,
            owner_id=current_user.id,
        )

        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
        )

    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
