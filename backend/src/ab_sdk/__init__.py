"""AutoBangumi 插件 SDK。

第三方插件只应 import ``ab_sdk``，不要 import ``module.*``：后者是宿主内部实现，
随时可能重构；``ab_sdk`` 按 ``SDK_VERSION`` 遵守语义化版本（4.0 期间为 0.x，
允许不兼容调整，4.1 冻结 1.0）。
"""

from .context import KeyValueStore, PluginContext
from .events import Event, PluginDisabled, PluginLoaded
from .hooks import Verdict, hook, provider, subscribe
from .plugin import Plugin

SDK_VERSION = "0.1.0"

__all__ = [
    "SDK_VERSION",
    "Event",
    "KeyValueStore",
    "Plugin",
    "PluginContext",
    "PluginDisabled",
    "PluginLoaded",
    "Verdict",
    "hook",
    "provider",
    "subscribe",
]
