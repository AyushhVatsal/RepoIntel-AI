import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime
from app.models.repository_file import FileCategory, LanguageSupportTier
from app.schemas.repository_file import RepositoryFileResponse
from app.services.parsers.models.file_content import FileContent
from app.services.parsers.tree_sitter.parser import TreeSitterParser

def main() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "ts" / "sample.ts"

    if not fixture_path.exists():
        print(f"❌ Fixture not found: {fixture_path}")
        print(f"   Creating sample TypeScript file...")
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text("""
// TypeScript sample
interface User {
    name: string;
    age: number;
}

enum Color {
    Red,
    Green,
    Blue
}

type Point = { x: number; y: number; };

class Person implements User {
    name: string;
    age: number;

    constructor(name: string, age: number) {
        this.name = name;
        this.age = age;
    }

    async greet(): Promise<void> {
        console.log("Hello");
    }
}

const arrow = (x: number): number => x * 2;
""")
        print(f"   Created: {fixture_path}")

    source = fixture_path.read_bytes()

    repository_file = RepositoryFileResponse(
        id=1,
        repository_id=1,
        path=str(fixture_path),
        relative_path="sample.ts",
        filename="sample.ts",
        extension=".ts",
        language="typescript",
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

    print("🔍 Parsing TypeScript file...")
    document = TreeSitterParser.parse(file_content)

    print(f"\n✅ Parsed successfully!")
    print(f"📄 File: {document.repository_file.filename}")
    print(f"📊 Symbols found: {len(document.symbols)}")

    for symbol in document.symbols:
        modifiers = f" [{', '.join(symbol.modifiers)}]" if symbol.modifiers else ""
        if hasattr(symbol, 'is_async') and symbol.is_async:
            modifiers += " [async]"
        print(f"  - {symbol.type.value}: {symbol.name}{modifiers}")

if __name__ == "__main__":
    main()
