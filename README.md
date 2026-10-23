# elabBot Standalone Summarizer

eLabFTW の実験ノートを自動要約し、コメント投稿と Teams 通知を行うスタンドアロンサービスです。

## 特徴

- eLabFTW 本体を改修せず、REST API (v2) のみで連携（**eLabFTW 5.6.x / 6.x 対応**）
- LLM バックエンドを切り替え可能（Azure OpenAI / Ollama / llama.cpp）
- Map-Reduce 方式で長文ノートも構造化要約
- Teams Webhook による自動通知
- SQLite ベースの状態管理で重複投稿を防止
- 対話型セットアップウィザードで導入を自動化

## ディレクトリ構成

```
elabBot/
├── README.md                          このドキュメント
├── pyproject.toml                     依存関係・プロジェクト定義
├── config/
│   └── standalone.env.example         環境変数テンプレート
├── docs/
│   ├── 01_architecture.md             アーキテクチャ概要
│   ├── 02_setup.md                    セットアップ手順
│   ├── 03_configuration.md            設定リファレンス
│   ├── 04_llm-backends.md             LLM バックエンド詳細
│   ├── 05_teams-notification.md       Teams 通知設定
│   ├── 06_operations.md               運用ガイド
│   └── 07_development.md              開発ガイド
├── prompts/
│   └── system.txt                     要約用システムプロンプト
├── src/standalone_summarizer/
│   ├── client/                        eLabFTW REST クライアント
│   ├── summarizer/                    LLM バックエンドとパイプライン
│   │   └── backends/                  各 LLM バックエンド実装
│   ├── config.py                      設定ローダ
│   ├── notify.py                      Teams 通知
│   ├── pipeline.py                    Map-Reduce 要約パイプライン
│   ├── state.py                       SQLite 状態管理
│   ├── worker.py                      CLI / cron 実行エントリ
│   ├── service.py                     FastAPI ヘルス/メトリクス
│   └── setup_check.py                 対話型セットアップウィザード
├── tests/                             ユニットテスト
├── data/                              state.db（実行時生成）
└── logs/                              ログ出力先
```

## クイックスタート

セットアップウィザードを使えば、対話形式ですべての設定が完了します。

```bash
git clone https://github.com/Kosaku-Noba/elabftw-standalone-summarizer.git
cd elabftw-standalone-summarizer
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
python -m standalone_summarizer.setup_check
```

ウィザードの詳細は [docs/02_setup.md](docs/02_setup.md) を参照してください。

## ドキュメント

| ドキュメント | 内容 |
|---|---|
| [01_architecture.md](docs/01_architecture.md) | システム構成・データフロー・セキュリティ |
| [02_setup.md](docs/02_setup.md) | セットアップウィザード・手動セットアップ |
| [03_configuration.md](docs/03_configuration.md) | 全環境変数の設定リファレンス |
| [04_llm-backends.md](docs/04_llm-backends.md) | Azure OpenAI / Ollama / llama.cpp の詳細 |
| [05_teams-notification.md](docs/05_teams-notification.md) | Teams 通知の設定と動作 |
| [06_operations.md](docs/06_operations.md) | systemd / ログ / 監視 / トラブルシューティング |
| [07_development.md](docs/07_development.md) | テスト・コード構成・コントリビューション |

## ライセンス

Pull Request や Issue でのフィードバック歓迎です。
