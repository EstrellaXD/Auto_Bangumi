import { defineConfig } from "vitepress";


const version = `v3.0`

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "AutoBangumi",
  description: "从 Mikan Project 全自动追番下载整理",

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/image/icons/light-logo.svg' }],
  ],

  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    logo: {
      dark: '/image/icons/dark-logo.svg',
      light: '/image/icons/light-logo.svg',
    },

    editLink: {
      pattern: 'https://github.com/vitejs/vite/blob/3.1-dev/docs/:path',
      text: 'Edit this page',
    },

    search: {
      provider: 'local'
    },

    socialLinks: [
      { icon: "github", link: "https://github.com/EstrellaXD/Auto_Bangumi" },
    ],

    nav: [
      { text: "项目说明", link: "/home/" },
      { text: "快速开始", link: "/deploy/quick-start" },
      { text: "排错流程", link: "/faq/排错流程" },
      { text: "常见问题", link: "/faq/常见问题" },
    ],

    footer: {
      message: `AutoBangumi Released under the MIT License. (latest: ${version})`,
      copyright: 'Copyright © 2021-present @EstrellaXD & AutoBangumi Contributors',
    },

    sidebar: [
      {
        text: "项目说明",
        items: [
          {
            text: "项目说明",
            link: "/home/",
          },
        ],
      },
      {
        text: "部署",
        items: [
          {
            text: "Docker-cli 部署",
            link: "/deploy/docker-cli",
          },
          {
            text: "Docker-Compose 部署",
            link: "/deploy/docker-compose",
          },
          {
            text: "群晖NAS",
            link: "/deploy/dsm",
          },
          {
            text: "WSL",
            link: "/deploy/wsl",
          },
        ],
      },
      {
        text: "源码运行",
        items: [
          {
            text: "Windows 本地部署",
            link: "/deploy/windows",
          },
          {
            text: "Unix 本地部署",
            link: "/deploy/unix",
          },
        ],
      },
      {
        text: "配置说明",
        items: [
            {
                text: "获取 RSS 订阅链接",
                link: "/config/rss",
            },
            {
              text: "主程序配置",
              link: "/config/program",
            },
            {
                text: "下载器配置",
                link: "/config/downloader",
            },
            {
                text: "解析器配置",
                link: "/config/parser",
            },
            {
                text: "推送器配置",
                link: "/config/notifier",
            },
            {
                text: "代理配置",
                link: "/config/proxy",
            }
            ]
      },
      {
        text: "FAQ",
        items: [
          {
            text: "排错流程",
            link: "/faq/排错流程",
          },
          {
            text: "常见问题",
            link: "/faq/常见问题",
          },
        ],
      },
      {
        text: "更新日志",
        items: [
          {
            text: "3.0 更新说明",
            link: "/changelog/3.0",
          },
          {
            text: "2.6 更新日志",
            link: "/changelog/2.6",
          },
        ],
      },
    ],
  },
});
