from fastapi import APIRouter

router = APIRouter(
    tags=["Health"],
)


@router.get(
    "/",
    summary="Root endpoint",
)
def root():
    return {
        "message": f"Welcome to RepoIntel AI",
    }


@router.get(
    "/health",
    summary="Health check",
)
def health_check():
    return {
        "status": "healthy",
    }