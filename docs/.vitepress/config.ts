import { defineConfig } from 'vitepress'

const version = `v3.2`

export default defineConfig({
  title: 'AutoBangumi',
  description: 'Automatic anime downloading and organization from RSS feeds',

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/light-logo.svg' }],
    ['meta', { property: 'og:image', content: '/social.png' }],
    ['meta', { property: 'og:site_name', content: 'AutoBangumi' }],
    ['meta', { property: 'og:url', content: 'https://www.autobangumi.org' }],
    ['script', { async: '', src: 'https://www.googletagmanager.com/gtag/js?id=G-3Z8W6WMN7J' }],
    ['script', {}, `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-3Z8W6WMN7J');`],
  ],

  themeConfig: {
    logo: {
      dark: '/dark-logo.svg',
      light: '/light-logo.svg',
    },

    editLink: {
      pattern: 'https://github.com/EstrellaXD/Auto_Bangumi/edit/main/docs/:path',
      text: 'Edit this page on GitHub',
    },

    search: {
      provider: 'local',
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

    nav: [
      { text: 'About', link: '/home/' },
      { text: 'Quick Start', link: '/deploy/quick-start' },
      { text: 'FAQ', link: '/faq/' },
      { text: 'API', link: '/api/' },
    ],

    footer: {
      message: `AutoBangumi is released under the MIT License. (latest: ${version})`,
      copyright: 'Copyright © 2021-present @EstrellaXD & AutoBangumi Contributors',
    },

    sidebar: [
      {
        items: [
          { text: 'About', link: '/home/' },
          { text: 'Quick Start', link: '/deploy/quick-start' },
          { text: 'How It Works', link: '/home/pipline' },
        ],
      },
      {
        text: 'Deployment',
        items: [
          { text: 'Docker CLI', link: '/deploy/docker-cli' },
          { text: 'Docker Compose', link: '/deploy/docker-compose' },
          { text: 'Synology NAS (DSM)', link: '/deploy/dsm' },
          { text: 'Local Deployment', link: '/deploy/local' },
        ],
      },
      {
        text: 'Configuration',
        items: [
          { text: 'RSS Feed Setup', link: '/config/rss' },
          { text: 'Program Settings', link: '/config/program' },
          { text: 'Downloader Settings', link: '/config/downloader' },
          { text: 'Parser Settings', link: '/config/parser' },
          { text: 'Notification Settings', link: '/config/notifier' },
          { text: 'Bangumi Manager', link: '/config/manager' },
          { text: 'Proxy Settings', link: '/config/proxy' },
          { text: 'Experimental Features', link: '/config/experimental' },
        ],
      },
      {
        text: 'Features',
        items: [
          { text: 'RSS Management', link: '/feature/rss' },
          { text: 'Bangumi Management', link: '/feature/bangumi' },
          { text: 'Calendar View', link: '/feature/calendar' },
          { text: 'File Renaming', link: '/feature/rename' },
          { text: 'Torrent Search', link: '/feature/search' },
        ],
      },
      {
        text: 'FAQ',
        items: [
          { text: 'Common Questions', link: '/faq/' },
          { text: 'Troubleshooting', link: '/faq/troubleshooting' },
          { text: 'Network Issues', link: '/faq/network' },
        ],
      },
      {
        text: 'API Reference',
        items: [
          { text: 'REST API', link: '/api/' },
        ],
      },
      {
        text: 'Changelog',
        items: [
          { text: '3.2 Release Notes', link: '/changelog/3.2' },
          { text: '3.1 Release Notes', link: '/changelog/3.1' },
          { text: '3.0 Release Notes', link: '/changelog/3.0' },
          { text: '2.6 Release Notes', link: '/changelog/2.6' },
        ],
      },
      {
        text: 'Developer Guide',
        items: [
          { text: 'Contributing', link: '/dev/' },
        ],
      },
    ],
  },
})
