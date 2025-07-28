import asyncio
import logging
from asyncio import Queue, create_task
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable
# 想想现在要几个 services
# 1. RSSService 用来定期刷新 rss
# 2. DownloadService 用来定期下载任务
# 3. BangumiService 用来定期处理旧的番剧数据
# 3. RenameService 用来定期重命名文件, 这个时间就会比之前长一些, 主要是用来处理意外的
# 触发式的有这几个
# 1. Download 用来和 DOwnloader 交互, DownloadService 下载好种子后, 启动检查是否下载完成了
# 2. Rename 当 Download 检查下载完成后, 触发重命名
logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class Task:
    id: str
    type: str
    priority: TaskPriority
    payload: dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3
    created_at: float | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = asyncio.get_event_loop().time()


class TaskQueue:
    def __init__(self, max_workers: int = 10):
        self._queue: Queue[Task] = Queue()
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._failed_tasks: list[Task] = []
        self._task_handlers: dict[str, Callable] = {}
        self._max_workers: int = max_workers
        self._workers: list[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._running = False

    def register_handler(self, task_type: str, handler: Callable[[Task], Any]) -> None:
        """注册任务处理器"""
        self._task_handlers[task_type] = handler
        logger.info(f"[TaskQueue] 注册处理器: {task_type}")

    async def enqueue(self, task: Task) -> None:
        """入队任务"""
        await self._queue.put(task)
        logger.debug(f"[TaskQueue] 任务入队: {task.type}_{task.id}")

    async def start(self) -> None:
        """启动任务队列处理"""
        if self._running:
            return

        self._running = True
        self._shutdown_event.clear()

        # 启动工作线程
        for i in range(self._max_workers):
            worker = create_task(self._worker(f"worker-{i}"), name=f"queue-worker-{i}")
            self._workers.append(worker)

        logger.info(f"[TaskQueue] 启动 {self._max_workers} 个工作线程")

    async def _worker(self, worker_name: str) -> None:
        """工作线程"""
        logger.debug(f"[TaskQueue] {worker_name} 启动")

        while self._running and not self._shutdown_event.is_set():
            try:
                # 等待任务，带超时
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._execute_task(task)
                self._queue.task_done()

            except asyncio.TimeoutError:
                continue  # 超时正常，继续等待
            except Exception as e:
                logger.error(f"[TaskQueue] {worker_name} 处理任务时发生错误: {e}")

        logger.debug(f"[TaskQueue] {worker_name} 停止")

    async def _execute_task(self, task: Task) -> None:
        """执行单个任务"""
        task_id = f"{task.type}_{task.id}"

        # 检查是否有对应的处理器
        handler = self._task_handlers.get(task.type)
        if not handler:
            logger.error(f"[TaskQueue] 未找到任务类型 {task.type} 的处理器")
            self._failed_tasks.append(task)
            return

        # 检查任务是否已在运行
        if task_id in self._running_tasks:
            logger.warning(f"[TaskQueue] 任务 {task_id} 已在运行中")
            return

        try:
            # 创建任务执行协程
            task_coro = create_task(handler(task), name=task_id)
            self._running_tasks[task_id] = task_coro

            logger.debug(f"[TaskQueue] 开始执行任务: {task_id}")
            await task_coro
            logger.debug(f"[TaskQueue] 任务执行完成: {task_id}")

        except Exception as e:
            logger.error(f"[TaskQueue] 任务 {task_id} 执行失败: {e}")
            # 重试逻辑
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                logger.info(
                    f"[TaskQueue] 任务 {task_id} 重试 {task.retry_count}/{task.max_retries}"
                )

                # 指数退避
                backoff_delay = min(60, 2**task.retry_count)
                await asyncio.sleep(backoff_delay)

                # 重新入队
                await self.enqueue(task)
            else:
                logger.error(f"[TaskQueue] 任务 {task_id} 达到最大重试次数，放弃执行")
                self._failed_tasks.append(task)

        finally:
            # 清理运行中的任务记录
            self._running_tasks.pop(task_id, None)

    async def shutdown(self, timeout: float = 30.0) -> None:
        """关闭任务队列"""
        if not self._running:
            return

        logger.info("[TaskQueue] 开始关闭任务队列...")
        self._running = False
        self._shutdown_event.set()

        # 等待队列中的任务完成
        if not self._queue.empty():
            logger.info(f"[TaskQueue] 等待 {self._queue.qsize()} 个任务完成...")
            try:
                await asyncio.wait_for(self._queue.join(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning("[TaskQueue] 等待任务完成超时")

        # 取消所有工作线程
        for worker in self._workers:
            worker.cancel()

        # 等待工作线程结束
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

        # 取消所有运行中的任务
        if self._running_tasks:
            logger.info(f"[TaskQueue] 取消 {len(self._running_tasks)} 个运行中的任务")
            for task in self._running_tasks.values():
                task.cancel()
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)

        self._workers.clear()
        self._running_tasks.clear()

        logger.info("[TaskQueue] 任务队列已关闭")

    def get_status(self) -> dict[str, Any]:
        """获取队列状态"""
        return {
            "running": self._running,
            "queue_size": self._queue.qsize(),
            "running_tasks": len(self._running_tasks),
            "failed_tasks": len(self._failed_tasks),
            "workers": len(self._workers),
            "registered_handlers": list(self._task_handlers.keys()),
        }


# 示例用法
if __name__ == "__main__":

    async def example_handler(task: Task) -> None:
        """示例任务处理器"""
        logger.info(f"处理任务: {task.id}, 数据: {task.payload}")
        await asyncio.sleep(1)  # 模拟工作

    async def main():
        # 设置日志
        logging.basicConfig(level=logging.INFO)

        # 创建任务队列
        queue = TaskQueue(max_workers=3)

        # 注册处理器
        queue.register_handler("example", example_handler)

        # 启动队列
        await queue.start()

        # 添加一些任务
        for i in range(5):
            task = Task(
                id=f"task-{i}",
                type="example",
                priority=TaskPriority.NORMAL,
                payload={"data": f"test-{i}"},
            )
            await queue.enqueue(task)

        # 等待一段时间
        await asyncio.sleep(10)

        # 关闭队列
        await queue.shutdown()

        # 显示状态
        print("最终状态:", queue.get_status())

    asyncio.run(main())
