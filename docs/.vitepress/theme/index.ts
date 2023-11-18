// https://vitepress.dev/guide/custom-theme
import {
    h,
    onMounted,
    watch,
    nextTick,
} from 'vue'
import Theme from 'vitepress/theme'
import {useRoute} from 'vitepress'
import mediumZoom from 'medium-zoom'
import Documate from '@documate/vue'
import '@documate/vue/dist/style.css'
import HomePreviewWebUI from './components/HomePreviewWebUI.vue'
import googleAnalytics from 'vitepress-plugin-google-analytics'

import './style.css'

export default {
    extends: Theme,
    Layout: () => {
        return h(Theme.Layout, null, {
            // https://vitepress.dev/guide/extending-default-theme#layout-slots
            'home-features-after': () => h(HomePreviewWebUI),
            'nav-bar-content-before': () => h(Documate, {
                endpoint: 'https://kp35gyb313.us.aircode.run/ask',
            }),
        })
    },
    setup() {
        const route = useRoute()
        const initZoom = () => {
            /**
             * Allow images to be zoomed in on click
             * https://github.com/vuejs/vitepress/issues/854
             */
            mediumZoom('[data-zoomable]', {background: 'var(--vp-c-bg)'})
        }

        onMounted(() => {
            initZoom()
        })

        watch(
            () => route.path,
            () => nextTick(initZoom),
        )
    },
    enhanceApp: (ctx) => {
    googleAnalytics({
      id: 'G-3Z8W6WMN7J',
    })
  },
}
