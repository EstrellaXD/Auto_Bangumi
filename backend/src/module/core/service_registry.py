import logging
from typing import Any
from threading import RLock

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """服务注册表
    
    管理所有可用服务的注册、获取和依赖关系
    """
    
    def __init__(self):
        self._services: dict[str, type] = {}
        self._service_instances: dict[str, Any] = {}
        self._service_metadata: dict[str, dict[str, Any]] = {}
        self._lock = RLock()
        
    def register_service(
        self, 
        service_class: type, 
        name: str | None = None,
        priority: int = 0,
        dependencies: list[str] | None = None,
        **metadata
    ) -> None:
        """注册服务类
        
        Args:
            service_class: 服务类
            name: 服务名称，如果不提供则使用类名
            priority: 服务启动优先级，数字越大优先级越高
            dependencies: 依赖的其他服务名称列表
            **metadata: 额外的服务元数据
        """
        with self._lock:
            service_name = name or service_class.__name__.lower().replace('service', '')
            
            if service_name in self._services:
                logger.warning(f"[ServiceRegistry] 服务 {service_name} 已注册，将被覆盖")
            
            self._services[service_name] = service_class
            self._service_metadata[service_name] = {
                'priority': priority,
                'dependencies': dependencies or [],
                'class_name': service_class.__name__,
                **metadata
            }
            
            logger.debug(f"[ServiceRegistry] 注册服务: {service_name} (优先级: {priority})")
    
    def get_service_class(self, name: str) -> type | None:
        """获取服务类"""
        with self._lock:
            return self._services.get(name)
    
    def get_service_instance(self, name: str) -> Any | None:
        """获取服务实例"""
        with self._lock:
            return self._service_instances.get(name)
    
    def set_service_instance(self, name: str, instance: Any) -> None:
        """设置服务实例"""
        with self._lock:
            self._service_instances[name] = instance
            logger.debug(f"[ServiceRegistry] 设置服务实例: {name}")
    
    def get_all_services(self) -> list[str]:
        """获取所有已注册的服务名称"""
        with self._lock:
            return list(self._services.keys())
    
    def get_services_by_priority(self) -> list[str]:
        """按优先级排序获取服务名称列表"""
        with self._lock:
            services = []
            for name in self._services.keys():
                priority = self._service_metadata[name]['priority']
                services.append((name, priority))
            
            # 按优先级降序排序
            services.sort(key=lambda x: x[1], reverse=True)
            return [name for name, _ in services]
    
    def get_service_metadata(self, name: str) -> dict[str, Any] | None:
        """获取服务元数据"""
        with self._lock:
            return self._service_metadata.get(name)
    
    def validate_dependencies(self) -> list[str]:
        """验证服务依赖关系，返回依赖错误列表"""
        errors = []
        with self._lock:
            for service_name, metadata in self._service_metadata.items():
                dependencies = metadata.get('dependencies', [])
                for dep in dependencies:
                    if dep not in self._services:
                        errors.append(f"服务 {service_name} 依赖的服务 {dep} 未注册")
        return errors
    
    def create_service_instances(self) -> list[Any]:
        """创建所有服务实例，按依赖关系和优先级排序"""
        with self._lock:
            # 验证依赖
            errors = self.validate_dependencies()
            if errors:
                for error in errors:
                    logger.error(f"[ServiceRegistry] {error}")
                raise ValueError(f"服务依赖验证失败: {errors}")
            
            # 按优先级创建实例
            instances = []
            service_names = self.get_services_by_priority()
            
            for service_name in service_names:
                service_class = self._services[service_name]
                try:
                    # 创建服务实例
                    instance = service_class()
                    self.set_service_instance(service_name, instance)
                    instances.append(instance)
                    logger.debug(f"[ServiceRegistry] 创建服务实例: {service_name}")
                except Exception as e:
                    logger.error(f"[ServiceRegistry] 创建服务实例失败 {service_name}: {e}")
                    raise
            
            return instances
    
    def clear(self) -> None:
        """清空注册表"""
        with self._lock:
            self._services.clear()
            self._service_instances.clear()
            self._service_metadata.clear()
            logger.debug("[ServiceRegistry] 注册表已清空")


# 全局服务注册表实例
service_registry = ServiceRegistry()


def register_service(
    service_class: type = None,
    *,
    name: str | None = None,
    priority: int = 0,
    dependencies: list[str] | None = None,
    **metadata
):
    """服务注册装饰器
    
    使用方式:
    @register_service(priority=10)
    class MyService(BaseService):
        pass
    """
    def decorator(cls):
        service_registry.register_service(
            cls, 
            name=name, 
            priority=priority, 
            dependencies=dependencies,
            **metadata
        )
        return cls
    
    if service_class is not None:
        # 直接调用 @register_service
        return decorator(service_class)
    else:
        # 带参数调用 @register_service(...)
        return decorator
