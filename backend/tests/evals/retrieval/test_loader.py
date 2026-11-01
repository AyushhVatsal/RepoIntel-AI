from pathlib import Path

from .loader import load_retrieval_eval_cases


def test_load_retrieval_eval_cases(monkeypatch) -> None:
    monkeypatch.delenv("RETRIEVAL_EVAL_REPOSITORY_ID", raising=False)
    file_path = Path(__file__).parent / "retrieval_v1.json"

    cases = load_retrieval_eval_cases(file_path)

    assert len(cases) == 8
    assert cases[0].id == "semantic_001"
    assert cases[0].repository_id == 49


def test_load_retrieval_eval_cases_can_override_repository_id(monkeypatch) -> None:
    monkeypatch.setenv("RETRIEVAL_EVAL_REPOSITORY_ID", "1752")
    file_path = Path(__file__).parent / "retrieval_v1.json"

    cases = load_retrieval_eval_cases(file_path)

    assert cases[0].repository_id == 1752
