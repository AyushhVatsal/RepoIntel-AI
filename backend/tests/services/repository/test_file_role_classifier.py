from app.models.repository_file import FileCategory, FileRole
from app.services.repository.file_role_classifier import (
    FileRoleClassifier,
)


def test_classifies_test_file() -> None:
    classifier = FileRoleClassifier()

    role = classifier.classify(
        relative_path="tests/services/embedding/test_embedding_service.py",
        filename="test_embedding_service.py",
        category=FileCategory.SOURCE,
    )

    assert role == FileRole.TEST


def test_classifies_fixture_file() -> None:
    classifier = FileRoleClassifier()

    role = classifier.classify(
        relative_path="tests/parsers/fixtures/python/sample.py",
        filename="sample.py",
        category=FileCategory.SOURCE,
    )

    assert role == FileRole.FIXTURE


def test_classifies_config_file() -> None:
    classifier = FileRoleClassifier()

    role = classifier.classify(
        relative_path="app/services/embedding/models/embedding_config.py",
        filename="embedding_config.py",
        category=FileCategory.SOURCE,
    )

    assert role == FileRole.CONFIG


def test_classifies_source_file() -> None:
    classifier = FileRoleClassifier()

    role = classifier.classify(
        relative_path="app/services/embedding/service.py",
        filename="service.py",
        category=FileCategory.SOURCE,
    )

    assert role == FileRole.SOURCE