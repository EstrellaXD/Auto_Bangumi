# 导入服务模块以确保服务注册
from .services import RSSService, DownloadService
from .service_registry import service_registry
from .aiocore import AsyncApplicationCore, app_core
from .program import Program

__all__ = [
    'RSSService',
    'DownloadService', 
    'service_registry',
    'AsyncApplicationCore',
    'app_core',
    'Program'
]
