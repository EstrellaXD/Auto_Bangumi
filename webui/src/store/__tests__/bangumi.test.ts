/**
 * Tests for Bangumi Store logic
 * Note: These tests focus on pure logic that can be tested without full Vue/Pinia setup
 */

import { describe, it, expect, vi } from 'vitest';
import { mockBangumiRule } from '@/test/mocks/api';

describe('Bangumi Store Logic', () => {
  describe('filter functions', () => {
    const filterActive = (list: typeof mockBangumiRule[]) =>
      list.filter((b) => !b.deleted && !b.archived);

    const filterArchived = (list: typeof mockBangumiRule[]) =>
      list.filter((b) => !b.deleted && b.archived);

    it('filterActive should filter out deleted and archived items', () => {
      const bangumi = [
        { ...mockBangumiRule, id: 1, deleted: false, archived: false },
        { ...mockBangumiRule, id: 2, deleted: true, archived: false },
        { ...mockBangumiRule, id: 3, deleted: false, archived: true },
        { ...mockBangumiRule, id: 4, deleted: false, archived: false },
      ];

      const result = filterActive(bangumi);

      expect(result.length).toBe(2);
      expect(result.map((b) => b.id)).toEqual([1, 4]);
    });

    it('filterArchived should return only archived, non-deleted items', () => {
      const bangumi = [
        { ...mockBangumiRule, id: 1, deleted: false, archived: false },
        { ...mockBangumiRule, id: 2, deleted: true, archived: true },
        { ...mockBangumiRule, id: 3, deleted: false, archived: true },
        { ...mockBangumiRule, id: 4, deleted: false, archived: true },
      ];

      const result = filterArchived(bangumi);

      expect(result.length).toBe(2);
      expect(result.map((b) => b.id)).toEqual([3, 4]);
    });

    it('filterActive should return empty when all are deleted', () => {
      const bangumi = [
        { ...mockBangumiRule, id: 1, deleted: true, archived: false },
        { ...mockBangumiRule, id: 2, deleted: true, archived: false },
      ];

      const result = filterActive(bangumi);

      expect(result.length).toBe(0);
    });
  });

  describe('sort functions', () => {
    it('should sort by id descending', () => {
      const bangumi = [
        { ...mockBangumiRule, id: 1, deleted: false },
        { ...mockBangumiRule, id: 3, deleted: false },
        { ...mockBangumiRule, id: 2, deleted: false },
      ];

      const sorted = bangumi.sort((a, b) => b.id - a.id);

      expect(sorted.map((b) => b.id)).toEqual([3, 2, 1]);
    });

    it('should separate enabled and disabled items', () => {
      const bangumi = [
        { ...mockBangumiRule, id: 1, deleted: false },
        { ...mockBangumiRule, id: 2, deleted: true },
        { ...mockBangumiRule, id: 3, deleted: false },
        { ...mockBangumiRule, id: 4, deleted: true },
      ];

      const enabled = bangumi.filter((e) => !e.deleted).sort((a, b) => b.id - a.id);
      const disabled = bangumi.filter((e) => e.deleted).sort((a, b) => b.id - a.id);
      const sorted = [...enabled, ...disabled];

      expect(sorted.map((b) => b.id)).toEqual([3, 1, 4, 2]);
    });
  });
});
