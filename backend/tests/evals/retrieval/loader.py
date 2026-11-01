import json
import os
from dataclasses import replace
from pathlib import Path

from .models import RetrievalEvalCase


def load_retrieval_eval_cases(
    file_path: Path,
) -> list[RetrievalEvalCase]:
    """Load retrieval evaluation cases from a JSON file."""

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    cases = [RetrievalEvalCase(**case) for case in data]
    repository_id_override = os.getenv("RETRIEVAL_EVAL_REPOSITORY_ID")
    if repository_id_override:
        repository_id = int(repository_id_override)
        cases = [replace(case, repository_id=repository_id) for case in cases]

    return cases
