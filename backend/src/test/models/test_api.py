import pytest
from module.models.api import (
    NotificationData,
    NotificationMessageIds,
    NotificationReponse,
)
from pydantic import ValidationError


class TestNotificationMessageIds:
    def test_init_property(self):
        body = NotificationMessageIds(message_ids=["foo"])
        assert body.message_ids == ["foo"]

    def test_init_with_invalid_message_ids(self):
        with pytest.raises(ValidationError) as exc:
            NotificationMessageIds(message_ids="foo")

        exc.match("value is not a valid list")


class TestAPIResponse:
    def test_init_property(self):
        response = NotificationReponse(code=200, msg="Success", data={"key": "value"})
        assert response.code == 200
        assert response.msg == "Success"
        assert response.data == {"key": "value"}

    def test_default_values(self):
        response = NotificationReponse(msg="ok")
        assert response.code == 200
        assert response.msg == "ok"
        assert response.data == {}

    def test_missing_message(self):
        with pytest.raises(ValidationError) as exc:
            NotificationReponse(code=200, data={"key": "value"})

        assert exc.match("field required")

    def test_dict_method(self):
        response = NotificationReponse(code=200, msg="Success", data={"key": "value"})
        response_dict = response.dict()
        assert response_dict["code"] == 200
        assert response_dict["msg"] == "Success"
        assert response_dict["data"] == {"key": "value"}

    def test_json_method(self):
        response = NotificationReponse(code=200, msg="Success", data={"key": "value"})
        response_json = response.json()
        assert (
            response_json == '{"code": 200, "msg": "Success", "data": {"key": "value"}}'
        )

    def test_different_data(self):
        response = NotificationReponse(code=200, msg="Success", data={"key": "value"})
        response.data = "New Data"
        assert response.data == "New Data"

        response.data = 123
        assert response.data == 123

        response.data = [1, 2, 3]
        assert response.data == [1, 2, 3]


class TestNotificationData:
    def test_init_property(self, fake_nanoseconds, fake_nanoseconds_datetime):
        data = NotificationData(
            title="Test Title",
            content="Test Content",
            datetime=fake_nanoseconds,
            has_read=True,
            id="test_id",
        )
        assert data.title == "Test Title"
        assert data.content == "Test Content"
        assert data.datetime == fake_nanoseconds_datetime
        assert data.has_read is True
        assert data.id == "test_id"

    def test_default_values(self, fake_nanoseconds, fake_nanoseconds_datetime):
        data = NotificationData(
            content="Test Content", datetime=fake_nanoseconds, id="test_id"
        )
        assert data.title == "AutoBangumi"
        assert data.content == "Test Content"
        assert data.datetime == fake_nanoseconds_datetime
        assert data.has_read is False
        assert data.id == "test_id"

    def test_invalid_datetime(self, fake_nanoseconds):
        with pytest.raises(ValidationError) as exc:
            NotificationData(
                datetime=fake_nanoseconds,
                has_read=True,
                id="test_id",
            )

        assert exc.match("field required")

    def test_from_nanoseconds_to_datetime(
        self, fake_nanoseconds, fake_nanoseconds_datetime
    ):
        data = NotificationData(
            title="Test Title",
            content="Test Content",
            datetime=fake_nanoseconds,
            has_read=True,
            id="test_id",
        )
        assert data.datetime == fake_nanoseconds_datetime
