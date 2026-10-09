import { describe, expect, it } from 'vitest';
import { idLabel } from '../id-label';
import en from '@/i18n/en.json';
import zhCN from '@/i18n/zh-CN.json';

const t = (key: string) => `t:${key}`;

describe('idLabel', () => {
  it.each([
    ['config.plugins_set.point_labels', 'downloader', 'downloader'],
    ['config.plugins_set.point_labels', 'torrent.filter', 'torrent_filter'],
    ['config.plugins_set.permission_labels', 'fs.write', 'fs_write'],
    ['config.manage_set.strategy_labels', 'template', 'template'],
  ])('should translate %s %s when the id is known', (group, id, name) => {
    expect(idLabel(t, group, id)).toBe(`t:${group}.${name}`);
  });

  it('should return the raw id when the id is unknown', () => {
    expect(idLabel(t, 'config.plugins_set.point_labels', 'my_point')).toBe(
      'my_point'
    );
  });

  it.each([
    'config.plugins_set.point_labels',
    'config.plugins_set.permission_labels',
    'config.manage_set.strategy_labels',
  ])('should have the same %s ids in both locales', (group) => {
    const pick = (root: object) =>
      Object.keys(
        group
          .split('.')
          .reduce<Record<string, unknown>>(
            (node, part) => node[part] as Record<string, unknown>,
            root as Record<string, unknown>
          )
      );
    expect(pick(zhCN)).toEqual(pick(en));
  });
});
