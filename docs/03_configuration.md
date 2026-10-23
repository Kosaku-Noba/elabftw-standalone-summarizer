# 03. 設定リファレンス

> 関連ドキュメント: [02_setup.md](02_setup.md) | [04_llm-backends.md](04_llm-backends.md) | [05_teams-notification.md](05_teams-notification.md)

すべての設定は環境変数で管理します。`config/standalone.env` に記述するか、シェルの環境変数として export してください。

## eLabFTW 接続設定

| 変数名 | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `ELAB_BASE_URL` | ✔ | `https://localhost:4443/api/v2` | eLabFTW REST API のベース URL |
| `ELAB_API_KEY` | ✔ | ― | eLabFTW の API キー |
| `ELAB_VERIFY_SSL` | | `true` | SSL 証明書の検証。自己署名証明書の場合は `false` |
| `ELAB_TIMEOUT` | | `30` | HTTP リクエストのタイムアウト（秒） |
| `ELAB_PAGE_SIZE` | | `50` | 1 回の API 呼び出しで取得するノート数 |
| `ELAB_MAX_PAGES` | | `20` | ページングの最大ページ数 |
| `ELAB_RETRY_ATTEMPTS` | | `3` | API 呼び出し失敗時のリトライ回数 |
| `ELAB_RETRY_BACKOFF_SECONDS` | | `2.0` | リトライ間隔の基本秒数（指数バックオフ） |

> **eLabFTW のバージョンについて**: 本サービスは eLabFTW 5.6.x / 6.x に対応します。一覧取得時に `full=1` を自動付与し、`offset` / `limit` でページングするため、バージョンごとの設定変更は不要です。

### API キーの取得方法

1. eLabFTW の Web UI にログイン
2. ユーザー設定 → API Keys
3. 新しいキーを生成（読み取り + 書き込み権限が必要）

## LLM バックエンド設定

| 変数名 | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `LLM_BACKEND` | ✔ | `ollama` | バックエンド種別: `azure_openai`, `ollama`, `llamacpp` |
| `LLM_ENDPOINT_URL` | ✔* | ― | LLM サーバーのエンドポイント URL |
| `LLM_MODEL_ID` | ✔* | ― | モデル ID またはデプロイメント名 |
| `LLM_API_KEY` | ✔* | ― | API キー（Azure OpenAI の場合に必須） |
| `LLM_MODEL_PATH` | ✔* | ― | GGUF モデルファイルのパス（llama.cpp の場合に必須） |
| `LLM_TEMPERATURE` | | `0.2` | 生成時の温度パラメータ。低いほど決定的な出力 |
| `LLM_MAX_INPUT_CHARS` | | `3000` | チャンク分割の最大文字数 |
| `LLM_CONTEXT_WINDOW` | | `4096` | モデルのコンテキストウィンドウサイズ |
| `LLM_MAX_OUTPUT_TOKENS` | | `512` | 生成する最大トークン数 |
| `LLM_RETRY_ATTEMPTS` | | `3` | LLM 呼び出し失敗時のリトライ回数 |
| `LLM_RETRY_BACKOFF_SECONDS` | | `2.0` | リトライ間隔の基本秒数 |
| `LLM_SYSTEM_PROMPT` | | `./prompts/system.txt` | システムプロンプトファイルのパス |

*✔\* = バックエンドの種類によって必須項目が異なります。詳細は [04_llm-backends.md](04_llm-backends.md) を参照。*

## Teams 通知設定

| 変数名 | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `TEAMS_WEBHOOK_URL` | | ― | 全タグ共通の Webhook URL。設定すると全通知がこの URL に送信される |
| `TEAMS_TAG_MAP` | | ― | タグごとの Webhook URL マッピング（後述） |

どちらも未設定の場合、Teams 通知は無効になります。詳細は [05_teams-notification.md](05_teams-notification.md) を参照してください。

## スケジューラ・ログ設定

| 変数名 | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `SCHEDULER_INTERVAL_SECONDS` | | `300` | ポーリング間隔（秒）。ヘルスチェック API の表示用 |
| `SCHEDULER_MAX_ITEMS` | | `10` | 1 サイクルあたりの最大処理件数 |
| `LOG_LEVEL` | | `INFO` | ログレベル: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_DIR` | | `./logs` | ログファイルの出力先ディレクトリ |
| `LOG_RETENTION_DAYS` | | `30` | ログファイルの保持日数 |
| `TARGET_TAGS` | | `summarize` | 要約対象のタグ（カンマ区切りで複数指定可） |

## 設定ファイルの例

```bash
# eLabFTW
ELAB_BASE_URL=https://elab.example.com/api/v2
ELAB_API_KEY=your_api_key_here
ELAB_VERIFY_SSL=true

# Azure OpenAI
LLM_BACKEND=azure_openai
LLM_ENDPOINT_URL=https://your-resource.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview
LLM_MODEL_ID=gpt-5.2-chat
LLM_API_KEY=your_azure_api_key_here

# Teams
TEAMS_WEBHOOK_URL=https://your-org.webhook.office.com/webhookb2/xxx

# 運用
TARGET_TAGS=summarize
LOG_LEVEL=INFO
LOG_DIR=./logs
```
