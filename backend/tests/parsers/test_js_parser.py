import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.repository_file import (
    FileCategory,
    LanguageSupportTier,
)
from app.schemas.repository_file import RepositoryFileResponse
from app.services.parsers.models.file_content import FileContent
from app.services.parsers.tree_sitter.parser import TreeSitterParser

def main() -> None:

    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "js"
        / "sample.js"
    )

    source = fixture_path.read_bytes()

    repository_file = RepositoryFileResponse(
        id=1,
        repository_id=1,

        path="tests/parsers/fixtures/js/sample.js",
        relative_path="sample.js",
        filename="sample.js",

        extension=".js",
        language="javascript",

        category=FileCategory.SOURCE,
        support_tier=LanguageSupportTier.TIER_1,

        size=len(source),

        sha256_hash=None,
        is_binary=False,

        last_modified=None,
        created_at=datetime.now(),
    )

    file_content = FileContent(
        repository_file=repository_file,
        content=source,
    )
        
    document = TreeSitterParser.parse(
        file_content,
    )

    print(document)

if __name__ == "__main__":
    main()