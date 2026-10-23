# 01. アーキテクチャ概要

> 関連ドキュメント: [02_setup.md](02_setup.md) | [03_configuration.md](03_configuration.md) | [06_operations.md](06_operations.md)

## システム全体像

elabBot Standalone Summarizer は、eLabFTW の実験ノートを自動的に取得・要約し、結果をコメントとして投稿するとともに Teams チャンネルへ通知するサービスです。eLabFTW 本体には一切の改修を加えず、REST API (v2) のみで連携します。**eLabFTW 5.6.x および 6.x 系に対応しています**（一覧 API の `full=1` パラメータ対応。詳細は後述の「ノート取得」を参照）。

```
┌──────────┐       HTTPS (REST API v2)       ┌──────────────┐
│  eLabFTW │ <────────────────────────────── │  elabBot      │
│  Server  │ ────────────────────────────── > │  Worker       │
└──────────┘  GET /experiments                │              │
              POST /experiments/{id}/comments │              │
                                              │  ┌──────────┐│
                                              │  │ LLM      ││
                                              │  │ Backend  ││
                                              │  └──────────┘│
                                              │              │
                                              │  ┌──────────┐│
                                              │  │ SQLite   ││
                                              │  │ State DB ││
                                              │  └──────────┘│
                                              └──────┬───────┘
                                                     │ Webhook POST
                                                     ▼
                                              ┌──────────────┐
                                              │ Teams Channel│
                                              └──────────────┘
```

## データフロー

1. **ノート取得**: Worker が eLabFTW REST API を呼び出し、指定タグが付いた実験ノートの一覧を取得します。ページングに対応しており、大量のノートがあっても漏れなく取得します。

   > **対応バージョンと `full=1` について**
   > eLabFTW 5.6 以降（6.x 系を含む）、一覧 API (`GET /experiments`) は既定で列を絞って返し、要約に必要な `body` や `elabid` が応答に含まれません。本サービスは一覧取得時に `full=1` を付与し、全列を取得します。ページングは v2 共通の `offset` / `limit` 方式、タグは `tags[]` 配列形式を用いるため、**eLabFTW 5.6.x および 6.x の両系統で動作します**。5.5 以前では `full` パラメータは無視されますが、既定で全列が返るため同様に動作します。

2. **重複チェック**: SQLite の状態データベース (`data/state.db`) に記録された実験 ID と本文ハッシュを照合し、未処理または更新されたノートのみを対象にします。

3. **要約生成**: Map-Reduce 方式の要約パイプラインが本文を処理します。長文ノートはチャンク分割され、各チャンクの部分要約を生成（Map）した後、統合要約（Reduce）を行います。詳細は [04_llm-backends.md](04_llm-backends.md) を参照してください。

4. **コメント投稿**: 生成された要約を eLabFTW の該当実験ノートにコメントとして POST します。リトライ機構を備えており、一時的なエラーにも対応します。

5. **Teams 通知**: 設定されている場合、Adaptive Card 形式で Teams チャンネルに通知を送信します。タグごとに異なるチャンネルへの振り分けも可能です。詳細は [05_teams-notification.md](05_teams-notification.md) を参照してください。

6. **状態記録**: 処理完了後、実験 ID・本文ハッシュ・使用モデル・トークン数などのメタデータを SQLite に記録します。

## コンポーネント構成

| コンポーネント | ファイル | 役割 |
|---|---|---|
| Worker | `worker.py` | CLI エントリポイント。cron / systemd timer から呼び出される |
| eLabFTW Client | `client/elab.py` | REST API ラッパー。ノート取得とコメント投稿を担当 |
| Pipeline | `pipeline.py` | Map-Reduce 方式の要約パイプライン |
| LLM Backends | `summarizer/backends/` | Azure OpenAI / Ollama / llama.cpp の各実装 |
| State Store | `state.py` | SQLite による処理済みノートの管理 |
| Notify | `notify.py` | Teams Webhook 通知 |
| Config | `config.py` | 環境変数からの設定読み込み |
| Service | `service.py` | FastAPI によるヘルスチェック・メトリクス API |
| Setup Wizard | `setup_check.py` | 対話型セットアップウィザード |

## セキュリティ設計

- **Pull 型アーキテクチャ**: elabBot から eLabFTW へ接続する一方向通信です。eLabFTW 側にインバウンドの設定変更は不要です。
- **API キー管理**: eLabFTW API キーと LLM API キーは環境変数ファイル (`config/standalone.env`) で管理し、Git リポジトリには含めません。
- **HTTPS 通信**: eLabFTW および Azure OpenAI との通信はすべて HTTPS で暗号化されます。
- **データ保持**: 実験ノートの本文はメモリ上でのみ処理され、ローカルディスクには保存されません。SQLite に記録されるのは実験 ID と本文のハッシュ値のみです。
