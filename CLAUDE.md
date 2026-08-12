# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RepoIntel AI is a **backend service** that indexes GitHub repositories, parses source code into a language-agnostic symbol model, detects frameworks, and (planned) powers RAG chat and architecture analysis.

- **Stack:** FastAPI + PostgreSQL + Tree-sitter + Python 3.12 + `uv`
- **Code:** All in `backend/` (FastAPI app). `frontend/` and `docs/` are empty placeholders.
- **Ignore:** Root `uv.lock`, empty `python` file, `backend/storage/repositories/` (cloned repos)

## Quick Start

```bash
cd backend

# Install dependencies
uv sync

# Run dev server
uv run uvicorn app.main:app --reload

# Database migrations
uv run alembic upgrade head
```

**Prerequisites:** PostgreSQL running, valid `backend/.env` file (see [docs/development/deployment.md](docs/development/deployment.md))

## Documentation Structure

This repository uses **modular documentation** in `docs/`:

### Architecture
- [Architecture Overview](docs/architecture/overview.md) — System design, tech stack, data flow
- [Database Schema](docs/architecture/database-schema.md) — Tables, relationships, migrations
- [Indexing Pipeline](docs/architecture/indexing-pipeline.md) — Clone → scan → classify → persist flow
- [Parser Subsystem](docs/architecture/parser-subsystem.md) — Tree-sitter → semantic captures → IR

### Modules (What's Implemented)
- [Auth Module](docs/modules/auth.md) — JWT + argon2 authentication (✅ Complete)
- [Repository Indexing](docs/modules/repository-indexing.md) — Git cloning + file scanning (✅ Complete)
- [Parser Module](docs/modules/parser.md) — Tree-sitter parsing for 4 languages (⚠️ 80% complete)

### Development
- [Collaboration Rules](docs/development/collaboration-rules.md) — **Required workflow for all code changes**
- [Testing Guide](docs/development/testing.md) — Current state + pytest setup plan
- [Deployment Guide](docs/development/deployment.md) — How to run locally and in production

### Roadmap (What's Next)
- [Phase 0: Stabilize](docs/roadmap/phase-0-stabilize.md) — Fix broken migration, remove debug code, add tests
- [Phase 1: Persist Symbols](docs/roadmap/phase-1-persist-symbols.md) — Save parser output to database
- [Phase 2: Background Jobs](docs/roadmap/phase-2-background-jobs.md) — Celery + Redis for async indexing
- [Phase 3: RAG Chat](docs/roadmap/phase-3-rag-chat.md) — Chunking + embeddings + pgvector + Groq LLM
- [Phase 4: Architecture Graph](docs/roadmap/phase-4-architecture-graph.md) — Dependency visualization with Mermaid

### Technical Debt
- [Known Issues & TODOs](docs/technical-debt.md) — Prioritized list of bugs, complexity, missing features

## Current Status (2026-08-12)

| Component | Status | LOC | Details |
|---|---|---|---|
| **Auth** | ✅ Complete | ~300 | JWT + argon2, production-ready |
| **Repository Indexing** | ✅ Complete | ~1,200 | Clone, scan, classify, framework detect |
| **Parser** | ⚠️ 80% | ~2,500 | Works but output not persisted, has debug prints |
| **RAG** | ❌ Not started | 0 | Empty files |
| **Architecture** | ❌ Not started | 0 | Empty files |
| **Tests** | ❌ No suite | ~200 | Debug scripts, not pytest |

**Next milestone:** Complete **Phase 0** (stabilize foundation) before building new features.

## Key Conventions

- **Singleton services:** One instance per module (`repository_service = RepositoryService()`)
- **Layering:** API → CRUD → Services → Models/DB (strict separation)
- **Exceptions:** Domain exceptions in `app/exceptions/` mapped to HTTP codes in routers
- **Auth:** JWT via `get_current_active_user` dependency, ownership enforced by `owner_id`
- **Config:** `constants.py` is single source of truth for all mappings/rules

## Working with Claude Code

**Before making ANY code changes:**

1. ✋ **Stop and explain** what/why/impact/risks
2. 📝 **Update relevant docs** in `docs/`
3. ⏸️ **Wait for approval** ("yes, do it")
4. 🔨 **After changes:** Show summary, remind to `git diff`, `git commit`, `git push`

**See full workflow:** [docs/development/collaboration-rules.md](docs/development/collaboration-rules.md)

## Parser Quick Reference

The parser is the most complex subsystem. Key concepts:

- **Tier 1 languages:** Python, Java, JavaScript, TypeScript (full AST extraction via Tree-sitter)
- **Tier 0 languages:** ~20 others (text-only, no AST)
- **Semantic captures:** `.scm` query files emit language-agnostic names (`@function.definition`, `@class.definition`)
- **Two registries:** `LanguageRegistry` (how language integrates) + `GrammarRegistry` (grammar metadata)
- **Pipeline:** FileContent → TreeSitterService → QueryExtractor → SymbolExtractor → ParsedDocument

**Deep dive:** [docs/architecture/parser-subsystem.md](docs/architecture/parser-subsystem.md)

## API Endpoints (Implemented)

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/auth/register` | POST | Create user account |
| `/auth/login` | POST | Get JWT token |
| `/auth/me` | GET | Get current user |
| `/repositories` | POST | Index a GitHub repo (sync, 10-60s) |
| `/repositories` | GET | List user's repos |
| `/repositories/{id}` | GET | Get repo details |
| `/repositories/{id}/files` | GET | List indexed files |
| `/repositories/{id}` | DELETE | Delete repo + cleanup |

**Planned:** `/repositories/{id}/chat`, `/repositories/{id}/architecture`, `/repositories/{id}/symbols`

## Commands Cheat Sheet

```bash
# Development
cd backend
uv run uvicorn app.main:app --reload           # Start dev server
uv run alembic upgrade head                     # Run migrations
uv run alembic revision --autogenerate -m "msg" # Create migration

# Debug parsers (not pytest)
uv run python tests/parsers/test_python_parser.py
uv run python tests/parsers/test_java_parser.py

# Database
psql repointel -c "SELECT * FROM repositories"
psql repointel -c "SELECT symbol_type, count(*) FROM repository_symbols GROUP BY 1"

# Future (once Phase 2 complete)
uv run celery -A app.worker.celery_app worker --loglevel=info
```

## Need Help?

- **Architecture questions?** Read [docs/architecture/](docs/architecture/)
- **How to implement X?** Check [docs/roadmap/](docs/roadmap/)
- **Found a bug?** Check [docs/technical-debt.md](docs/technical-debt.md)
- **Want to contribute?** Read [docs/development/collaboration-rules.md](docs/development/collaboration-rules.md) first
