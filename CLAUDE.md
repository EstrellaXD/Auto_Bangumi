# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoBangumi is an RSS-based automatic anime downloading and organization tool. It monitors RSS feeds from anime torrent sites (Mikan, DMHY, Nyaa), downloads episodes via qBittorrent, and organizes files into a Plex/Jellyfin-compatible directory structure with automatic renaming.

## Development Commands

### Backend (Python)

```bash
# Install dependencies
cd backend && uv sync

# Install with dev tools
cd backend && uv sync --group dev

# Run development server (port 7892, API docs at /docs)
cd backend/src && uv run python main.py

# Run tests
cd backend && uv run pytest
cd backend && uv run pytest src/test/test_xxx.py -v  # run specific test

# Linting and formatting
cd backend && uv run ruff check src
cd backend && uv run black src

# Add a dependency
cd backend && uv add <package>

# Add a dev dependency
cd backend && uv add --group dev <package>
```

### Frontend (Vue 3 + TypeScript)

```bash
cd webui

# Install dependencies (uses pnpm, not npm)
pnpm install

# Development server (port 5173)
pnpm dev

# Build for production
pnpm build

# Type checking
pnpm test:build

# Linting and formatting
pnpm lint
pnpm lint:fix
pnpm format
```

### Docker

```bash
docker build -t auto_bangumi:latest .
docker run -p 7892:7892 -v /path/to/config:/app/config -v /path/to/data:/app/data auto_bangumi:latest
```

## Architecture

```
backend/src/
├── main.py                 # FastAPI entry point, mounts API at /api
├── module/
│   ├── api/               # REST API routes (v1 prefix)
│   │   ├── auth.py        # Authentication endpoints
│   │   ├── bangumi.py     # Anime series CRUD
│   │   ├── rss.py         # RSS feed management
│   │   ├── config.py      # Configuration endpoints
│   │   ├── program.py     # Program status/control
│   │   └── search.py      # Torrent search
│   ├── core/              # Application logic
│   │   ├── context.py     # AppContext composition root (built in create_app, on app.state.ctx)
│   │   ├── scheduler.py   # PeriodicTask + Scheduler (generic background-loop runner)
│   │   ├── loops.py       # The individual periodic tick functions (rss/rename/offset/calendar)
│   │   └── offset_scanner.py
│   ├── models/            # SQLModel ORM models (Pydantic + SQLAlchemy)
│   ├── database/          # Async DB (aiosqlite) — repos + Database + migrations.py
│   ├── rss/               # RSS parsing and analysis
│   ├── downloader/        # qBittorrent integration
│   │   ├── base.py        # Downloader Protocol + DownloaderCapabilities
│   │   └── client/        # Download client implementations (qb, aria2, mock)
│   ├── searcher/          # Torrent search providers (Mikan, DMHY, Nyaa)
│   ├── parser/            # Torrent name parsing, metadata extraction
│   │   └── analyser/      # TMDB, Mikan, OpenAI parsers
│   ├── manager/           # File organization and renaming
│   ├── notification/      # Notification plugins (Telegram, Bark, etc.)
│   ├── conf/              # Configuration management, settings
│   ├── network/           # HTTP client utilities
│   └── security/          # JWT authentication

webui/src/
├── api/                   # Axios API client functions
├── components/            # Vue components (basic/, layout/, setting/)
├── pages/                 # Router-based page components
├── router/                # Vue Router configuration
├── store/                 # Pinia state management
├── i18n/                  # Internationalization (zh-CN, en-US)
└── hooks/                 # Custom Vue composables
```

## Key Data Flow

1. RSS feeds are parsed by `module/rss/` to extract torrent information
2. Torrent names are analyzed by `module/parser/analyser/` to extract anime metadata
3. Downloads are managed via `module/downloader/` (qBittorrent API)
4. Files are organized by `module/manager/` into standard directory structure
5. Periodic loops (`module/core/loops.py`) run under a `Scheduler` owned by the lifespan `AppContext` (`module/core/context.py`)

## Architecture conventions (3.3+)

- **Async DB throughout.** Everything runs on the async engine (`sqlite+aiosqlite`, WAL). Repositories (`database/{bangumi,rss,torrent,user,passkey}.py`) take an `AsyncSession` and are `async def`. `Database` is an async context manager owning one session with the repos attached (`db.rss`, `db.bangumi`, …).
- **Session per operation.** Get a session via `Depends(get_db)` in routes, or `async with Database() as db:` in loops/services. Never store a session on anything that outlives one request or one loop tick. `AppContext` holds no session.
- **Services take dependencies in their constructor** (composition, not inheritance): `RSSEngine(db)`, `TorrentManager(db)`, `Renamer(client)`, `SearchTorrent()`. They use `self.db.<repo>` internally; callers that only need a repo use `db.<repo>` directly.
- **Downloaders** implement the `Downloader` Protocol and declare `DownloaderCapabilities`; the facade (`DownloadClient`) skips-and-logs unsupported ops rather than crashing. The qB client is reused across operations (one login), not re-authed per call.
- **Config reloads** go through `AppContext.reload_settings()` (settings + http client + notifier + scheduler), not ad-hoc `settings.load()`.

## Code Style

- Python: Black (88 char lines), Ruff linter (E, F, I rules), target Python 3.10+
- TypeScript: ESLint + Prettier
- Run formatters before committing

## Git Branching

- `main`: Stable releases only
- `X.Y-dev` branches: Active development (e.g., `3.2-dev`)
- Bug fixes → PR to current released version's `-dev` branch
- New features → PR to next version's `-dev` branch

## Releasing a Beta Version

1. Update version in `backend/pyproject.toml`
2. Update `CHANGELOG.md` with the new version heading
3. Commit and push to the dev branch
4. Create and push a tag with the version name (e.g., `3.2.0-beta.4`):
   ```bash
   git tag 3.2.0-beta.4
   git push origin 3.2.0-beta.4
   ```
5. The CI/CD workflow (`.github/workflows/build.yml`) detects the tag contains "beta", uses the tag name as the VERSION string, generates `module/__version__.py`, and builds the Docker image

The VERSION is injected at build time via CI — `module/__version__.py` does not exist in the repo. At runtime, `module/conf/config.py` imports it or falls back to `"DEV_VERSION"`.

## Database Migrations

Schema migrations are tracked via a `schema_version` table in SQLite. To add a new migration:

1. Append a `Migration(version, "description", (…SQL…), already_applied=column_exists("table", "col"))` entry to the `MIGRATIONS` tuple in `backend/src/module/database/migrations.py` (`CURRENT_SCHEMA_VERSION` is derived from the list — do not edit it by hand)
2. Provide an `already_applied` guard (`column_exists` / `table_exists`) so a schema created out-of-band is detected and skipped
3. Migrations run automatically on startup via `run_migrations()` (each in a SAVEPOINT, stopping on first failure)

## Notes

- Documentation and comments are in Chinese
- Uses SQLModel (hybrid Pydantic + SQLAlchemy ORM)
- External integrations: qBittorrent API, TMDB API, OpenAI API
- Version tracked in `/config/version.info` (for cross-version upgrade detection)
