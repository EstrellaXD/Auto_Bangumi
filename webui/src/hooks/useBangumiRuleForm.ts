import type { Ref } from 'vue';
import type { BangumiRule } from '#/bangumi';

export interface InfoTag {
  value: string;
  type: 'season' | 'resolution' | 'subtitle' | 'group' | 'etype';
  /** value 是 i18n key（由组件翻译），而非直接展示的文本 */
  i18n?: boolean;
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
    const { season, season_raw, dpi, subtitle, group_name, episode_type } =
      rule.value;

    // 普通剧集不打标签，只标出剧场版/特别篇这类少数情况
    if (episode_type === 'movie' || episode_type === 'special') {
      tags.push({
        value: `homepage.rule.type_${episode_type}`,
        type: 'etype',
        i18n: true,
      });
    }

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
    await copyTextWithFallback(link);
    copied.value = true;
    clearTimeout(copyTimer);
    copyTimer = setTimeout(() => {
      copied.value = false;
    }, 2000);
  }

  onBeforeUnmount(() => {
    clearTimeout(copyTimer);
  });

  /**
   * 复制内容到剪切板
   * 当环境为http 或者非安全上下文时，使用回退方案
   * 注：回退方案已被标记为 deprecated，未来可能会被移除，所以并不能保证永远生效
   * @param text
   */
  async function copyTextWithFallback(text: string): Promise<boolean> {
    try {
      if (
        // 确认剪切板对象存在且当前为安全上下文
        navigator.clipboard &&
        window.isSecureContext
      ) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch {
      // 忽略报错，使用 fallback 复制方案
    }

    // fallback 方案：创建一个不可见的 textarea 元素，选中内容并执行复制命令
    const textarea = document.createElement('textarea');
    try {
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      textarea.style.top = '-9999px';
      textarea.setAttribute('readonly', '');

      document.body.appendChild(textarea);

      textarea.select();
      textarea.setSelectionRange(0, textarea.value.length);

      return document.execCommand('copy');
    } catch (err) {
      return false;
    } finally {
      document.body.removeChild(textarea);
    }

  }

  return {
    posterSrc,
    infoTags,
    showAdvanced,
    copied,
    copyRssLink,
  };
}
