# 贡献指南

我们欢迎贡献者帮助改进 AutoBangumi，更好地解决用户遇到的问题。

本指南将引导您了解如何向 AutoBangumi 贡献代码。请在提交 Pull Request 之前花几分钟阅读。

本文涵盖：

- [项目路线图](#项目路线图)
  - [征求意见稿 (RFC)](#征求意见稿-rfc)
- [Git 分支管理](#git-分支管理)
  - [版本号规则](#版本号规则)
  - [分支开发，主干发布](#分支开发主干发布)
  - [分支生命周期](#分支生命周期)
  - [Git 工作流程概述](#git-工作流程概述)
- [Pull Request](#pull-request)
- [发布流程](#发布流程)


## 项目路线图

AutoBangumi 开发团队使用 [GitHub Project](https://github.com/EstrellaXD/Auto_Bangumi/projects?query=is%3Aopen) 看板来管理计划中的开发、正在进行的修复及其进度。

这可以帮助您了解：
- 开发团队正在做什么
- 哪些内容与您想要的贡献一致，以便您直接参与
- 哪些工作已经在进行中，避免重复工作

在 [Project](https://github.com/EstrellaXD/Auto_Bangumi/projects?query=is%3Aopen) 中，除了常见的 `[Feature Request]`、`[BUG]` 和小改进外，您还会看到 **`[RFC]`** 条目。

### 征求意见稿 (RFC)

> 通过 issues 中的 `RFC` 标签查找现有的 [AutoBangumi RFC](https://github.com/EstrellaXD/Auto_Bangumi/issues?q=is%3Aissue+label%3ARFC)。

对于小改进或 bug 修复，可以直接调整代码并提交 Pull Request。只需阅读[分支管理](#git-分支管理)部分以确保基于正确的分支进行工作，以及 [Pull Request](#pull-request) 部分了解 PR 如何被合并。

<br/>

对于涉及范围较广的**较大**功能重构，请首先通过 [Issue: Feature Proposal](https://github.com/EstrellaXD/Auto_Bangumi/issues/new?assignees=&labels=RFC&projects=&template=rfc.yml&title=%5BRFC%5D%3A+) 编写 RFC 提案，简要描述您的方法并寻求开发者讨论和共识。

某些提案可能与开发团队已经做出的决定冲突，此步骤有助于避免浪费精力。

> 如果您只是想讨论是否添加或改进某个功能（而不是"如何实现"），请使用 -> [Issue: Feature Request](https://github.com/EstrellaXD/Auto_Bangumi/issues/new?labels=feature+request&template=feature_request.yml&title=%5BFeature+Request%5D+)


<br/>

[RFC 提案](https://github.com/EstrellaXD/Auto_Bangumi/issues?q=is%3Aissue+is%3Aopen+label%3ARFC)是**"在功能/重构的具体开发之前，供开发者审查技术设计/方法的文档"**。

其目的是确保协作的开发者清楚地知道"要做什么"和"如何完成"，所有开发者都可以参与公开讨论。

这有助于评估影响（被忽略的考虑因素、向后兼容性、与现有功能的冲突）。

因此，提案重点描述解决问题的**方法、设计和步骤**。


## Git 分支管理

### 版本号规则

AutoBangumi 项目中的 Git 分支与发布版本规则密切相关。

AutoBangumi 遵循[语义化版本控制 (SemVer)](https://semver.org/)，使用 `<Major>.<Minor>.<Patch>` 格式：

- **Major**：主版本更新，可能包含不兼容的配置/API 变更
- **Minor**：向后兼容的新功能
- **Patch**：向后兼容的 bug 修复/小改进

### 分支开发，主干发布

AutoBangumi 使用"分支开发，主干发布"模式。

[**`main`**](https://github.com/EstrellaXD/Auto_Bangumi/commits/main) 是稳定的**主干分支**，仅用于发布，不直接用于开发。

每个 Minor 版本都有对应的**开发分支**，用于新功能和发布后的维护。

开发分支命名为 `<Major>.<Minor>-dev`，例如 `3.1-dev`、`3.0-dev`、`2.6-dev`。在[所有分支](https://github.com/EstrellaXD/Auto_Bangumi/branches/all?query=-dev)中查找它们。


### 分支生命周期

当一个 Minor 开发分支（如 `3.1-dev`）完成功能开发并**首次**合并到 main 时：
- 发布 Minor 版本（如 `3.1.0`）
- 创建**下一个** Minor 开发分支（`3.2-dev`）用于下个版本的功能
  - **上一个**版本的分支（`3.0-dev`）将被归档
- 当前 Minor 分支（`3.1-dev`）进入维护期——不再添加新功能/重构，只修复 bug
  - Bug 修复先合并到维护分支，然后合并到 main 进行 `Patch` 发布

对于选择 Git 分支的贡献者：
- **Bug 修复** — 基于**当前已发布版本**的 Minor 分支，向该分支提交 PR
- **新功能/重构** — 基于**下一个未发布版本**的 Minor 分支，向该分支提交 PR

> "当前已发布版本"是 [[Releases 页面]](https://github.com/EstrellaXD/Auto_Bangumi/releases) 上的最新版本


### Git 工作流程概述

> 提交时间线从左到右 --->

![dev-branch](../image/dev/branch.png)


## Pull Request

请确保按照上述 Git 分支管理部分选择正确的 PR 目标分支：
> - **Bug 修复** → 向**当前已发布版本**的 Minor 维护分支提交 PR
> - **新功能/重构** → 向**下一版本**的 Minor 开发分支提交 PR

<br/>

- 一个 PR 应该对应单一关注点，不要引入无关的更改。

  将不同的关注点拆分为多个 PR，以帮助团队在每次审查中专注于一个问题。

- 在 PR 标题和描述中，简要说明更改内容，包括原因和意图。

  在 PR 描述中链接相关的 issues 或 RFC。

  这有助于团队在代码审查时快速了解上下文。

- 确保勾选"允许维护者编辑"。这允许直接进行小的编辑/重构，节省时间。

- 确保本地测试和代码检查通过。这些也会在 PR CI 中检查。
  - 对于 bug 修复和新功能，团队可能会要求相应的单元测试覆盖。


开发团队将尽快审查贡献者的 PR，进行讨论或批准合并。

## 发布流程

目前，发布是在开发团队手动合并特定的"发布 PR"后自动触发的。

Bug 修复 PR 通常会快速发布，一般在一周内。

新功能发布需要更长时间，时间不太可预测。查看 [GitHub Project](https://github.com/EstrellaXD/Auto_Bangumi/projects?query=is%3Aopen) 看板了解开发进度——当所有计划功能完成时发布版本。
