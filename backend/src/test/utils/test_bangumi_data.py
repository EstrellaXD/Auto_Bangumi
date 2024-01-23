from unittest import mock

from module.utils import bangumi_data


def test_get_poster_with_mock_database():
    with mock.patch.object(bangumi_data, "get_poster") as m:
        # 调用被测试函数
        m.return_value = "bar"
        res = bangumi_data.get_poster(title="foo")
        m.assert_called_once_with(title="foo")
        assert res == "bar"


def test_get_poster_failed():
    with mock.patch.object(bangumi_data, "get_poster") as m:
        m.return_value = ""
        res = bangumi_data.get_poster(title="")
        m.assert_called_once_with(title="")
        assert res == ""
