import { defineConfig } from 'vitepress'

const version = `v3.3.2`

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

// 插件开发文档的页面表：[路径, 中文, English, 日本語]
const pluginPages: [string, string, string, string][] = [
  ['', '概览', 'Overview', '概要'],
  ['/sdk', '获取 SDK', 'Get the SDK', 'SDK の入手'],
  ['/concepts', '核心概念', 'Concepts', '基本概念'],
  ['/config-forms', '配置表单', 'Config forms', '設定フォーム'],
  ['/events', '事件', 'Events', 'イベント'],
  ['/frontend-slots', '前端挂载点', 'Frontend slots', 'フロントエンドスロット'],
  ['/cli', '命令行 ab-plugin', 'The ab-plugin command', 'コマンド ab-plugin'],
  ['/signing', '签名与分发', 'Signing and distribution', '署名と配布'],
  ['/publish', '上架插件', 'List a plugin', 'プラグインの掲載'],
  ['/builtin', '内置插件', 'Built-in plugins', '組み込みプラグイン'],
  ['/examples', '示例插件', 'Example plugins', 'サンプルプラグイン'],
]
const pluginPoints: [string, string, string, string][] = [
  ['downloader', '下载器', 'Downloader', 'ダウンローダー'],
  ['notifier', '通知渠道', 'Notifier', '通知チャンネル'],
  ['llm-provider', 'LLM 提供商', 'LLM provider', 'LLM プロバイダー'],
  ['search-site', '搜索站点', 'Search site', '検索サイト'],
  ['scheduled-task', '定时任务', 'Scheduled task', '定期タスク'],
  ['metadata-provider', '元数据源', 'Metadata provider', 'メタデータソース'],
  ['rename-strategy', '重命名方式', 'Rename strategy', 'リネーム方式'],
  ['media-files', '文件分类', 'Media files', 'ファイル分類'],
  ['conflict-policy', '版本冲突策略', 'Conflict policy', 'バージョン競合ポリシー'],
  ['api-router', 'REST 路由', 'REST routes', 'REST ルート'],
  ['mcp', 'MCP 工具与资源', 'MCP tools and resources', 'MCP ツールとリソース'],
  ['torrent-filter', '种子过滤', 'Torrent filter', 'トレントフィルター'],
  ['title-parsed', '修正解析结果', 'Parsed title', '解析結果の補正'],
  ['torrent-adding', '修改添加请求', 'Adding request', '追加リクエストの変更'],
  ['http-request', '请求头', 'HTTP request', 'HTTP リクエスト'],
  ['message-template', '通知文案模板', 'Message template', '通知メッセージテンプレート'],
]

// lang: 0 中文，1 English，2 日本語
function pluginSidebar(lang: 0 | 1 | 2) {
  const prefix = ['', '/en', '/ja'][lang]
  const label = (row: string[]) => row[lang + 1]
  return [
    ...pluginPages.map((row) => ({
      text: label(row),
      link: `${prefix}/dev/plugins${row[0]}`,
    })),
    {
      text: ['扩展点', 'Extension points', '拡張ポイント'][lang],
      collapsed: true,
      items: pluginPoints.map((row) => ({
        text: label(row),
        link: `${prefix}/dev/plugins/points/${row[0]}`,
      })),
    },
  ]
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
      { text: '从 3.3 升级到 4.0', link: '/deploy/upgrade-4.0' },
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
      { text: '插件设置', link: '/config/plugins' },
      { text: '代理设置', link: '/config/proxy' },
      { text: '网络设置', link: '/config/network' },
      { text: '搜索源设置', link: '/config/search-provider' },
      { text: '播放器设置', link: '/config/player' },
      { text: 'LLM 解析器', link: '/config/llm' },
      { text: 'Passkey 设置', link: '/config/passkey' },
      { text: '安全设置', link: '/config/security' },
      { text: '软件更新', link: '/config/update' },
    ],
  },
  {
    text: '功能',
    items: [
      { text: 'RSS 管理', link: '/feature/rss' },
      { text: '番剧管理', link: '/feature/bangumi' },
      { text: '日历视图', link: '/feature/calendar' },
      { text: '文件重命名', link: '/feature/rename' },
      { text: '插件', link: '/feature/plugins' },
      { text: '多下载器', link: '/feature/downloaders' },
      { text: '硬链接到媒体库', link: '/feature/hardlink' },
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
      { text: '4.0 版本说明', link: '/changelog/4.0' },
      { text: '3.3 版本说明', link: '/changelog/3.3' },
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
      { text: '数据库开发指南', link: '/dev/database' },
      { text: 'E2E 测试指南', link: '/dev/e2e-test-guide' },
    ],
  },
  { text: '插件开发', items: pluginSidebar(0) },
]

// Japanese sidebar
const jaSidebar = [
  {
    items: [
      { text: '概要', link: '/ja/home/' },
      { text: 'クイックスタート', link: '/ja/deploy/quick-start' },
      { text: '仕組み', link: '/ja/home/pipline' },
    ],
  },
  {
    text: 'デプロイ',
    items: [
      { text: 'Docker CLI', link: '/ja/deploy/docker-cli' },
      { text: 'Docker Compose', link: '/ja/deploy/docker-compose' },
      { text: 'Synology NAS (DSM)', link: '/ja/deploy/dsm' },
      { text: 'ローカルデプロイ', link: '/ja/deploy/local' },
      { text: '3.3 から 4.0 へのアップグレード', link: '/ja/deploy/upgrade-4.0' },
    ],
  },
  {
    text: '設定',
    items: [
      { text: 'RSS購読設定', link: '/ja/config/rss' },
      { text: 'プログラム設定', link: '/ja/config/program' },
      { text: 'ダウンローダー設定', link: '/ja/config/downloader' },
      { text: 'パーサー設定', link: '/ja/config/parser' },
      { text: '通知設定', link: '/ja/config/notifier' },
      { text: 'アニメ管理設定', link: '/ja/config/manager' },
      { text: 'プラグイン設定', link: '/ja/config/plugins' },
      { text: 'プロキシ設定', link: '/ja/config/proxy' },
      { text: 'ネットワーク設定', link: '/ja/config/network' },
      { text: '検索プロバイダー設定', link: '/ja/config/search-provider' },
      { text: 'プレイヤー設定', link: '/ja/config/player' },
      { text: 'LLMパーサー', link: '/ja/config/llm' },
      { text: 'Passkey設定', link: '/ja/config/passkey' },
      { text: 'セキュリティ設定', link: '/ja/config/security' },
      { text: 'ソフトウェア更新', link: '/ja/config/update' },
    ],
  },
  {
    text: '機能',
    items: [
      { text: 'RSS管理', link: '/ja/feature/rss' },
      { text: 'アニメ管理', link: '/ja/feature/bangumi' },
      { text: 'カレンダー表示', link: '/ja/feature/calendar' },
      { text: 'ファイルリネーム', link: '/ja/feature/rename' },
      { text: 'プラグイン', link: '/ja/feature/plugins' },
      { text: '複数のダウンローダー', link: '/ja/feature/downloaders' },
      { text: 'メディアライブラリへのハードリンク', link: '/ja/feature/hardlink' },
      { text: 'トレント検索', link: '/ja/feature/search' },
    ],
  },
  {
    text: 'FAQ',
    items: [
      { text: 'よくある質問', link: '/ja/faq/' },
      { text: 'トラブルシューティング', link: '/ja/faq/troubleshooting' },
      { text: 'ネットワーク問題', link: '/ja/faq/network' },
    ],
  },
  {
    text: 'APIリファレンス',
    items: [
      { text: 'REST API', link: '/ja/api/' },
    ],
  },
  {
    text: '更新履歴',
    items: [
      { text: '4.0 リリースノート', link: '/ja/changelog/4.0' },
      { text: '3.3 リリースノート', link: '/ja/changelog/3.3' },
      { text: '3.2 リリースノート', link: '/ja/changelog/3.2' },
      { text: '3.1 リリースノート', link: '/ja/changelog/3.1' },
      { text: '3.0 リリースノート', link: '/ja/changelog/3.0' },
      { text: '2.6 リリースノート', link: '/ja/changelog/2.6' },
    ],
  },
  {
    text: '開発者ガイド',
    items: [
      { text: 'コントリビュート', link: '/ja/dev/' },
      { text: 'データベース開発ガイド', link: '/ja/dev/database' },
      { text: 'E2E テストガイド', link: '/ja/dev/e2e-test-guide' },
    ],
  },
  { text: 'プラグイン開発', items: pluginSidebar(2) },
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
      { text: 'Upgrade from 3.3 to 4.0', link: '/en/deploy/upgrade-4.0' },
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
      { text: 'Plugin Settings', link: '/en/config/plugins' },
      { text: 'Proxy Settings', link: '/en/config/proxy' },
      { text: 'Network Settings', link: '/en/config/network' },
      { text: 'Search Providers', link: '/en/config/search-provider' },
      { text: 'Player Settings', link: '/en/config/player' },
      { text: 'LLM Parser', link: '/en/config/llm' },
      { text: 'Passkey Settings', link: '/en/config/passkey' },
      { text: 'Security Settings', link: '/en/config/security' },
      { text: 'Software Update', link: '/en/config/update' },
    ],
  },
  {
    text: 'Features',
    items: [
      { text: 'RSS Management', link: '/en/feature/rss' },
      { text: 'Bangumi Management', link: '/en/feature/bangumi' },
      { text: 'Calendar View', link: '/en/feature/calendar' },
      { text: 'File Renaming', link: '/en/feature/rename' },
      { text: 'Plugins', link: '/en/feature/plugins' },
      { text: 'Multiple Downloaders', link: '/en/feature/downloaders' },
      { text: 'Hard Links to a Media Library', link: '/en/feature/hardlink' },
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
      { text: '4.0 Release Notes', link: '/en/changelog/4.0' },
      { text: '3.3 Release Notes', link: '/en/changelog/3.3' },
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
      { text: 'Database guide', link: '/en/dev/database' },
      { text: 'E2E test guide', link: '/en/dev/e2e-test-guide' },
    ],
  },
  { text: 'Plugin Development', items: pluginSidebar(1) },
]

export default defineConfig({
  lang: 'zh-CN',
  srcExclude: ['plans/**', 'superpowers/**', '**/README.md', '**/node_modules/**'],
  sitemap: { hostname: 'https://www.autobangumi.org' },
  title: 'AutoBangumi',
  description: '基于 RSS 的全自动番剧下载与整理工具',
  ...sharedConfig,

  locales: {
    root: {
      label: '简体中文',
      lang: 'zh-CN',
      link: '/',
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
      description: 'An RSS-based automatic anime downloading and organization tool',
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
        docFooter: {
          prev: 'Previous page',
          next: 'Next page',
        },
        outline: {
          label: 'On this page',
        },
        lastUpdated: {
          text: 'Last updated',
        },
        returnToTopLabel: 'Return to top',
        sidebarMenuLabel: 'Menu',
        darkModeSwitchLabel: 'Theme',
        langMenuLabel: 'Change language',
      },
    },
    ja: {
      label: '日本語',
      lang: 'ja-JP',
      link: '/ja/',
      description: 'RSSベースの全自動アニメダウンロード・整理ツール',
      themeConfig: {
        nav: [
          { text: '概要', link: '/ja/home/' },
          { text: 'クイックスタート', link: '/ja/deploy/quick-start' },
          { text: 'FAQ', link: '/ja/faq/' },
          { text: 'API', link: '/ja/api/' },
        ],
        sidebar: jaSidebar,
        editLink: {
          pattern: 'https://github.com/EstrellaXD/Auto_Bangumi/edit/main/docs/:path',
          text: 'GitHubでこのページを編集',
        },
        footer: {
          message: `AutoBangumiはMITライセンスの下で公開されています。(最新版: ${version})`,
          copyright: 'Copyright © 2021-present @EstrellaXD & AutoBangumi Contributors',
        },
        docFooter: {
          prev: '前のページ',
          next: '次のページ',
        },
        outline: {
          label: '目次',
        },
        lastUpdated: {
          text: '最終更新',
        },
        returnToTopLabel: 'トップに戻る',
        sidebarMenuLabel: 'メニュー',
        darkModeSwitchLabel: 'テーマ',
        langMenuLabel: '言語を切り替え',
      },
    },
  },
})
