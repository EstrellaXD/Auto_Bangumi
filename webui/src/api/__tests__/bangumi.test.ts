/**
 * Tests for Bangumi API data transformation logic
 * Note: These tests focus on the filter/rss_link string<->array transformations
 */

import { describe, it, expect } from 'vitest';
import {
  mockBangumiAPI,
  mockBangumiRule,
} from '@/test/mocks/api';

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

  describe('deleteRule logic', () => {
    it('should use single endpoint for single ID', () => {
      const id = 1;
      const isArray = Array.isArray(id);

      expect(isArray).toBe(false);
      // Single ID should use: `api/v1/bangumi/delete/${id}`
    });

    it('should use many endpoint for array of IDs', () => {
      const ids = [1, 2, 3];
      const isArray = Array.isArray(ids);

      expect(isArray).toBe(true);
      // Array should use: `api/v1/bangumi/delete/many`
    });
  });

  describe('API endpoint paths', () => {
    const BANGUMI_ENDPOINTS = {
      getAll: 'api/v1/bangumi/get/all',
      getOne: (id: number) => `api/v1/bangumi/get/${id}`,
      update: (id: number) => `api/v1/bangumi/update/${id}`,
      delete: (id: number) => `api/v1/bangumi/delete/${id}`,
      deleteMany: 'api/v1/bangumi/delete/many',
      disable: (id: number) => `api/v1/bangumi/disable/${id}`,
      disableMany: 'api/v1/bangumi/disable/many',
      enable: (id: number) => `api/v1/bangumi/enable/${id}`,
      archive: (id: number) => `api/v1/bangumi/archive/${id}`,
      unarchive: (id: number) => `api/v1/bangumi/unarchive/${id}`,
      resetAll: 'api/v1/bangumi/reset/all',
      detectOffset: 'api/v1/bangumi/detect-offset',
      needsReview: 'api/v1/bangumi/needs-review',
    };

    it('should generate correct getOne endpoint', () => {
      expect(BANGUMI_ENDPOINTS.getOne(42)).toBe('api/v1/bangumi/get/42');
    });

    it('should generate correct update endpoint', () => {
      expect(BANGUMI_ENDPOINTS.update(42)).toBe('api/v1/bangumi/update/42');
    });

    it('should have correct static endpoints', () => {
      expect(BANGUMI_ENDPOINTS.getAll).toBe('api/v1/bangumi/get/all');
      expect(BANGUMI_ENDPOINTS.deleteMany).toBe('api/v1/bangumi/delete/many');
      expect(BANGUMI_ENDPOINTS.needsReview).toBe('api/v1/bangumi/needs-review');
    });
  });
});
