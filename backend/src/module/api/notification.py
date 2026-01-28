"""Notification API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from module.notification import NotificationManager
from module.models.config import NotificationProvider as ProviderConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notification", tags=["notification"])


class TestProviderRequest(BaseModel):
    """Request body for testing a saved provider by index."""

    provider_index: int = Field(..., description="Index of the provider to test")


class TestProviderConfigRequest(BaseModel):
    """Request body for testing an unsaved provider configuration."""

    type: str = Field(..., description="Provider type")
    enabled: bool = Field(True, description="Whether provider is enabled")
    token: Optional[str] = Field(None, description="Auth token")
    chat_id: Optional[str] = Field(None, description="Chat/channel ID")
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    server_url: Optional[str] = Field(None, description="Server URL")
    device_key: Optional[str] = Field(None, description="Device key")
    user_key: Optional[str] = Field(None, description="User key")
    api_token: Optional[str] = Field(None, description="API token")
    template: Optional[str] = Field(None, description="Custom template")
    url: Optional[str] = Field(None, description="URL for generic webhook")


class TestResponse(BaseModel):
    """Response for test notification endpoints."""

    success: bool
    message: str
    message_zh: str = ""
    message_en: str = ""


@router.post("/test", response_model=TestResponse)
async def test_provider(request: TestProviderRequest):
    """Test a configured notification provider by its index.

    Sends a test notification using the provider at the specified index
    in the current configuration.
    """
    try:
        manager = NotificationManager()
        if request.provider_index >= len(manager):
            return TestResponse(
                success=False,
                message=f"Invalid provider index: {request.provider_index}",
                message_zh=f"无效的提供者索引: {request.provider_index}",
                message_en=f"Invalid provider index: {request.provider_index}",
            )

        success, message = await manager.test_provider(request.provider_index)
        return TestResponse(
            success=success,
            message=message,
            message_zh="测试成功" if success else f"测试失败: {message}",
            message_en="Test successful" if success else f"Test failed: {message}",
        )
    except Exception as e:
        logger.error(f"Failed to test provider: {e}")
        return TestResponse(
            success=False,
            message=str(e),
            message_zh=f"测试失败: {e}",
            message_en=f"Test failed: {e}",
        )


@router.post("/test-config", response_model=TestResponse)
async def test_provider_config(request: TestProviderConfigRequest):
    """Test an unsaved notification provider configuration.

    Useful for testing a provider before saving it to the configuration.
    """
    try:
        # Convert request to ProviderConfig
        config = ProviderConfig(
            type=request.type,
            enabled=request.enabled,
            token=request.token or "",
            chat_id=request.chat_id or "",
            webhook_url=request.webhook_url or "",
            server_url=request.server_url or "",
            device_key=request.device_key or "",
            user_key=request.user_key or "",
            api_token=request.api_token or "",
            template=request.template,
            url=request.url or "",
        )

        success, message = await NotificationManager.test_provider_config(config)
        return TestResponse(
            success=success,
            message=message,
            message_zh="测试成功" if success else f"测试失败: {message}",
            message_en="Test successful" if success else f"Test failed: {message}",
        )
    except Exception as e:
        logger.error(f"Failed to test provider config: {e}")
        return TestResponse(
            success=False,
            message=str(e),
            message_zh=f"测试失败: {e}",
            message_en=f"Test failed: {e}",
        )
