import { createI18n } from 'vue-i18n';
import enUS from './lang/en-US.json';
import zhCN from './lang/zh-CN.json';

const messages = {
  'en-US': enUS,
  'zh-CN': zhCN,
};

// Default language is the same as last setting (undefined is browser language)
let lang = localStorage.getItem('lang');
if (lang === null) {
  const navLang = navigator.language;
  const localLang = navLang || false;
  lang = localLang || 'en-US';
}
localStorage.setItem('lang', lang);

const i18n = createI18n({
  legacy: false,
  locale: lang,
  globalInjection: true,
  silentTranslationWarn: true,
  globalInstall: true,
  messages,
});

export default i18n;
