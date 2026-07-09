"""Application composition root: concrete adapters are wired only here."""

from module.application.auth import AuthenticationService
from module.database import Database
from module.security.jwt import decode_token

auth_service = AuthenticationService(Database, legacy_token_decoder=decode_token)
