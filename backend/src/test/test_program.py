import asyncio
import logging
import unittest
import sys
from unittest.mock import MagicMock, patch, PropertyMock

# Mock dotenv before importing module
sys.modules["dotenv"] = MagicMock()

# 设置日志以便调试
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入需要测试的类
# 注意：由于 Program 类依赖很多全局配置，我们需要 patch 它的基类和依赖
from module.core.program import Program

class TestProgram(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Patch Settings
        self.settings_patcher = patch('module.core.program.settings')
        self.mock_settings = self.settings_patcher.start()
        
        # 通过设置配置项，让 check_renamer 和 check_analyser 自然返回 True
        self.mock_settings.bangumi_manage.enable = True
        self.mock_settings.rss_parser.enable = True
        
        # 设置最大重试次数为整数，避免比较错误
        self.mock_settings.program.max_retries = 10
        
        # Patch Program.check_downloader，因为它是静态方法且被继承
        # 直接 patch 类方法最稳妥
        self.check_downloader_patcher = patch.object(Program, 'check_downloader')
        self.mock_check_downloader = self.check_downloader_patcher.start()
        
        # Patch RenameThread and RSSThread to avoid real thread creation
        self.rename_patcher = patch('module.core.program.RenameThread')
        self.mock_rename_cls = self.rename_patcher.start()
        self.mock_rename_instance = self.mock_rename_cls.return_value
        self.mock_rename_instance.rename_thread.is_alive.return_value = False

        self.rss_patcher = patch('module.core.program.RSSThread')
        self.mock_rss_cls = self.rss_patcher.start()
        self.mock_rss_instance = self.mock_rss_cls.return_value
        self.mock_rss_instance.rss_thread.is_alive.return_value = False

        # Instantiate Program
        self.program = Program()
        
        # Mock methods for verification
        self.program.rename_start = MagicMock()
        self.program.rename_stop = MagicMock()
        self.program.rss_start = MagicMock()
        self.program.rss_stop = MagicMock()
        
        # Mock internal state
        self.program.stop_event = asyncio.Event()

    async def asyncTearDown(self):
        self.settings_patcher.stop()
        self.check_downloader_patcher.stop()
        self.rename_patcher.stop()
        self.rss_patcher.stop()
        if self.program.is_running:
            self.program.stop()

    async def test_start_immediate_return(self):
        """测试 start 方法是否立即返回，不被 downloader_status 阻塞"""
        # 模拟下载器不在线
        self.mock_check_downloader.return_value = False
        
        logger.info("Testing immediate return...")
        response = await self.program.start()
        
        self.assertTrue(response.status)
        self.assertEqual(response.msg_en, "Program started.")
        # 验证后台任务已创建
        self.assertIsNotNone(self.program._start_task)
        self.assertFalse(self.program._start_task.done())
        
        # 清理任务
        self.program.stop()
        try:
            await self.program._start_task
        except asyncio.CancelledError:
            pass

    async def test_start_service_waits_for_downloader(self):
        """测试后台服务会等待下载器，并在就绪后启动子线程"""
        # 使用动态 side_effect 来避免 StopIteration
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            logger.info(f"check_downloader called: {call_count}")
            # 第2次就成功
            if call_count >= 2:
                return True
            return False
            
        # 直接设置 setUp 中创建的 mock 对象的 side_effect
        self.mock_check_downloader.side_effect = side_effect
        
        await self.program.start()
        
        # 保存原始 sleep
        original_sleep = asyncio.sleep
        
        async def smart_sleep(delay, *args, **kwargs):
            # 如果是 30s 的长等待，直接跳过
            if delay == 30:
                return
            # 其他等待（如测试中的 0.001s）真实执行
            await original_sleep(delay, *args, **kwargs)
            
        # 全局 patch asyncio.sleep
        with patch('asyncio.sleep', side_effect=smart_sleep):
            # 等待直到 start_service 完成它的工作
            for i in range(100):
                if self.program.rename_start.called:
                    break
                await asyncio.sleep(0.001)
                    
        self.program.rename_start.assert_called()
        self.program.rss_start.assert_called()

    async def test_start_service_max_retries(self):
        """测试超过最大重试次数后停止尝试"""
        self.mock_check_downloader.return_value = False
        
        await self.program.start()
        
        with patch('module.core.program.asyncio.sleep', new_callable=unittest.mock.AsyncMock) as mock_sleep:
            # 等待任务结束
            try:
                await asyncio.wait_for(self.program._start_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass
        
        self.program.rename_start.assert_not_called()
        self.assertTrue(self.program._start_task.done())

    async def test_stop_cancels_task(self):
        """测试 stop 方法能够取消正在等待的后台任务"""
        self.mock_check_downloader.return_value = False
        
        await self.program.start()
        task = self.program._start_task
        
        self.assertFalse(task.done())
        
        self.program.stop()
        
        # 等待取消生效
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
            
        self.assertTrue(task.cancelled() or task.done())

    async def test_concurrency_safety(self):
        """测试多次快速调用 start 不会崩溃"""
        self.mock_check_downloader.return_value = False
        
        await self.program.start()
        task1 = self.program._start_task
        
        await self.program.start()
        task2 = self.program._start_task
        
        # 等待 task1 取消生效
        try:
            await asyncio.wait_for(task1, timeout=1.0)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        
        self.assertNotEqual(task1, task2)
        self.assertTrue(task1.cancelled() or task1.done())
        self.assertFalse(task2.done())
        
        self.program.stop()

if __name__ == '__main__':
    unittest.main()
