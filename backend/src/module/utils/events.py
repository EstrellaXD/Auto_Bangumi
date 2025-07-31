import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


# 统一异常类
class CoreException(Exception):
    """核心模块基础异常"""
    pass


class ServiceException(CoreException):
    """服务相关异常"""
    def __init__(self, service_name: str, message: str):
        self.service_name = service_name
        super().__init__(f"[{service_name}] {message}")


class TaskException(CoreException):
    """任务相关异常"""
    def __init__(self, task_name: str, message: str):
        self.task_name = task_name
        super().__init__(f"[Task:{task_name}] {message}")


class QueueException(CoreException):
    """队列相关异常"""
    pass


class EventType(Enum):
    DOWNLOAD_COMPLETED = "download_completed"
    DOWNLOAD_STARTED = "download_started"
    RENAME_COMPLETED = "rename_completed"
    TORRENT_ADDED = "torrent_added"
    NOTIFICATION_REQUEST = "notification_request"


@dataclass
class Event:
    type: EventType
    data: dict[str, Any]
    timestamp: float|None = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class EventBus:
    def __init__(self):
        self._subscribers: dict[EventType, list[Callable]] = {}

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"[EventBus] 订阅事件: {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: Callable) -> bool:
        """取消订阅事件"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                logger.debug(f"[EventBus] 取消订阅事件: {event_type.value}")
                return True
            except ValueError:
                pass
        return False

    async def publish(self, event: Event) -> None:
        """发布事件"""
        handlers = self._subscribers.get(event.type, [])
        if not handlers:
            logger.debug(f"[EventBus] 没有订阅者处理事件: {event.type.value}")
            return
            
        logger.debug(f"[EventBus] 发布事件: {event.type.value} -> {len(handlers)} 个处理器")
        
        # 并发执行所有处理器
        tasks = []
        for handler in handlers:
            try:
                task = asyncio.create_task(handler(event))
                tasks.append(task)
            except Exception as e:
                logger.error(f"[EventBus] 创建事件处理任务失败: {e}")
        
        if tasks:
            # 等待所有处理器完成，但不阻塞失败的处理器
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"[EventBus] 事件处理器 {i} 执行失败: {result}")

    def get_subscribers_count(self) -> dict[str, int]:
        """获取订阅者数量"""
        return {
            event_type.value: len(handlers) 
            for event_type, handlers in self._subscribers.items()
        }

event_bus = EventBus()
