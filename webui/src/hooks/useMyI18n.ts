import { createI18n } from 'vue-i18n';
import enUS from '@/i18n/en.json';
import zhCN from '@/i18n/zh-CN.json';

const messages = {
  en: enUS,
  'zh-CN': zhCN,
};

export const useMyI18n = createSharedComposable(() => {
  const lang = useLocalStorage('lang', navigator.language);

  const i18n = createI18n({
    legacy: false,
    locale: lang.value,
    fallbackLocale: 'en',
    messages,
  });

  function changeLocale() {
    if (lang.value === 'zh-CN') {
      i18n.global.locale.value = 'en';
      lang.value = 'en';
    } else {
      i18n.global.locale.value = 'zh-CN';
      lang.value = 'zh-CN';
    }
  }

  return {
    lang,
    i18n,
    t: i18n.global.t,
    locale: i18n.global.locale,
    changeLocale,
  };
});
