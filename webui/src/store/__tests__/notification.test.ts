import { describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useNotificationStore } from '@/store/notification';
import type { InboxMessage } from '@/api/notification';

vi.mock('@/api/notification', () => ({ apiNotification: {} }));
vi.mock('@/hooks/useEventStream', () => ({
  useEventStream: () => ({ connected: ref(true), notificationData: ref(null) }),
}));
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ isLoggedIn: ref(false) }),
}));
vi.mock('@/hooks/useMessage', () => ({
  useMessage: () => ({ error: vi.fn() }),
}));
vi.mock('@/hooks/useMyI18n', () => ({
  useMyI18n: () => ({
    t: (key: string, params?: Record<string, unknown>) =>
      params ? `${key}|${params.strategy}` : key,
  }),
}));

describe('notification store', () => {
  it.each([
    ['pn', 'config.manage_set.strategy_labels.pn'],
    ['my-plugin-way', 'my-plugin-way'],
  ])(
    'should show the rename method name for strategy %s',
    (strategy, label) => {
      const { bodyOf } = useNotificationStore();
      const msg = {
        kind: 'rename_skipped',
        payload: { strategy, torrent_name: 'x', reason: 'r' },
      } as unknown as InboxMessage;
      expect(bodyOf(msg)).toBe(
        `notifications.kind.rename_skipped.body|${label}`
      );
    }
  );
});
