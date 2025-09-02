"""
环境检测工具

用于检测程序运行在哪种环境中，以便选择合适的更新策略。
"""
import logging
import os

logger = logging.getLogger(__name__)


def is_docker_environment() -> bool:
    """检测是否在 Docker 容器中运行
    
    Returns:
        bool: 如果在 Docker 环境中返回 True，否则返回 False
    """
    try:
        # 方法1: 检查 /.dockerenv 文件（Docker 会创建这个文件）
        if os.path.exists('/.dockerenv'):
            logger.debug("[Environment] Detected Docker environment via /.dockerenv")
            return True
        
        # 方法2: 检查 /proc/1/cgroup 文件（容器中的进程信息）
        if os.path.exists('/proc/1/cgroup'):
            with open('/proc/1/cgroup', 'r') as f:
                content = f.read()
                if 'docker' in content or 'containerd' in content:
                    logger.debug("[Environment] Detected Docker environment via /proc/1/cgroup")
                    return True
        
        # 方法3: 检查环境变量（某些容器会设置这些变量）
        if any(env in os.environ for env in ['DOCKER_CONTAINER', 'container']):
            logger.debug("[Environment] Detected Docker environment via environment variables")
            return True
            
        logger.debug("[Environment] No Docker environment detected")
        return False
        
    except Exception as e:
        logger.warning(f"[Environment] Error detecting Docker environment: {e}")
        return False


def get_environment_info() -> dict:
    """获取详细的环境信息
    
    Returns:
        dict: 包含环境信息的字典
    """
    info = {
        "is_docker": is_docker_environment(),
        "platform": os.name,
        "working_directory": os.getcwd(),
    }
    
    # 如果在 Docker 中，获取更多信息
    if info["is_docker"]:
        try:
            # 尝试获取容器信息
            if os.path.exists('/proc/1/cgroup'):
                with open('/proc/1/cgroup', 'r') as f:
                    info["cgroup_info"] = f.read()[:200]  # 只取前200字符
        except Exception:
            pass
    
    return info