import pytest
from pydantic import ValidationError

from app.services.retrieval.filters import RetrievalFilters


def test_filters_default_to_none():
    filters = RetrievalFilters()

    assert filters.language is None
    assert filters.file_path is None
    assert filters.chunk_type is None
    assert filters.symbol_name is None


def test_language_filter():
    filters = RetrievalFilters(
        language="python",
    )

    assert filters.language == "python"
    assert filters.file_path is None
    assert filters.chunk_type is None
    assert filters.symbol_name is None


def test_file_path_filter():
    filters = RetrievalFilters(
        file_path="backend/auth/",
    )

    assert filters.file_path == "backend/auth/"


def test_chunk_type_filter():
    filters = RetrievalFilters(
        chunk_type="function",
    )

    assert filters.chunk_type == "function"


def test_symbol_name_filter():
    filters = RetrievalFilters(
        symbol_name="authenticate_user",
    )

    assert filters.symbol_name == "authenticate_user"


def test_multiple_filters():
    filters = RetrievalFilters(
        language="python",
        file_path="backend/auth/",
        chunk_type="function",
        symbol_name="authenticate_user",
    )

    assert filters.language == "python"
    assert filters.file_path == "backend/auth/"
    assert filters.chunk_type == "function"
    assert filters.symbol_name == "authenticate_user"


@pytest.mark.parametrize(
    "field",
    [
        "language",
        "file_path",
        "chunk_type",
        "symbol_name",
    ],
)
def test_empty_filter_values_are_rejected(field):
    with pytest.raises(ValidationError):
        RetrievalFilters(**{field: ""})


def test_repository_id_is_not_a_metadata_filter():
    filters = RetrievalFilters(
        language="python",
    )

    assert not hasattr(filters, "repository_id")