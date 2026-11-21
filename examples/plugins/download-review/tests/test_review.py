from types import SimpleNamespace
from unittest.mock import AsyncMock

from ab_sdk.admission import AdmissionRequest, Candidate, CandidatePage, ReleaseSnapshot
from ab_sdk.bangumi import BangumiSnapshot
from ab_sdk.ingest import TorrentInfo
from ab_sdk.testing import DownloadPreflightContract, create_plugin
from review import Review


def request():
    bangumi = BangumiSnapshot(1, 'Example', 'Example', '2024', 'episode', 1, 0, 0, 1, 'Group', '', '', None, None, False, False, 'mapping')
    release = ReleaseSnapshot(episode=1, group='Group', version=1)
    candidate = Candidate('one', 'batch', 'rss', TorrentInfo('Example - 01', 'magnet:one'), 1, 'matched', '', 'revision', (1,), release)
    return AdmissionRequest('submission', (candidate,), bangumi, 'default', 'policy')


class TestGate(DownloadPreflightContract):
    def create(self):
        plugin, _ = create_plugin(Review)
        return plugin.gate()

    def samples(self):
        return [request()]


def test_prefers_newer_revision_from_host_batch():
    import asyncio
    from dataclasses import replace

    sample = request()
    v1 = sample.candidates[0]
    v2 = replace(v1, id='two', release=replace(v1.release, version=2))
    downloads = SimpleNamespace(candidates=AsyncMock(return_value=CandidatePage((v1, v2), None)))
    plugin, _ = create_plugin(Review, {'approved': True}, downloads=downloads)
    assert asyncio.run(plugin.preflight(sample)).decision == 'reject'
    assert asyncio.run(plugin.preflight(replace(sample, candidates=(v2,)))).decision == 'allow'
