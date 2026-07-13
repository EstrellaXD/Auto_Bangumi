"""Dependency-inversion contracts used by application services."""

from .auth import AuthUnitOfWork

__all__ = ["AuthUnitOfWork"]
