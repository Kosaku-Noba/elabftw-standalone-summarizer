# 04. LLM バックエンド詳細

> 関連ドキュメント: [03_configuration.md](03_configuration.md) | [01_architecture.md](01_architecture.md)

elabBot は 3 種類の LLM バックエンドに対応しています。`LLM_BACKEND` 環境変数で切り替えます。

## Azure OpenAI

クラウド上の Azure OpenAI Service を利用するバックエンドです。高品質な要約が得られますが、ネットワーク接続とAPIキーが必要です。

### 対応 API

Azure OpenAI には 2 つの API 形式があり、elabBot はエンドポイント URL から自動判定します。

| API | URL パターン | 特徴 |
|---|---|---|
| Chat Completions API | `https://{resource}.openai.azure.com` | 従来型。デプロイメント名を `LLM_MODEL_ID` に指定 |
| Responses API | `https://{resource}.cognitiveservices.azure.com/openai/responses?api-version=...` | 新型。URL にフルパスを指定可能 |

URL に `/openai/responses` が含まれていれば Responses API、それ以外は Chat Completions API として処理されます。フル URL を貼り付けても、ホスト部分だけを指定しても、どちらでも正しく動作します。

### 設定例

```bash
# Responses API（推奨）
LLM_BACKEND=azure_openai
LLM_ENDPOINT_URL=https://your-resource.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview
LLM_MODEL_ID=gpt-5.2-chat
LLM_API_KEY=your_api_key

# Chat Completions API
LLM_BACKEND=azure_openai
LLM_ENDPOINT_URL=https://your-resource.openai.azure.com
LLM_MODEL_ID=gpt-4
LLM_API_KEY=your_api_key
```

### バックエンド名のエイリアス

`LLM_BACKEND` には以下のいずれかを指定できます（大文字小文字不問）:

- `azure_openai`
- `azure`
- `azureopenai`

### コストに関する注意

Azure OpenAI は従量課金です。`/metrics` エンドポイントや Worker のログでトークン使用量を確認できます。Azure Portal でも予算アラートの設定を推奨します。

## Ollama

ローカルまたはリモートの Ollama サーバーを利用するバックエンドです。データを外部に送信せずに運用できます。

### 前提条件

- Ollama がインストール・起動されていること
- 使用するモデルが `ollama pull` で取得済みであること

### 設定例

```bash
LLM_BACKEND=ollama
LLM_ENDPOINT_URL=http://127.0.0.1:11434
LLM_MODEL_ID=qwen2.5:3b-instruct-q4
```

### 推奨モデル

| モデル | RAM 目安 | 特徴 |
|---|---|---|
| `qwen2.5:3b-instruct-q4` | 約 2–3 GB | 日本語要約性能が高い。軽量環境向け |
| `qwen2.5:7b-instruct-q4` | 約 6 GB | 品質重視。GPU 推奨 |
| `llama3.2:3b-instruct` | 約 3 GB | 英日混在に強い |

### Ollama サーバーの起動

```bash
# サーバー起動
ollama serve

# モデル取得
ollama pull qwen2.5:3b-instruct-q4

# 動作確認
curl http://127.0.0.1:11434/api/tags
```

## llama.cpp

GGUF 形式のモデルファイルを直接ロードして推論するバックエンドです。Ollama を使わずにローカル推論を行いたい場合に使用します。

### 前提条件

- `llama-cpp-python` パッケージがインストール済みであること（`pip install -e .` で自動インストール）
- GGUF 形式のモデルファイルが配置されていること

### 設定例

```bash
LLM_BACKEND=llamacpp
LLM_MODEL_PATH=/opt/models/qwen2.5-3b-instruct-q4.gguf
LLM_CONTEXT_WINDOW=4096
LLM_MAX_OUTPUT_TOKENS=512
```

### バックエンド名のエイリアス

- `llamacpp`
- `llama.cpp`

### 注意事項

- 初回実行時にモデルをメモリにロードするため、起動に時間がかかります
- GPU を使用する場合は `llama-cpp-python` を CUDA 対応でビルドする必要があります
- メモリ不足の場合はより小さい量子化モデル（Q4 など）を使用してください

## Map-Reduce 要約パイプライン

どのバックエンドを使用しても、要約処理は共通の Map-Reduce パイプラインで実行されます。

### 処理フロー

1. **前処理**: eLabFTW のノート本文（HTML）をプレーンテキストに変換
2. **チャンク分割**: `LLM_MAX_INPUT_CHARS`（デフォルト 3000 文字）ごとに分割
3. **Map フェーズ**: 各チャンクに対して部分要約を生成。出力形式は「目的・方法・結果・次のアクション・リスク/懸念・キーワード」
4. **Reduce フェーズ**: 複数の部分要約を統合し、重複や矛盾を解消した最終要約を生成
5. **単一チャンクの場合**: Reduce フェーズをスキップし、Map の結果をそのまま返却

### システムプロンプト

`prompts/system.txt` に要約の指示を記述します。デフォルトでは以下の方針が設定されています:

- 事実と解釈を混同しない
- 入力本文に含まれない情報は生成しない
- 目的・方法・結果・次のアクションの順で簡潔にまとめる
- キーワードは 3〜5 語

組織のルールに合わせてカスタマイズしてください。`LLM_SYSTEM_PROMPT` 環境変数で別ファイルを指定することも可能です。
