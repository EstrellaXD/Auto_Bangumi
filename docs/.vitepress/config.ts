import {defineConfig} from 'vitepress';


const version = `v3.1`

// https://vitepress.dev/reference/site-config
// @ts-ignore
export default defineConfig({
    title: "AutoBangumi",
    description: "从 Mikan Project 全自动追番下载整理",

    head: [
        ['link', {rel: 'icon', type: 'image/svg+xml', href: '/light-logo.svg'}],
        ['meta', {property: 'og:image', content: '/social.png'}],
        ['meta', {property: 'og:site_name', content: 'AutoBangumi'}],
        ['meta', {property: 'og:url', content: 'https://www.autobangumi.org'}],
        ["script", {src: '/_vercel/insights/script.js'}]
    ],

    themeConfig: {
        // https://vitepress.dev/reference/default-theme-config
        logo: {
            dark: '/dark-logo.svg',
            light: '/light-logo.svg',
        },

        editLink: {
            pattern: 'https://github.com/vitejs/vite/blob/3.1-dev/docs/:path',
            text: 'Edit this page',
        },

        search: {
            provider: 'local'
        },

        socialLinks: [
            {icon: "github", link: "https://github.com/EstrellaXD/Auto_Bangumi"},
            {
                icon: {
                    svg: '<svg xmlns="http://www.w3.org/2000/svg" role="img" viewBox="0 0 24 24"><title>Telegram</title><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>'
                },
                link: "https://t.me/autobangumi"
            },
        ],

        nav: [
            {text: "项目说明", link: "/home/"},
            {text: "快速开始", link: "/deploy/quick-start"},
            {text: "常见问题", link: "/faq/"},
        ],
        footer: {
            message: `AutoBangumi Released under the MIT License. (latest: ${version})`,
            copyright: 'Copyright © 2021-present @EstrellaXD & AutoBangumi Contributors',
        },

        sidebar: [
            {
                items: [
                    {
                        text: "项目说明",
                        link: "/home/",
                    },
                    {
                        text: "快速开始",
                        link: "/deploy/quick-start",
                    },
                    {
                        text: "运行原理",
                        link: "/home/pipline",
                    }
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
                        text: "番剧管理配置",
                        link: "/config/manager",
                    },
                    {
                        text: "代理配置",
                        link: "/config/proxy",
                    }
                ]
            },
            {
                text: "功能说明",
                items: [
                    {
                        text: "RSS 管理",
                        link: "/feature/rss",
                    },
                    {
                        text: "重命名",
                        link: "/feature/rename",
                    },
                    {
                        text: "搜索番组",
                        link: "/feature/search",
                    }
                ]
            },
            {
                text: "FAQ",
                items: [
                    {
                        text: "常见问题",
                        link: "/faq/",
                    },
                    {
                        text: "排错流程",
                        link: "/faq/troubleshooting",
                    },
                    {
                        text: "网络问题",
                        link: "/faq/mikan-network",
                    }
                ],
            },
            {
                text: "更新日志",
                items: [
                    {
                        text: "3.1 更新说明",
                        link: "/changelog/3.1",
                    },
                    {
                        text: "3.0 更新说明",
                        link: "/changelog/3.0",
                    },
                    {
                      text: "2.6 更新说明",
                      link: "/changelog/2.6",
                    },
                ],
            },
            {
                text: "开发者文档",
                items: [
                    {
                        text: "贡献指南",
                        link: "/dev/",
                    },
                ]
            }
        ],
    },
});
