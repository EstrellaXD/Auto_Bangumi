# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Development Environment Setup:**
```bash
cd backend && ./dev.sh
```
This sets up a Python virtual environment, installs dependencies with Tsinghua mirror, configures pre-commit hooks, and starts the development server on port 7892.

**Run Application:**
```bash
cd backend/src && python main.py
```

**Frontend Development:**
```bash
cd webui && pnpm install && pnpm run dev  # Development server
cd webui && pnpm run build               # Production build
./build-frontend.sh                      # Build and move to backend/src/dist
```

**Linting and Formatting:**
```bash
cd backend && ./venv/bin/ruff check .
cd backend && ./venv/bin/ruff format .
cd backend && ./venv/bin/black .
cd webui && pnpm run lint                # Frontend linting
cd webui && pnpm run format              # Frontend formatting
```

**Testing:**
```bash
cd backend && ./venv/bin/pytest
cd backend && ./venv/bin/pytest test/test_specific_module.py  # Run specific test
cd webui && pnpm run test                # Frontend tests
cd webui && pnpm run test:build          # TypeScript type checking
```

## Architecture

Auto_Bangumi is an RSS-based automatic anime downloading and organization tool with a FastAPI backend and Vue.js frontend.

**Backend Structure (Python FastAPI):**
- `main.py`: FastAPI application entry point with poster serving and static file mounting
- `module/core/`: Core async application framework
  - `aiocore.py`: AsyncApplicationCore manages service lifecycle and task scheduling
  - `services/`: Service implementations extending BaseService (RSS, Download, Renamer)
  - `monitors/`: Background monitors for downloads, notifications, and renaming
  - `task_manager.py`: TaskManager handles async task scheduling and execution
- `module/api/`: REST API endpoints organized by feature (auth, bangumi, config, etc.)
- `module/parser/`: Content parsing system for RSS feeds, torrents, and metadata
- `module/downloader/`: Download client abstractions (qBittorrent, Aria2, Transmission)
- `module/manager/`: File management (collection, renaming) and torrent handling
- `module/rss/`: RSS feed processing and analysis
- `module/database/`: SQLModel-based database layer for bangumi, RSS, and torrent data
- `module/network/`: HTTP client abstractions with proxy and caching support

**Frontend Structure (Vue.js + TypeScript):**
- Located in `webui/` with Vite build system
- Uses UnoCSS for styling, Naive UI for components
- Auto-import configuration for Vue Composition API
- API client in `src/api/` matching backend endpoints
- Pinia for state management
- Vue Router with file-based routing

**Key Data Flow:**
1. RSS feeds are parsed and analyzed for anime information
2. TMDB/Bangumi APIs provide metadata enrichment  
3. Download clients handle torrent/magnet downloads
4. File renamer organizes downloads into media library structure
5. Web UI provides management interface via REST API

**Service Architecture:**
The application uses an async service-based architecture where:
- Each service (RSS, Download, Renamer) extends BaseService
- AsyncApplicationCore manages service lifecycle
- TaskManager schedules periodic service execution
- Services communicate via events system
- Monitors handle background tasks like download tracking

**Configuration:**
- Main config in `config/config.json`
- Search providers in `config/search_provider.json`
- Environment variables for runtime settings

## Development Guidelines

**Branch Strategy:**
- `main`: Stable releases only
- `<version>-dev`: Development branches for each minor version (e.g., `3.1-dev`)
- Bug fixes go to current version dev branch
- New features go to next version dev branch

**Code Style:**
- Backend: Ruff + Black formatting, Python 3.10+ target
- Frontend: ESLint + Prettier, TypeScript strict mode
- Pre-commit hooks enforce formatting