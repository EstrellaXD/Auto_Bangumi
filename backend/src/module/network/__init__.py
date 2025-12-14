from models.config import Proxy
from conf.config import get_config_by_key

from .cache import load_image, save_image
from .proxy import get_proxy_config, set_proxy_config
from .request_contents import RequestContent

__all__ = ["RequestContent", "load_image", "save_image", "get_proxy_config"]


def init(config: Proxy | None = None):
    if config is None:
        config = get_config_by_key("proxy", Proxy)
    set_proxy_config(config)
