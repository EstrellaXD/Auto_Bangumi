import pytest
from module.models.bangumi import Notification


@pytest.fixture
def fake_notification():
    yield Notification(
        official_title="AutoBangumi Test",
        season=1,
        episode=1,
        poster_path="https://mikanani.me",
    )
