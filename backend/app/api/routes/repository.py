from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_active_user
from app.api.deps.db import get_db
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
from app.models.user import User
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryResponse,
)
from app.schemas.repository_file import RepositoryFileResponse
from app.services.repository.repository_service import (
    repository_service,
)

router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"],
)


@router.post(
    "/",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_repository(
    repository_in: RepositoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RepositoryResponse:

    try:
        return repository_service.index_repository(
            db=db,
            owner_id=current_user.id,
            repository_in=repository_in,
        )

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

    return repository_service.list_repositories(
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
        return repository_service.get_repository(
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
    "/{repository_id}/files",
    response_model=list[RepositoryFileResponse],
)
def list_repository_files(
    repository_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[RepositoryFileResponse]:

    try:
        return repository_service.list_repository_files(
            db=db,
            repository_id=repository_id,
            owner_id=current_user.id,
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
        repository_service.delete_repository(
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