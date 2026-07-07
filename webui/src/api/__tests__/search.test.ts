/**
 * Contract tests for apiSearch: call the real functions against a mocked
 * axios instance so a drift between the wrapper and the FastAPI routes in
 * backend/src/module/api/search.py fails a test instead of going
 * unnoticed.
 *
 * Note: `apiSearch.get()` is an EventSource-based composable, not an axios
 * call, so it is out of scope for this contract test.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createAxiosMock } from '@/test/mocks/axios';

import { apiSearch } from '@/api/search';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

describe('Search API contract (path + HTTP method)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should GET api/v1/search/provider when fetching providers', async () => {
    (axios.get as any).mockResolvedValue({ data: ['mikan', 'dmhy'] });
    await apiSearch.getProvider();
    expect(axios.get).toHaveBeenCalledWith('api/v1/search/provider');
  });
});

/**
 * EventSource lifecycle: a re-search must replace the previous stream.
 * The old behaviour leaked the previous EventSource — leaked streams kept
 * appending duplicate results, and their onerror closed the NEW stream
 * while the leaked one auto-reconnected forever (idle spinner).
 */
class FakeEventSource {
  static instances: FakeEventSource[] = [];
  url: string;
  closed = false;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;

  constructor(url: string, _opts?: unknown) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
  }
}

const payload = JSON.stringify({
  official_title: 'Test Anime',
  title_raw: 'Test Anime Raw',
  filter: '720',
  rss_link: 'https://mikanani.me/RSS/Search?searchstr=test',
});

describe('apiSearch.get() EventSource lifecycle', () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    vi.stubGlobal('EventSource', FakeEventSource);
  });

  it('should close the previous stream when a new search opens', () => {
    const search = apiSearch.get();
    search.keyword.value = 'foo';
    search.provider.value = 'mikan';

    search.open();
    search.open();

    expect(FakeEventSource.instances).toHaveLength(2);
    expect(FakeEventSource.instances[0].closed).toBe(true);
    expect(FakeEventSource.instances[1].closed).toBe(false);
  });

  it('should ignore stale stream events when a stale stream errors', () => {
    const search = apiSearch.get();
    search.keyword.value = 'foo';

    search.open();
    const first = FakeEventSource.instances[0];
    search.open();
    const second = FakeEventSource.instances[1];
    second.onopen?.();

    first.onerror?.(new Event('error'));

    expect(second.closed).toBe(false);
    expect(search.error.value).toBe(false);
    expect(search.status.value).toBe('OPEN');
  });

  it('should not append the same result twice', () => {
    const search = apiSearch.get();
    search.keyword.value = 'foo';

    search.open();
    const es = FakeEventSource.instances[0];
    es.onmessage?.({ data: payload });
    es.onmessage?.({ data: payload });

    expect(search.data.value).toHaveLength(1);
  });
});
