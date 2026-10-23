"""All-in-one interactive setup wizard for elabBot standalone summarizer.

Run:
    python -m standalone_summarizer.setup_check
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# ── ANSI helpers ──────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(msg: str) -> None:
    print(f"  {GREEN}✔{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}✘{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}!{RESET} {msg}")


def step(n: int, total: int, title: str) -> None:
    print(f"\n{BOLD}{CYAN}[Step {n}/{total}] {title}{RESET}")


def ask(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"  {label}{suffix}: ").strip()
    return val or default


def ask_choice(label: str, choices: list[str], default: str = "") -> str:
    opts = " / ".join(choices)
    return ask(f"{label} ({opts})", default)


def confirm(label: str, default_yes: bool = True) -> bool:
    hint = "Y/n" if default_yes else "y/N"
    ans = input(f"  {label} [{hint}]: ").strip().lower()
    if not ans:
        return default_yes
    return ans.startswith("y")


# ── Network test helpers ─────────────────────────────────────────────────
def _test_elab(base_url: str, api_key: str, verify_ssl: bool) -> bool:
    import requests

    try:
        r = requests.get(
            f"{base_url.rstrip('/')}/experiments?limit=1",
            headers={"Authorization": api_key},
            timeout=10,
            verify=verify_ssl,
        )
        if r.status_code < 400:
            ok(f"eLabFTW 接続成功 (HTTP {r.status_code})")
            return True
        fail(f"eLabFTW 応答エラー (HTTP {r.status_code})")
        return False
    except Exception as exc:
        fail(f"eLabFTW 接続失敗 — {exc}")
        return False


def _test_azure(endpoint: str, api_key: str, deployment: str) -> bool:
    import requests
    from standalone_summarizer.summarizer.backends.azure_openai import parse_azure_endpoint

    base, dep, api_ver, api_style = parse_azure_endpoint(endpoint, deployment)

    if api_style == "responses":
        url = f"{base}/openai/responses?api-version={api_ver}"
        payload: dict = {
            "model": dep or deployment,
            "input": "ping",
            "max_output_tokens": 16,
        }
    else:
        url = f"{base}/openai/deployments/{dep}/chat/completions?api-version={api_ver}"
        payload = {
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
        }

    label = dep or deployment or "unknown"
    try:
        r = requests.post(url, json=payload, headers={"api-key": api_key}, timeout=15)
        if r.status_code == 200:
            ok(f"Azure OpenAI ({label}) 応答 OK — {api_style} API")
            return True
        fail(f"Azure OpenAI — HTTP {r.status_code}")
        return False
    except Exception as exc:
        fail(f"Azure OpenAI 接続失敗 — {exc}")
        return False


def _test_ollama(endpoint: str, model_id: str) -> bool:
    import requests

    try:
        r = requests.get(f"{endpoint.rstrip('/')}/api/tags", timeout=10)
        models = [m.get("name", "") for m in r.json().get("models", [])]
        if any(model_id in m for m in models):
            ok(f"Ollama モデル '{model_id}' 利用可能")
            return True
        warn(f"モデル '{model_id}' 未検出。利用可能: {', '.join(models) or '(なし)'}")
        return False
    except Exception as exc:
        fail(f"Ollama 接続失敗 — {exc}")
        return False


TOTAL_STEPS = 9


# ── Main wizard ──────────────────────────────────────────────────────────
def main() -> None:
    print(f"\n{BOLD}{'=' * 50}")
    print(f"  elabBot セットアップウィザード")
    print(f"{'=' * 50}{RESET}")
    print(f"  対話形式で設定を進めます。Enter でデフォルト値を使用。\n")

    # ── Step 1: Python & packages ────────────────────────────────────────
    step(1, TOTAL_STEPS, "環境チェック")
    v = sys.version_info
    if v >= (3, 10):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        fail(f"Python {v.major}.{v.minor} — 3.10 以上が必要です")
        print("  Python をアップグレードしてから再実行してください。")
        sys.exit(1)

    missing = []
    for pkg in ("requests", "fastapi", "uvicorn"):
        try:
            __import__(pkg)
            ok(pkg)
        except ImportError:
            missing.append(pkg)
            fail(pkg)

    if missing:
        if confirm("依存パッケージをインストールしますか？"):
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])
            ok("インストール完了")
        else:
            fail("依存パッケージが不足しています。pip install -e . を実行してください。")
            sys.exit(1)

    # ── Step 2: eLabFTW 設定 ─────────────────────────────────────────────
    step(2, TOTAL_STEPS, "eLabFTW 接続設定")
    elab_url = ask("eLabFTW ベース URL", "https://your-elabftw-host.example.com/api/v2")
    elab_key = ask("eLabFTW API キー", "")
    elab_ssl = ask_choice("SSL 検証", ["true", "false"], "false")

    # ── Step 3: LLM バックエンド ─────────────────────────────────────────
    step(3, TOTAL_STEPS, "LLM バックエンド設定")
    backend = ask_choice("バックエンド", ["azure_openai", "ollama"], "azure_openai")

    llm_endpoint = ""
    llm_model = ""
    llm_api_key = ""

    if backend == "azure_openai":
        llm_endpoint = ask("Azure OpenAI エンドポイント URL", "https://your-resource.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview")
        llm_model = ask("デプロイメント名", "gpt-5.2-chat")
        llm_api_key = ask("Azure OpenAI API キー", "")
    else:
        llm_endpoint = ask("Ollama エンドポイント URL", "http://127.0.0.1:11434")
        llm_model = ask("モデル ID", "qwen2.5:3b-instruct-q4")

    # ── Step 4: Teams 通知設定 ──────────────────────────────────────────
    step(4, TOTAL_STEPS, "Teams 通知設定")

    teams_webhook = ""
    teams_tag_map = ""
    if confirm("Teams 通知を設定しますか？"):
        mode = ask_choice("設定方式", ["single", "tag_map"], "single")
        if mode == "single":
            teams_webhook = ask("Teams Webhook URL")
        else:
            print("  タグごとに Webhook URL を入力（空 Enter で終了）")
            pairs: list[str] = []
            while True:
                tag = ask("タグ名（空で終了）")
                if not tag:
                    break
                url = ask(f"  {tag} の Webhook URL")
                if url:
                    pairs.append(f"{tag}={url}")
            teams_tag_map = ",".join(pairs)
    else:
        warn("Teams 通知はスキップ（後から standalone.env に追加可能）")

    # ── Step 5: 運用設定 ─────────────────────────────────────────────────
    step(5, TOTAL_STEPS, "運用設定")
    tags = ask("対象タグ（カンマ区切り）", "summarize")
    log_dir = ask("ログ出力先", "./logs")
    log_level = ask_choice("ログレベル", ["INFO", "DEBUG", "WARNING"], "INFO")

    # ── Step 6: ディレクトリ作成 & env 書き出し ──────────────────────────
    step(6, TOTAL_STEPS, "設定ファイル生成")

    for d in (Path(log_dir), Path("./data")):
        d.mkdir(parents=True, exist_ok=True)
        ok(f"{d}/ 準備完了")

    env_path = Path("config/standalone.env")
    env_path.parent.mkdir(parents=True, exist_ok=True)

    env_content = f"""\
# Generated by elabBot setup wizard
# eLabFTW
ELAB_BASE_URL={elab_url}
ELAB_API_KEY={elab_key}
ELAB_VERIFY_SSL={elab_ssl}
ELAB_TIMEOUT=30
ELAB_PAGE_SIZE=50
ELAB_MAX_PAGES=20
ELAB_RETRY_ATTEMPTS=3
ELAB_RETRY_BACKOFF_SECONDS=2.0

# LLM
LLM_BACKEND={backend}
LLM_ENDPOINT_URL={llm_endpoint}
LLM_MODEL_ID={llm_model}
LLM_API_KEY={llm_api_key}
LLM_TEMPERATURE=0.2
LLM_MAX_INPUT_CHARS=3000
LLM_CONTEXT_WINDOW=4096
LLM_MAX_OUTPUT_TOKENS=512
LLM_RETRY_ATTEMPTS=3
LLM_RETRY_BACKOFF_SECONDS=2.0
LLM_SYSTEM_PROMPT=./prompts/system.txt

# Scheduler / Logging
SCHEDULER_INTERVAL_SECONDS=300
SCHEDULER_MAX_ITEMS=10
LOG_LEVEL={log_level}
LOG_DIR={log_dir}
LOG_RETENTION_DAYS=30
TARGET_TAGS={tags}

# Teams notification
TEAMS_WEBHOOK_URL={teams_webhook}
TEAMS_TAG_MAP={teams_tag_map}
"""
    env_path.write_text(env_content, encoding="utf-8")
    ok(f"{env_path} を生成しました")

    # ── Step 7: 接続テスト ───────────────────────────────────────────────
    step(7, TOTAL_STEPS, "接続テスト")

    elab_ok = _test_elab(elab_url, elab_key, elab_ssl == "true")

    if backend == "azure_openai" and llm_api_key:
        llm_ok = _test_azure(llm_endpoint, llm_api_key, llm_model)
    elif backend == "ollama":
        llm_ok = _test_ollama(llm_endpoint, llm_model)
    else:
        warn("LLM 接続テストをスキップ（API キー未設定）")
        llm_ok = False

    if not elab_ok or not llm_ok:
        if not confirm("接続エラーがあります。続行しますか？", default_yes=False):
            print("\n  設定を修正して再実行してください:")
            print(f"  python -m standalone_summarizer.setup_check")
            sys.exit(1)

    # ── Step 8: ドライラン ───────────────────────────────────────────────
    step(8, TOTAL_STEPS, "ドライラン（テスト実行）")

    import os

    # Load env vars
    for line in env_content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ[k.strip()] = v.strip()

    dry_run_ok = False
    if confirm("ドライランを実行しますか？（実際の投稿はしません）"):
        try:
            from standalone_summarizer.worker import run_once
            from standalone_summarizer.config import AppConfig

            cfg = AppConfig.from_env()
            run_once(cfg, dry_run=True, limit=2)
            ok("ドライラン完了")
            dry_run_ok = True
        except Exception as exc:
            fail(f"ドライラン失敗 — {exc}")
            warn("設定を確認して再実行してください")

        # Teams notification test
        if dry_run_ok and (teams_webhook or teams_tag_map):
            if confirm("Teams にテスト通知を送信しますか？"):
                from standalone_summarizer.notify import send_teams_notification

                test_urls: list[str] = []
                if teams_webhook:
                    test_urls.append(teams_webhook)
                elif teams_tag_map:
                    test_urls = [p.partition("=")[2] for p in teams_tag_map.split(",") if "=" in p]

                for u in test_urls:
                    try:
                        send_teams_notification(
                            webhook_url=u,
                            title="elabBot セットアップテスト",
                            summary="これはセットアップウィザードからのテスト通知です。正常に受信できていれば設定は完了です。",
                            experiment_url=elab_url.replace("/api/v2", ""),
                            tags=tags,
                        )
                        ok(f"テスト通知送信完了")
                    except Exception as exc:
                        fail(f"テスト通知失敗 — {exc}")
    else:
        warn("スキップしました")

    # ── Step 9: 本番設定 ─────────────────────────────────────────────────
    step(9, TOTAL_STEPS, "本番設定（systemd timer）")

    if not dry_run_ok:
        warn("ドライランが未完了のため、本番設定はスキップします")
    elif not confirm("systemd timer で定期実行を設定しますか？"):
        warn("スキップしました — 手動で実行する場合:")
        print(f"    set -a && source {env_path.resolve()} && set +a")
        print(f"    python -m standalone_summarizer.worker")
    else:
        schedule = ask("実行スケジュール (OnCalendar 形式)", "*-*-* 09:00:00")
        run_user = ask("実行ユーザー", os.environ.get("USER", "root"))
        work_dir = Path.cwd().resolve()
        venv_python = Path(sys.executable).resolve()

        service_unit = f"""\
[Unit]
Description=elabBot Standalone Summarizer
After=network.target

[Service]
Type=oneshot
User={run_user}
WorkingDirectory={work_dir}
EnvironmentFile={work_dir / "config" / "standalone.env"}
ExecStart={venv_python} -m standalone_summarizer.worker
StandardOutput=journal
StandardError=journal
"""
        timer_unit = f"""\
[Unit]
Description=elabBot Summarizer Timer

[Timer]
OnCalendar={schedule}
Persistent=true

[Install]
WantedBy=timers.target
"""
        svc_name = "elabbot-summarizer"
        svc_path = Path(f"/etc/systemd/system/{svc_name}.service")
        tmr_path = Path(f"/etc/systemd/system/{svc_name}.timer")

        try:
            subprocess.run(
                ["sudo", "tee", str(svc_path)],
                input=service_unit.encode(), check=True, stdout=subprocess.DEVNULL,
            )
            ok(f"{svc_path} 作成")

            subprocess.run(
                ["sudo", "tee", str(tmr_path)],
                input=timer_unit.encode(), check=True, stdout=subprocess.DEVNULL,
            )
            ok(f"{tmr_path} 作成")

            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
            subprocess.run(["sudo", "systemctl", "enable", f"{svc_name}.timer"], check=True)
            subprocess.run(["sudo", "systemctl", "start", f"{svc_name}.timer"], check=True)
            ok(f"{svc_name}.timer 有効化・起動完了")

            result = subprocess.run(
                ["systemctl", "status", f"{svc_name}.timer", "--no-pager"],
                capture_output=True, text=True,
            )
            print(f"\n{result.stdout}")

            if confirm("今すぐ本番実行を 1 回テストしますか？", default_yes=False):
                subprocess.run(
                    ["sudo", "systemctl", "start", f"{svc_name}.service"],
                    check=True,
                )
                ok("本番実行完了")
                result = subprocess.run(
                    ["journalctl", "-u", f"{svc_name}.service", "-n", "20", "--no-pager"],
                    capture_output=True, text=True,
                )
                print(f"\n{result.stdout}")

        except subprocess.CalledProcessError as exc:
            fail(f"systemd 設定失敗 — {exc}")
            warn("手動で設定してください:")
            print(f"\n--- {svc_path} ---\n{service_unit}")
            print(f"--- {tmr_path} ---\n{timer_unit}")
        except PermissionError:
            fail("sudo 権限がありません")
            warn("以下の内容で手動作成してください:")
            print(f"\n--- {svc_path} ---\n{service_unit}")
            print(f"--- {tmr_path} ---\n{timer_unit}")

    # ── Done ─────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'=' * 50}")
    print(f"  セットアップ完了！")
    print(f"{'=' * 50}{RESET}")
    print(f"""
  状態確認:
    systemctl status elabbot-summarizer.timer
    journalctl -u elabbot-summarizer.service -f
""")


if __name__ == "__main__":
    main()
