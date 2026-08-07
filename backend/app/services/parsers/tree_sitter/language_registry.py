from __future__ import annotations

from pathlib import Path

from .language_config import LanguageConfig

QUERY_DIRECTORY = Path(__file__).parent / "queries"


class LanguageRegistry:
    """
    Registry containing parser configuration for every supported language.
    """

    _registry: dict[str, LanguageConfig] = {

        # ==========================================================
        # Tier 1 Languages
        # ==========================================================

        "python": LanguageConfig(
            language="python",
            extensions=(".py",),
            tier="tier_1",
            parser="tree_sitter",
            grammar_name="python",
            grammar_module="tree_sitter_python",
            query_file=QUERY_DIRECTORY / "python.scm",
            supports_ast=True,
            supports_symbols=True,
            supports_docstrings=True,
            supports_return_types=True,
            supports_incremental_parsing=True,
        ),

        "java": LanguageConfig(
            language="java",
            extensions=(".java",),
            tier="tier_1",
            parser="tree_sitter",
            grammar_name="java",
            grammar_module="tree_sitter_java",
            query_file=QUERY_DIRECTORY / "java.scm",
            supports_ast=True,
            supports_symbols=True,
            supports_docstrings=True,
            supports_return_types=True,
            supports_incremental_parsing=True,
        ),

        "javascript": LanguageConfig(
            language="javascript",
            extensions=(".js", ".jsx"),
            tier="tier_1",
            parser="tree_sitter",
            grammar_name="javascript",
            grammar_module="tree_sitter_javascript",
            query_file=QUERY_DIRECTORY / "javascript.scm",
            supports_ast=True,
            supports_symbols=True,
            supports_docstrings=True,
            supports_return_types=False,
            supports_incremental_parsing=True,
        ),

        "typescript": LanguageConfig(
            language="typescript",
            extensions=(".ts", ".tsx"),
            tier="tier_1",
            parser="tree_sitter",
            grammar_name="typescript",
            grammar_module="tree_sitter_typescript",
            query_file=QUERY_DIRECTORY / "typescript.scm",
            supports_ast=True,
            supports_symbols=True,
            supports_docstrings=True,
            supports_return_types=True,
            supports_incremental_parsing=True,
        ),

        # ==========================================================
        # Tier 0 Languages
        # ==========================================================

        "go": LanguageConfig(
            language="go",
            extensions=(".go",),
            tier="tier_0",
            parser="text",
        ),

        "rust": LanguageConfig(
            language="rust",
            extensions=(".rs",),
            tier="tier_0",
            parser="text",
        ),

        "c": LanguageConfig(
            language="c",
            extensions=(".c", ".h"),
            tier="tier_0",
            parser="text",
        ),

        "cpp": LanguageConfig(
            language="cpp",
            extensions=(".cpp", ".cc", ".cxx", ".hpp"),
            tier="tier_0",
            parser="text",
        ),

        "csharp": LanguageConfig(
            language="csharp",
            extensions=(".cs",),
            tier="tier_0",
            parser="text",
        ),

        "kotlin": LanguageConfig(
            language="kotlin",
            extensions=(".kt",),
            tier="tier_0",
            parser="text",
        ),

        "swift": LanguageConfig(
            language="swift",
            extensions=(".swift",),
            tier="tier_0",
            parser="text",
        ),

        "php": LanguageConfig(
            language="php",
            extensions=(".php",),
            tier="tier_0",
            parser="text",
        ),

        "ruby": LanguageConfig(
            language="ruby",
            extensions=(".rb",),
            tier="tier_0",
            parser="text",
        ),

        "html": LanguageConfig(
            language="html",
            extensions=(".html", ".htm"),
            tier="tier_0",
            parser="text",
        ),

        "css": LanguageConfig(
            language="css",
            extensions=(".css",),
            tier="tier_0",
            parser="text",
        ),

        "scss": LanguageConfig(
            language="scss",
            extensions=(".scss",),
            tier="tier_0",
            parser="text",
        ),

        "sass": LanguageConfig(
            language="sass",
            extensions=(".sass",),
            tier="tier_0",
            parser="text",
        ),

        "dart": LanguageConfig(
            language="dart",
            extensions=(".dart",),
            tier="tier_0",
            parser="text",
        ),

        "scala": LanguageConfig(
            language="scala",
            extensions=(".scala",),
            tier="tier_0",
            parser="text",
        ),

        "lua": LanguageConfig(
            language="lua",
            extensions=(".lua",),
            tier="tier_0",
            parser="text",
        ),

        "shell": LanguageConfig(
            language="shell",
            extensions=(".sh", ".bash", ".zsh"),
            tier="tier_0",
            parser="text",
        ),

        "r": LanguageConfig(
            language="r",
            extensions=(".r",),
            tier="tier_0",
            parser="text",
        ),

        "matlab": LanguageConfig(
            language="matlab",
            extensions=(".m",),
            tier="tier_0",
            parser="text",
        ),
    }

    @classmethod
    def get(cls, language: str) -> LanguageConfig:
        try:
            return cls._registry[language.lower()]
        except KeyError:
            raise ValueError(f"Unsupported language: {language}")

    @classmethod
    def is_supported(cls, language: str) -> bool:
        return language.lower() in cls._registry

    @classmethod
    def supported_languages(cls) -> list[str]:
        return sorted(cls._registry.keys())