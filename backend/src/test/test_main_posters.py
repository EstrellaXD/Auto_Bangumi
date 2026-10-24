"""/posters 路由只能读海报目录内的文件。"""

import pytest
from fastapi.responses import FileResponse

import main


@pytest.mark.parametrize(
    ("path", "allowed"),
    [
        ("a.jpg", True),
        # 同名前缀的兄弟目录：按字符串前缀检查时会被放行
        ("../posters_x/secret.jpg", False),
        ("../secret.jpg", False),
    ],
)
def test_posters_rejects_paths_outside_base(tmp_path, monkeypatch, path, allowed):
    base = tmp_path / "posters"
    base.mkdir()
    monkeypatch.setattr(main, "_POSTERS_BASE", base)

    resp = main.posters(path)

    assert isinstance(resp, FileResponse) is allowed
    if not allowed:
        assert resp.status_code == 403
