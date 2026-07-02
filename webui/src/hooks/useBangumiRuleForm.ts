import type { Ref } from 'vue';
import type { BangumiRule } from '#/bangumi';

export interface InfoTag {
  value: string;
  type: 'season' | 'resolution' | 'subtitle' | 'group';
}

/**
 * ab-add-rss / ab-edit-rule 共用的表单逻辑：海报地址、信息标签、
 * RSS 链接复制、以及“高级设置”展开状态。两个编辑器各自保留自己
 * 特有的 offset 检测/审核流程，不在此处统一。
 */
export function useBangumiRuleForm(rule: Ref<BangumiRule>) {
  const posterSrc = computed(() => resolvePosterUrl(rule.value.poster_link));

  const infoTags = computed<InfoTag[]>(() => {
    const tags: InfoTag[] = [];
    const { season, season_raw, dpi, subtitle, group_name } = rule.value;

    if (season || season_raw) {
      const seasonDisplay = season_raw || (season ? `S${season}` : '');
      tags.push({ value: seasonDisplay, type: 'season' });
    }

    if (dpi) {
      tags.push({ value: dpi, type: 'resolution' });
    }

    if (subtitle) {
      tags.push({ value: subtitle, type: 'subtitle' });
    }

    if (group_name) {
      tags.push({ value: group_name, type: 'group' });
    }

    return tags;
  });

  const showAdvanced = ref(true);
  const copied = ref(false);
  let copyTimer: ReturnType<typeof setTimeout> | undefined;

  async function copyRssLink(link: string) {
    if (!link) return;
    await navigator.clipboard.writeText(link);
    copied.value = true;
    clearTimeout(copyTimer);
    copyTimer = setTimeout(() => {
      copied.value = false;
    }, 2000);
  }

  onBeforeUnmount(() => {
    clearTimeout(copyTimer);
  });

  return {
    posterSrc,
    infoTags,
    showAdvanced,
    copied,
    copyRssLink,
  };
}
