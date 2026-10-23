# 02. セットアップ手順

> 関連ドキュメント: [01_architecture.md](01_architecture.md) | [03_configuration.md](03_configuration.md) | [04_llm-backends.md](04_llm-backends.md)

## セットアップウィザード（推奨）

対話型ウィザードを使えば、環境チェックから本番設定まで 1 コマンドで完了します。

```bash
git clone https://github.com/Kosaku-Noba/elabftw-standalone-summarizer.git
cd elabftw-standalone-summarizer
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
python -m standalone_summarizer.setup_check
```

### ウィザードの流れ

ウィザードは以下の 9 ステップを順番に実行します。

| Step | 内容 | 説明 |
|------|------|------|
| 1 | 環境チェック | Python バージョンと依存パッケージの確認。不足があればその場でインストール |
| 2 | eLabFTW 接続設定 | ベース URL、API キー、SSL 検証の設定 |
| 3 | LLM バックエンド設定 | Azure OpenAI / Ollama の選択とエンドポイント情報の入力 |
| 4 | Teams 通知設定 | Webhook URL の入力。タグごとの振り分けも対応 |
| 5 | 運用設定 | 対象タグ、ログ出力先、ログレベルの設定 |
| 6 | 設定ファイル生成 | 入力内容から `config/standalone.env` を自動生成 |
| 7 | 接続テスト | eLabFTW と LLM バックエンドへの疎通確認 |
| 8 | ドライラン | 実際の要約パイプラインをテスト実行（投稿はしない）。Teams テスト通知も送信可能 |
| 9 | 本番設定 | systemd timer の作成・有効化。即時実行テストも可能 |

### ウィザード実行例

```
==================================================
  elabBot セットアップウィザード
==================================================

[Step 1/9] 環境チェック
  ✔ Python 3.10.19
  ✔ requests
  ✔ fastapi
  ✔ uvicorn

[Step 2/9] eLabFTW 接続設定
  eLabFTW ベース URL [https://localhost:4443/api/v2]: https://elab.example.com/api/v2
  eLabFTW API キー: xxxxxxxx
  SSL 検証 (true / false) [true]: true

[Step 3/9] LLM バックエンド設定
  バックエンド (azure_openai / ollama) [azure_openai]:
  Azure OpenAI エンドポイント URL [...]: (Enter でデフォルト)
  デプロイメント名 [gpt-5.2-chat]: (Enter でデフォルト)
  Azure OpenAI API キー [...]: (Enter でデフォルト)

[Step 4/9] Teams 通知設定
  Teams 通知を設定しますか？ [Y/n]: y
  設定方式 (single / tag_map) [single]: single
  Teams Webhook URL: https://your-org.webhook.office.com/xxx

[Step 5/9] 運用設定
  対象タグ（カンマ区切り） [summarize]: 要約対象
  ログ出力先 [./logs]:
  ログレベル (INFO / DEBUG / WARNING) [INFO]:

[Step 6/9] 設定ファイル生成
  ✔ logs/ 準備完了
  ✔ data/ 準備完了
  ✔ config/standalone.env を生成しました

[Step 7/9] 接続テスト
  ✔ eLabFTW 接続成功 (HTTP 200)
  ✔ Azure OpenAI (gpt-5.2-chat) 応答 OK — responses API

[Step 8/9] ドライラン（テスト実行）
  ✔ ドライラン完了
  ✔ テスト通知送信完了

[Step 9/9] 本番設定（systemd timer）
  ✔ elabbot-summarizer.timer 有効化・起動完了

==================================================
  セットアップ完了！
==================================================
```

## 手動セットアップ

ウィザードを使わず手動で設定する場合の手順です。

### 1. リポジトリ取得と環境構築

```bash
git clone https://github.com/Kosaku-Noba/elabftw-standalone-summarizer.git
cd elabftw-standalone-summarizer
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### 2. 設定ファイル作成

```bash
cp config/standalone.env.example config/standalone.env
nano config/standalone.env
```

各環境変数の詳細は [03_configuration.md](03_configuration.md) を参照してください。

### 3. ディレクトリ作成

```bash
mkdir -p logs data
```

### 4. 動作確認

```bash
source .venv/bin/activate
set -a && source config/standalone.env && set +a
python -m standalone_summarizer.worker --dry-run
```

### 5. 本番実行

```bash
python -m standalone_summarizer.worker
```

定期実行の設定は [06_operations.md](06_operations.md) を参照してください。

## 事前準備チェックリスト

導入先に事前にお願いする項目です。

### 必須

- [ ] Python 3.10 以上のインストール
- [ ] eLabFTW の REST API キー（管理者権限推奨）
- [ ] eLabFTW のベース URL
- [ ] Azure OpenAI のエンドポイント URL・API キー・デプロイメント名
- [ ] 作業用サーバーへのアクセス情報

### あるとスムーズ

- [ ] Teams 通知先チャンネルの Webhook URL
- [ ] サーバーの sudo 権限（systemd timer 設定用）
- [ ] 定期実行の頻度・タイミングの希望
- [ ] テスト用の実験ノート（対象タグ付き）1〜2 件
- [ ] ネットワーク疎通の事前確認（Azure OpenAI への通信がブロックされていないか）
