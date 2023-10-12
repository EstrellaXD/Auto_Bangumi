import pytest
from module.models.api import NotificationMessageIds
from pydantic import ValidationError


class TestNotificationMessageIds:
    def test_init_property(self):
        body = NotificationMessageIds(message_ids=["foo"])
        assert body.message_ids == ["foo"]

    def test_init_with_invalid_message_ids(self):
        with pytest.raises(ValidationError) as exc:
            NotificationMessageIds(message_ids="foo")

        exc.match("value is not a valid list")
