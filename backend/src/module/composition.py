"""Application composition root: concrete adapters are wired only here."""

from module.application.auth import AuthenticationService
from module.database import Database

auth_service = AuthenticationService(Database)
