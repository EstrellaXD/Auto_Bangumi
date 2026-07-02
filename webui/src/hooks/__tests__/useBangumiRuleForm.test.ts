/**
 * Tests for useBangumiRuleForm — the shared composable extracted from
 * ab-add-rss.vue / ab-edit-rule.vue.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, ref } from 'vue';
import type { Ref } from 'vue';
import { mount } from '@vue/test-utils';
import type { BangumiRule } from '#/bangumi';
import { ruleTemplate } from '#/bangumi';
import { useBangumiRuleForm } from '@/hooks/useBangumiRuleForm';

/** 在真实的组件实例内运行 composable，使 onBeforeUnmount 等生命周期钩子可用 */
function withSetup(rule: Ref<BangumiRule>) {
  let result!: ReturnType<typeof useBangumiRuleForm>;
  const wrapper = mount(
    defineComponent({
      setup() {
        result = useBangumiRuleForm(rule);
        return () => null;
      },
    })
  );
  return { result, wrapper };
}

describe('useBangumiRuleForm', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('should build no info tags when rule has no season/dpi/subtitle/group', () => {
    const rule = ref<BangumiRule>({ ...ruleTemplate, season: 0 });
    const { result } = withSetup(rule);

    expect(result.infoTags.value).toEqual([]);
  });

  it('should build info tags in season/resolution/subtitle/group order when populated', () => {
    const rule = ref<BangumiRule>({
      ...ruleTemplate,
      season: 2,
      dpi: '1080p',
      subtitle: 'CHS',
      group_name: 'ANi',
    });
    const { result } = withSetup(rule);

    expect(result.infoTags.value).toEqual([
      { value: 'S2', type: 'season' },
      { value: '1080p', type: 'resolution' },
      { value: 'CHS', type: 'subtitle' },
      { value: 'ANi', type: 'group' },
    ]);
  });

  it('should prefer season_raw over the numeric season when both are set', () => {
    const rule = ref<BangumiRule>({
      ...ruleTemplate,
      season: 2,
      season_raw: 'S2 Part 2',
    });
    const { result } = withSetup(rule);

    expect(result.infoTags.value).toEqual([
      { value: 'S2 Part 2', type: 'season' },
    ]);
  });

  it('should default showAdvanced to true', () => {
    const rule = ref<BangumiRule>({ ...ruleTemplate });
    const { result } = withSetup(rule);

    expect(result.showAdvanced.value).toBe(true);
  });

  it('should set copied to true after copyRssLink and clear it after the timeout', async () => {
    vi.useFakeTimers();
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('navigator', { clipboard: { writeText } });

    const rule = ref<BangumiRule>({ ...ruleTemplate });
    const { result } = withSetup(rule);

    await result.copyRssLink('https://example.com/rss');
    expect(writeText).toHaveBeenCalledWith('https://example.com/rss');
    expect(result.copied.value).toBe(true);

    vi.advanceTimersByTime(2000);
    expect(result.copied.value).toBe(false);

    vi.useRealTimers();
  });

  it('should not touch the clipboard when copyRssLink is called with an empty link', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('navigator', { clipboard: { writeText } });

    const rule = ref<BangumiRule>({ ...ruleTemplate });
    const { result } = withSetup(rule);

    await result.copyRssLink('');
    expect(writeText).not.toHaveBeenCalled();
    expect(result.copied.value).toBe(false);
  });
});
