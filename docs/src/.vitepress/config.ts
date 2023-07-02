import { defineConfig } from "vitepress";

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "Auto_Bangumi",
  description: "A Auto_Bangumi Documents",
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: "Home", link: "/" },
      { text: "开始部署", link: "/deploy/部署说明" },
      { text: "排错流程", link: "/faq/排错流程" },
      { text: "常见问题", link: "/faq/常见问题" },
    ],

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
      {
        text: "部署",
        items: [
          {
            text: "部署前准备",
            link: "/deploy/部署说明",
          },
          {
            text: "Docker-cli 部署",
            link: "/deploy/Docker-cli",
          },
          {
            text: "Docker-Compose 部署",
            link: "/deploy/Docker-compose",
          },
          {
            text: "群晖NAS",
            link: "/deploy/群晖",
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
            link: "/deploy/Windows-本地部署",
          },
          {
            text: "Unix 本地部署",
            link: "/deploy/local-run",
          },
        ],
      },
      {
        text: "使用说明",
        items: [
          {
            text: "使用说明",
            link: "/use/使用说明",
          },
          {
            text: "配置选项说明",
            link: "/use/配置选项说明",
          },
        ],
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
    ],

    socialLinks: [
      { icon: "github", link: "https://github.com/EstrellaXD/Auto_Bangumi" },
    ],
  },
});
