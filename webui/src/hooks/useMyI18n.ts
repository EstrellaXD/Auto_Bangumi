import { createI18n } from 'vue-i18n';
import { createSharedComposable, useLocalStorage } from '@vueuse/core';
import enUS from '@/i18n/en.json';
import type { ApiSuccess } from '#/api';

type Languages = 'en' | 'zh-CN';

function normalizeLocale(locale: string): Languages {
  if (locale.startsWith('zh')) return 'zh-CN';
  return 'en';
}

export const i18n = createI18n({
  legacy: false,
  locale: normalizeLocale(navigator.language),
  fallbackLocale: 'en',
  // zh-CN 先放空壳以固定语言类型，真正的消息由 loadLocale 载入
  messages: { en: enUS, 'zh-CN': {} },
});

// 默认语言（en）静态打包；其它语言首次使用时才加载
const loaded = new Set<Languages>(['en']);

export async function loadLocale(locale: Languages) {
  if (loaded.has(locale)) return;
  const { default: msgs } = await import('@/i18n/zh-CN.json');
  i18n.global.setLocaleMessage(locale, msgs);
  loaded.add(locale);
}

/** 首次渲染前预载已保存的语言，避免先闪出英文 */
export function loadSavedLocale() {
  let saved: string | null = null;
  try {
    saved = localStorage.getItem('lang');
  } catch {
    // 隐私模式等场景下读取会抛错，回退到浏览器语言
  }
  return loadLocale(normalizeLocale(saved ?? navigator.language));
}

export const useMyI18n = createSharedComposable(() => {
  const lang = useLocalStorage<Languages>(
    'lang',
    normalizeLocale(navigator.language)
  );

  i18n.global.locale.value = lang.value;

  // 先加载语言包再切换，切换期间沿用旧语言
  watch(lang, async (val) => {
    await loadLocale(val);
    // 慢的导入返回时用户可能已切到别的语言，只应用最新一次
    if (lang.value === val) i18n.global.locale.value = val;
  });

  function changeLocale() {
    if (lang.value === 'zh-CN') {
      lang.value = 'en';
    } else {
      lang.value = 'zh-CN';
    }
  }

  function returnUserLangText(texts: {
    [k in Languages]: string;
  }) {
    return texts[lang.value] ?? texts.en;
  }

  function returnUserLangMsg(res: ApiSuccess) {
    const msg = returnUserLangText({
      en: res.msg_en,
      'zh-CN': res.msg_zh,
    });
    return msg;
  }

  return {
    lang,
    i18n,
    t: i18n.global.t,
    locale: i18n.global.locale,
    changeLocale,
    returnUserLangText,
    returnUserLangMsg,
  };
});
