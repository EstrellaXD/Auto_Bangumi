import pytest


class TestNotificationAPI:
    @pytest.mark.asyncio
    async def test_send_notification(self, aclient):
        resp = await aclient.post("/v1/notification/send", json=dict(content="fooo"))
        assert resp.status_code == 200
        assert resp.json() == dict(code=0, msg="success")

    @pytest.mark.asyncio
    async def test_send_notification_with_failed(self, aclient):
        pass
