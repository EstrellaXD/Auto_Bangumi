import { createI18n } from 'vue-i18n';
import enUS from '@/i18n/en.json';
import zhCN from '@/i18n/zh-CN.json';

const messages = {
  en: enUS,
  'zh-CN': zhCN,
};

type Languages = keyof typeof messages;

export const useMyI18n = createSharedComposable(() => {
  const lang = useLocalStorage<Languages>(
    'lang',
    navigator.language as Languages
  );

  const i18n = createI18n({
    legacy: false,
    locale: lang.value,
    fallbackLocale: 'en',
    messages,
  });

  watch(lang, (val) => {
    i18n.global.locale.value = val;
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
    return computed(() => texts[lang.value]);
  }

  return {
    lang,
    i18n,
    t: i18n.global.t,
    locale: i18n.global.locale,
    changeLocale,
    getText: returnUserLangText,
    returnUserLangText,
  };
});
