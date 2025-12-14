# 初始化 conf,logger 等等
from conf.config import get_config_by_key
import log
from models.config import Log
log_config = get_config_by_key("log", Log)
log.init(log_config)
