from datetime import datetime

from module.notification.base import DEFAULT_LOG_TEMPLATE
from module.utils.log import make_template


def test_make_template_with_asctime(fake_log_record, fake_log_message):
    fake_log_record.asctime = datetime(2022, 1, 1, 0, 0, 0).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    assert make_template(fake_log_record) == DEFAULT_LOG_TEMPLATE.format(
        dt=fake_log_record.asctime,
        levelname=fake_log_record.levelname,
        msg=fake_log_record.msg,
    )


def test_make_template_without_asctime(fake_log_record, fake_log_message):
    assert make_template(fake_log_record) == fake_log_message
