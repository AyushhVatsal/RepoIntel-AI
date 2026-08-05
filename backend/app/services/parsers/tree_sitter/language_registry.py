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

        "Python": LanguageConfig(
            language="Python",
            supports_tree_sitter=True,
            tree_sitter_language="python",
            grammar_module="tree_sitter_python",
            query_file=QUERY_DIRECTORY / "python.scm",
        ),

        "Java": LanguageConfig(
            language="Java",
            supports_tree_sitter=True,
            tree_sitter_language="java",
            grammar_module="tree_sitter_java",
            query_file=QUERY_DIRECTORY / "java.scm",
        ),

        "JavaScript": LanguageConfig(
            language="JavaScript",
            supports_tree_sitter=True,
            tree_sitter_language="javascript",
            grammar_module="tree_sitter_javascript",
            query_file=QUERY_DIRECTORY / "javascript.scm",
        ),

        "TypeScript": LanguageConfig(
            language="TypeScript",
            supports_tree_sitter=True,
            tree_sitter_language="typescript",
            grammar_module="tree_sitter_typescript",
            query_file=QUERY_DIRECTORY / "typescript.scm",
        ),

        # ==========================================================
        # Tier 0 Languages
        # ==========================================================

        "Go": LanguageConfig(
            language="Go",
            supports_tree_sitter=False,
        ),

        "Rust": LanguageConfig(
            language="Rust",
            supports_tree_sitter=False,
        ),

        "C": LanguageConfig(
            language="C",
            supports_tree_sitter=False,
        ),

        "C++": LanguageConfig(
            language="C++",
            supports_tree_sitter=False,
        ),

        "C#": LanguageConfig(
            language="C#",
            supports_tree_sitter=False,
        ),

        "Kotlin": LanguageConfig(
            language="Kotlin",
            supports_tree_sitter=False,
        ),

        "Swift": LanguageConfig(
            language="Swift",
            supports_tree_sitter=False,
        ),

        "PHP": LanguageConfig(
            language="PHP",
            supports_tree_sitter=False,
        ),

        "Ruby": LanguageConfig(
            language="Ruby",
            supports_tree_sitter=False,
        ),

        "HTML": LanguageConfig(
            language="HTML",
            supports_tree_sitter=False,
        ),

        "CSS": LanguageConfig(
            language="CSS",
            supports_tree_sitter=False,
        ),

        "SCSS": LanguageConfig(
            language="SCSS",
            supports_tree_sitter=False,
        ),

        "SASS": LanguageConfig(
            language="SASS",
            supports_tree_sitter=False,
        ),

        "Dart": LanguageConfig(
            language="Dart",
            supports_tree_sitter=False,
        ),

        "Scala": LanguageConfig(
            language="Scala",
            supports_tree_sitter=False,
        ),

        "Lua": LanguageConfig(
            language="Lua",
            supports_tree_sitter=False,
        ),

        "Shell": LanguageConfig(
            language="Shell",
            supports_tree_sitter=False,
        ),

        "R": LanguageConfig(
            language="R",
            supports_tree_sitter=False,
        ),

        "MATLAB": LanguageConfig(
            language="MATLAB",
            supports_tree_sitter=False,
        ),
    }

    @classmethod
    def get(cls, language: str) -> LanguageConfig:
        try:
            return cls._registry[language]
        except KeyError:
            raise ValueError(f"Unsupported language: {language}")

    @classmethod
    def is_supported(cls, language: str) -> bool:
        return language in cls._registry

    @classmethod
    def supported_languages(cls) -> list[str]:
        return sorted(cls._registry.keys())