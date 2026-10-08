import httpx
from ntfy_notifier import NtfyNotifier

from ab_sdk.notify import NotifierSettings
from ab_sdk.testing import NotifierContract, create_plugin


def channel(status: int):
    plugin, _ = create_plugin(NtfyNotifier, {"topic": "ab"})
    plugin.client_factory = lambda: httpx.AsyncClient(  # type: ignore[method-assign]
        transport=httpx.MockTransport(lambda request: httpx.Response(status))
    )
    return plugin.channel()(NotifierSettings())


class TestChannel(NotifierContract):
    def create(self):
        return channel(200)

    def create_failing(self):
        return channel(403)
