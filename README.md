# HustCA Mainpage

计算机协会主页的 Hugo 静态站点仓库，保存主页源码、主题配置、已构建的静态文件，以及服务器使用的 Docker Compose 部署配置与脚本。

> **当前已是使用真实计协品牌和资料的可浏览主页，不再是 Gentoo 社区示例首页。活动排期和成员档案等未确认内容仍明确标为占位，不能视为正式通知或真实成员名单。**

## 当前状态

- 使用 [gentoozh-theme](https://github.com/Gentoo-zh/gentoozh-theme) `v0.3.23`，在 Hextra 之上提供 Gentoo 风格、Bento 首页及文章／贡献者页面模板。当前锁定的 Hextra 版本为 `v0.13.0`。
- 沿用 Gentoo 原生 Bento 网格、文章卡片、共建方向卡片、文档侧栏和搜索，不重写页面结构；明暗配色采用从计协 Logo 蓝绿主色生成的 Material 3 色板。
- 已有首页、协会介绍、加入与交流、Touranki 项目展台、文章与活动、共学手册、四个共建方向及网站共建指南；文章标签、RSS、手机导航、群号复制和 404 页面均有对应入口。
- 使用本机提供的原版 CA Logo、两张最新招新海报及对应二维码、历史义务维修招牌裁图，以及 Touranki 项目既有背景。来源、裁剪方法和公开范围记录在 `data/materials.yaml`；未发布人脸合照、旧二维码、私人表单或原始 PPT。
- 协会介绍与参与方向依据已有公开资料整理。`content/posts/activity-example/` 是明确标注的活动文案示例；`content/contributors/` 展示软件、硬件、内容设计和活动运营方向，成员档案待补充，不虚构人物或提交次数。
- 首页中的入口来自 `data/home.yaml`，最新文章从 `content/posts/` 读取；QQ 群号为 `1071797934` 与 `695523861`，Telegram 为 [@hustca](https://t.me/hustca)。交流入口集中在 `content/join/index.md`，二维码链接是否继续可用以 QQ 客户端为准。

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

Touranki 的游戏源码不在本仓库：分别由 [touranki-web](https://github.com/HustCAteam/touranki-web)、[touranki-server](https://github.com/HustCAteam/touranki-server) 与 [touranki-core](https://github.com/HustCAteam/touranki-core) 管理。招新密码小游戏由独立的 [password-game](https://github.com/HustCAteam/password-game) 私有仓库管理。`deploy/` 保存这三个站点共享的服务器部署配置，不包含小游戏源码。

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
- 原主题 `assets/css/custom.css` 未覆盖；`assets/css/site.css` 经 `custom/head-end` 加载，承载站点配色、导航适配、媒体尺寸与标题换行。
- 色板使用 Material 官方 `material-color-utilities` 的 Tonal Spot／标准对比度方案：Logo 蓝 `#0ea1d7` 生成主色及中性表面，绿 `#32b76c` 生成辅助色。明暗语义色固化在 CSS 中，浏览器不加载配色库；按钮、标签、搜索弹窗与页面表面共用这些变量。
- 导航 Logo 在 `hugo.yaml` 中设为 `28 × 28`；搜索文字与快捷键保持单行、不参与挤压，低于 `64rem` 时显示带无障碍名称的搜索图标，点击仍打开完整搜索弹窗。
- Hugo Module 版本继续由 `go.mod`、`go.sum` 锁定。主题许可位于 `static/licenses/`；素材没有因此统一改授 MIT 或 CC 许可。

## 版本管理与发布

修改主页源码后，需要重新构建 `public/`，将源码和对应静态产物一起提交、推送 GitHub。**单纯推送源码不会自动重新生成或部署网站。**

- `deploy/scripts/stage-mainpage.sh` 只读取远端主页仓库已提交 HEAD 中的 `public/`，不自动运行 Hugo，也不使用本机旧副本覆盖远端源码。
- `deploy/scripts/deploy.sh` 是主页、Touranki 与招新密码小游戏的完整发布入口，需要预先配置构建工具、Docker 与密钥 SSH，并准备三个项目的远端源码仓库；它不是通用的一键安装脚本。
- 完整发布会同步编排配置并更新服务，可能重建 Touranki 后端。后端房间、会话与对局保存在内存中，重建会丢失这些状态；仅修改主页时，不应未经核对就执行完整发布。
- 服务器当前运行目录为 `/root/cateam`，配置的版本化副本在本仓库 `deploy/`。修改运行配置后，应同步版本化副本并提交，避免运行状态与 Git 记录分叉。
- Caddy 的 `hustca.cn` 站点错误处理会以原 404 状态返回 `public/404.html`；不改 Touranki 路由及现有 404／443 端口映射。
- 密码、私钥、面板凭据和其他秘密不得提交到仓库。

### 招新小游戏：喻家山密码挑战

- 入口为 [https://pg.hustca.cn:404/](https://pg.hustca.cn:404/)，DNS A 记录指向 `121.40.128.93`。404 端口直接提供 HTTPS 页面，不是跳转到 80 端口；备案及后续端口调整仍由服务器维护者处理。
- 总共 **10 条规则**，逐步解锁、持续复查，包含 `1037`、`绝望坡`、小写 `cateam`，以及长度、数字、大写、半角标点、数字和、英文月份与罗马数字乘积。全部同时满足后才能提交；没有隐藏的第十一关。
- 前端使用原生 HTML/CSS/ES Module，服务端使用 Node.js 24+ 与内置 SQLite，不依赖 Hugo，也不复刻 Gentoo 模板。复用计协 Logo 与蓝绿 Material 配色，适配手机和系统暗色模式；灵感来自 [The Password Game](https://neal.fun/password-game/)，不是原作官方版本。
- 普通游玩、通关和勾选同意都不会上传输入。只有通关后明确勾选公开同意，再点击「公开分享」，完整游戏密码才会上传、保存并向所有访客公开；页面禁止使用真实密码或个人信息。刷新和重新开始只清空本地游戏，不删除公开记录；当前没有玩家自助撤回接口。通关后仍提供招新页与 [Telegram 社群](https://t.me/hustca) 入口。
- 「公开解法」默认折叠并标明剧透，访客无需通关即可主动展开查看；支持刷新、每页 12 条的游标分页、空列表及失败重试。密码仅作为文字渲染，不执行其中的 HTML。
- 浏览器需要支持 `Intl.Segmenter`；汉字和完整表情按用户感知的字符计数。开发需要 Node.js 24+，无 npm 依赖；在 **password-game 仓库**运行 `npm test`、`npm run build`，再用 `npm run preview` 在 `http://127.0.0.1:18405/` 预览真实页面与 API。本地数据在被 Git 和 Docker 构建忽略的 `.data/shares.sqlite`。
- 前后端共同使用 `src/rules.js` 判定十条规则，避免浏览器伪造通关结果；交互在 `src/app.js`、`src/shares.js`，共享分享限制在 `src/share-policy.js`，HTTP/SQLite 服务在 `server/`。`scripts/build.mjs` 只复制必要前端文件到 `public/`；测试、数据库、服务端源码及 Git 文件不对外提供，构建产物不纳入小游戏 Git 仓库。

服务器源码在 `/root/password-game`，生产前端和 API 一同构建进 `cateam/password-game:local` 镜像。Compose 的 `password-game` 服务以非 root 用户运行，只读根文件系统，**不新增宿主机端口**；现有网关通过 Compose 内网反向代理，复用 404／443 端口。静态页面使用 `no-cache`，API 使用 `no-store`；CSP 仅允许同源连接，仍禁止表单外送。Caddy 覆盖 `X-Game-Client-IP`，服务端仅在启用 `TRUST_PROXY=1` 时信任该值，避免客户端伪造限流来源。

分享数据位于命名卷 `cateam_password_game_data` 内的 `/data/shares.sqlite`，开启 WAL 与同步持久化；重启或更换容器不清空记录。**不要执行 `docker compose down -v`，不要将数据库或 WAL 文件提交到 Git 或放进 `public/`。** 备份应使用 SQLite 备份接口，或只停止小游戏后备份完整数据卷，不能只复制运行中的主数据库文件而忽略 WAL。需要移除公开内容时，由服务器维护者在数据库中按记录 ID 处理。

`POST /api/shares` 只接受本站来源、JSON 和显式 `consent: true`，并重新检查全部十条规则；完全相同的密码去重。公开分享另限 256 个字符、4096 个 UTF-8 字节，请求体最多 16 KiB；这些限制不影响原有十条规则通关。每个客户端每分钟最多 60 次提交尝试，限流地址只保存在有界内存中，不写入数据库；最多保存 10000 条记录，满后拒绝新增但仍可浏览、识别重复，不静默删除旧记录。`GET /api/shares` 支持 `before` 游标，`GET /healthz` 检查服务和数据库可读性。

小游戏源码修改后先提交、推送 GitHub，并将对应提交同步至服务器源码仓库。SSH 与 GitHub 各自需要有效的密钥或认证；发布脚本不保存 GitHub 凭据，也不自动执行 `git pull`。在具有 Docker、`rsync` 和密钥 SSH 的部署工作机上运行：

```bash
# 在本仓库运行；默认 SSH 别名为 cateam
bash deploy/scripts/deploy-password-game.sh
```

该脚本通过 `build-password-game.sh` 归档服务器**已提交 HEAD**，使用锁定摘要的 Node 24 Alpine 基础镜像在工作机构建完整镜像，再通过 SSH 传给服务器；不发布未提交改动，也不依赖服务器访问 Docker Hub。它只更新小游戏容器、保留 SQLite 数据卷，验证并热加载 Caddy，不重建网关或 Touranki 后端。仅更新小游戏时，不要改用完整 `deploy.sh`。

如 SSH 不可达，可通过已经固定证书身份的 Portainer Docker API 传输 Git bundle、已构建镜像及这份版本化配置，再执行同样的限定操作：`docker compose --project-directory /root/cateam up -d --no-deps --no-build --pull never --wait password-game`，随后在 `gateway` 内运行 `caddy validate` 和 `caddy reload`。先确保源码与镜像来自同一提交；临时维护容器用后删除，凭据不得写入仓库。旧的宿主机 `/root/password-game/public` 静态挂载已退出生产发布流程。

主题与首页示例分别来自 [Gentoo 主题仓库](https://github.com/Gentoo-zh/gentoozh-theme)和 [Gentoo 官网源码](https://github.com/Gentoo-zh/gentoo-zh.github.io)。使用或改写上游资源时，应遵守其原有许可证并保留必要署名。
