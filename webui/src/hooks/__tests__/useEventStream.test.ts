/**
 * Tests for useEventStream — the shared SSE connection that replaces the
 * status/downloader/log polling loops (useAppInfo, downloader store, log
 * store) when available.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { withSetup } from './test-utils';

// useAuth.ts creates a vue-router instance at module scope, which the test
// setup doesn't mock (see useAuth.test.ts's own note about this). Stub the
// composable itself instead of pulling in the router.
const isLoggedIn = ref(false);
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ isLoggedIn }),
}));

/** Minimal EventSource stand-in that lets tests emit named SSE frames. */
class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  withCredentials: boolean;
  listeners: Record<string, Array<(e: { data: string }) => void>> = {};
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;

  constructor(url: string, opts?: { withCredentials?: boolean }) {
    this.url = url;
    this.withCredentials = opts?.withCredentials ?? false;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, cb: (e: { data: string }) => void) {
    (this.listeners[type] ??= []).push(cb);
  }

  emit(type: string, data: string) {
    for (const cb of this.listeners[type] || []) cb({ data });
  }

  close() {
    this.closed = true;
  }
}

/**
 * useEventStream is a module-level shared singleton (createSharedComposable),
 * so each test resets the module registry and re-imports it fresh — this
 * avoids state (the open connection, registered watchers) leaking between
 * tests, and makes the synchronous `{ immediate: true }` watch see whatever
 * `isLoggedIn` value the test set up beforehand.
 */
async function freshEventStream() {
  vi.resetModules();
  const mod = await import('@/hooks/useEventStream');
  return mod.useEventStream;
}

describe('useEventStream', () => {
  beforeEach(() => {
    isLoggedIn.value = false;
    MockEventSource.instances = [];
    vi.stubGlobal('EventSource', MockEventSource);
  });

  it('should open a connection to the events stream when logged in', async () => {
    isLoggedIn.value = true;
    const useEventStream = await freshEventStream();

    withSetup(() => useEventStream());

    const latest = MockEventSource.instances.at(-1)!;
    expect(latest.url).toBe('api/v1/events/stream');
    expect(latest.withCredentials).toBe(true);
  });

  it('should not open a connection when logged out', async () => {
    isLoggedIn.value = false;
    const useEventStream = await freshEventStream();

    withSetup(() => useEventStream());

    expect(MockEventSource.instances).toHaveLength(0);
  });

  it('should set connected to true on open and parse status frames', async () => {
    isLoggedIn.value = true;
    const useEventStream = await freshEventStream();

    const result = withSetup(() => useEventStream());
    const es = MockEventSource.instances.at(-1)!;

    es.onopen?.();
    expect(result.connected.value).toBe(true);

    es.emit(
      'status',
      JSON.stringify({ status: true, version: '3.3.0', first_run: false })
    );
    expect(result.statusData.value).toEqual({
      status: true,
      version: '3.3.0',
      first_run: false,
    });
  });

  it('should parse downloader frames and pass through log frames as-is', async () => {
    isLoggedIn.value = true;
    const useEventStream = await freshEventStream();

    const result = withSetup(() => useEventStream());
    const es = MockEventSource.instances.at(-1)!;

    es.emit('downloader', JSON.stringify([{ hash: 'abc', name: 'Episode 1' }]));
    expect(result.downloaderData.value).toEqual([
      { hash: 'abc', name: 'Episode 1' },
    ]);

    es.emit('log', 'line one\nline two\n');
    expect(result.logData.value).toBe('line one\nline two\n');
  });

  it('should close the connection and reset connected on error', async () => {
    isLoggedIn.value = true;
    const useEventStream = await freshEventStream();

    const result = withSetup(() => useEventStream());
    const es = MockEventSource.instances.at(-1)!;
    es.onopen?.();
    expect(result.connected.value).toBe(true);

    es.onerror?.();
    expect(result.connected.value).toBe(false);
    expect(es.closed).toBe(true);
  });
});
