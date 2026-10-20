/**
 * Tests for useEventStream — the shared SSE connection that replaces the
 * status/downloader/log polling loops (useAppInfo, downloader store, log
 * store) when available.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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
  // 单例在模块级注册 visibilitychange 监听且从不卸载；逐测试移除，避免旧实例串扰
  const visibilityHandlers: EventListener[] = [];
  const realAddEventListener = document.addEventListener.bind(document);

  beforeEach(() => {
    vi.spyOn(document, 'addEventListener').mockImplementation(
      (type: string, handler: unknown, opts?: unknown) => {
        if (type === 'visibilitychange') {
          visibilityHandlers.push(handler as EventListener);
        }
        realAddEventListener(type, handler as EventListener, opts as never);
      }
    );
    isLoggedIn.value = false;
    MockEventSource.instances = [];
    vi.stubGlobal('EventSource', MockEventSource);
  });

  afterEach(() => {
    for (const h of visibilityHandlers.splice(0)) {
      document.removeEventListener('visibilitychange', h);
    }
    vi.restoreAllMocks();
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

  it('should deliver bus frames to listeners of that kind until unsubscribed', async () => {
    isLoggedIn.value = true;
    const useEventStream = await freshEventStream();
    const { onBus } = withSetup(() => useEventStream());
    const es = MockEventSource.instances.at(-1)!;

    const picked = vi.fn();
    const other = vi.fn();
    const off = onBus('manual-pick.picked', picked);
    onBus('other.kind', other);

    const frame = JSON.stringify({
      kind: 'manual-pick.picked',
      payload: { bangumi_id: 3 },
    });
    es.emit('bus', frame);
    expect(picked).toHaveBeenCalledWith({ bangumi_id: 3 });
    expect(other).not.toHaveBeenCalled();

    off();
    es.emit('bus', frame);
    expect(picked).toHaveBeenCalledTimes(1);
  });

  it('should keep delivering when one bus listener throws', async () => {
    isLoggedIn.value = true;
    const useEventStream = await freshEventStream();
    const { onBus } = withSetup(() => useEventStream());
    const es = MockEventSource.instances.at(-1)!;
    vi.spyOn(console, 'error').mockImplementation(() => {});

    const second = vi.fn();
    onBus('k', () => {
      throw new Error('plugin bug');
    });
    onBus('k', second);
    es.emit('bus', JSON.stringify({ kind: 'k', payload: 1 }));

    expect(second).toHaveBeenCalledWith(1);
  });

  it('should append log_append frames and replace on a log frame', async () => {
    isLoggedIn.value = true;
    const useEventStream = await freshEventStream();
    const result = withSetup(() => useEventStream());
    const es = MockEventSource.instances.at(-1)!;

    es.emit('log_append', 'a\n');
    expect(result.logData.value).toBe('a\n');
    es.emit('log', 'snapshot\n');
    es.emit('log_append', 'b\n');
    expect(result.logData.value).toBe('snapshot\nb\n');
    es.emit('log', 'rotated\n');
    expect(result.logData.value).toBe('rotated\n');
  });

  it('should empty the log when a log_clear frame arrives', async () => {
    isLoggedIn.value = true;
    const useEventStream = await freshEventStream();
    const result = withSetup(() => useEventStream());
    const es = MockEventSource.instances.at(-1)!;

    es.emit('log', 'stale\n');
    es.emit('log_clear', '1');
    expect(result.logData.value).toBe('');
    es.emit('log_append', 'fresh\n');
    expect(result.logData.value).toBe('fresh\n');
  });

  it('should trim the oldest lines when appended log exceeds the cap', async () => {
    isLoggedIn.value = true;
    const useEventStream = await freshEventStream();
    const result = withSetup(() => useEventStream());
    const es = MockEventSource.instances.at(-1)!;

    const line = `${'x'.repeat(99)}\n`;
    es.emit('log', line.repeat(5000));
    es.emit('log_append', 'tail\n');
    const text = result.logData.value!;
    expect(text.length).toBeLessThanOrEqual(512 * 1024);
    expect(text.endsWith('x\ntail\n')).toBe(true);
    expect(text.startsWith(`${'x'.repeat(99)}\n`)).toBe(true);
  });

  describe('hidden tab', () => {
    let hidden = false;
    function setHidden(value: boolean) {
      hidden = value;
      document.dispatchEvent(new Event('visibilitychange'));
    }

    beforeEach(() => {
      vi.useFakeTimers();
      hidden = false;
      vi.spyOn(document, 'hidden', 'get').mockImplementation(() => hidden);
    });
    afterEach(() => {
      vi.useRealTimers();
    });

    it('should close the stream after 30 s hidden and reconnect on visible', async () => {
      isLoggedIn.value = true;
      const useEventStream = await freshEventStream();
      const result = withSetup(() => useEventStream());
      const es = MockEventSource.instances.at(-1)!;
      es.onopen?.();
      // 旧测试遗留的单例也会连接，故以当前数量为基线
      const baseline = MockEventSource.instances.length;

      setHidden(true);
      vi.advanceTimersByTime(30_000);
      expect(es.closed).toBe(true);
      expect(result.connected.value).toBe(false);

      // 隐藏期间不会重连
      vi.advanceTimersByTime(60_000);
      expect(MockEventSource.instances).toHaveLength(baseline);

      setHidden(false);
      expect(MockEventSource.instances).toHaveLength(baseline + 1);
      expect(MockEventSource.instances.at(-1)!.closed).toBe(false);
    });

    it('should keep the stream when hidden for less than 30 s', async () => {
      isLoggedIn.value = true;
      const useEventStream = await freshEventStream();
      withSetup(() => useEventStream());
      const es = MockEventSource.instances.at(-1)!;
      const baseline = MockEventSource.instances.length;

      setHidden(true);
      vi.advanceTimersByTime(29_000);
      setHidden(false);
      vi.advanceTimersByTime(60_000);

      expect(es.closed).toBe(false);
      expect(MockEventSource.instances).toHaveLength(baseline);
    });
  });
});
