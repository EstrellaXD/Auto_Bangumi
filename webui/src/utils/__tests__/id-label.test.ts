import { describe, expect, it, vi } from 'vitest';
import { idLabel } from '../id-label';
import en from '@/i18n/en.json';
import zhCN from '@/i18n/zh-CN.json';

const t = (key: string) => `t:${key}`;

// 应用里 @intlify/unplugin-vue-i18n 把 i18n/*.json 的文案预编译成消息函数，
// 这里同样把叶子换成函数，按生产环境的形态测试
vi.mock('@/i18n/en.json', async (importOriginal) => {
  const compile = (node: unknown): unknown =>
    typeof node === 'string'
      ? () => node
      : Object.fromEntries(
          Object.entries(node as object).map(([k, v]) => [k, compile(v)])
        );
  const { default: source } = await importOriginal<{ default: object }>();
  return { default: compile(source) };
});

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
