from pathlib import Path

from .loader import load_retrieval_eval_cases


def test_load_retrieval_eval_cases() -> None:
    file_path = (
        Path(__file__).parent
        / "retrieval_v1.json"
    )

    cases = load_retrieval_eval_cases(file_path)

    assert len(cases) == 4
    assert cases[0].id == "semantic_001"
    assert cases[0].repository_id == 49