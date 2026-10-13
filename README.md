# HustCA Mainpage

计算机协会主页的 Hugo 静态站点仓库，保存主页源码、主题配置、已构建的静态文件，以及服务器使用的 Docker Compose 部署配置与脚本。

> **当前已是使用真实计协品牌和资料的可浏览主页，不再是 Gentoo 社区示例首页。活动排期和成员档案等未确认内容仍明确标为占位，不能视为正式通知或真实成员名单。**

## 当前状态

- 使用 [gentoozh-theme](https://github.com/Gentoo-zh/gentoozh-theme) `v0.3.23`，在 Hextra 之上提供 Gentoo 风格、Bento 首页及文章／贡献者页面模板。当前锁定的 Hextra 版本为 `v0.13.0`。
- 沿用 Gentoo 原生 Bento 网格、文章卡片、共建方向卡片、文档侧栏、搜索与深浅色模式，不重写主题配色和整套布局。
- 已有首页、协会介绍、加入与交流、Touranki 项目展台、文章与活动、共学手册、四个共建方向及网站共建指南；文章标签、RSS、手机导航、群号复制和 404 页面均有对应入口。
- 使用本机提供的原版 CA Logo、两张最新招新海报及对应二维码、历史义务维修招牌裁图，以及 Touranki 项目既有背景。来源、裁剪方法和公开范围记录在 `data/materials.yaml`；未发布人脸合照、旧二维码、私人表单或原始 PPT。
- 协会介绍与参与方向依据已有公开资料整理。`content/posts/activity-example/` 是明确标注的活动文案示例；`content/contributors/` 展示软件、硬件、内容设计和活动运营方向，成员档案待补充，不虚构人物或提交次数。
- 首页中的入口来自 `data/home.yaml`，最新文章从 `content/posts/` 读取；群号为 `1071797934` 与 `695523861`，二维码链接是否继续可用以 QQ 客户端为准。

主页域名为 `hustca.cn`，当前临时 HTTPS 入口为 [https://hustca.cn:404/](https://hustca.cn:404/)。入口可访问不表示占位内容已获确认，也不表示备案要求已满足。

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `hugo.yaml` | 域名、语言、主题导入和页面参数 |
| `go.mod`、`go.sum` | Hugo Module 依赖及版本锁定 |
| `content/` | 首页与各栏目 Markdown 内容 |
| `archetypes/` | 新内容的默认前置元数据 |
| `assets/`、`static/` | 站点资源与原样发布的静态文件 |
| `layouts/`、`i18n/` | 主题允许的站点级适配与翻译，不修改下载的模块文件 |
| `data/home.yaml` | 首页入口、社区链接、素材卡片与共建方向 |
| `data/materials.yaml` | 素材来源、处理记录、使用限制及未发布材料说明 |
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

编辑首页文案从 `content/_index.md` 开始，入口配置在 `data/home.yaml`；菜单、Logo、搜索等参数在 `hugo.yaml`。文章放在 `content/posts/<slug>/index.md`，栏目已经设置 `type: blog`；共学手册在 `content/docs/`，方向档案在 `content/contributors/`。正式活动确认前，保留标题、摘要与正文中的占位标记。`draft: true` 的内容默认不进入生产构建。

### 主题适配边界

- `layouts/shortcodes/home-bento.html` 保留原生 Bento 类名，改用计协数据，去掉 Gentoo 专属的固定社交链接与运行天数。
- `layouts/contributors/list.html` 复用原生卡片，展示参与方向，不套用上游由权重推算提交次数的逻辑。
- `layouts/_partials/` 通过主题扩展点替换站点身份、图标、元信息与页脚；`layouts/404.html` 沿用主题错误页样式。
- 原主题 `assets/css/custom.css` 未覆盖；`assets/css/site.css` 仅补充本站媒体尺寸与标题换行，经 `custom/head-end` 加载。
- Hugo Module 版本继续由 `go.mod`、`go.sum` 锁定。主题许可位于 `static/licenses/`；素材没有因此统一改授 MIT 或 CC 许可。

## 版本管理与发布

修改主页源码后，需要重新构建 `public/`，将源码和对应静态产物一起提交、推送 GitHub。**单纯推送源码不会自动重新生成或部署网站。**

- `deploy/scripts/stage-mainpage.sh` 只读取远端主页仓库已提交 HEAD 中的 `public/`，不自动运行 Hugo，也不使用本机旧副本覆盖远端源码。
- `deploy/scripts/deploy.sh` 是主页与 Touranki 的完整发布入口，需要预先配置构建工具、Docker 与密钥 SSH；它不是通用的一键安装脚本。
- 完整发布会同步编排配置并更新服务，可能重建 Touranki 后端。后端房间、会话与对局保存在内存中，重建会丢失这些状态；仅修改主页时，不应未经核对就执行完整发布。
- 服务器当前运行目录为 `/root/cateam`，配置的版本化副本在本仓库 `deploy/`。修改运行配置后，应同步版本化副本并提交，避免运行状态与 Git 记录分叉。
- Caddy 的 `hustca.cn` 站点错误处理会以原 404 状态返回 `public/404.html`；不改 Touranki 路由及现有 404／443 端口映射。
- 密码、私钥、面板凭据和其他秘密不得提交到仓库。

主题与首页示例分别来自 [Gentoo 主题仓库](https://github.com/Gentoo-zh/gentoozh-theme)和 [Gentoo 官网源码](https://github.com/Gentoo-zh/gentoo-zh.github.io)。使用或改写上游资源时，应遵守其原有许可证并保留必要署名。
