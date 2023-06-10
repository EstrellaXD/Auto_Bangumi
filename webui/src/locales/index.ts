import { createI18n } from 'vue-i18n';
import messages from '@intlify/unplugin-vue-i18n/messages'

const i18n = createI18n({
    legacy: false,
    locale: 'zh-CN',
    globalInjection: true,
    silentTranslationWarn: true,
    globalInstall: true,
    messages
  })

export default i18n;