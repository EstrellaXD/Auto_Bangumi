"""Notification manager for handling multiple providers."""

import asyncio
import logging
from typing import TYPE_CHECKING

from module.conf import settings
from module.database import Database
from module.models.bangumi import Notification

if TYPE_CHECKING:
    from module.notification.base import NotificationProvider
    from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manager for handling notifications across multiple providers."""

    def __init__(self):
        self.providers: list["NotificationProvider"] = []
        self._load_providers()

    def _load_providers(self):
        """Initialize providers from configuration."""
        from module.notification.providers import PROVIDER_REGISTRY

        for cfg in settings.notification.providers:
            if not cfg.enabled:
                continue

            provider_cls = PROVIDER_REGISTRY.get(cfg.type.lower())
            if provider_cls:
                try:
                    provider = provider_cls(cfg)
                    self.providers.append(provider)
                    logger.debug(f"Loaded notification provider: {cfg.type}")
                except Exception as e:
                    logger.warning(f"Failed to load provider {cfg.type}: {e}")
            else:
                logger.warning(f"Unknown notification provider type: {cfg.type}")

    async def _get_poster(self, notification: Notification):
        """Fetch poster path from database if not already set."""
        if notification.poster_path:
            return

        def _get_poster_sync():
            with Database() as db:
                data = db.bangumi.search_official_title(notification.official_title)
                if data:
                    notification.poster_path = data.poster_link

        await asyncio.to_thread(_get_poster_sync)

    async def send_all(self, notification: Notification):
        """Send notification to all enabled providers.

        Args:
            notification: The notification data to send.
        """
        if not self.providers:
            logger.debug("No notification providers configured")
            return

        # Fetch poster if needed
        await self._get_poster(notification)

        # Send to all providers in parallel
        async def send_to_provider(provider: "NotificationProvider"):
            try:
                async with provider:
                    await provider.send(notification)
                logger.debug(
                    f"Sent notification via {provider.__class__.__name__}: "
                    f"{notification.official_title}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to send notification via {provider.__class__.__name__}: {e}"
                )

        await asyncio.gather(
            *[send_to_provider(p) for p in self.providers],
            return_exceptions=True,
        )

    async def test_provider(self, index: int) -> tuple[bool, str]:
        """Test a specific provider by index.

        Args:
            index: The index of the provider in the providers list.

        Returns:
            A tuple of (success, message).
        """
        if index < 0 or index >= len(self.providers):
            return False, f"Invalid provider index: {index}"

        provider = self.providers[index]
        try:
            async with provider:
                return await provider.test()
        except Exception as e:
            return False, f"Test failed: {e}"

    @staticmethod
    async def test_provider_config(config: "ProviderConfig") -> tuple[bool, str]:
        """Test a provider configuration without saving it.

        Args:
            config: The provider configuration to test.

        Returns:
            A tuple of (success, message).
        """
        from module.notification.providers import PROVIDER_REGISTRY

        provider_cls = PROVIDER_REGISTRY.get(config.type.lower())
        if not provider_cls:
            return False, f"Unknown provider type: {config.type}"

        try:
            provider = provider_cls(config)
            async with provider:
                return await provider.test()
        except Exception as e:
            return False, f"Test failed: {e}"

    def __len__(self) -> int:
        return len(self.providers)
