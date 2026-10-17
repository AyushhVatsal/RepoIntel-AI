from app.services.retrieval.result import RetrievalResult
from app.services.retrieval.reranking.cross_encoder import CrossEncoderReranker


query = "What embedding model and vector dimensions does RepoIntel use?"

documents = {
    1247: """class VectorStoreService:
    def __init__(self, db: Session) -> None:
        self.repository = VectorStoreRepository(db)

    def store_embedding(
        self,
        chunk_id: int,
        model: str,
        dimensions: int,
        embedding: list[float],
    ):
        if chunk_id <= 0:
            raise ValueError("chunk_id must be greater than 0")

        if not model.strip():
            raise ValueError("model must not be empty")

        if dimensions <= 0:
            raise ValueError("dimensions must be greater than 0")

        if len(embedding) != dimensions:
            raise ValueError(
                f"embedding dimension mismatch: "
                f"expected {dimensions}, got {len(embedding)}"
            )

        return upsert(
            db=self.repository.db,
            chunk_id=chunk_id,
            model=model,
            dimensions=dimensions,
            embedding=embedding,
        )""",

    1268: """class EmbeddingProvider(Protocol):
    \"\"\"Interface implemented by embedding providers.\"\"\"

    @property
    def model(self) -> str:
        \"\"\"Return the embedding model identifier.\"\"\"
        ...

    @property
    def dimensions(self) -> int:
        \"\"\"Return the embedding vector dimensions.\"\"\"
        ...

    def embed(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        \"\"\"Generate embeddings for the supplied texts.\"\"\"
        ...""",

    1077: """def root():
    return {
        "message": f"Welcome to RepoIntel AI",
    }""",

    1264: """class EmbeddingConfig(BaseModel):
    \"\"\"Configuration for the embedding pipeline.\"\"\"

    provider: str = Field(
        default="sentence_transformers",
        min_length=1,
    )

    model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        min_length=1,
    )

    dimensions: int = Field(
        default=384,
        gt=0,
    )

    batch_size: int = Field(
        default=64,
        gt=0,
    )

    max_retries: int = Field(
        default=3,
        ge=0,
    )

    max_concurrency: int = Field(
        default=1,
        gt=0,
    )""",

    1272: """class LocalEmbeddingProvider:
    \"\"\"Embedding provider backed by a local Sentence Transformers model.\"\"\"

    def __init__(
        self,
        model_name: str,
    ) -> None:
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)

    @property
    def model(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._model.get_embedding_dimension()""",
}

results = [
    RetrievalResult(
        chunk_id=1247,
        score=0.03252247488101534,
        dense_score=0.7750899925774354,
        retrieval_score=0.03252247488101534,
    ),
    RetrievalResult(
        chunk_id=1268,
        score=0.03200204813108039,
        dense_score=0.7699889677769575,
        retrieval_score=0.03200204813108039,
    ),
    RetrievalResult(
        chunk_id=1077,
        score=0.01639344262295082,
        dense_score=None,
        retrieval_score=0.01639344262295082,
    ),
    RetrievalResult(
        chunk_id=1264,
        score=0.015873015873015872,
        dense_score=0.7554151561608831,
        retrieval_score=0.015873015873015872,
    ),
    RetrievalResult(
        chunk_id=1272,
        score=0.015625,
        dense_score=0.7521826176534536,
        retrieval_score=0.015625,
    ),
]

reranker = CrossEncoderReranker()

reranked = reranker.rerank(
    query=query,
    results=results,
    documents=documents,
    top_k=5,
)

print("\nV2.1 RRF ORDER:")
for rank, result in enumerate(results, start=1):
    print(
        f"{rank}. chunk_id={result.chunk_id} "
        f"rrf={result.retrieval_score:.6f}"
    )

print("\nCROSS-ENCODER ORDER:")
for rank, result in enumerate(reranked, start=1):
    print(
        f"{rank}. chunk_id={result.chunk_id} "
        f"score={result.score:.6f}"
    )