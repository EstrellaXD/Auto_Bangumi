import { createI18n } from 'vue-i18n';
import messages from '@intlify/unplugin-vue-i18n/messages'

//Default language is the same as last setting (undefined is browser language)
let lang = localStorage.getItem('lang');
if(lang === null){
    const navLang = navigator.language;
    let localLang = navLang || false;
    lang = localLang || 'en-US';
}
localStorage.setItem('lang', lang);

const i18n = createI18n({
    legacy: false,
    locale: lang,
    globalInjection: true,
    silentTranslationWarn: true,
    globalInstall: true,
    messages
  })

export default i18n;