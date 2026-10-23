# 06. 運用ガイド

> 関連ドキュメント: [02_setup.md](02_setup.md) | [03_configuration.md](03_configuration.md) | [01_architecture.md](01_architecture.md)

## プロセス構成

elabBot は以下の 2 つのプロセスで構成されます。

| プロセス | 実行方法 | 役割 |
|---|---|---|
| Worker | `python -m standalone_summarizer.worker` | ノート取得 → 要約 → コメント投稿 → Teams 通知 |
| Service (任意) | `uvicorn standalone_summarizer.service:app` | `/healthz` と `/metrics` を提供 |

Worker は 1 回実行して終了する oneshot 型です。定期実行には systemd timer または cron を使用します。

## systemd による定期実行

### サービスファイル

`/etc/systemd/system/elabbot-summarizer.service`:

```ini
[Unit]
Description=elabBot Standalone Summarizer
After=network.target

[Service]
Type=oneshot
User=your-user
WorkingDirectory=/path/to/elabBot
EnvironmentFile=/path/to/elabBot/config/standalone.env
ExecStart=/path/to/elabBot/.venv/bin/python -m standalone_summarizer.worker
StandardOutput=journal
StandardError=journal
```

### タイマーファイル

`/etc/systemd/system/elabbot-summarizer.timer`:

```ini
[Unit]
Description=elabBot Summarizer Timer

[Timer]
OnCalendar=*-*-* 09:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

`OnCalendar` の書式例:

| 設定値 | 実行タイミング |
|---|---|
| `*-*-* 09:00:00` | 毎日 9:00 |
| `*-*-* *:00/5:00` | 5 分ごと |
| `Mon..Fri *-*-* 09:00:00` | 平日 9:00 |
| `*-*-* 09,18:00:00` | 毎日 9:00 と 18:00 |

### 有効化と起動

```bash
sudo systemctl daemon-reload
sudo systemctl enable elabbot-summarizer.timer
sudo systemctl start elabbot-summarizer.timer

# 状態確認
systemctl status elabbot-summarizer.timer
systemctl list-timers --all | grep elabbot

# 手動で即時実行
sudo systemctl start elabbot-summarizer.service

# ログ確認
journalctl -u elabbot-summarizer.service -f
```

### セットアップウィザードでの自動設定

[セットアップウィザード](02_setup.md) の Step 9 で systemd timer を対話的に作成・有効化できます。パス・ユーザー名・スケジュールは自動検出されます。

## cron による定期実行

systemd を使わない場合は cron でも実行できます。

```bash
crontab -e

# 毎日 9:00 に実行
0 9 * * * cd /path/to/elabBot && source .venv/bin/activate && set -a && source config/standalone.env && set +a && python -m standalone_summarizer.worker >> logs/cron.log 2>&1
```

## ヘルスチェック・メトリクス API

FastAPI サービスを起動すると、外部監視ツールからの死活監視やメトリクス収集が可能になります。

```bash
uvicorn standalone_summarizer.service:app --host 0.0.0.0 --port 8080
```

### エンドポイント

| パス | メソッド | 説明 |
|---|---|---|
| `/healthz` | GET | サービスの稼働状態を返却 |
| `/metrics` | GET | 処理済みノート件数と稼働時間を返却 |

### レスポンス例

```json
// GET /healthz
{
  "status": "ok",
  "tags": ["summarize"],
  "scheduler_interval_seconds": 300
}

// GET /metrics
{
  "processed_count": 42,
  "uptime_seconds": 86400.5,
  "log_directory": "./logs"
}
```

Prometheus 等の監視ツールから `/metrics` をスクレイプすることで、処理件数の推移を可視化できます。

## ログ管理

### ログファイル

Worker と Service のログは `LOG_DIR`（デフォルト: `./logs`）に出力されます。

- ファイル名: `standalone-summarizer.log`
- ローテーション: 日次（`TimedRotatingFileHandler`）
- 保持期間: `LOG_RETENTION_DAYS`（デフォルト: 30 日）

### ログレベル

| レベル | 用途 |
|---|---|
| `DEBUG` | 開発・トラブルシューティング時。API リクエスト/レスポンスの詳細を出力 |
| `INFO` | 通常運用。処理件数・トークン数・所要時間を出力 |
| `WARNING` | 注意が必要な事象。リトライ発生、Teams 通知失敗など |
| `ERROR` | 処理失敗。API エラー、LLM 接続エラーなど |

### ログの確認

```bash
# リアルタイム監視
tail -f logs/standalone-summarizer.log

# systemd の場合
journalctl -u elabbot-summarizer.service -f

# エラーのみ抽出
grep ERROR logs/standalone-summarizer.log
```

## 状態データベース

`data/state.db`（SQLite）に処理済みノートの情報を記録し、重複投稿を防止します。

### 記録内容

- 実験 ID
- eLabFTW 内部 ID (elabid)
- 本文のハッシュ値
- 処理日時
- 使用モデル名、入出力トークン数

### ノートが更新された場合

本文のハッシュ値が変わるため、次回実行時に再度要約が生成されます。

### リセット方法

テスト時に状態をリセットしたい場合:

```bash
rm data/state.db
```

次回実行時に自動的に再作成されます。本番環境では慎重に行ってください。

### バックアップ

```bash
cp data/state.db data/state.db.bak
```

## トラブルシューティング

### よくある問題と対処

| 症状 | 原因と対処 |
|---|---|
| eLabFTW 接続エラー | API キーが有効か確認。`ELAB_VERIFY_SSL=false` で自己署名証明書に対応 |
| Azure OpenAI HTTP 404 | エンドポイント URL が二重パスになっていないか確認。[04_llm-backends.md](04_llm-backends.md) 参照 |
| Azure OpenAI HTTP 400 | リクエスト形式のエラー。`LLM_MAX_OUTPUT_TOKENS` が最小値（16）以上か確認 |
| Azure OpenAI HTTP 429 | レート制限。`LLM_RETRY_ATTEMPTS` と `LLM_RETRY_BACKOFF_SECONDS` を増やす |
| Ollama 接続エラー | `ollama serve` が起動しているか確認。エンドポイント URL が正しいか確認 |
| 要約が生成されない | 対象タグが付いたノートが存在するか確認。`--dry-run` で動作確認 |
| 同じノートが何度も処理される | `data/state.db` が書き込み可能か確認。ディスク容量も確認 |
| Teams 通知が届かない | Webhook URL が有効か確認。[05_teams-notification.md](05_teams-notification.md) 参照 |

### デバッグ実行

```bash
# 詳細ログを有効にして 1 件だけ処理
LOG_LEVEL=DEBUG python -m standalone_summarizer.worker --dry-run --limit 1
```
