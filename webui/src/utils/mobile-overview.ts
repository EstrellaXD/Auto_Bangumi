import type { BangumiRule } from '#/bangumi';
import type { QbTorrentInfo, QbTorrentState } from '#/downloader';
import type { RSS } from '#/rss';

const ACTIVE_DOWNLOAD_STATES = new Set<QbTorrentState>([
  'allocating',
  'checkingDL',
  'checkingResumeData',
  'downloading',
  'forcedDL',
  'metaDL',
  'moving',
  'queuedDL',
  'stalledDL',
]);

export interface BangumiOverview {
  active: number;
  needsReview: number;
}

export interface RssOverview {
  enabled: number;
  errors: number;
}

export interface DownloadOverview {
  active: number;
  bytesPerSecond: number;
}

export function summarizeBangumi(rules: BangumiRule[]): BangumiOverview {
  const activeRules = rules.filter((rule) => !rule.deleted && !rule.archived);
  return {
    active: activeRules.length,
    needsReview: activeRules.filter((rule) => rule.needs_review).length,
  };
}

export function summarizeRss(feeds: RSS[]): RssOverview {
  const enabledFeeds = feeds.filter((feed) => feed.enabled);
  return {
    enabled: enabledFeeds.length,
    errors: enabledFeeds.filter((feed) => feed.connection_status === 'error')
      .length,
  };
}

export function summarizeDownloads(
  torrents: QbTorrentInfo[]
): DownloadOverview {
  return {
    active: torrents.filter((torrent) =>
      ACTIVE_DOWNLOAD_STATES.has(torrent.state)
    ).length,
    bytesPerSecond: torrents.reduce(
      (total, torrent) =>
        total +
        (Number.isFinite(torrent.dlspeed) && torrent.dlspeed >= 0
          ? torrent.dlspeed
          : 0),
      0
    ),
  };
}
