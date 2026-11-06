import asyncio
import logging
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api import api_router
from app.core.config import settings
from app.services.chunking.token_counter import warmup_tokenizer
from app.services.retrieval.retrieval_service import (
    warmup_recent_retrieval_indexes,
    warmup_retrieval_models,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Move model loading and first-inference setup out of user requests."""
    try:
        await asyncio.to_thread(warmup_tokenizer)
        logger.info("Tokenizer initialized")
    except Exception:
        # Keep the API available when optional tokenizer assets cannot be
        # fetched at startup; the indexing job will report the failure.
        logger.exception("Tokenizer warmup failed")

    started = perf_counter()
    query_vector = None
    try:
        query_vector = await asyncio.to_thread(warmup_retrieval_models)
        logger.info(
            "Retrieval model warmup completed in %.1f ms",
            (perf_counter() - started) * 1000,
        )
    except Exception:
        # Keep non-retrieval routes available if local model assets cannot be
        # loaded. Retrieval will log/fail through its normal request path.
        logger.exception("Retrieval model warmup failed")

    bm25_started = perf_counter()
    try:
        repository_ids = (
            await asyncio.to_thread(
                warmup_recent_retrieval_indexes,
                query_vector,
            )
            if query_vector is not None
            else []
        )
        if repository_ids:
            logger.info(
                "Retrieval indexes primed for repositories %s in %.1f ms",
                repository_ids,
                (perf_counter() - bm25_started) * 1000,
            )
    except Exception:
        # BM25 can still build on demand if the database is unavailable during
        # startup; do not prevent unrelated application routes from starting.
        logger.exception("BM25 index warmup failed")

    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
