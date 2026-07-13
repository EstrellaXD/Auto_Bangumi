"""Hermetic E2E lanes for isolated runtime and real-downloader contracts.

Root-level ``e2e/scripts/stack.py`` owns production-image orchestration and
local-only support services.  Runtime tests own one source-process sandbox per
test; downloader tests consume one explicitly selected Compose stack.
"""
