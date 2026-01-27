import { defineConfig } from 'vitepress'

const version = `v3.2`

// Shared configuration
const sharedConfig = {
  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/light-logo.svg' }],
    ['meta', { property: 'og:image', content: '/social.png' }],
    ['meta', { property: 'og:site_name', content: 'AutoBangumi' }],
    ['meta', { property: 'og:url', content: 'https://www.autobangumi.org' }],
    ['script', { async: '', src: 'https://www.googletagmanager.com/gtag/js?id=G-3Z8W6WMN7J' }],
    ['script', {}, `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-3Z8W6WMN7J');`],
  ] as any,

  themeConfig: {
    logo: {
      dark: '/dark-logo.svg',
      light: '/light-logo.svg',
    },
    socialLinks: [
      { icon: 'github', link: 'https://github.com/EstrellaXD/Auto_Bangumi' },
      {
        icon: {
          svg: '<svg xmlns="http://www.w3.org/2000/svg" role="img" viewBox="0 0 24 24"><title>Telegram</title><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>',
        },
        link: 'https://t.me/autobangumi',
      },
    ],
    search: {
      provider: 'local',
    },
  },
}

// Chinese sidebar (default)
const zhSidebar = [
  {
    items: [
      { text: '关于', link: '/home/' },
      { text: '快速开始', link: '/deploy/quick-start' },
      { text: '工作原理', link: '/home/pipline' },
    ],
  },
  {
    text: '部署',
    items: [
      { text: 'Docker CLI', link: '/deploy/docker-cli' },
      { text: 'Docker Compose', link: '/deploy/docker-compose' },
      { text: '群晖 NAS (DSM)', link: '/deploy/dsm' },
      { text: '本地部署', link: '/deploy/local' },
    ],
  },
  {
    text: '配置',
    items: [
      { text: 'RSS 订阅设置', link: '/config/rss' },
      { text: '程序设置', link: '/config/program' },
      { text: '下载器设置', link: '/config/downloader' },
      { text: '解析器设置', link: '/config/parser' },
      { text: '通知设置', link: '/config/notifier' },
      { text: '番剧管理设置', link: '/config/manager' },
      { text: '代理设置', link: '/config/proxy' },
      { text: '实验性功能', link: '/config/experimental' },
    ],
  },
  {
    text: '功能',
    items: [
      { text: 'RSS 管理', link: '/feature/rss' },
      { text: '番剧管理', link: '/feature/bangumi' },
      { text: '日历视图', link: '/feature/calendar' },
      { text: '文件重命名', link: '/feature/rename' },
      { text: '种子搜索', link: '/feature/search' },
    ],
  },
  {
    text: '常见问题',
    items: [
      { text: '常见问题', link: '/faq/' },
      { text: '故障排除', link: '/faq/troubleshooting' },
      { text: '网络问题', link: '/faq/network' },
    ],
  },
  {
    text: 'API 参考',
    items: [
      { text: 'REST API', link: '/api/' },
    ],
  },
  {
    text: '更新日志',
    items: [
      { text: '3.2 版本说明', link: '/changelog/3.2' },
      { text: '3.1 版本说明', link: '/changelog/3.1' },
      { text: '3.0 版本说明', link: '/changelog/3.0' },
      { text: '2.6 版本说明', link: '/changelog/2.6' },
    ],
  },
  {
    text: '开发者指南',
    items: [
      { text: '参与贡献', link: '/dev/' },
    ],
  },
]

// English sidebar
const enSidebar = [
  {
    items: [
      { text: 'About', link: '/en/home/' },
      { text: 'Quick Start', link: '/en/deploy/quick-start' },
      { text: 'How It Works', link: '/en/home/pipline' },
    ],
  },
  {
    text: 'Deployment',
    items: [
      { text: 'Docker CLI', link: '/en/deploy/docker-cli' },
      { text: 'Docker Compose', link: '/en/deploy/docker-compose' },
      { text: 'Synology NAS (DSM)', link: '/en/deploy/dsm' },
      { text: 'Local Deployment', link: '/en/deploy/local' },
    ],
  },
  {
    text: 'Configuration',
    items: [
      { text: 'RSS Feed Setup', link: '/en/config/rss' },
      { text: 'Program Settings', link: '/en/config/program' },
      { text: 'Downloader Settings', link: '/en/config/downloader' },
      { text: 'Parser Settings', link: '/en/config/parser' },
      { text: 'Notification Settings', link: '/en/config/notifier' },
      { text: 'Bangumi Manager', link: '/en/config/manager' },
      { text: 'Proxy Settings', link: '/en/config/proxy' },
      { text: 'Experimental Features', link: '/en/config/experimental' },
    ],
  },
  {
    text: 'Features',
    items: [
      { text: 'RSS Management', link: '/en/feature/rss' },
      { text: 'Bangumi Management', link: '/en/feature/bangumi' },
      { text: 'Calendar View', link: '/en/feature/calendar' },
      { text: 'File Renaming', link: '/en/feature/rename' },
      { text: 'Torrent Search', link: '/en/feature/search' },
    ],
  },
  {
    text: 'FAQ',
    items: [
      { text: 'Common Questions', link: '/en/faq/' },
      { text: 'Troubleshooting', link: '/en/faq/troubleshooting' },
      { text: 'Network Issues', link: '/en/faq/network' },
    ],
  },
  {
    text: 'API Reference',
    items: [
      { text: 'REST API', link: '/en/api/' },
    ],
  },
  {
    text: 'Changelog',
    items: [
      { text: '3.2 Release Notes', link: '/en/changelog/3.2' },
      { text: '3.1 Release Notes', link: '/en/changelog/3.1' },
      { text: '3.0 Release Notes', link: '/en/changelog/3.0' },
      { text: '2.6 Release Notes', link: '/en/changelog/2.6' },
    ],
  },
  {
    text: 'Developer Guide',
    items: [
      { text: 'Contributing', link: '/en/dev/' },
    ],
  },
]

export default defineConfig({
  title: 'AutoBangumi',
  description: '基于 RSS 的全自动番剧下载与整理工具',
  ...sharedConfig,

  locales: {
    root: {
      label: '简体中文',
      lang: 'zh-CN',
      themeConfig: {
        nav: [
          { text: '关于', link: '/home/' },
          { text: '快速开始', link: '/deploy/quick-start' },
          { text: '常见问题', link: '/faq/' },
          { text: 'API', link: '/api/' },
        ],
        sidebar: zhSidebar,
        editLink: {
          pattern: 'https://github.com/EstrellaXD/Auto_Bangumi/edit/main/docs/:path',
          text: '在 GitHub 上编辑此页',
        },
        footer: {
          message: `AutoBangumi 基于 MIT 许可证发布。(最新版本: ${version})`,
          copyright: 'Copyright © 2021-present @EstrellaXD & AutoBangumi Contributors',
        },
        docFooter: {
          prev: '上一页',
          next: '下一页',
        },
        outline: {
          label: '目录',
        },
        lastUpdated: {
          text: '最后更新于',
        },
        returnToTopLabel: '返回顶部',
        sidebarMenuLabel: '菜单',
        darkModeSwitchLabel: '主题',
        langMenuLabel: '切换语言',
      },
    },
    en: {
      label: 'English',
      lang: 'en-US',
      link: '/en/',
      themeConfig: {
        nav: [
          { text: 'About', link: '/en/home/' },
          { text: 'Quick Start', link: '/en/deploy/quick-start' },
          { text: 'FAQ', link: '/en/faq/' },
          { text: 'API', link: '/en/api/' },
        ],
        sidebar: enSidebar,
        editLink: {
          pattern: 'https://github.com/EstrellaXD/Auto_Bangumi/edit/main/docs/:path',
          text: 'Edit this page on GitHub',
        },
        footer: {
          message: `AutoBangumi is released under the MIT License. (latest: ${version})`,
          copyright: 'Copyright © 2021-present @EstrellaXD & AutoBangumi Contributors',
        },
      },
    },
  },
})
