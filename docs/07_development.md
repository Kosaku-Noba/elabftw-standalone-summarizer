# 07. 開発ガイド

> 関連ドキュメント: [01_architecture.md](01_architecture.md) | [03_configuration.md](03_configuration.md)

## 開発環境のセットアップ

```bash
git clone https://github.com/Kosaku-Noba/elabftw-standalone-summarizer.git
cd elabftw-standalone-summarizer
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## コード構成

```
src/standalone_summarizer/
├── __init__.py
├── config.py                  設定ローダ（環境変数 → dataclass）
├── logging_utils.py           ログ設定ユーティリティ
├── notify.py                  Teams Webhook 通知
├── pipeline.py                Map-Reduce 要約パイプライン
├── service.py                 FastAPI ヘルス/メトリクス
├── setup_check.py             対話型セットアップウィザード
├── state.py                   SQLite 状態管理
├── test_runner.py             テストランナー
├── worker.py                  CLI エントリポイント
├── client/
│   ├── __init__.py
│   └── elab.py                eLabFTW REST API クライアント
└── summarizer/
    ├── __init__.py
    ├── base.py                SummarizerBackend 基底クラス
    ├── factory.py             バックエンドファクトリー
    └── backends/
        ├── __init__.py
        ├── azure_openai.py    Azure OpenAI バックエンド
        ├── ollama.py          Ollama バックエンド
        ├── llamacpp.py        llama.cpp バックエンド
        └── mock.py            テスト用モックバックエンド
```

## 主要クラスの関係

```
AppConfig.from_env()
    │
    ├── ElabClient(config)          … eLabFTW API 操作
    ├── create_backend(config.llm)  … LLM バックエンド生成
    │       │
    │       ├── AzureOpenAIBackend
    │       ├── OllamaBackend
    │       ├── LlamaCppBackend
    │       └── MockBackend
    │
    ├── SummarizationPipeline(config, backend)
    │       └── summarize_experiment(experiment) → SummarizeResponse
    │
    ├── StateStore()                … SQLite 状態管理
    └── send_teams_notification()   … Teams 通知
```

## 新しい LLM バックエンドの追加方法

1. `summarizer/backends/` に新しいファイルを作成
2. `SummarizerBackend` を継承し、`summarize()` メソッドを実装

```python
from standalone_summarizer.summarizer.base import (
    SummarizeRequest, SummarizeResponse, SummarizerBackend,
)

class MyBackend(SummarizerBackend):
    def __init__(self, config):
        self._config = config

    def summarize(self, request: SummarizeRequest) -> SummarizeResponse:
        # LLM 呼び出しロジック
        return SummarizeResponse(
            summary="...",
            tokens_in=0,
            tokens_out=0,
            model="my-model",
        )
```

3. `summarizer/backends/__init__.py` にインポートを追加
4. `summarizer/factory.py` の `create_backend()` に分岐を追加

## テスト

### ユニットテストの実行

```bash
source .venv/bin/activate
PYTHONPATH=src python -m unittest discover -s tests
```

### テストランナー（ログ付き）

```bash
LOG_DIR=./logs PYTHONPATH=src python -m standalone_summarizer.test_runner
```

### テストファイル

| ファイル | 対象 |
|---|---|
| `tests/test_elab_client.py` | REST クライアントのページング・リトライ |
| `tests/test_pipeline.py` | Map-Reduce パイプラインの挙動 |

### モックバックエンドの利用

テスト時は `LLM_BACKEND=mock` を指定すると、実際の LLM を呼び出さずに固定文字列を返すモックバックエンドが使用されます。

```bash
LLM_BACKEND=mock python -m standalone_summarizer.worker --dry-run
```

## Worker の処理フロー

`worker.py` の `run_once()` は以下の順序で処理を行います:

1. `ElabClient.fetch_experiments(tags)` で対象ノートを取得
2. 各ノートについて `StateStore.has_changed()` で変更チェック
3. `SummarizationPipeline.summarize_experiment()` で要約生成
4. `ElabClient.post_comment()` でコメント投稿
5. `send_teams_notification()` で Teams 通知（設定時のみ）
6. `StateStore.mark_processed()` で状態記録

`--dry-run` フラグを付けると、ステップ 4〜5 をスキップします。

## 依存パッケージ

`pyproject.toml` で管理しています。主要な依存:

| パッケージ | 用途 |
|---|---|
| `requests` | HTTP クライアント（eLabFTW / Ollama / Azure OpenAI） |
| `fastapi` / `uvicorn` | ヘルスチェック・メトリクス API |
| `llama-cpp-python` | llama.cpp バックエンド |
| `html2text` | eLabFTW ノート本文の HTML → テキスト変換 |
| `pymsteams` | Teams 通知（レガシー互換） |

## コーディング規約

- 型ヒントを積極的に使用（`from __future__ import annotations`）
- dataclass は `frozen=True` で不変に
- ログは `logging.getLogger(__name__)` で取得し、`extra` でメタデータを付与
- 外部通信にはリトライ機構を実装
