"""
Repository module constants.
"""

from pathlib import Path

# =============================================================================
# Repository Limits
# =============================================================================

MAX_REPOSITORY_SIZE_MB = 500
MAX_FILE_SIZE_MB = 2
CLONE_TIMEOUT_SECONDS = 300
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

MAX_REPOSITORY_SIZE_BYTES = (
    MAX_REPOSITORY_SIZE_MB * 1024 * 1024
)

# =============================================================================
# Supported Git Providers
# =============================================================================

SUPPORTED_GIT_HOSTS = {
    "github.com",
}

# =============================================================================
# Clone Directory
# =============================================================================

CLONE_DIRECTORY = Path("storage/repositories")

# =============================================================================
# Tier 1 Languages
#
# Full language support:
# - Tree-sitter parsing
# - AST generation
# - Import extraction
# - Symbol extraction
# - Architecture graph
# =============================================================================

TIER_1_SOURCE_EXTENSIONS = {
    ".py",
    ".java",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
}

# =============================================================================
# Tier 0 Languages
#
# Recognized as source code.
# Used for:
# - Repository scanning
# - Chunking
# - Embeddings
# - RAG chat
#
# No AST / dependency graph yet.
# =============================================================================

TIER_0_SOURCE_EXTENSIONS = {
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".cc",
    ".h",
    ".hpp",
    ".cs",
    ".kt",
    ".swift",
    ".php",
    ".rb",
}

# =============================================================================
# Documentation Files
# =============================================================================

SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".md",
    ".txt",
    ".rst",
}

# =============================================================================
# Configuration Files
# =============================================================================

SUPPORTED_CONFIG_EXTENSIONS = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".ini",
    ".sql",
}

# =============================================================================
# Special Text Files
#
# These are matched by filename, not extension.
# =============================================================================

SPECIAL_TEXT_FILENAMES = {
    ".env",
    ".env.example",
    ".gitignore",
    ".dockerignore",
    "Dockerfile",
    "Makefile",
    "LICENSE",
    "README",
}

# =============================================================================
# Language Manifest Files
#
# Used to identify the project's language ecosystem.
# Framework detection happens later by inspecting these files.
# =============================================================================

LANGUAGE_MANIFEST_FILES = {
    "Python": [
        "pyproject.toml",
        "requirements.txt",
        "Pipfile",
        "poetry.lock",
    ],
    "JavaScript": [
        "package.json",
    ],
    "Java": [
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
    ],
    "Go": [
        "go.mod",
    ],
    "Rust": [
        "Cargo.toml",
    ],
    "PHP": [
        "composer.json",
    ],
}

# =============================================================================
# Ignored Directories
# =============================================================================

IGNORED_DIRECTORIES = {
    ".git",
    ".github",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "target",
    "bin",
    "obj",
}

# =============================================================================
# Ignored Files
# =============================================================================

IGNORED_FILES = {
    ".DS_Store",
    "Thumbs.db",
}

# =============================================================================
# Binary File Extensions
#
# These files are skipped during indexing.
# =============================================================================

BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".class",
    ".jar",
    ".pyc",
}

from app.models.repository_file import (
    FileCategory,
    LanguageSupportTier,
)

# =============================================================================
# Extension -> Language
# =============================================================================

EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",

    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".h": "C",
    ".hpp": "C++",
    ".cs": "C#",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".php": "PHP",
    ".rb": "Ruby",
}

# =============================================================================
# Extension -> Support Tier
# =============================================================================

EXTENSION_TIER_MAP = {
    **{
        extension: LanguageSupportTier.TIER_1
        for extension in TIER_1_SOURCE_EXTENSIONS
    },
    **{
        extension: LanguageSupportTier.TIER_0
        for extension in TIER_0_SOURCE_EXTENSIONS
    },
}

# =============================================================================
# Category -> Extensions
# =============================================================================

CATEGORY_EXTENSION_MAP = {
    FileCategory.SOURCE: (
        TIER_1_SOURCE_EXTENSIONS
        | TIER_0_SOURCE_EXTENSIONS
    ),
    FileCategory.DOCUMENTATION: SUPPORTED_DOCUMENT_EXTENSIONS,
    FileCategory.CONFIGURATION: SUPPORTED_CONFIG_EXTENSIONS,
    FileCategory.BINARY: BINARY_EXTENSIONS,
}

SOURCE_EXTENSIONS = (
    TIER_1_SOURCE_EXTENSIONS
    | TIER_0_SOURCE_EXTENSIONS
)

# =============================================================================
# Frameworks
# =============================================================================

FRAMEWORK_DETECTION_RULES = {
    "Python": {
        "manifests": [
            "requirements.txt",
            "requirements-dev.txt",
            "pyproject.toml",
            "Pipfile",
            "poetry.lock",
        ],
        "frameworks": {
            "fastapi": "FastAPI",
            "django": "Django",
            "flask": "Flask",
            "starlette": "Starlette",
            "litestar": "Litestar",
            "streamlit": "Streamlit",
            "gradio": "Gradio",
            "sanic": "Sanic",
            "bottle": "Bottle",
            "pyramid": "Pyramid",
            "tornado": "Tornado",
        },
    },

    "JavaScript": {
        "package_json": True,
        "frameworks": {
            "react": "React",
            "next": "Next.js",
            "express": "Express",
            "vue": "Vue",
            "nuxt": "Nuxt",
            "svelte": "Svelte",
            "astro": "Astro",
            "@remix-run": "Remix",
            "electron": "Electron",
        },
    },

    "TypeScript": {
        "package_json": True,
        "frameworks": {
            "react": "React",
            "next": "Next.js",
            "express": "Express",
            "@nestjs/core": "NestJS",
            "@angular/core": "Angular",
            "vue": "Vue",
            "nuxt": "Nuxt",
            "svelte": "Svelte",
            "astro": "Astro",
        },
    },

    "Java": {
        "manifests": [
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
        ],
        "frameworks": {
            "spring-boot": "Spring Boot",
            "spring-webmvc": "Spring MVC",
            "quarkus": "Quarkus",
            "micronaut": "Micronaut",
            "jakarta": "Jakarta EE",
            "dropwizard": "Dropwizard",
        },
    },

    "Go": {
        "manifests": ["go.mod"],
        "frameworks": {
            "github.com/gin-gonic/gin": "Gin",
            "github.com/gofiber/fiber": "Fiber",
            "github.com/labstack/echo": "Echo",
            "github.com/go-chi/chi": "Chi",
            "github.com/astaxie/beego": "Beego",
        },
    },

    "Rust": {
        "manifests": ["Cargo.toml"],
        "frameworks": {
            "actix-web": "Actix Web",
            "axum": "Axum",
            "rocket": "Rocket",
            "warp": "Warp",
        },
    },

    "C#": {
        "manifests": ["*.csproj"],
        "frameworks": {
            "Microsoft.AspNetCore.App": "ASP.NET Core",
            "Microsoft.AspNetCore": "ASP.NET Core",
            "Blazor": "Blazor",
        },
    },

    "PHP": {
        "manifests": ["composer.json"],
        "frameworks": {
            "laravel/framework": "Laravel",
            "symfony/framework-bundle": "Symfony",
            "codeigniter4/framework": "CodeIgniter",
            "cakephp/cakephp": "CakePHP",
            "yiisoft/yii2": "Yii",
            "slim/slim": "Slim",
        },
    },

    "Ruby": {
        "manifests": ["Gemfile"],
        "frameworks": {
            "rails": "Ruby on Rails",
            "sinatra": "Sinatra",
            "hanami": "Hanami",
        },
    },

    "Kotlin": {
        "manifests": ["build.gradle.kts"],
        "frameworks": {
            "ktor": "Ktor",
            "spring-boot": "Spring Boot",
        },
    },

    "Swift": {
        "manifests": ["Package.swift"],
        "frameworks": {
            "vapor": "Vapor",
            "kitura": "Kitura",
        },
    },

    "Dart": {
        "manifests": ["pubspec.yaml"],
        "frameworks": {
            "flutter": "Flutter",
            "shelf": "Shelf",
        },
    },

    "Scala": {
        "manifests": ["build.sbt"],
        "frameworks": {
            "play": "Play Framework",
            "akka-http": "Akka HTTP",
            "scalatra": "Scalatra",
        },
    },

    "Elixir": {
        "manifests": ["mix.exs"],
        "frameworks": {
            "phoenix": "Phoenix",
        },
    },

    "C++": {
        "manifests": ["CMakeLists.txt"],
        "frameworks": {
            "qt": "Qt",
            "juce": "JUCE",
            "poco": "POCO",
        },
    },

    "C": {
        "manifests": ["CMakeLists.txt"],
        "frameworks": {
            "esp-idf": "ESP-IDF",
            "zephyr": "Zephyr",
        },
    },

    "Lua": {
        "manifests": ["rockspec"],
        "frameworks": {
            "openresty": "OpenResty",
            "love": "LÖVE",
        },
    },

    "R": {
        "manifests": ["DESCRIPTION"],
        "frameworks": {
            "shiny": "Shiny",
            "plumber": "Plumber",
        },
    },

    "MATLAB": {
        "manifests": [],
        "frameworks": {
            "simulink": "Simulink",
        },
    },
}