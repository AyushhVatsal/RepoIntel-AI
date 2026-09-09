import json
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

    return [
        RetrievalEvalCase(**case)
        for case in data
    ]