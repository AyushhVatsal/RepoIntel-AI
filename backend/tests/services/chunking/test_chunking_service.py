from datetime import datetime

from app.models.repository_file import FileCategory, LanguageSupportTier
from app.schemas.repository_file import RepositoryFileResponse
from app.services.chunking.service import ChunkingService
from app.services.parsers.models.enums import SymbolType
from app.services.parsers.models.parsed_document import ParsedDocument
from app.services.parsers.models.symbols import BaseSymbol, SourceLocation


def test_tier_1_creates_symbol_chunks_from_parsed_document():
    source_code = """\
class UserService:
    def login(self, username):
        return username

    def logout(self):
        return True
"""

    repository_file = RepositoryFileResponse(
        id=1,
        repository_id=1,
        path="app/auth/service.py",
        relative_path="app/auth/service.py",
        filename="service.py",
        extension=".py",
        language="python",
        category=FileCategory.SOURCE,
        support_tier=LanguageSupportTier.TIER_1,
        size=len(source_code),
        sha256_hash=None,
        is_binary=False,
        last_modified=None,
        created_at=datetime.now(),
    )

    symbol = BaseSymbol(
        symbol_id="user-service",
        name="UserService",
        qualified_name="UserService",
        type=SymbolType.CLASS,
        location=SourceLocation(
            start_line=1,
            start_column=0,
            end_line=6,
            end_column=17,
        ),
        language="python",
    )

    parsed_document = ParsedDocument(
        repository_file=repository_file,
        source_code=source_code,
        symbols=[symbol],
    )

    service = ChunkingService()

    chunks = service.chunk(
        parsed_document,
        support_tier=LanguageSupportTier.TIER_1,
    )

    assert len(chunks) == 1

    chunk = chunks[0]

    assert chunk.chunk_type.value == "class"
    assert chunk.symbol_name == "UserService"
    assert chunk.qualified_name == "UserService"
    assert chunk.start_line == 1
    assert chunk.end_line == 6
    assert chunk.token_count > 0

    assert chunk.metadata["language"] == "python"
    assert chunk.metadata["file_path"] == "app/auth/service.py"
    assert chunk.metadata["support_tier"] == "tier_1"

def test_none_tier_returns_no_chunks():
    source_code = """\
some content that should not be chunked
"""

    repository_file = RepositoryFileResponse(
        id=2,
        repository_id=1,
        path="README.md",
        relative_path="README.md",
        filename="README.md",
        extension=".md",
        language=None,
        category=FileCategory.DOCUMENTATION,
        support_tier=LanguageSupportTier.NONE,
        size=len(source_code),
        sha256_hash=None,
        is_binary=False,
        last_modified=None,
        created_at=datetime.now(),
    )

    parsed_document = ParsedDocument(
        repository_file=repository_file,
        source_code=source_code,
        symbols=[],
    )

    service = ChunkingService()

    chunks = service.chunk(
        parsed_document,
        support_tier=LanguageSupportTier.NONE,
    )

    assert chunks == []

def test_tier_0_creates_text_chunks():
    source_code = """\
configuration:
    database:
        host: localhost
        port: 5432
"""

    repository_file = RepositoryFileResponse(
        id=3,
        repository_id=1,
        path="config.yaml",
        relative_path="config.yaml",
        filename="config.yaml",
        extension=".yaml",
        language="yaml",
        category=FileCategory.CONFIGURATION,
        support_tier=LanguageSupportTier.TIER_0,
        size=len(source_code),
        sha256_hash=None,
        is_binary=False,
        last_modified=None,
        created_at=datetime.now(),
    )

    parsed_document = ParsedDocument(
        repository_file=repository_file,
        source_code=source_code,
        symbols=[],
    )

    service = ChunkingService()

    chunks = service.chunk(
        parsed_document,
        support_tier=LanguageSupportTier.TIER_0,
    )

    assert len(chunks) >= 1

    for chunk in chunks:
        assert chunk.chunk_type.value == "text"
        assert chunk.token_count > 0
        assert chunk.content
        assert chunk.metadata["language"] == "yaml"
        assert chunk.metadata["support_tier"] == "tier_0"