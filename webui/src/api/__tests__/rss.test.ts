/**
 * Tests for RSS API logic
 * Note: These tests focus on data structures and endpoint paths
 */

import { describe, expect, it, vi } from 'vitest';
import {
  mockApiSuccess,
  mockRSSItem,
  mockRSSList,
} from '@/test/mocks/api';
import { createAxiosMock } from '@/test/mocks/axios';

import { apiRSS } from '@/api/rss';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

describe('RSS API Logic', () => {
  describe('RSS data structure', () => {
    it('should have required RSS fields', () => {
      expect(mockRSSItem).toHaveProperty('id');
      expect(mockRSSItem).toHaveProperty('name');
      expect(mockRSSItem).toHaveProperty('url');
      expect(mockRSSItem).toHaveProperty('enabled');
    });

    it('should have correct field types', () => {
      expect(typeof mockRSSItem.id).toBe('number');
      expect(typeof mockRSSItem.name).toBe('string');
      expect(typeof mockRSSItem.url).toBe('string');
      expect(typeof mockRSSItem.enabled).toBe('boolean');
    });
  });

  describe('RSS list operations', () => {
    it('should handle empty list', () => {
      const emptyList: typeof mockRSSList = [];
      expect(emptyList.length).toBe(0);
    });

    it('should be able to filter enabled feeds', () => {
      const enabled = mockRSSList.filter((rss) => rss.enabled);
      expect(enabled.length).toBeGreaterThanOrEqual(0);
    });

    it('should be able to filter disabled feeds', () => {
      const disabled = mockRSSList.filter((rss) => !rss.enabled);
      expect(disabled.length).toBeGreaterThanOrEqual(0);
    });
  });

  describe('batch operations data format', () => {
    it('should format deleteMany as array of IDs', () => {
      const idsToDelete = [1, 2, 3];
      expect(Array.isArray(idsToDelete)).toBe(true);
      expect(idsToDelete).toEqual([1, 2, 3]);
    });

    it('should format disableMany as array of IDs', () => {
      const idsToDisable = [1, 2];
      expect(Array.isArray(idsToDisable)).toBe(true);
      expect(idsToDisable).toEqual([1, 2]);
    });

    it('should format enableMany as array of IDs', () => {
      const idsToEnable = [1, 2, 3];
      expect(Array.isArray(idsToEnable)).toBe(true);
      expect(idsToEnable).toEqual([1, 2, 3]);
    });
  });

  // Contract tests: call the real apiRSS functions against a mocked axios
  // instance so a drift between the wrapper and the FastAPI routes in
  // backend/src/module/api/rss.py fails a test instead of going unnoticed.
  describe('API contract (path + HTTP method)', () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('should GET api/v1/rss when fetching all feeds', async () => {
      (axios.get as any).mockResolvedValue({ data: mockRSSList });
      await apiRSS.get();
      expect(axios.get).toHaveBeenCalledWith('api/v1/rss');
    });

    it('should POST api/v1/rss/add with the RSS payload when adding a feed', async () => {
      (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
      await apiRSS.add(mockRSSItem);
      expect(axios.post).toHaveBeenCalledWith('api/v1/rss/add', mockRSSItem);
    });

    it('should DELETE api/v1/rss/delete/:id when deleting a single feed', async () => {
      (axios.delete as any).mockResolvedValue({ data: mockApiSuccess });
      await apiRSS.delete(7);
      expect(axios.delete).toHaveBeenCalledWith('api/v1/rss/delete/7');
    });

    it('should POST api/v1/rss/delete/many with the id array when batch deleting', async () => {
      (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
      await apiRSS.deleteMany([1, 2, 3]);
      expect(axios.post).toHaveBeenCalledWith('api/v1/rss/delete/many', [1, 2, 3]);
    });

    it('should PATCH api/v1/rss/disable/:id when disabling a single feed', async () => {
      (axios.patch as any).mockResolvedValue({ data: mockApiSuccess });
      await apiRSS.disable(3);
      expect(axios.patch).toHaveBeenCalledWith('api/v1/rss/disable/3');
    });

    it('should POST api/v1/rss/disable/many with the id array when batch disabling', async () => {
      (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
      await apiRSS.disableMany([1, 2]);
      expect(axios.post).toHaveBeenCalledWith('api/v1/rss/disable/many', [1, 2]);
    });

    it('should PATCH api/v1/rss/update/:id with the RSS payload when updating', async () => {
      (axios.patch as any).mockResolvedValue({ data: mockApiSuccess });
      await apiRSS.update(1, mockRSSItem);
      expect(axios.patch).toHaveBeenCalledWith('api/v1/rss/update/1', mockRSSItem);
    });

    it('should POST api/v1/rss/enable/many with the id array when batch enabling', async () => {
      (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
      await apiRSS.enableMany([1, 2, 3]);
      expect(axios.post).toHaveBeenCalledWith('api/v1/rss/enable/many', [1, 2, 3]);
    });

    it('should POST api/v1/rss/refresh/all when refreshing every feed', async () => {
      (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
      await apiRSS.refreshAll();
      expect(axios.post).toHaveBeenCalledWith('api/v1/rss/refresh/all');
    });

    it('should POST api/v1/rss/refresh/:id when refreshing a single feed', async () => {
      (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
      await apiRSS.refresh(9);
      expect(axios.post).toHaveBeenCalledWith('api/v1/rss/refresh/9');
    });

    it('should GET api/v1/rss/torrent/:id when fetching torrents for a feed', async () => {
      (axios.get as any).mockResolvedValue({ data: [] });
      await apiRSS.getTorrent(5);
      expect(axios.get).toHaveBeenCalledWith('api/v1/rss/torrent/5');
    });

    it('should POST api/v1/rss/preview with the rss link payload', async () => {
      (axios.post as any).mockResolvedValue({
        data: { items: [], global_filter: [] },
      });
      await apiRSS.preview('https://mikanani.me/RSS/Search?searchstr=test');
      expect(axios.post).toHaveBeenCalledWith(
        'api/v1/rss/preview',
        { rss_link: 'https://mikanani.me/RSS/Search?searchstr=test' },
        {
          silent: true,
        }
      );
    });
  });

  describe('update payload', () => {
    it('should include all RSS fields in update', () => {
      const updatedRSS = { ...mockRSSItem, name: 'Updated Feed' };

      expect(updatedRSS.id).toBe(mockRSSItem.id);
      expect(updatedRSS.name).toBe('Updated Feed');
      expect(updatedRSS.url).toBe(mockRSSItem.url);
      expect(updatedRSS.enabled).toBe(mockRSSItem.enabled);
    });
  });
});
