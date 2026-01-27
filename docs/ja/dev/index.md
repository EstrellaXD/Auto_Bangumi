# コントリビューションガイド

AutoBangumiをより良くするためにユーザーが遭遇する問題を解決する手助けをしていただけるコントリビューターを歓迎します。

このガイドでは、AutoBangumiにコードをコントリビュートする方法を説明します。Pull Requestを提出する前に数分間お読みください。

この記事では以下を扱います：

- [プロジェクトロードマップ](#プロジェクトロードマップ)
  - [Request for Comments (RFC)](#request-for-comments-rfc)
- [Gitブランチ管理](#gitブランチ管理)
  - [バージョン番号](#バージョン番号)
  - [ブランチ開発、トランクリリース](#ブランチ開発トランクリリース)
  - [ブランチライフサイクル](#ブランチライフサイクル)
  - [Gitワークフローの概要](#gitワークフローの概要)
- [Pull Request](#pull-request)
- [リリースプロセス](#リリースプロセス)


## プロジェクトロードマップ

AutoBangumi開発チームは[GitHub Project](https://github.com/EstrellaXD/Auto_Bangumi/projects?query=is%3Aopen)ボードを使用して、計画された開発、進行中の修正、およびその進捗を管理しています。

これにより以下を理解できます：
- 開発チームが取り組んでいること
- あなたの意図するコントリビューションに合致するものがあり、直接参加できること
- すでに進行中のものがあり、重複作業を避けられること

[Project](https://github.com/EstrellaXD/Auto_Bangumi/projects?query=is%3Aopen)では、通常の`[Feature Request]`、`[BUG]`、小さな改善に加えて、**`[RFC]`**アイテムがあります。

### Request for Comments (RFC)

> issuesの`RFC`ラベルを介して既存の[AutoBangumi RFC](https://github.com/EstrellaXD/Auto_Bangumi/issues?q=is%3Aissue+label%3ARFC)を見つけてください。

小さな改善やバグ修正については、コードを調整してPull Requestを提出してください。[ブランチ管理](#gitブランチ管理)セクションを読んで正しいブランチに基づいて作業し、[Pull Request](#pull-request)セクションでPRがどのようにマージされるかを理解してください。

<br/>

広範囲にわたる**大きな**機能リファクタリングについては、まず[Issue: Feature Proposal](https://github.com/EstrellaXD/Auto_Bangumi/issues/new?assignees=&labels=RFC&projects=&template=rfc.yml&title=%5BRFC%5D%3A+)を介してRFC提案を書き、アプローチを簡潔に説明し、開発者の議論とコンセンサスを求めてください。

一部の提案は開発チームがすでに行った決定と競合する可能性があり、このステップは無駄な努力を避けるのに役立ちます。

> 機能を追加または改善するかどうか（「実装方法」ではなく）について議論したい場合は -> [Issue: Feature Request](https://github.com/EstrellaXD/Auto_Bangumi/issues/new?labels=feature+request&template=feature_request.yml&title=%5BFeature+Request%5D+)を使用してください


<br/>

[RFC提案](https://github.com/EstrellaXD/Auto_Bangumi/issues?q=is%3Aissue+is%3Aopen+label%3ARFC)は**「機能/リファクタリングの具体的な開発前に開発者が技術設計/アプローチをレビューするためのドキュメント」**です。

目的は、協力する開発者が「何をするか」と「どのように行われるか」を明確に知り、すべての開発者がオープンな議論に参加できるようにすることです。

これにより、影響（見落とされた考慮事項、後方互換性、既存機能との競合）を評価できます。

したがって、提案は問題を解決するための**アプローチ、設計、ステップ**の説明に焦点を当てます。


## Gitブランチ管理

### バージョン番号

AutoBangumiプロジェクトのGitブランチは、リリースバージョンルールと密接に関連しています。

AutoBangumiは[セマンティックバージョニング（SemVer）](https://semver.org/)に従い、`<Major>.<Minor>.<Patch>`形式を使用します：

- **Major**：メジャーバージョン更新、互換性のない設定/API変更がある可能性
- **Minor**：後方互換性のある新機能
- **Patch**：後方互換性のあるバグ修正 / 小さな改善

### ブランチ開発、トランクリリース

AutoBangumiは「ブランチ開発、トランクリリース」モデルを使用しています。

[**`main`**](https://github.com/EstrellaXD/Auto_Bangumi/commits/main)は安定した**トランクブランチ**で、リリースにのみ使用され、直接開発には使用されません。

各Minorバージョンには、新機能とリリース後のメンテナンス用の対応する**開発ブランチ**があります。

開発ブランチは`<Major>.<Minor>-dev`という名前で、例：`3.1-dev`、`3.0-dev`、`2.6-dev`。[All Branches](https://github.com/EstrellaXD/Auto_Bangumi/branches/all?query=-dev)で見つけてください。


### ブランチライフサイクル

Minor開発ブランチ（例：`3.1-dev`）が機能開発を完了し、**最初に**mainにマージするとき：
- Minorバージョン（例：`3.1.0`）をリリース
- **次の**Minor開発ブランチ（`3.2-dev`）を次バージョンの機能用に作成
  - **前の**バージョンのブランチ（`3.0-dev`）はアーカイブ
- このMinorブランチ（`3.1-dev`）はメンテナンスに入る — 新機能/リファクタリングなし、バグ修正のみ
  - バグ修正はメンテナンスブランチにマージされ、その後`Patch`リリースのためにmainへ

コントリビューターのGitブランチ選択：
- **バグ修正** — **現在リリースされているバージョンの**Minorブランチに基づき、そのブランチにPR
- **新機能/リファクタリング** — **次の未リリースバージョンの**Minorブランチに基づき、そのブランチにPR

> 「現在リリースされているバージョン」は[[Releases page]](https://github.com/EstrellaXD/Auto_Bangumi/releases)の最新バージョンです


### Gitワークフローの概要

> コミットタイムラインは左から右へ --->

![dev-branch](/image/dev/branch.png)


## Pull Request

上記のGitブランチ管理セクションに従って、正しいPRターゲットブランチを選択していることを確認してください：
> - **バグ修正** → **現在リリースされているバージョンの**Minorメンテナンスブランチに PR
> - **新機能/リファクタリング** → **次バージョンの**Minor開発ブランチに PR

<br/>

- PRは単一の関心事に対応し、無関係な変更を導入しないでください。

  異なる関心事を複数のPRに分割して、チームがレビューごとに1つの問題に集中できるようにしてください。

- PRタイトルと説明で、理由と意図を含めて変更を簡潔に説明してください。

  PR説明に関連するissuesやRFCをリンクしてください。

  これにより、コードレビュー中にチームがコンテキストを素早く理解できます。

- 「メンテナーからの編集を許可」がチェックされていることを確認してください。これにより、小さな編集/リファクタリングを直接行うことができ、時間を節約できます。

- ローカルテストとリンティングがパスすることを確認してください。これらはPR CIでもチェックされます。
  - バグ修正と新機能については、チームが対応するユニットテストカバレッジを要求する場合があります。


開発チームはコントリビューターのPRをレビューし、できるだけ早く議論またはマージを承認します。

## リリースプロセス

リリースは現在、開発チームが特定の「リリースPR」を手動でマージした後に自動的にトリガーされます。

バグ修正PRは通常、迅速にリリースされ、通常は1週間以内です。

新機能リリースはより長くかかり、予測が難しいです。開発進捗については[GitHub Project](https://github.com/EstrellaXD/Auto_Bangumi/projects?query=is%3Aopen)ボードを確認してください — すべての計画された機能が完了するとバージョンがリリースされます。
