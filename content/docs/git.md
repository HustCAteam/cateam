---
title: "Git：提交一次小修改"
description: "用本站的一处文字修改，认识分支、提交和 Pull Request。"
weight: 10
---

Git 用来记录文件变化，GitHub 则是本项目存放代码和讨论修改的平台。**保存文件不等于提交，提交也不等于推送**：修改先发生在本机，再由你选择记录和分享哪些内容。

## 先认识四个词

| 名称 | 在这次练习中的含义 |
| --- | --- |
| 仓库 | 项目文件与修改历史的集合 |
| 分支 | 一条相对独立的修改线，便于集中处理一个问题 |
| 提交（commit） | 一组文件变化及其说明 |
| Pull Request（PR） | 请求维护者审阅并合并你的分支 |

## 练习：修正一句介绍

下面以没有仓库直接写入权限的贡献者为例，需要已安装 Git，并拥有自己的 GitHub 账号。不需要服务器访问权限。

{{% steps %}}

### 取得自己的副本

打开 [HustCAteam/cateam](https://github.com/HustCAteam/cateam)，通过 GitHub 的 Fork 功能创建个人副本，再在自己的仓库页面复制 HTTPS 克隆地址。

在终端输入 `git clone`，后面跟上刚复制的地址。进入克隆下来的目录，然后建立一个只处理这次修改的分支：

```sh
git switch -c docs/clarify-introduction
```

克隆地址应来自你自己的 Fork，不要把示例用户名当成真实地址。

### 修改一个文件

本站源码根目录中的 `content/about/index.md` 是协会介绍。选一处确实需要改进的文字，保持文件顶部 `---` 包围的配置完整。其他栏目路径见[网站共建指南](/contributing/)。

先查看自己改动了什么：

```sh
git status
git diff -- content/about/index.md
```

`git diff` 显示尚未暂存的差异。确认没有意外文件、私人信息或整篇无关格式变化。

### 选择变化并提交

```sh
git add content/about/index.md
git diff --cached
git commit -m "docs: clarify association introduction"
```

`git add` 将该文件当前的变化放入暂存区，`git diff --cached` 检查本次将记录的内容。提交说明应解释这次做了什么，不必故作复杂。

如果 Git 提示缺少作者身份，在当前仓库用 `git config user.name` 和 `git config user.email` 配置自己的提交信息；邮箱可能公开在提交历史中，可使用 GitHub 账号设置提供的隐私邮箱。不要复制别人的身份。

### 推送并请求审阅

```sh
git push -u origin docs/clarify-introduction
```

到 GitHub 上从自己的分支向原仓库当前默认分支发起 PR，写清楚修改原因、影响页面和信息来源。按仓库说明预览页面，并说明实际做过哪些检查；没做过的不要写成“已通过”。维护者可能会提出修改意见，这正是协作的一部分。

{{% /steps %}}

## 不小心改多了怎么办

先运行 `git status`，再区分“工作区修改”“已暂存”“已提交”。不确定时保留现场并[提问](/docs/asking/)，不要为了清理状态直接使用会丢弃工作的命令。

{{< callout type="warning" >}}
不要提交密码、访问令牌、私钥或私人聊天截图。如果敏感信息已经推送，删除当前文件并不能移除历史中的内容；应尽快撤销或轮换相关凭据，并联系维护者处理，不要继续公开传播。
{{< /callout >}}
