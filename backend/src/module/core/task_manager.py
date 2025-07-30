import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class TaskState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    name: str
    state: TaskState = TaskState.PENDING
    task: asyncio.Task[Any]|None = None
    last_run:float|None = None
    error_count: int = 0
    max_retries: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskManager:
    def __init__(self):
        self._tasks: dict[str, TaskInfo] = {}
        self._running:bool = False
        self._shutdown_event:asyncio.Event = asyncio.Event()

    async def register_task(
        self, name: str, coro_func: Callable, interval: int, max_retries: int = 3
    ) -> None:
        """注册任务"""
        self._tasks[name] = TaskInfo(
            name=name,
            max_retries=max_retries,
            metadata={"coro_func": coro_func, "interval": interval},
        )
        logger.info(f"[TaskManager] 已注册任务: {name}")

    async def start_all(self):
        """启动所有任务"""
        self._running = True
        self._shutdown_event.clear()

        for name, task_info in self._tasks.items():
            if task_info.state == TaskState.PENDING:
                logger.info(f"[TaskManager] 准备启动任务: {name}")
                await self._start_task(name)
            else:
                logger.warning(f"[TaskManager] 任务 {name} 已经在运行或已完成，跳过启动")

    async def _start_task(self, name: str):
        """启动单个任务"""
        task_info = self._tasks[name]
        if task_info.task and not task_info.task.done():
            return

        task_info.task = asyncio.create_task(self._task_wrapper(name), name=name)
        task_info.state = TaskState.RUNNING
        logger.info(f"[TaskManager] 启动任务: {name}")

    async def _task_wrapper(self, name: str):
        """任务包装器，处理循环和错误恢复"""
        task_info = self._tasks[name]
        coro_func = task_info.metadata["coro_func"]
        interval = task_info.metadata["interval"]

        while self._running and not self._shutdown_event.is_set():
            try:
                # 执行任务
                await coro_func()
                task_info.error_count = 0  # 重置错误计数
                task_info.last_run = asyncio.get_event_loop().time()

            except Exception as e:
                logger.error(f"[TaskManager] 任务 {name} 执行失败: {e}")

            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=interval)
                break  # 收到关闭信号
            except asyncio.TimeoutError:
                continue  # 超时正常，继续下次循环

        task_info.state = TaskState.COMPLETED
        logger.info(f"[TaskManager] 任务 {name} 已完成")

    async def shutdown(self):
        """关闭所有任务"""
        logger.info("[TaskManager] 开始关闭所有任务...")
        self._running = False
        self._shutdown_event.set()

        # 取消所有正在运行的任务
        for task_info in self._tasks.values():
            if task_info.task and not task_info.task.done():
                logger.info(f"[TaskManager] 取消任务: {task_info.name}")
                task_info.task.cancel()

                # await asyncio.gather(*pending_tasks, return_exceptions=True)

        logger.info("[TaskManager] 所有任务已关闭")

    def reset_tasks_state(self):
        """重置所有任务状态为 PENDING，用于重启"""
        for task_info in self._tasks.values():
            task_info.state = TaskState.PENDING
            task_info.task = None
        logger.info("[TaskManager] 已重置所有任务状态为 PENDING")

    def get_status(self) -> dict[str, dict]:
        """获取所有任务状态"""
        return {
            name: {
                "state": task_info.state.value,
                "error_count": task_info.error_count,
                "last_run": task_info.last_run,
            }
            for name, task_info in self._tasks.items()
        }
