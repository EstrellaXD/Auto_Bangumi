from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from module.notification.manager import NotificationConfig, NotificationType

logger = logging.getLogger(__name__)


@dataclass
class NotificationSettings:
    """通知系统配置"""

    enabled: bool = True
    default_retry_count: int = 3
    default_timeout: float = 30.0
    batch_delay: int = 30
    max_concurrent_sends: int = 10
    configs: List[NotificationConfig] = None

    def __post_init__(self):
        if self.configs is None:
            self.configs = []


class NotificationConfigManager:
    """
    通知配置管理器
    负责配置的加载、保存、验证和管理
    """

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file
        self.settings = NotificationSettings()
        self.logger = logging.getLogger(self.__class__.__name__)

        if config_file and config_file.exists():
            self.load_from_file()

    def load_from_file(self) -> bool:
        """从文件加载配置"""
        if not self.config_file or not self.config_file.exists():
            self.logger.warning(f"配置文件不存在: {self.config_file}")
            return False

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.settings = self._parse_config_data(data)
            self.logger.info(f"成功加载通知配置: {self.config_file}")
            return True

        except Exception as e:
            self.logger.error(f"加载配置文件失败: {self.config_file} - {e}")
            return False

    def save_to_file(self) -> bool:
        """保存配置到文件"""
        if not self.config_file:
            self.logger.error("未指定配置文件路径")
            return False

        try:
            # 确保目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            data = self._serialize_config()
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"成功保存通知配置: {self.config_file}")
            return True

        except Exception as e:
            self.logger.error(f"保存配置文件失败: {self.config_file} - {e}")
            return False

    def _parse_config_data(self, data: Dict[str, Any]) -> NotificationSettings:
        """解析配置数据"""
        settings = NotificationSettings()

        # 基本设置
        settings.enabled = data.get("enabled", True)
        settings.default_retry_count = data.get("default_retry_count", 3)
        settings.default_timeout = data.get("default_timeout", 30.0)
        settings.batch_delay = data.get("batch_delay", 30)
        settings.max_concurrent_sends = data.get("max_concurrent_sends", 10)

        # 通知配置列表
        configs_data = data.get("configs", [])
        settings.configs = []

        for config_data in configs_data:
            try:
                notification_type = NotificationType(config_data["type"])
                config = NotificationConfig(
                    type=notification_type,
                    token=config_data.get("token", ""),
                    chat_id=config_data.get("chat_id"),
                    enabled=config_data.get("enabled", True),
                    retry_count=config_data.get(
                        "retry_count", settings.default_retry_count
                    ),
                    timeout=config_data.get("timeout", settings.default_timeout),
                    extra_config=config_data.get("extra_config", {}),
                )
                settings.configs.append(config)
            except (KeyError, ValueError) as e:
                self.logger.warning(f"跳过无效的通知配置: {config_data} - {e}")

        return settings

    def _serialize_config(self) -> Dict[str, Any]:
        """序列化配置数据"""
        return {
            "enabled": self.settings.enabled,
            "default_retry_count": self.settings.default_retry_count,
            "default_timeout": self.settings.default_timeout,
            "batch_delay": self.settings.batch_delay,
            "max_concurrent_sends": self.settings.max_concurrent_sends,
            "configs": [
                {
                    "type": config.type.value,
                    "token": config.token,
                    "chat_id": config.chat_id,
                    "enabled": config.enabled,
                    "retry_count": config.retry_count,
                    "timeout": config.timeout,
                    "extra_config": config.extra_config,
                }
                for config in self.settings.configs
            ],
        }

    def add_config(self, config: NotificationConfig) -> bool:
        """添加通知配置"""
        # 验证配置
        errors = self.validate_config(config)
        if errors:
            self.logger.error(f"配置验证失败: {errors}")
            return False

        self.settings.configs.append(config)
        self.logger.info(f"添加通知配置: {config.type.value}")
        return True

    def remove_config(self, config_type: NotificationType, token: str = None) -> int:
        """移除通知配置"""
        original_count = len(self.settings.configs)

        self.settings.configs = [
            c
            for c in self.settings.configs
            if not (c.type == config_type and (token is None or c.token == token))
        ]

        removed_count = original_count - len(self.settings.configs)
        if removed_count > 0:
            self.logger.info(f"移除了 {removed_count} 个 {config_type.value} 配置")

        return removed_count

    def get_configs_by_type(
        self, config_type: NotificationType
    ) -> List[NotificationConfig]:
        """根据类型获取配置"""
        return [c for c in self.settings.configs if c.type == config_type]

    def enable_config(self, config_type: NotificationType, enabled: bool = True) -> int:
        """启用/禁用指定类型的配置"""
        count = 0
        for config in self.settings.configs:
            if config.type == config_type:
                config.enabled = enabled
                count += 1

        if count > 0:
            status = "启用" if enabled else "禁用"
            self.logger.info(f"{status}了 {count} 个 {config_type.value} 配置")

        return count

    def validate_config(self, config: NotificationConfig) -> List[str]:
        """验证单个配置"""
        errors = []

        # 基本验证
        if not config.token and config.type != NotificationType.LOG:
            errors.append(f"{config.type.value}: token不能为空")

        if (
            config.type in [NotificationType.TELEGRAM, NotificationType.WECOM]
            and not config.chat_id
        ):
            errors.append(f"{config.type.value}: chat_id不能为空")

        if config.retry_count < 0:
            errors.append(f"{config.type.value}: retry_count不能为负数")

        if config.timeout <= 0:
            errors.append(f"{config.type.value}: timeout必须大于0")

        return errors

    def validate_all_configs(self) -> Dict[str, List[str]]:
        """验证所有配置"""
        all_errors = {}

        for i, config in enumerate(self.settings.configs):
            errors = self.validate_config(config)
            if errors:
                all_errors[f"{config.type.value}_{i}"] = errors

        return all_errors

    def get_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        type_counts = {}
        enabled_counts = {}

        for config in self.settings.configs:
            type_name = config.type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

            if config.enabled:
                enabled_counts[type_name] = enabled_counts.get(type_name, 0) + 1

        return {
            "total_configs": len(self.settings.configs),
            "enabled_configs": len([c for c in self.settings.configs if c.enabled]),
            "global_enabled": self.settings.enabled,
            "type_counts": type_counts,
            "enabled_counts": enabled_counts,
            "settings": {
                "default_retry_count": self.settings.default_retry_count,
                "default_timeout": self.settings.default_timeout,
                "batch_delay": self.settings.batch_delay,
                "max_concurrent_sends": self.settings.max_concurrent_sends,
            },
        }


def create_default_config() -> NotificationSettings:
    """创建默认配置"""
    return NotificationSettings(
        enabled=True,
        default_retry_count=3,
        default_timeout=30.0,
        batch_delay=30,
        max_concurrent_sends=10,
        configs=[
            NotificationConfig(
                type=NotificationType.LOG,
                token="",
                enabled=True,
                retry_count=1,
                timeout=5.0,
            )
        ],
    )


def load_config_from_dict(data: Dict[str, Any]) -> NotificationSettings:
    """从字典加载配置"""
    manager = NotificationConfigManager()
    return manager._parse_config_data(data)
