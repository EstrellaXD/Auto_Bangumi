/**
 * Tests for Bangumi API data transformation logic
 * Note: These tests focus on the filter/rss_link string<->array transformations
 */

import { describe, expect, it, vi } from 'vitest';
import {
  mockApiSuccess,
  mockBangumiAPI,
  mockBangumiRule,
} from '@/test/mocks/api';
import { createAxiosMock } from '@/test/mocks/axios';
import type { DetectOffsetRequest } from '#/bangumi';

import { apiBangumi } from '@/api/bangumi';
import { axios } from '@/utils/axios';

vi.mock('@/utils/axios', () => ({ axios: createAxiosMock() }));

describe('Bangumi API Logic', () => {
  describe('getAll transformation (string to array)', () => {
    // This transformation happens when receiving data from API
    const transformApiResponse = <T extends { filter: string; rss_link: string }>(item: T) => ({
      ...item,
      filter: item.filter.split(','),
      rss_link: item.rss_link.split(','),
    });

    it('should transform filter string to array', () => {
      const apiData = { ...mockBangumiAPI, filter: '720', rss_link: 'url1' };
      const result = transformApiResponse(apiData);

      expect(Array.isArray(result.filter)).toBe(true);
      expect(result.filter).toEqual(['720']);
    });

    it('should handle empty filter string', () => {
      const apiData = { ...mockBangumiAPI, filter: '', rss_link: '' };
      const result = transformApiResponse(apiData);

      expect(result.filter).toEqual(['']);
      expect(result.rss_link).toEqual(['']);
    });

    it('should handle multiple comma-separated values', () => {
      const apiData = {
        ...mockBangumiAPI,
        filter: '720,1080,480',
        rss_link: 'url1,url2,url3',
      };
      const result = transformApiResponse(apiData);

      expect(result.filter).toEqual(['720', '1080', '480']);
      expect(result.rss_link).toEqual(['url1', 'url2', 'url3']);
    });

    it('should preserve other fields during transformation', () => {
      const apiData = {
        ...mockBangumiAPI,
        id: 42,
        title_raw: 'Test Title',
        filter: '720',
        rss_link: 'url1',
      };
      const result = transformApiResponse(apiData);

      expect(result.id).toBe(42);
      expect(result.title_raw).toBe('Test Title');
    });
  });

  describe('updateRule transformation (array to string)', () => {
    // This transformation happens when sending data to API
    const transformForUpdate = (rule: { id: number; filter: string[]; rss_link: string[] }) => {
      const { id, ...rest } = rule;
      return {
        ...rest,
        filter: rule.filter.join(','),
        rss_link: rule.rss_link.join(','),
      };
    };

    it('should transform filter array to string', () => {
      const rule = { ...mockBangumiRule, filter: ['720'], rss_link: ['url1'] };
      const result = transformForUpdate(rule);

      expect(typeof result.filter).toBe('string');
      expect(result.filter).toBe('720');
    });

    it('should join multiple filter values with commas', () => {
      const rule = {
        ...mockBangumiRule,
        filter: ['720', '1080', '480'],
        rss_link: ['url1', 'url2'],
      };
      const result = transformForUpdate(rule);

      expect(result.filter).toBe('720,1080,480');
      expect(result.rss_link).toBe('url1,url2');
    });

    it('should omit id from update payload', () => {
      const rule = { ...mockBangumiRule, id: 123 };
      const result = transformForUpdate(rule);

      expect(result).not.toHaveProperty('id');
    });

    it('should handle empty arrays', () => {
      const rule = { ...mockBangumiRule, filter: [], rss_link: [] };
      const result = transformForUpdate(rule);

      expect(result.filter).toBe('');
      expect(result.rss_link).toBe('');
    });
  });

  // Contract tests: call the real apiBangumi functions against a mocked
  // axios instance so a drift between the wrapper and the FastAPI routes in
  // backend/src/module/api/bangumi.py fails a test instead of going
  // unnoticed.
  describe('API contract (path + HTTP method)', () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('should GET api/v1/bangumi/get/all when fetching all rules', async () => {
      (axios.get as any).mockResolvedValue({ data: [mockBangumiAPI] });
      await apiBangumi.getAll();
      expect(axios.get).toHaveBeenCalledWith('api/v1/bangumi/get/all');
    });

    it('should PATCH api/v1/bangumi/update/:id with the id omitted when updating a rule', async () => {
      (axios.patch as any).mockResolvedValue({ data: mockApiSuccess });
      await apiBangumi.updateRule(1, mockBangumiRule);
      expect(axios.patch).toHaveBeenCalledWith(
        'api/v1/bangumi/update/1',
        expect.not.objectContaining({ id: expect.anything() })
      );
    });

    it('should DELETE api/v1/bangumi/delete/:id with the file param when deleting a single rule', async () => {
      (axios.delete as any).mockResolvedValue({ data: mockApiSuccess });
      await apiBangumi.deleteRule(1, true);
      expect(axios.delete).toHaveBeenCalledWith('api/v1/bangumi/delete/1', {
        params: { file: true },
      });
    });

    it('should POST api/v1/bangumi/delete/many with the id array when batch deleting', async () => {
      (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
      await apiBangumi.deleteRule([1, 2, 3], false);
      expect(axios.post).toHaveBeenCalledWith(
        'api/v1/bangumi/delete/many',
        [1, 2, 3],
        { params: { file: false } }
      );
    });

    it('should POST api/v1/bangumi/disable/:id with the file param when disabling a single rule', async () => {
      (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
      await apiBangumi.disableRule(1, true);
      expect(axios.post).toHaveBeenCalledWith(
        'api/v1/bangumi/disable/1',
        null,
        { params: { file: true } }
      );
    });

    it('should POST api/v1/bangumi/disable/many with the id array when batch disabling', async () => {
      (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
      await apiBangumi.disableRule([1, 2], false);
      expect(axios.post).toHaveBeenCalledWith(
        'api/v1/bangumi/disable/many',
        [1, 2],
        { params: { file: false } }
      );
    });

    it('should POST api/v1/bangumi/enable/:id when enabling a rule', async () => {
      (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
      await apiBangumi.enableRule(1);
      expect(axios.post).toHaveBeenCalledWith('api/v1/bangumi/enable/1');
    });

    it('should POST api/v1/bangumi/reset/all when resetting all rules', async () => {
      (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
      await apiBangumi.resetAll();
      expect(axios.post).toHaveBeenCalledWith('api/v1/bangumi/reset/all');
    });

    it('should GET api/v1/bangumi/refresh/poster/all when refreshing posters', async () => {
      (axios.get as any).mockResolvedValue({ data: mockApiSuccess });
      await apiBangumi.refreshPoster();
      expect(axios.get).toHaveBeenCalledWith('api/v1/bangumi/refresh/poster/all');
    });

    it('should GET api/v1/bangumi/refresh/calendar when refreshing the calendar', async () => {
      (axios.get as any).mockResolvedValue({ data: mockApiSuccess });
      await apiBangumi.refreshCalendar();
      expect(axios.get).toHaveBeenCalledWith('api/v1/bangumi/refresh/calendar');
    });

    it('should PATCH api/v1/bangumi/archive/:id when archiving a rule', async () => {
      (axios.patch as any).mockResolvedValue({ data: mockApiSuccess });
      await apiBangumi.archiveRule(1);
      expect(axios.patch).toHaveBeenCalledWith('api/v1/bangumi/archive/1');
    });

    it('should PATCH api/v1/bangumi/unarchive/:id when unarchiving a rule', async () => {
      (axios.patch as any).mockResolvedValue({ data: mockApiSuccess });
      await apiBangumi.unarchiveRule(1);
      expect(axios.patch).toHaveBeenCalledWith('api/v1/bangumi/unarchive/1');
    });

    it('should GET api/v1/bangumi/refresh/metadata when refreshing metadata', async () => {
      (axios.get as any).mockResolvedValue({ data: mockApiSuccess });
      await apiBangumi.refreshMetadata();
      expect(axios.get).toHaveBeenCalledWith('api/v1/bangumi/refresh/metadata');
    });

    it('should GET api/v1/bangumi/suggest-offset/:id when suggesting an offset', async () => {
      (axios.get as any).mockResolvedValue({
        data: { suggested_offset: 1, reason: 'test' },
      });
      await apiBangumi.suggestOffset(1);
      expect(axios.get).toHaveBeenCalledWith('api/v1/bangumi/suggest-offset/1');
    });

    it('should POST api/v1/bangumi/detect-offset with the request body when detecting offset', async () => {
      const request: DetectOffsetRequest = {
        title: 'Test Anime',
        parsed_season: 1,
        parsed_episode: 1,
      };
      (axios.post as any).mockResolvedValue({
        data: { has_mismatch: false, suggestion: null, tmdb_info: null },
      });
      await apiBangumi.detectOffset(request);
      expect(axios.post).toHaveBeenCalledWith('api/v1/bangumi/detect-offset', request);
    });

    it('should POST api/v1/bangumi/dismiss-review/:id when dismissing a review flag', async () => {
      (axios.post as any).mockResolvedValue({ data: mockApiSuccess });
      await apiBangumi.dismissReview(1);
      expect(axios.post).toHaveBeenCalledWith('api/v1/bangumi/dismiss-review/1');
    });

    it('should PATCH api/v1/bangumi/:id/weekday with the weekday when setting the weekday', async () => {
      (axios.patch as any).mockResolvedValue({ data: mockApiSuccess });
      await apiBangumi.setWeekday(1, 3);
      expect(axios.patch).toHaveBeenCalledWith('api/v1/bangumi/1/weekday', {
        weekday: 3,
      });
    });
  });
});
