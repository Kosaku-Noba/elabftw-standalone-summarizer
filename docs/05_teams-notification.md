# 05. Teams 通知設定

> 関連ドキュメント: [03_configuration.md](03_configuration.md) | [02_setup.md](02_setup.md) | [06_operations.md](06_operations.md)

## 概要

elabBot は要約完了後に Microsoft Teams チャンネルへ Adaptive Card 形式の通知を送信できます。通知にはノートのタイトル、タグ、AI 要約、eLabFTW へのリンクが含まれます。

## 通知カードの内容

Teams に送信される Adaptive Card には以下の情報が含まれます:

- **タイトル**: 実験ノートのタイトル
- **タグ**: 対象タグの一覧
- **AI 要約**: LLM が生成した構造化要約
- **リンクボタン**: eLabFTW の該当ノートを直接開くボタン

## 設定方法

### 方法 1: 全タグ共通の Webhook（シンプル）

すべての通知を 1 つの Teams チャンネルに送信します。

```bash
TEAMS_WEBHOOK_URL=https://your-org.webhook.office.com/webhookb2/xxx
```

### 方法 2: タグごとに異なる Webhook

タグに応じて異なるチャンネルに通知を振り分けます。

```bash
TEAMS_TAG_MAP=summarize=https://webhook1.example.com,実験ノート=https://webhook2.example.com
```

形式は `タグ名=Webhook URL` のペアをカンマ区切りで指定します。実験ノートに付与されたタグとマッチした Webhook URL に通知が送信されます。

### 通知を無効にする

`TEAMS_WEBHOOK_URL` と `TEAMS_TAG_MAP` のどちらも設定しなければ、Teams 通知は無効になります。eLabFTW へのコメント投稿のみが行われます。

## Webhook URL の取得方法

### Power Automate Workflows（推奨）

Microsoft は従来の Incoming Webhook コネクタを段階的に廃止しており、Power Automate の Workflows を推奨しています。

1. Teams の対象チャンネルで「ワークフロー」を選択
2. 「Webhook 要求を受信したときにチャネルに投稿する」テンプレートを選択
3. 生成された URL をコピーして `TEAMS_WEBHOOK_URL` に設定

### 従来の Incoming Webhook

1. Teams の対象チャンネル → コネクタ → Incoming Webhook
2. 名前とアイコンを設定して作成
3. 生成された URL をコピー

## セットアップウィザードでの設定

[セットアップウィザード](02_setup.md) の Step 4 で Teams 通知を対話的に設定できます。

```
[Step 4/9] Teams 通知設定
  Teams 通知を設定しますか？ [Y/n]: y
  設定方式 (single / tag_map) [single]: single
  Teams Webhook URL: https://your-org.webhook.office.com/xxx
```

`tag_map` を選択した場合は、タグごとに Webhook URL を入力します:

```
  設定方式 (single / tag_map) [single]: tag_map
  タグごとに Webhook URL を入力（空 Enter で終了）
  タグ名（空で終了）: summarize
    summarize の Webhook URL: https://webhook1.example.com
  タグ名（空で終了）: 実験ノート
    実験ノート の Webhook URL: https://webhook2.example.com
  タグ名（空で終了）:
```

## テスト通知

ウィザードの Step 8（ドライラン）で、Teams にテスト通知を送信できます。

```
[Step 8/9] ドライラン（テスト実行）
  ✔ ドライラン完了
  Teams にテスト通知を送信しますか？ [Y/n]: y
  ✔ テスト通知送信完了
```

Teams チャンネルに「elabBot セットアップテスト」というカードが届けば設定は正常です。

## トラブルシューティング

| 症状 | 原因と対処 |
|---|---|
| 通知が届かない | Webhook URL が正しいか確認。期限切れの場合は再作成 |
| HTTP 400 エラー | Adaptive Card の形式エラー。ログで詳細を確認 |
| HTTP 403 エラー | Webhook が無効化されている。Teams の設定で再有効化 |
| 一部のタグだけ届かない | `TEAMS_TAG_MAP` のタグ名が実験ノートのタグと完全一致しているか確認 |
