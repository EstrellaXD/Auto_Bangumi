import { describe, expect, it } from 'vitest';
import { dirtyConfigGroups } from '../config-diff';
import { initConfig } from '#/config';
import type { Config } from '#/config';

function clone(config: Config): Config {
  return JSON.parse(JSON.stringify(config));
}

describe('dirtyConfigGroups', () => {
  it('should return empty array when configs are identical', () => {
    expect(dirtyConfigGroups(initConfig, clone(initConfig))).toEqual([]);
  });

  it('should report the group containing a changed scalar field', () => {
    const current = clone(initConfig);
    current.program.rss_time = 1800;
    expect(dirtyConfigGroups(initConfig, current)).toEqual(['program']);
  });

  it('should report multiple changed groups', () => {
    const current = clone(initConfig);
    current.downloader.host = 'nas:8080';
    current.proxy.enable = true;
    expect(dirtyConfigGroups(initConfig, current)).toEqual([
      'downloader',
      'proxy',
    ]);
  });

  it('should detect changes inside arrays', () => {
    const current = clone(initConfig);
    current.rss_parser.filter = ['720p'];
    expect(dirtyConfigGroups(initConfig, current)).toEqual(['rss_parser']);
  });

  it('should not report a group after the change is reverted', () => {
    const current = clone(initConfig);
    current.log.debug_enable = true;
    current.log.debug_enable = initConfig.log.debug_enable;
    expect(dirtyConfigGroups(initConfig, current)).toEqual([]);
  });
});
