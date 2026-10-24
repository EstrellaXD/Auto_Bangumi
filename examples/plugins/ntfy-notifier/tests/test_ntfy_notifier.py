import httpx2
from ntfy_notifier import NtfyNotifier

from ab_sdk.notify import NotifierSettings
from ab_sdk.testing import NotifierContract, create_plugin


def channel(status: int):
    plugin, _ = create_plugin(NtfyNotifier, {"topic": "ab"})
    plugin.client_factory = lambda: httpx2.AsyncClient(  # type: ignore[method-assign]
        transport=httpx2.MockTransport(lambda request: httpx2.Response(status))
    )
    return plugin.channel()(NotifierSettings())


class TestChannel(NotifierContract):
    def create(self):
        return channel(200)

    def create_failing(self):
        return channel(403)
