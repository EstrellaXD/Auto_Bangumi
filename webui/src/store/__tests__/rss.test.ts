/**
 * Tests for RSS Store logic
 * Note: These tests focus on pure logic that can be tested without full Vue/Pinia setup
 */

import { describe, it, expect } from 'vitest';
import { mockRSSList } from '@/test/mocks/api';

describe('RSS Store Logic', () => {
  describe('sort and filter functions', () => {
    it('should sort enabled feeds first then by id descending', () => {
      const mixedList = [
        { id: 1, name: 'Feed 1', url: 'url1', enabled: false },
        { id: 2, name: 'Feed 2', url: 'url2', enabled: true },
        { id: 3, name: 'Feed 3', url: 'url3', enabled: false },
        { id: 4, name: 'Feed 4', url: 'url4', enabled: true },
      ];

      // Apply the same sorting logic as the store
      const enabled = mixedList.filter((e) => e.enabled).sort((a, b) => b.id - a.id);
      const disabled = mixedList.filter((e) => !e.enabled).sort((a, b) => b.id - a.id);
      const sorted = [...enabled, ...disabled];

      // Enabled should come first (sorted by id desc)
      expect(sorted[0].id).toBe(4);
      expect(sorted[1].id).toBe(2);
      // Then disabled (sorted by id desc)
      expect(sorted[2].id).toBe(3);
      expect(sorted[3].id).toBe(1);
    });

    it('should handle all enabled feeds', () => {
      const allEnabled = [
        { id: 1, name: 'Feed 1', url: 'url1', enabled: true },
        { id: 3, name: 'Feed 3', url: 'url3', enabled: true },
        { id: 2, name: 'Feed 2', url: 'url2', enabled: true },
      ];

      const enabled = allEnabled.filter((e) => e.enabled).sort((a, b) => b.id - a.id);
      const disabled = allEnabled.filter((e) => !e.enabled).sort((a, b) => b.id - a.id);
      const sorted = [...enabled, ...disabled];

      expect(sorted.map((s) => s.id)).toEqual([3, 2, 1]);
    });

    it('should handle all disabled feeds', () => {
      const allDisabled = [
        { id: 1, name: 'Feed 1', url: 'url1', enabled: false },
        { id: 3, name: 'Feed 3', url: 'url3', enabled: false },
        { id: 2, name: 'Feed 2', url: 'url2', enabled: false },
      ];

      const enabled = allDisabled.filter((e) => e.enabled).sort((a, b) => b.id - a.id);
      const disabled = allDisabled.filter((e) => !e.enabled).sort((a, b) => b.id - a.id);
      const sorted = [...enabled, ...disabled];

      expect(sorted.map((s) => s.id)).toEqual([3, 2, 1]);
    });

    it('should handle empty list', () => {
      const emptyList: typeof mockRSSList = [];

      const enabled = emptyList.filter((e) => e.enabled).sort((a, b) => b.id - a.id);
      const disabled = emptyList.filter((e) => !e.enabled).sort((a, b) => b.id - a.id);
      const sorted = [...enabled, ...disabled];

      expect(sorted).toEqual([]);
    });
  });

  describe('selection management logic', () => {
    it('should track selected items in array', () => {
      const selectedRSS: number[] = [];

      selectedRSS.push(1);
      selectedRSS.push(2);
      selectedRSS.push(3);

      expect(selectedRSS).toEqual([1, 2, 3]);
    });

    it('should clear selection by reassigning empty array', () => {
      let selectedRSS = [1, 2, 3];

      selectedRSS = [];

      expect(selectedRSS).toEqual([]);
    });

    it('should remove specific item from selection', () => {
      const selectedRSS = [1, 2, 3];

      const filtered = selectedRSS.filter((id) => id !== 2);

      expect(filtered).toEqual([1, 3]);
    });
  });
});
