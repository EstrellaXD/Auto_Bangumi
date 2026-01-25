# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoBangumi is an RSS-based automatic anime downloading and organization tool. It monitors RSS feeds from anime torrent sites (Mikan, DMHY, Nyaa), downloads episodes via qBittorrent/Aria2/Transmission, and organizes files into a Plex/Jellyfin-compatible directory structure with automatic renaming.

**Current Version:** 3.2.0-beta.4

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
cd backend && uv run ruff check src --fix  # auto-fix issues
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
docker run -p 7892:7892 \
  -v /path/to/config:/app/config \
  -v /path/to/data:/app/data \
  -e PUID=1000 -e PGID=1000 \
  auto_bangumi:latest
```

## Architecture

### Backend Structure

```
backend/src/
├── main.py                 # FastAPI entry point, mounts API at /api
├── dev_server.py           # Development server runner
├── module/
│   ├── api/               # REST API routes (v1 prefix)
│   │   ├── auth.py        # JWT authentication endpoints
│   │   ├── passkey.py     # WebAuthn/Passkey endpoints
│   │   ├── bangumi.py     # Anime series CRUD
│   │   ├── rss.py         # RSS feed management
│   │   ├── config.py      # Configuration endpoints
│   │   ├── program.py     # Program status/control
│   │   ├── downloader.py  # Download client status
│   │   ├── search.py      # Torrent search
│   │   ├── setup.py       # Initial setup wizard
│   │   └── log.py         # Log retrieval
│   ├── core/              # Application logic
│   │   ├── program.py     # Main controller, orchestrates all operations
│   │   ├── sub_thread.py  # Background tasks (RSSThread, RenameThread)
│   │   └── status.py      # Application state tracking
│   ├── models/            # SQLModel ORM models (Pydantic + SQLAlchemy)
│   │   ├── bangumi.py     # Bangumi & Episode models
│   │   ├── rss.py         # RSSItem model
│   │   ├── torrent.py     # Torrent, EpisodeFile, SubtitleFile
│   │   ├── user.py        # User & UserLogin models
│   │   ├── passkey.py     # WebAuthn Passkey model
│   │   └── config.py      # Configuration models
│   ├── database/          # Database operations (SQLite at data/data.db)
│   │   ├── combine.py     # Database class, migrations
│   │   ├── engine.py      # SQLAlchemy engine config
│   │   ├── bangumi.py     # Bangumi ORM operations
│   │   ├── rss.py         # RSS ORM operations
│   │   ├── torrent.py     # Torrent ORM operations
│   │   └── user.py        # User ORM operations
│   ├── rss/               # RSS parsing and analysis
│   │   ├── engine.py      # Core RSS parsing logic
│   │   └── analyser.py    # Feed analysis
│   ├── downloader/        # Download client integration
│   │   ├── download_client.py  # Abstract base class
│   │   ├── path.py        # Download path utilities
│   │   └── client/        # Client implementations
│   │       ├── qb_downloader.py    # qBittorrent API
│   │       ├── aria2_downloader.py # Aria2 RPC
│   │       └── tr_downloader.py    # Transmission RPC
│   ├── searcher/          # Torrent search (Mikan, DMHY, Nyaa)
│   ├── parser/            # Torrent name parsing
│   │   ├── title_parser.py # Title parsing engine
│   │   └── analyser/      # Metadata extractors
│   │       ├── raw_parser.py     # Basic extraction
│   │       ├── torrent_parser.py # Advanced analysis
│   │       ├── mikan_parser.py   # Mikan-specific
│   │       ├── tmdb_parser.py    # TMDB enrichment
│   │       ├── bgm_parser.py     # Bangumi.tv integration
│   │       └── openai.py         # OpenAI smart parsing
│   ├── manager/           # File organization and renaming
│   │   ├── renamer.py     # Automatic file renaming
│   │   ├── collector.py   # File collection
│   │   └── torrent.py     # Torrent file processing
│   ├── notification/      # Notification plugins
│   │   └── plugin/
│   │       ├── telegram.py    # Telegram
│   │       ├── bark.py        # Bark (iOS)
│   │       ├── wecom.py       # WeChat Work
│   │       ├── slack.py       # Slack
│   │       └── server_chan.py # ServerChan
│   ├── security/          # Authentication
│   │   ├── jwt.py         # JWT token handling
│   │   ├── webauthn.py    # WebAuthn/Passkey support
│   │   ├── auth_strategy.py # Auth strategy selection
│   │   └── api.py         # Auth dependency injection
│   ├── conf/              # Configuration management
│   │   ├── config.py      # Settings with version migration
│   │   ├── const.py       # Environment variable mappings
│   │   └── log.py         # Logging configuration
│   ├── network/           # HTTP client utilities
│   ├── update/            # Version checking, data migration
│   ├── checker/           # Configuration validation
│   └── utils/             # Helper utilities
└── test/                  # Test suite (24 test files)
    ├── conftest.py        # Pytest fixtures
    ├── factories.py       # Test data factories
    ├── test_api_*.py      # API endpoint tests
    ├── test_integration.py # End-to-end tests
    └── test_*.py          # Unit tests
```

### Frontend Structure

```
webui/src/
├── api/                   # Axios API client (12 modules)
│   ├── auth.ts, passkey.ts, bangumi.ts, rss.ts
│   ├── config.ts, downloader.ts, program.ts
│   ├── search.ts, setup.ts, log.ts, check.ts
├── components/
│   ├── basic/             # Reusable UI components (25+)
│   ├── layout/            # Sidebar, topbar, mobile nav
│   ├── setting/           # Configuration panels
│   │   ├── config-download.vue, config-normal.vue
│   │   ├── config-notification.vue, config-passkey.vue
│   │   ├── config-openai.vue, config-proxy.vue
│   │   └── config-parser.vue, config-player.vue
│   └── setup/             # Setup wizard (8 steps)
├── pages/index/           # Router-based pages
│   ├── bangumi.vue        # Anime series management
│   ├── calendar.vue       # Schedule calendar
│   ├── rss.vue            # RSS feed management
│   ├── downloader.vue     # Download monitoring
│   ├── config.vue         # Settings page
│   ├── log.vue            # Application logs
│   └── player.vue         # Media player
├── store/                 # Pinia state management (9 stores)
├── hooks/                 # Vue composables (9 hooks)
├── services/              # Service layer (webauthn.ts)
├── types/                 # TypeScript definitions
├── i18n/                  # Localization (en.json, zh-CN.json)
├── style/                 # SCSS modules
└── router/                # Vue Router config
```

## API Endpoints

All API routes are prefixed with `/api/v1`:

| Route | Module | Purpose |
|-------|--------|---------|
| `/auth/*` | auth.py | JWT login/logout |
| `/passkey/*` | passkey.py | WebAuthn registration/auth |
| `/bangumi/*` | bangumi.py | Anime series CRUD |
| `/rss/*` | rss.py | RSS feed management |
| `/config/*` | config.py | Configuration get/set |
| `/program/*` | program.py | Start/stop/status |
| `/downloader/*` | downloader.py | Download client status |
| `/search/*` | search.py | Torrent search |
| `/setup/*` | setup.py | Initial setup wizard |
| `/log/*` | log.py | Log retrieval |

## Key Data Flow

1. RSS feeds are parsed by `module/rss/` to extract torrent information
2. Torrent names are analyzed by `module/parser/analyser/` to extract anime metadata
3. TMDB/Mikan/OpenAI enriches metadata with official titles and artwork
4. Downloads are managed via `module/downloader/` (qBittorrent/Aria2/Transmission API)
5. Files are organized by `module/manager/` into standard directory structure
6. Background tasks run in `module/core/sub_thread.py` to avoid blocking

## Database

**Location:** `data/data.db` (SQLite)

**Tables:** bangumi, rssitem, torrent, torrent_episode, user, passkey, schema_version

**Current Schema Version:** 3

### Migrations

Schema migrations are tracked via a `schema_version` table. To add a new migration:

1. Increment `CURRENT_SCHEMA_VERSION` in `backend/src/module/database/combine.py`
2. Append a new entry to the `MIGRATIONS` list:
   ```python
   (
       version_number,
       "description",
       ["SQL statement 1", "SQL statement 2"],
   ),
   ```
3. Migrations run automatically on startup via `run_migrations()`

**Existing migrations:**
- v1: Add `air_weekday` column to bangumi table
- v2: Add RSS connection status columns (`connection_status`, `last_checked_at`, `last_error`)
- v3: Create passkey table for WebAuthn support

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AB_INTERVAL_TIME` | 900 | RSS check interval (seconds) |
| `AB_RENAME_FREQ` | 60 | Rename check interval (seconds) |
| `AB_WEBUI_PORT` | 7892 | Web UI port |
| `AB_DOWNLOADER_HOST` | 172.17.0.1:8080 | Downloader address |
| `AB_DOWNLOADER_USERNAME` | admin | Downloader username |
| `AB_DOWNLOADER_PASSWORD` | adminadmin | Downloader password |
| `AB_DOWNLOAD_PATH` | /downloads/Bangumi | Download directory |
| `AB_RSS_COLLECTOR` | true | Enable RSS parsing |
| `AB_RENAME` | true | Enable file renaming |
| `AB_METHOD` | pn | Rename method |
| `AB_DEBUG_MODE` | false | Enable debug logging |
| `HOST` | 0.0.0.0 | Bind address |
| `IPV6` | (unset) | Enable IPv6 binding (::) |
| `PUID` | 1000 | Container user ID |
| `PGID` | 1000 | Container group ID |
| `UMASK` | 022 | File creation mask |
| `TZ` | Asia/Shanghai | Timezone |

## Code Style

- **Python:** Black (88 char lines), Ruff linter (E, F, I rules), target Python 3.10+
- **TypeScript:** ESLint + Prettier
- **Pre-commit hooks:** Black and Ruff configured in `.pre-commit-config.yaml`
- Run formatters before committing

## Git Branching & Contribution Workflow

### Semantic Versioning

AutoBangumi follows [Semantic Versioning (SemVer)](https://semver.org/) with `<Major>.<Minor>.<Patch>` format:
- **Major**: Breaking changes to configuration/API
- **Minor**: Backward-compatible new features
- **Patch**: Backward-compatible bug fixes

### Branch Model: "Branch Development, Trunk Release"

- **`main`**: Stable releases only, never commit directly
- **`X.Y-dev`**: Active development branches (e.g., `3.2-dev`, `3.1-dev`)

### Which Branch to Use?

| Type of Change | Target Branch | Example |
|---------------|---------------|---------|
| Bug fix | Current released version's `-dev` branch | If `3.1.0` is latest release, PR to `3.1-dev` |
| New feature | Next unreleased version's `-dev` branch | If `3.1.0` is latest, PR to `3.2-dev` |
| Documentation | `docs-update` branch | - |

### Branch Lifecycle

1. When `3.1-dev` merges to `main` → releases `3.1.0`
2. New branch `3.2-dev` is created for next features
3. Previous `3.0-dev` is archived
4. `3.1-dev` enters maintenance mode (bug fixes only)
5. Bug fixes in `3.1-dev` → merge to `main` → releases `3.1.1`, `3.1.2`, etc.

### Pull Request Guidelines

1. **One PR = One concern** — don't mix unrelated changes
2. **Write clear title/description** — explain what and why
3. **Link related issues/RFCs** — provide context for reviewers
4. **Check "Allow edits from maintainers"** — enables quick fixes
5. **Ensure tests and linting pass locally** — CI will also check

### Request for Comments (RFC)

For large features or refactors, create an RFC proposal first via [Issue: Feature Proposal](https://github.com/EstrellaXD/Auto_Bangumi/issues/new?assignees=&labels=RFC&projects=&template=rfc.yml&title=%5BRFC%5D%3A+) to seek consensus before implementation.

Find existing RFCs: [AutoBangumi RFCs](https://github.com/EstrellaXD/Auto_Bangumi/issues?q=is%3Aissue+label%3ARFC)

### Project Roadmap

Check [GitHub Project boards](https://github.com/EstrellaXD/Auto_Bangumi/projects?query=is%3Aopen) for:
- Current development priorities
- In-progress work (avoid duplicating effort)
- Planned features and bug fixes

## CI/CD Workflow

The GitHub Actions workflow (`.github/workflows/build.yml`) runs:

1. **test** - Python backend tests with pytest
2. **webui-test** - TypeScript type checking
3. **version-info** - Detect version from tags/PRs
4. **build-webui** - Vite production build
5. **build-docker** - Multi-platform Docker build (amd64, arm64)
6. **release** - GitHub release with artifacts
7. **telegram** - Notification on release

### Docker Images

Published to:
- Docker Hub: `estrellaxd/auto_bangumi`
- GitHub Container Registry: `ghcr.io/estrellaxd/auto_bangumi`

Tags:
- `latest` - Latest stable release
- `dev-latest` - Latest alpha/beta
- `X.Y.Z` - Specific version

## Releasing a Beta Version

1. Update version in `backend/pyproject.toml`
2. Update `CHANGELOG.md` with the new version heading
3. Commit and push to the dev branch
4. Create and push a tag with the version name (e.g., `3.2.0-beta.4`):
   ```bash
   git tag 3.2.0-beta.4
   git push origin 3.2.0-beta.4
   ```
5. The CI/CD workflow detects the tag contains "beta", uses the tag name as the VERSION string, generates `module/__version__.py`, and builds the Docker image

The VERSION is injected at build time via CI - `module/__version__.py` does not exist in the repo. At runtime, `module/conf/config.py` imports it or falls back to `"DEV_VERSION"`.

## Testing

### Running Tests

```bash
# All tests
cd backend && uv run pytest

# Specific test file
cd backend && uv run pytest src/test/test_api_bangumi.py -v

# With coverage
cd backend && uv run pytest --cov=module

# Frontend type checking
cd webui && pnpm test:build
```

### Test Structure

- `conftest.py` - Shared fixtures (test database, mock clients)
- `factories.py` - Test data factories for models
- `test_api_*.py` - API endpoint tests
- `test_integration.py` - End-to-end workflow tests
- Unit tests for parsers, renamer, notification, etc.

## Key Dependencies

### Backend (Python 3.10+)
- FastAPI 0.109.0+ (web framework)
- SQLModel 0.0.14+ (ORM: Pydantic + SQLAlchemy)
- HTTPX 0.25.0+ (async HTTP client)
- Uvicorn 0.27.0+ (ASGI server)
- WebAuthn 2.0.0 (passkey authentication)
- OpenAI 1.54.3+ (smart parsing)

### Frontend
- Vue 3.5.8 (Composition API)
- TypeScript 4.9.5
- Pinia 2.2.2 (state management)
- Naive UI 2.39.0 (component library)
- UnoCSS (utility CSS)
- Vite 4.5.5 (build tool)

## Notes

- Documentation and comments are in Chinese
- Uses SQLModel (hybrid Pydantic + SQLAlchemy ORM)
- External integrations: qBittorrent API, TMDB API, OpenAI API, Bangumi.tv
- Version tracked in `/config/version.info` (for cross-version upgrade detection)
- WebAuthn/Passkey support added for passwordless authentication
- RSS feeds track connection status for monitoring feed health

## Common Tasks

### Adding a New API Endpoint

1. Create route in `backend/src/module/api/`
2. Add router to `backend/src/module/api/__init__.py`
3. Add corresponding TypeScript API client in `webui/src/api/`
4. Add types in `webui/src/types/`

### Adding a New Notification Plugin

1. Create plugin in `backend/src/module/notification/plugin/`
2. Implement required interface methods
3. Register in notification module `__init__.py`
4. Add UI configuration in `webui/src/components/setting/config-notification.vue`

### Adding a Database Column

1. Update SQLModel in `backend/src/module/models/`
2. Add migration in `backend/src/module/database/combine.py`
3. Increment `CURRENT_SCHEMA_VERSION`
4. Update related database operations

### Adding a Download Client

1. Create client in `backend/src/module/downloader/client/`
2. Extend `DownloadClient` base class
3. Register in downloader factory
4. Add UI configuration options
