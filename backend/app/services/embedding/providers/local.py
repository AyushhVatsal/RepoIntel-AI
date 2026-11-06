from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from threading import Lock, local
from time import perf_counter
from types import MethodType

import torch
from sentence_transformers import SentenceTransformer


class LocalEmbeddingProvider:
    """Embedding provider backed by a local Sentence Transformers model."""

    def __init__(
        self,
        model_name: str,
    ) -> None:
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        self._profile_state = local()
        self._profile_lock = Lock()
        self._profile = {
            "encode_ms": 0.0,
            "tokenize_ms": 0.0,
            "model_forward_ms": 0.0,
            "tensor_to_list_ms": 0.0,
            "embeddings": 0,
            "provider_calls": 0,
            "model_batches": 0,
            "token_positions": 0,
        }
        self._instrument_model_stages()

    def _instrument_model_stages(self) -> None:
        """Measure tokenizer and transformer-forward time inside encode()."""
        original_preprocess = self._model.preprocess
        original_forward = self._model.forward

        def timed_preprocess(
            model,
            *args,
            **kwargs,
        ):
            state = getattr(self._profile_state, "current", None)
            if state is None:
                return original_preprocess(*args, **kwargs)

            started = perf_counter()
            features = original_preprocess(*args, **kwargs)
            state["tokenize_ms"] += (perf_counter() - started) * 1000
            input_ids = features.get("input_ids")
            if input_ids is not None:
                state["token_positions"] += int(input_ids.numel())
            return features

        def timed_forward(
            model,
            *args,
            **kwargs,
        ):
            state = getattr(self._profile_state, "current", None)
            if state is None:
                return original_forward(*args, **kwargs)

            started = perf_counter()
            output = original_forward(*args, **kwargs)
            state["model_forward_ms"] += (
                perf_counter() - started
            ) * 1000
            state["model_batches"] += 1
            return output

        self._model.preprocess = MethodType(timed_preprocess, self._model)
        self._model.forward = MethodType(timed_forward, self._model)

    @property
    def model(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._model.get_embedding_dimension()

    def embed(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        profile = {
            "tokenize_ms": 0.0,
            "model_forward_ms": 0.0,
            "token_positions": 0,
            "model_batches": 0,
        }
        self._profile_state.current = profile
        encode_started = perf_counter()
        is_cuda = str(self._model.device).startswith("cuda")
        batch_size = min(len(texts), 16 if is_cuda else 32)
        try:
            while True:
                try:
                    embeddings = self._model.encode(
                        list(texts),
                        # CUDA batch 16 was slightly faster and used less VRAM
                        # than 32 in the Graphify benchmark. Keep CPU batch 32.
                        batch_size=batch_size,
                        show_progress_bar=False,
                        convert_to_numpy=True,
                        normalize_embeddings=True,
                    )
                    break
                except RuntimeError as exc:
                    message = str(exc).casefold()
                    is_oom = (
                        isinstance(exc, torch.cuda.OutOfMemoryError)
                        or "out of memory" in message
                        or "cudaerrormemoryallocation" in message
                    )
                    if not is_cuda or not is_oom or batch_size <= 1:
                        raise
                    batch_size = max(batch_size // 2, 1)
                    torch.cuda.empty_cache()
            encode_ms = (perf_counter() - encode_started) * 1000

            convert_started = perf_counter()
            result = embeddings.tolist()
            tensor_to_list_ms = (perf_counter() - convert_started) * 1000
        finally:
            self._profile_state.current = None

        with self._profile_lock:
            self._profile["encode_ms"] += encode_ms
            self._profile["tokenize_ms"] += profile["tokenize_ms"]
            self._profile["model_forward_ms"] += profile["model_forward_ms"]
            self._profile["tensor_to_list_ms"] += tensor_to_list_ms
            self._profile["embeddings"] += len(texts)
            self._profile["provider_calls"] += 1
            self._profile["model_batches"] += profile["model_batches"]
            self._profile["token_positions"] += profile["token_positions"]
        return result

    def profile_snapshot(self) -> dict[str, float | int | str]:
        """Return cumulative tokenizer and inference profiling counters."""
        with self._profile_lock:
            snapshot = dict(self._profile)
        encode_seconds = snapshot["encode_ms"] / 1000
        snapshot["embeddings_per_second"] = (
            snapshot["embeddings"] / encode_seconds
            if encode_seconds
            else 0.0
        )
        snapshot["mean_batch_size"] = (
            snapshot["embeddings"] / snapshot["model_batches"]
            if snapshot["model_batches"]
            else 0.0
        )
        snapshot["device"] = str(self._model.device)
        return snapshot

    def reset_profile(self) -> None:
        """Clear cumulative counters before a new indexing job."""
        with self._profile_lock:
            for key in self._profile:
                self._profile[key] = 0

@lru_cache(maxsize=4)
def get_local_embedding_provider(model_name: str) -> LocalEmbeddingProvider:
    """Reuse a loaded embedding provider across requests."""
    return LocalEmbeddingProvider(model_name)
