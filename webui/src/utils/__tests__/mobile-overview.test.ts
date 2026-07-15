import { describe, expect, it } from 'vitest';
import {
  summarizeBangumi,
  summarizeDownloads,
  summarizeRss,
} from '../mobile-overview';
import { mockBangumiRule } from '@/test/mocks/api';
import type { QbTorrentInfo } from '#/downloader';
import type { RSS } from '#/rss';

function torrent(
  state: QbTorrentInfo['state'],
  dlspeed: number
): QbTorrentInfo {
  return {
    hash: `${state}-${dlspeed}`,
    name: state,
    size: 1,
    progress: 0.5,
    dlspeed,
    upspeed: 0,
    num_seeds: 0,
    num_leechs: 0,
    state,
    eta: 0,
    category: '',
    save_path: '/',
    added_on: 0,
  };
}

function rss(
  id: number,
  enabled: boolean,
  connectionStatus: string | null
): RSS {
  return {
    id,
    name: `RSS ${id}`,
    url: `https://example.com/${id}`,
    aggregate: false,
    parser: 'mikan',
    enabled,
    connection_status: connectionStatus,
    last_checked_at: null,
    last_error: null,
  };
}

describe('summarizeBangumi', () => {
  const rules = [
    { ...mockBangumiRule, id: 1, deleted: false, archived: false },
    {
      ...mockBangumiRule,
      id: 2,
      deleted: false,
      archived: false,
      needs_review: true,
    },
    { ...mockBangumiRule, id: 3, deleted: false, archived: true },
    { ...mockBangumiRule, id: 4, deleted: true, archived: false },
  ];

  it('should count active rules when archived and deleted rules exist', () => {
    expect(summarizeBangumi(rules).active).toBe(2);
  });

  it('should count review items when an active rule needs review', () => {
    expect(summarizeBangumi(rules).needsReview).toBe(1);
  });
});

describe('summarizeRss', () => {
  const feeds = [
    rss(1, true, 'healthy'),
    rss(2, true, 'error'),
    rss(3, false, 'error'),
  ];

  it('should count enabled feeds when disabled feeds exist', () => {
    expect(summarizeRss(feeds).enabled).toBe(2);
  });

  it('should count errors only when the feed is enabled', () => {
    expect(summarizeRss(feeds).errors).toBe(1);
  });
});

describe('summarizeDownloads', () => {
  const torrents = [
    torrent('downloading', 200),
    torrent('stalledDL', 0),
    torrent('pausedDL', 100),
    torrent('uploading', 0),
  ];

  it('should count active download states when paused items exist', () => {
    expect(summarizeDownloads(torrents).active).toBe(2);
  });

  it('should sum current download speed across every torrent', () => {
    expect(summarizeDownloads(torrents).bytesPerSecond).toBe(300);
  });
});
