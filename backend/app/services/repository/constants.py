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
    # Existing
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

    # Web
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",

    # Additional
    ".dart",
    ".scala",
    ".lua",
    ".sh",
    ".bash",
    ".zsh",
    ".r",
    ".m",
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
    "python": [
        "pyproject.toml",
        "requirements.txt",
        "Pipfile",
        "poetry.lock",
    ],

    "javascript": [
        "package.json",
    ],

    "typescript": [
        "package.json",
    ],

    "java": [
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
    ],

    "go": [
        "go.mod",
    ],

    "rust": [
        "Cargo.toml",
    ],

    "php": [
        "composer.json",
    ],

    "dart": [
        "pubspec.yaml",
    ],

    "scala": [
        "build.sbt",
    ],

    "lua": [
        "*.rockspec",
    ],

    "ruby": [
        "Gemfile",
    ],

    "cpp": [
        "CMakeLists.txt",
    ],

    "c": [
        "CMakeLists.txt",
    ],

    "csharp": [
        "*.csproj",
    ],

    "kotlin": [
        "build.gradle.kts",
    ],

    "swift": [
        "Package.swift",
    ],

    "shell": [],

    "html": [],

    "css": [],

    "scss": [],

    "sass": [],

    "r": [
        "DESCRIPTION",
    ],

    "matlab": [],
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
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",

    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".kt": "kotlin",
    ".swift": "swift",
    ".php": "php",
    ".rb": "ruby",

    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",

    ".dart": "dart",
    ".scala": "scala",
    ".lua": "lua",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".r": "r",
    ".m": "matlab",
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
    "python": {
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

    "javascript": {
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

    "typescript": {
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

    "java": {
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

    "go": {
        "manifests": ["go.mod"],
        "frameworks": {
            "github.com/gin-gonic/gin": "Gin",
            "github.com/gofiber/fiber": "Fiber",
            "github.com/labstack/echo": "Echo",
            "github.com/go-chi/chi": "Chi",
            "github.com/astaxie/beego": "Beego",
        },
    },

    "rust": {
        "manifests": ["Cargo.toml"],
        "frameworks": {
            "actix-web": "Actix Web",
            "axum": "Axum",
            "rocket": "Rocket",
            "warp": "Warp",
        },
    },

    "csharp": {
        "manifests": ["*.csproj"],
        "frameworks": {
            "Microsoft.AspNetCore.App": "ASP.NET Core",
            "Microsoft.AspNetCore": "ASP.NET Core",
            "Blazor": "Blazor",
        },
    },

    "php": {
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

    "ruby": {
        "manifests": ["Gemfile"],
        "frameworks": {
            "rails": "Ruby on Rails",
            "sinatra": "Sinatra",
            "hanami": "Hanami",
        },
    },

    "kotlin": {
        "manifests": ["build.gradle.kts"],
        "frameworks": {
            "ktor": "Ktor",
            "spring-boot": "Spring Boot",
        },
    },

    "swift": {
        "manifests": ["Package.swift"],
        "frameworks": {
            "vapor": "Vapor",
            "kitura": "Kitura",
        },
    },

    "dart": {
        "manifests": ["pubspec.yaml"],
        "frameworks": {
            "flutter": "Flutter",
            "shelf": "Shelf",
        },
    },

    "scala": {
        "manifests": ["build.sbt"],
        "frameworks": {
            "play": "Play Framework",
            "akka-http": "Akka HTTP",
            "scalatra": "Scalatra",
        },
    },

    "elixir": {
        "manifests": ["mix.exs"],
        "frameworks": {
            "phoenix": "Phoenix",
        },
    },

    "cpp": {
        "manifests": ["CMakeLists.txt"],
        "frameworks": {
            "qt": "Qt",
            "juce": "JUCE",
            "poco": "POCO",
        },
    },

    "c": {
        "manifests": ["CMakeLists.txt"],
        "frameworks": {
            "esp-idf": "ESP-IDF",
            "zephyr": "Zephyr",
        },
    },

    "lua": {
        "manifests": ["rockspec"],
        "frameworks": {
            "openresty": "OpenResty",
            "love": "LÖVE",
        },
    },

    "r": {
        "manifests": ["DESCRIPTION"],
        "frameworks": {
            "shiny": "Shiny",
            "plumber": "Plumber",
        },
    },

    "matlab": {
        "manifests": [],
        "frameworks": {
            "simulink": "Simulink",
        },
    },
}