import asyncio
import importlib
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

from module.models import Notification
from module.notification.plugin.base_notifier import BaseNotifier


logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """支持的通知类型"""
    TELEGRAM = "telegram"
    BARK = "bark"
    SERVER_CHAN = "server_chan"
    WECOM = "wecom"
    LOG = "log"


@dataclass
class NotificationConfig:
    """通知配置"""
    type: NotificationType
    token: str
    chat_id: Optional[str] = None
    enabled: bool = True
    retry_count: int = 3
    timeout: float = 30.0
    extra_config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_config is None:
            self.extra_config = {}


class NotificationManager:
    """
    统一的通知管理器
    支持多种通知方式并发发送、重试机制、配置管理等
    """
    
    def __init__(self, configs: List[NotificationConfig] = None):
        self.configs = configs or []
        self.notifiers: Dict[str, BaseNotifier] = {}
        self._enabled_types: Set[NotificationType] = set()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 初始化通知器
        self._initialize_notifiers()
    
    def _initialize_notifiers(self):
        """初始化所有通知器"""
        self.notifiers.clear()
        self._enabled_types.clear()
        
        for config in self.configs:
            if not config.enabled:
                continue
                
            try:
                notifier = self._create_notifier(config)
                if notifier:
                    key = f"{config.type.value}_{id(config)}"
                    self.notifiers[key] = notifier
                    self._enabled_types.add(config.type)
                    self.logger.info(f"初始化通知器成功: {config.type.value}")
            except Exception as e:
                self.logger.error(f"初始化通知器失败 {config.type.value}: {e}")
    
    def _create_notifier(self, config: NotificationConfig) -> Optional[BaseNotifier]:
        """根据配置创建通知器实例"""
        try:
            # 动态导入通知插件
            package_path = f"module.notification.plugin.{config.type.value}"
            notification_module = importlib.import_module(package_path)
            NotifierClass = notification_module.Notifier
            
            # 创建通知器实例
            kwargs = config.extra_config.copy()
            if config.chat_id:
                kwargs["chat_id"] = config.chat_id
            
            notifier = NotifierClass(token=config.token, **kwargs)
            return notifier
            
        except Exception as e:
            self.logger.error(f"创建通知器失败 {config.type.value}: {e}")
            return None
    
    def add_config(self, config: NotificationConfig):
        """添加通知配置"""
        self.configs.append(config)
        self._initialize_notifiers()
    
    def remove_config(self, notification_type: NotificationType, token: str = None):
        """移除通知配置"""
        self.configs = [
            c for c in self.configs 
            if not (c.type == notification_type and (token is None or c.token == token))
        ]
        self._initialize_notifiers()
    
    def enable_type(self, notification_type: NotificationType, enabled: bool = True):
        """启用/禁用特定类型的通知"""
        for config in self.configs:
            if config.type == notification_type:
                config.enabled = enabled
        self._initialize_notifiers()
    
    async def send_notification(self, notification: Notification, 
                              use_retry: bool = True) -> Dict[str, bool]:
        """
        发送通知到所有启用的通知器
        
        Args:
            notification: 通知对象
            use_retry: 是否使用重试机制
            
        Returns:
            Dict[str, bool]: 每个通知器的发送结果
        """
        if not self.notifiers:
            self.logger.warning("没有可用的通知器")
            return {}
        
        # 并发发送通知
        tasks = []
        for key, notifier in self.notifiers.items():
            config = self._get_config_by_key(key)
            if config and config.enabled:
                task = self._send_single_notification(
                    key, notifier, notification, config, use_retry
                )
                tasks.append(task)
        
        if not tasks:
            self.logger.warning("没有启用的通知器")
            return {}
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        result_dict = {}
        for i, (key, notifier) in enumerate(self.notifiers.items()):
            config = self._get_config_by_key(key)
            if config and config.enabled:
                try:
                    result_dict[key] = results[i] if not isinstance(results[i], Exception) else False
                    if isinstance(results[i], Exception):
                        self.logger.error(f"通知器 {key} 发送异常: {results[i]}")
                except IndexError:
                    result_dict[key] = False
        
        # 记录发送结果
        success_count = sum(1 for r in result_dict.values() if r)
        total_count = len(result_dict)
        
        if success_count > 0:
            self.logger.info(f"通知发送完成: {notification.title} ({success_count}/{total_count} 成功)")
        else:
            self.logger.error(f"通知发送全部失败: {notification.title}")
        
        return result_dict
    
    async def _send_single_notification(self, key: str, notifier: BaseNotifier, 
                                      notification: Notification, config: NotificationConfig,
                                      use_retry: bool) -> bool:
        """发送单个通知"""
        try:
            # 应用超时
            if use_retry:
                result = await asyncio.wait_for(
                    notifier.send_with_retry(notification, config.retry_count),
                    timeout=config.timeout
                )
            else:
                result = await asyncio.wait_for(
                    notifier.post_msg(notification),
                    timeout=config.timeout
                )
            
            if result:
                self.logger.debug(f"通知器 {key} 发送成功: {notification.title}")
            else:
                self.logger.warning(f"通知器 {key} 发送失败: {notification.title}")
            
            return result
            
        except asyncio.TimeoutError:
            self.logger.error(f"通知器 {key} 发送超时: {notification.title}")
            return False
        except Exception as e:
            self.logger.error(f"通知器 {key} 发送异常: {notification.title} - {e}")
            return False
    
    def _get_config_by_key(self, key: str) -> Optional[NotificationConfig]:
        """根据key获取配置"""
        key_parts = key.split('_')
        if len(key_parts) < 2:
            return None
        
        notification_type = key_parts[0]
        config_id = key_parts[1] if len(key_parts) > 1 else None
        
        for config in self.configs:
            if config.type.value == notification_type:
                if config_id is None or str(id(config)) == config_id:
                    return config
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """获取通知管理器状态"""
        return {
            "total_configs": len(self.configs),
            "enabled_configs": len([c for c in self.configs if c.enabled]),
            "active_notifiers": len(self.notifiers),
            "enabled_types": [t.value for t in self._enabled_types],
            "configs": [
                {
                    "type": config.type.value,
                    "enabled": config.enabled,
                    "has_token": bool(config.token),
                    "has_chat_id": bool(config.chat_id),
                    "retry_count": config.retry_count,
                    "timeout": config.timeout
                }
                for config in self.configs
            ]
        }
    
    def validate_config(self, config: NotificationConfig) -> List[str]:
        """验证通知配置"""
        errors = []
        
        # 基本验证
        if not config.token and config.type != NotificationType.LOG:
            errors.append(f"{config.type.value}: token不能为空")
        
        if config.type in [NotificationType.TELEGRAM, NotificationType.WECOM] and not config.chat_id:
            errors.append(f"{config.type.value}: chat_id不能为空")
        
        if config.retry_count < 0:
            errors.append(f"{config.type.value}: retry_count不能为负数")
        
        if config.timeout <= 0:
            errors.append(f"{config.type.value}: timeout必须大于0")
        
        # 尝试创建通知器实例来验证配置
        try:
            notifier = self._create_notifier(config)
            if not notifier:
                errors.append(f"{config.type.value}: 无法创建通知器实例")
        except Exception as e:
            errors.append(f"{config.type.value}: 配置验证失败 - {e}")
        
        return errors


class LegacyNotificationAdapter:
    """
    兼容旧版通知接口的适配器
    用于平滑迁移到新的通知系统
    """
    
    def __init__(self, manager: NotificationManager):
        self.manager = manager
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def send(self, notify: Notification) -> bool:
        """兼容旧版send接口"""
        results = await self.manager.send_notification(notify)
        # 只要有一个成功就返回True，保持与旧版本的兼容性
        return any(results.values()) if results else False