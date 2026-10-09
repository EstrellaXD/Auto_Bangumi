import { describe, expect, it } from 'vitest';
import {
  categoriesOf,
  categoryCounts,
  entryState,
  filterEntries,
  permissionDiff,
  readCachedCatalog,
  sourceUrl,
  writeCachedCatalog,
} from '../plugin-market';
import type { CatalogEntry } from '#/plugins';

function catalogEntry(overrides: Partial<CatalogEntry> = {}): CatalogEntry {
  return {
    id: 'ntfy',
    name: 'ntfy',
    version: '0.2.0',
    kind: 'plugin',
    extension_points: ['notifier'],
    description: '',
    sdk: '>=0.5,<1',
    min_ab_version: '4.0.0',
    authors: ['AutoBangumi'],
    permissions: [],
    has_web: false,
    repo: 'EstrellaXD/Auto_Bangumi',
    commit: 'a421814c0ffee',
    path: '.',
    readme: '',
    installed_version: null,
    ...overrides,
  };
}

describe('categoriesOf', () => {
  it.each([
    [['notifier'], false, ['notify']],
    [['search_site', 'http.request'], false, ['source']],
    [['rename_strategy', 'notifier'], false, ['notify', 'organize']],
    [['downloader'], false, ['other']],
    [['api_router'], true, ['interface']],
    [[], true, ['interface']],
    [[], false, ['other']],
  ])(
    'should map points %j with has_web=%s to %j',
    (points, hasWeb, categories) => {
      const entry = catalogEntry({
        extension_points: points,
        has_web: hasWeb,
      });
      expect(categoriesOf(entry)).toEqual(categories);
    }
  );
});

describe('entryState', () => {
  it.each([
    [null, 'available'],
    ['0.2.0', 'installed'],
    ['0.1.0', 'update'],
  ] as const)('should be %s → %s', (installed, state) => {
    expect(entryState(catalogEntry({ installed_version: installed }))).toBe(
      state
    );
  });
});

describe('filterEntries', () => {
  const entries = [
    catalogEntry({ id: 'ntfy', name: 'ntfy 通知', installed_version: '0.2.0' }),
    catalogEntry({
      id: 'bili',
      name: 'Bilibili 源',
      extension_points: ['search_site'],
      authors: ['alice'],
    }),
    catalogEntry({
      id: 'nfo',
      name: 'NFO',
      extension_points: ['rename_strategy', 'notifier'],
      description: 'Writes Jellyfin metadata',
      installed_version: '0.1.0',
    }),
  ];
  const ids = (list: CatalogEntry[]) => list.map((e) => e.id);
  const all = { query: '', category: 'all', state: 'all' } as const;

  it.each([
    ['BILI', ['bili']],
    ['alice', ['bili']],
    ['jellyfin', ['nfo']],
    ['通知', ['ntfy']],
    ['  ', ['ntfy', 'bili', 'nfo']],
    ['nothing', []],
  ])('should match query %j by name, id, author or description', (q, out) => {
    expect(ids(filterEntries(entries, { ...all, query: q }))).toEqual(out);
  });

  it('should list a plugin in every category it belongs to', () => {
    expect(ids(filterEntries(entries, { ...all, category: 'notify' }))).toEqual(
      ['ntfy', 'nfo']
    );
    expect(
      ids(filterEntries(entries, { ...all, category: 'organize' }))
    ).toEqual(['nfo']);
  });

  it.each([
    ['installed', ['ntfy']],
    ['update', ['nfo']],
    ['available', ['bili']],
  ] as const)('should keep only %s plugins', (state, out) => {
    expect(ids(filterEntries(entries, { ...all, state }))).toEqual(out);
  });

  it('should count a multi-category plugin once in all', () => {
    expect(categoryCounts(entries, { query: '', state: 'all' })).toEqual({
      all: 3,
      source: 1,
      notify: 2,
      organize: 1,
      interface: 0,
      other: 0,
    });
    expect(categoryCounts(entries, { query: 'nfo', state: 'all' }).all).toBe(1);
  });
});

describe('permissionDiff', () => {
  it('should split kept, added and removed permissions', () => {
    expect(
      permissionDiff(['filesystem', 'fs.write'], ['filesystem', 'network'])
    ).toEqual({
      kept: ['filesystem'],
      added: ['network'],
      removed: ['fs.write'],
    });
  });
});

describe('sourceUrl', () => {
  it.each([
    ['.', 'https://github.com/alice/repo/tree/abc'],
    ['plugins/bili', 'https://github.com/alice/repo/tree/abc/plugins/bili'],
  ])('should build the GitHub tree URL for path %j', (path, url) => {
    expect(
      sourceUrl(catalogEntry({ repo: 'alice/repo', commit: 'abc', path }))
    ).toBe(url);
  });
});

describe('catalog cache', () => {
  const getItem = vi.mocked(localStorage.getItem);
  const setItem = vi.mocked(localStorage.setItem);

  it('should round-trip the last good catalog', () => {
    const cache = { entries: [catalogEntry()], fetchedAt: 1 };
    writeCachedCatalog(cache);
    getItem.mockReturnValueOnce(setItem.mock.lastCall?.[1] ?? null);
    expect(readCachedCatalog()).toEqual(cache);
  });

  it.each([
    ['missing', () => null],
    ['corrupt', () => '{'],
    [
      'blocked',
      () => {
        throw new Error('SecurityError');
      },
    ],
  ])(
    'should return null when the cache is %s',
    (_, read: () => string | null) => {
      getItem.mockImplementationOnce(read);
      expect(readCachedCatalog()).toBeNull();
    }
  );

  it('should ignore a failing write', () => {
    setItem.mockImplementationOnce(() => {
      throw new Error('QuotaExceededError');
    });
    expect(() =>
      writeCachedCatalog({ entries: [], fetchedAt: 0 })
    ).not.toThrow();
  });
});
