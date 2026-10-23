import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


import requests

from standalone_summarizer.client.elab import ElabClient
from standalone_summarizer.config import AppConfig, ElabConfig, LLMConfig


class StubResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


class StubSession:
    def __init__(self, get_responses=None, post_responses=None):
        self.get_calls = []
        self.post_calls = []
        self._get_responses = get_responses or []
        self._post_responses = post_responses or []

    def get(self, url, params=None, timeout=None, verify=None):
        self.get_calls.append((url, params, timeout, verify))
        index = len(self.get_calls) - 1
        return self._get_responses[min(index, len(self._get_responses) - 1)]

    def post(self, url, json=None, timeout=None, verify=None):
        self.post_calls.append((url, json, timeout, verify))
        index = len(self.post_calls) - 1
        return self._post_responses[min(index, len(self._post_responses) - 1)]


def _build_config(**elab_overrides):
    params = dict(
        base_url="https://example/elab",
        api_key="token",
        verify_ssl=False,
        timeout_seconds=1,
        page_size=2,
        max_pages=3,
        retry_attempts=2,
        retry_backoff_seconds=0,
    )
    params.update(elab_overrides)
    elab = ElabConfig(**params)
    llm = LLMConfig(backend="ollama")
    return AppConfig(elab=elab, llm=llm)


class ElabClientTests(unittest.TestCase):
    def test_initializes_authorization_header(self):
        config = _build_config()
        client = ElabClient(config)

        self.assertEqual(
            client._session.headers["Authorization"],  # type: ignore[attr-defined]
            config.elab.api_key,
        )

    def test_fetch_experiments_paginates(self):
        responses = [
            StubResponse([
                {"id": 1, "elabid": "a", "title": "t1", "body": "b1"},
                {"id": 2, "elabid": "b", "title": "t2", "body": "b2"},
            ]),
            StubResponse([
                {"id": 3, "elabid": "c", "title": "t3", "body": "b3"},
            ]),
        ]
        session = StubSession(get_responses=responses)
        config = _build_config()
        client = ElabClient(config)
        client._session = session  # type: ignore[attr-defined]

        experiments = client.fetch_experiments(["summarize"])

        self.assertEqual([exp.id for exp in experiments], [1, 2, 3])
        self.assertEqual(len(session.get_calls), 2)
        first_call_params = session.get_calls[0][1]
        # v2 共通の offset/limit ページング
        self.assertEqual(first_call_params["offset"], 0)
        self.assertEqual(first_call_params["limit"], config.elab.page_size)
        # 5.6.15 / 6.x で body・elabid を得るため full=1 が必須
        self.assertEqual(first_call_params["full"], 1)
        # タグは tags[] 配列形式
        self.assertEqual(first_call_params["tags[]"], ["summarize"])
        # 2 ページ目は offset が page_size 分進む
        second_call_params = session.get_calls[1][1]
        self.assertEqual(second_call_params["offset"], config.elab.page_size)

    def test_fetch_experiments_skips_malformed_entries(self):
        # page_size=2 に対し有効エントリ1件のみ返す（= 最終ページ）ようにして
        # ページング終端を明確にする。
        responses = [
            StubResponse([
                {"id": 1, "elabid": "a", "title": "t1", "body": "b1"},
                "not-a-dict",  # 非 dict → スキップ（len=2 だが有効は1件）
            ]),
            StubResponse([
                {"elabid": "no-id", "title": "missing id"},  # id 欠落 → スキップ
            ]),
        ]
        session = StubSession(get_responses=responses)
        config = _build_config(page_size=2, max_pages=3)
        client = ElabClient(config)
        client._session = session  # type: ignore[attr-defined]

        experiments = client.fetch_experiments(["summarize"])

        self.assertEqual([exp.id for exp in experiments], [1])

    def test_fetch_experiments_handles_null_body(self):
        # 5.6.15 等で body/elabid が null で返るケースでも空文字にフォールバック
        responses = [
            StubResponse([
                {"id": 5, "elabid": None, "title": None, "body": None},
            ]),
        ]
        session = StubSession(get_responses=responses)
        config = _build_config()
        client = ElabClient(config)
        client._session = session  # type: ignore[attr-defined]

        experiments = client.fetch_experiments(["summarize"])

        self.assertEqual(len(experiments), 1)
        self.assertEqual(experiments[0].elabid, "")
        self.assertEqual(experiments[0].title, "")
        self.assertEqual(experiments[0].body, "")

    def test_post_comment_retries(self):
        session = StubSession(
            post_responses=[StubResponse({}, status_code=500), StubResponse({}, status_code=200)]
        )
        config = _build_config(retry_attempts=2)
        client = ElabClient(config)
        client._session = session  # type: ignore[attr-defined]
        client._sleep = lambda _seconds: None  # type: ignore[attr-defined]

        client.post_comment(1, "hi")

        self.assertEqual(len(session.post_calls), 2)
        self.assertEqual(session.post_calls[0][1]["body"], "hi")


if __name__ == "__main__":
    unittest.main()
