import { describe, expect, it } from 'vitest';
import {
  formatTorrentEta,
  formatTorrentSize,
  formatTorrentSpeed,
  torrentStateLabel,
  torrentStateType,
} from '../downloader-display';

describe('downloader display formatting', () => {
  it('should format a binary torrent size', () => {
    expect(formatTorrentSize(2 * 1024 ** 3)).toBe('2.0 GB');
  });

  it('should use a dash for an idle transfer speed', () => {
    expect(formatTorrentSpeed(0)).toBe('-');
  });

  it('should format an active transfer speed per second', () => {
    expect(formatTorrentSpeed(1024 ** 2)).toBe('1.0 MB/s');
  });

  it('should format a multi-hour ETA compactly', () => {
    expect(formatTorrentEta(3660)).toBe('1h1m');
  });

  it('should translate a known qBittorrent state', () => {
    expect(torrentStateLabel('stoppedDL', (key) => key)).toBe(
      'downloader.state.paused'
    );
  });

  it('should preserve an unknown qBittorrent state', () => {
    expect(torrentStateLabel('newState', (key) => key)).toBe('newState');
  });

  it('should give an error state a danger tone', () => {
    expect(torrentStateType('missingFiles')).toBe('danger');
  });
});
