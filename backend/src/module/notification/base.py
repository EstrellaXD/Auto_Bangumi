import aiohttp
import requests
from tenacity import retry, stop_after_attempt, wait_fixed

retry_strateges = dict(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
)


class RequestMixin:
    """RequestMixin is a mixin class for request object. \
        It provides synchronous and asynchronous methods for http request.
    """

    sess: requests.Session = requests.Session
    asess: aiohttp.ClientSession = aiohttp.ClientSession

    @retry(**retry_strateges)
    def request(self, *args, **kwargs):
        with self.sess() as req:
            return req.request(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.request(method="GET", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.request(method="POST", *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.request(method="PUT", *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.request(method="DELETE", *args, **kwargs)

    @retry(**retry_strateges)
    async def arequest(self, *args, **kwargs):
        async with self.asess() as req:
            return req.request(*args, **kwargs)

    async def aget(self, *args, **kwargs):
        return self.arequest(method="GET", *args, **kwargs)

    async def apost(self, *args, **kwargs):
        return self.arequest(method="POST", *args, **kwargs)

    async def aput(self, *args, **kwargs):
        return self.arequest(method="PUT", *args, **kwargs)

    async def adelete(self, *args, **kwargs):
        return self.arequest(method="DELETE", *args, **kwargs)


class NotifyAdapter:
    """NotifyAdapter is a base class for specific notification adapter.
    There are some methods that must be implemented in subclass.

    TODO: It should support both sync and async methods by using RequestMixin.
    TODO: It also should support grap logging data from logger.
    """

    def send(self, *args, **kwargs):
        raise NotImplementedError()
