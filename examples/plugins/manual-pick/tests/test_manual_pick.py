from fastapi import FastAPI
from fastapi.testclient import TestClient
from manual_pick import ManualPick, Picked

from ab_sdk.testing import create_plugin


def client():
    plugin, ctx = create_plugin(ManualPick)
    app = FastAPI()
    app.include_router(plugin.api())
    return TestClient(app), ctx


def test_get_pick_nothing_picked_returns_null():
    http, _ = client()
    assert http.get("/picks/1").json() == {"torrent_id": None}


def test_put_pick_saves_selection_per_bangumi():
    http, ctx = client()
    assert http.put("/picks/1", json={"torrent_id": 7}).json() == {"torrent_id": 7}
    assert http.get("/picks/1").json() == {"torrent_id": 7}
    assert http.get("/picks/2").json() == {"torrent_id": None}
    assert ctx.kv.data == {"pick:1": 7}


def test_put_pick_publishes_picked_event():
    http, ctx = client()
    http.put("/picks/3", json={"torrent_id": 9})
    assert ctx.bus.published == [Picked(bangumi_id=3, torrent_id=9)]


def test_put_pick_invalid_body_returns_422_and_publishes_nothing():
    http, ctx = client()
    assert http.put("/picks/1", json={"torrent_id": "x"}).status_code == 422
    assert ctx.bus.published == []
