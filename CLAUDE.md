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

**Linting and Formatting:**
```bash
cd backend && ./venv/bin/ruff check .
cd backend && ./venv/bin/ruff format .
cd backend && ./venv/bin/black .
```

**Testing:**
```bash
cd backend && ./venv/bin/pytest
cd backend && ./venv/bin/pytest test/test_specific_module.py  # Run specific test
```

## Architecture

Auto_Bangumi is an RSS-based automatic anime downloading and organization tool with a FastAPI backend and Vue.js frontend.

**Backend Structure (Python FastAPI):**
- `main.py`: FastAPI application entry point with poster serving and static file mounting
- `module/core/`: Core async application framework
  - `aiocore.py`: AsyncApplicationCore manages service lifecycle and task scheduling
  - `services.py`: BaseService abstract class and service implementations (RSS, Download, Renamer)
  - `task_manager.py`: TaskManager handles async task scheduling and execution
  - `events.py`: Event system for inter-service communication
- `module/api/`: REST API endpoints organized by feature (auth, bangumi, config, etc.)
- `module/parser/`: Content parsing system for RSS feeds, torrents, and metadata
- `module/downloader/`: Download client abstractions (qBittorrent, Aria2, Transmission)
- `module/manager/`: File management (collection, renaming) and torrent handling
- `module/rss/`: RSS feed processing and analysis
- `module/database/`: SQLModel-based database layer for bangumi, RSS, and torrent data
- `module/network/`: HTTP client abstractions with proxy and caching support

**Frontend Structure (Vue.js + TypeScript):**
- Located in `webui/` with standard Vue project structure
- API client in `src/api/` matching backend endpoints
- Component-based UI with reusable elements in `src/components/`

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

**Configuration:**
- Main config in `config/config.json`
- Search providers in `config/search_provider.json`
- Environment variables for runtime settings