import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import MarketConfirm from '../market-confirm.vue';
import type { CatalogEntry } from '#/plugins';

vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({ t: (key: string) => key }),
}));

function entry(overrides: Partial<CatalogEntry> = {}): CatalogEntry {
  return {
    id: 'nfo',
    name: 'NFO',
    version: '0.2.0',
    kind: 'plugin',
    extension_points: [],
    description: '',
    sdk: '',
    min_ab_version: '4.0.0',
    authors: [],
    permissions: ['filesystem', 'network'],
    has_web: false,
    repo: 'alice/nfo',
    commit: '7c0d9e2aa',
    path: '.',
    readme: '',
    installed_version: '0.1.0',
    ...overrides,
  };
}

function mountConfirm(e: CatalogEntry, installedPermissions: string[]) {
  return mount(MarketConfirm, {
    props: { entry: e, installedPermissions, busy: false },
  });
}

function primary(w: ReturnType<typeof mountConfirm>) {
  return w.findAll('button').at(-1)!;
}

describe('market-confirm', () => {
  it('should require the acknowledgement before an update that adds permissions', async () => {
    const w = mountConfirm(entry(), ['filesystem']);

    expect(w.find('.perm--added').attributes('title')).toContain('network');
    expect(primary(w).text()).toBe('market.update');
    expect(primary(w).attributes('disabled')).toBeDefined();

    await w.find('input[type="checkbox"]').setValue(true);
    await primary(w).trigger('click');

    expect(primary(w).attributes('disabled')).toBeUndefined();
    expect(w.emitted('confirm')).toHaveLength(1);
  });

  it.each([
    ['an update without new permissions', entry(), ['filesystem', 'network']],
    ['an install', entry({ installed_version: null }), []],
  ])('should not ask for acknowledgement for %s', (_, e, installed) => {
    const w = mountConfirm(e, installed);

    expect(w.find('input[type="checkbox"]').exists()).toBe(false);
    expect(w.find('.perm--added').exists()).toBe(false);
    expect(primary(w).attributes('disabled')).toBeUndefined();
    expect(primary(w).text()).toBe(
      e.installed_version ? 'market.update' : 'market.install_enable'
    );
  });

  it('should show a permission dropped by the update as removed', () => {
    const w = mountConfirm(entry({ permissions: ['network'] }), [
      'network',
      'fs.write',
    ]);
    expect(w.find('.perm--removed').attributes('title')).toContain('fs.write');
  });
});
