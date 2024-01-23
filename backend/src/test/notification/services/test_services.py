from typing import get_args

import pytest
from module.notification.services import NotificationType


@pytest.mark.parametrize(
    argnames=["service_name", "expected", "reason"],
    argvalues=[
        ("bark", True, None),
        ("server-chan", True, None),
        pytest.param(
            "serverChan",
            False,
            None,
            marks=pytest.mark.xfail(reason="Incorrect service name format"),
        ),
        pytest.param(
            "unsupported-service-name",
            False,
            None,
            marks=pytest.mark.xfail(reason="Unsupported service name"),
        ),
    ],
)
def test_service_name_is_NotificationTypes(service_name, expected, reason):
    assert (service_name in get_args(NotificationType)) is expected, reason
