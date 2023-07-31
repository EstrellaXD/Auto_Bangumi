// https://vitepress.dev/guide/custom-theme
import { 
  h, 
  onMounted, 
  watch,
  nextTick,
} from 'vue'
import Theme from 'vitepress/theme'
import { useRoute } from 'vitepress'
import mediumZoom from 'medium-zoom'
import HomePreviewWebUI from './components/HomePreviewWebUI.vue'

import './style.css'

export default {
  extends: Theme,
  Layout: () => {
    return h(Theme.Layout, null, {
      // https://vitepress.dev/guide/extending-default-theme#layout-slots
      'home-features-after': () => h(HomePreviewWebUI),
    })
  },
  setup() {
    const route = useRoute()
    const initZoom = () => {
      /**
       * Allow images to be zoomed in on click 
       * https://github.com/vuejs/vitepress/issues/854
       */
      mediumZoom('[data-zoomable]', { background: 'var(--vp-c-bg)' })
    }
    
    onMounted(() => {
      initZoom()
    })

    watch(
      () => route.path,
      () => nextTick(initZoom),
    )
  },
  enhanceApp({ app, router, siteData }) {
    // ...
  }
}
