# HustCA Mainpage

计算机协会主页的 Hugo 静态站点仓库，保存主页源码、主题配置、已构建的静态文件，以及服务器使用的 Docker Compose 部署配置与脚本。

> **当前主页仍是 Gentoo 主题的模板／示例状态，不是内容已经完善的计协正式官网。**

## 当前状态

- 使用 [gentoozh-theme](https://github.com/Gentoo-zh/gentoozh-theme) `v0.3.23`，在 Hextra 之上提供 Gentoo 风格、Bento 首页及文章／贡献者页面模板。当前锁定的 Hextra 版本为 `v0.13.0`。
- 首页使用主题原生 `home-bento` 短代码，不放站点级自定义布局或 CSS 来覆盖主题。
- 首页中的「Gentoo 中文社区」、社区链接、示例入口与运行天数来自上游示例，**不代表计协的正式介绍、服务或成立时间**，需要由维护者自行替换。
- 计协的 Logo、导航菜单、栏目和正式内容尚未配置完成。部分示例站内链接没有对应页面；Blog／文章和贡献者栏目尚未建立，现有 `content/docs/_index.md` 仍是草稿。
- 引入主题不等于复制 Gentoo 官网整站：菜单、图片、文章和人物资料属于站点内容，需要另外配置；首页的最新文章与贡献者区块会在有对应已发布内容时显示。

主页域名为 `hustca.cn`，当前临时 HTTPS 入口为 [https://hustca.cn:404/](https://hustca.cn:404/)。入口可访问不表示内容已正式发布，也不表示备案要求已满足。

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `hugo.yaml` | 域名、语言、主题导入和页面参数 |
| `go.mod`、`go.sum` | Hugo Module 依赖及版本锁定 |
| `content/` | 首页与各栏目 Markdown 内容 |
| `archetypes/` | 新内容的默认前置元数据 |
| `assets/`、`static/` | 站点资源与原样发布的静态文件 |
| `layouts/`、`i18n/`、`data/` | 站点级模板、翻译与数据扩展位置；主题主体通过模块引入 |
| `public/` | 已构建的静态站点，当前纳入 Git 版本管理 |
| `deploy/` | 非敏感编排配置、Caddy 配置、镜像定义及发布脚本 |

Touranki 的游戏源码不在本仓库：分别由 [touranki-web](https://github.com/HustCAteam/touranki-web)、[touranki-server](https://github.com/HustCAteam/touranki-server) 与 [touranki-core](https://github.com/HustCAteam/touranki-core) 管理。`deploy/` 中包含主页与 Touranki 共享的服务器部署配置。

## 本地预览与构建

需要 Go `1.26.3` 或更高版本，以及 Hugo extended；当前站点已使用 Hugo extended `0.154.5` 构建。首次运行会拉取锁定的主题模块。

在仓库根目录执行：

```bash
# 本地预览，默认地址为 http://localhost:1313/
hugo server

# 生产构建，输出到 public/
hugo --environment production --minify
```

编辑首页从 `content/_index.md` 开始；站点参数在 `hugo.yaml` 中配置。新增文章栏目时可使用 `content/posts/_index.md` 并设置 `type: blog`；导航菜单需要另行添加。`draft: true` 的内容默认不进入生产构建。

## 版本管理与发布

修改主页源码后，需要重新构建 `public/`，将源码和对应静态产物一起提交、推送 GitHub。**单纯推送源码不会自动重新生成或部署网站。**

- `deploy/scripts/stage-mainpage.sh` 只读取远端主页仓库已提交 HEAD 中的 `public/`，不自动运行 Hugo，也不使用本机旧副本覆盖远端源码。
- `deploy/scripts/deploy.sh` 是主页与 Touranki 的完整发布入口，需要预先配置构建工具、Docker 与密钥 SSH；它不是通用的一键安装脚本。
- 完整发布会同步编排配置并更新服务，可能重建 Touranki 后端。后端房间、会话与对局保存在内存中，重建会丢失这些状态；仅修改主页时，不应未经核对就执行完整发布。
- 服务器当前运行目录为 `/root/cateam`，配置的版本化副本在本仓库 `deploy/`。修改运行配置后，应同步版本化副本并提交，避免运行状态与 Git 记录分叉。
- 密码、私钥、面板凭据和其他秘密不得提交到仓库。

主题与首页示例分别来自 [Gentoo 主题仓库](https://github.com/Gentoo-zh/gentoozh-theme)和 [Gentoo 官网源码](https://github.com/Gentoo-zh/gentoo-zh.github.io)。使用或改写上游资源时，应遵守其原有许可证并保留必要署名。
