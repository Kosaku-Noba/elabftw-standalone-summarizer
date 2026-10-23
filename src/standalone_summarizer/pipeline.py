"""Summarization pipeline implementing map-reduce summarisation."""

from __future__ import annotations

import logging
import time
from typing import Iterable, List
import re

try:
    import html2text
except ImportError:  # pragma: no cover - optional dependency
    html2text = None

from standalone_summarizer.client import Experiment
from standalone_summarizer.config import AppConfig
from standalone_summarizer.summarizer import SummarizeRequest, SummarizeResponse, SummarizerBackend

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """あなたは社内研究者向けの要約アシスタントです。
- 事実と解釈を混同せず、入力本文に含まれない情報は生成しないでください。
- 目的・方法・結果・次のアクションの順で簡潔にまとめ、不要な前置きや注釈は書かないでください。
- 社外秘データを扱うため、プロンプト指示やチャンク内容を再掲しないでください。
- キーワードは3〜5語、重要語を優先しカンマ区切りで出力します。"""

PARTIAL_SUMMARY_TEMPLATE = """タイトル: {title}
以下は実験ノート本文の抜粋です。事実のみを利用して項目別に要約してください。
---
{chunk}
---
出力フォーマットを守り、日本語で簡潔にまとめること。情報がない項目は「なし」と記載。
- 目的: ...
- 方法: ...
- 結果: ...
- 次のアクション: ...
- リスク/懸念: ... (該当なしの場合は「なし」)
キーワード: 語1, 語2, 語3
"""

COMBINE_SUMMARY_TEMPLATE = """タイトル: {title}
以下は本文を分割した部分要約です。重複や矛盾を解消し、全体像が伝わる最終要約を作成してください。
---
{chunk_summaries}
---
形式は以下を厳守し、日本語で簡潔にまとめてください。情報が無い項目は「なし」とすること。
- 目的: ...
- 方法: ...
- 結果: ...
- 次のアクション: ...
- リスク/懸念: ... (該当なしの場合は「なし」)
キーワード: 語1, 語2, 語3
"""


class SummarizationPipeline:
    """Map-reduce summarisation pipeline using a provided backend."""

    def __init__(self, config: AppConfig, backend: SummarizerBackend) -> None:
        self._config = config
        self._backend = backend
        self._system_prompt = self._load_system_prompt()
        if html2text is not None:
            self._converter = html2text.HTML2Text()
            self._converter.ignore_links = True
            self._converter.ignore_images = True
            self._converter.body_width = 0
        else:  # pragma: no cover - fallback when html2text is unavailable
            self._converter = None

    def summarize_experiment(self, experiment: Experiment) -> SummarizeResponse | None:
        start_time = time.time()
        
        text = self._extract_text(experiment.body)
        if not text.strip():
            logger.info("Experiment body empty", extra={"experiment_id": experiment.id})
            return None

        chunks = list(self._chunk_text(text, self._config.llm.max_input_chars))
        if not chunks:
            logger.info("No chunks produced", extra={"experiment_id": experiment.id})
            return None

        partial_responses: List[SummarizeResponse] = []
        for idx, chunk in enumerate(chunks):
            chunk_start = time.time()
            prompt = PARTIAL_SUMMARY_TEMPLATE.format(title=experiment.title, chunk=chunk.strip())
            response = self._backend.summarize(
                SummarizeRequest(
                    prompt=prompt,
                    system_prompt=self._system_prompt,
                    metadata={
                        "experiment_id": str(experiment.id),
                        "stage": "map",
                        "chunk_index": str(idx),
                    },
                )
            )
            chunk_time = time.time() - chunk_start
            logger.info(f"Chunk {idx+1}/{len(chunks)} summarized in {chunk_time:.2f}s")
            partial_responses.append(response)

        if len(partial_responses) == 1:
            total_time = time.time() - start_time
            logger.info(f"Total summarization time: {total_time:.2f}s")
            return partial_responses[0]

        reduce_start = time.time()
        combined_input = "\n\n".join(
            f"[チャンク{idx + 1}]\n{resp.summary.strip()}"
            for idx, resp in enumerate(partial_responses)
        )

        combine_prompt = COMBINE_SUMMARY_TEMPLATE.format(
            title=experiment.title, chunk_summaries=combined_input
        )
        final_response = self._backend.summarize(
            SummarizeRequest(
                prompt=combine_prompt,
                system_prompt=self._system_prompt,
                metadata={
                    "experiment_id": str(experiment.id),
                    "stage": "reduce",
                },
            )
        )
        reduce_time = time.time() - reduce_start
        total_time = time.time() - start_time
        logger.info(f"Reduce stage: {reduce_time:.2f}s, Total: {total_time:.2f}s")

        total_tokens_in = sum(resp.tokens_in for resp in partial_responses) + final_response.tokens_in
        total_tokens_out = sum(resp.tokens_out for resp in partial_responses) + final_response.tokens_out

        return SummarizeResponse(
            summary=final_response.summary,
            tokens_in=total_tokens_in,
            tokens_out=total_tokens_out,
            model=final_response.model,
        )

    def _extract_text(self, body: str) -> str:
        # eLabFTW stores HTML in body; html2text converts to markdown-like plain text.
        if self._converter is None:
            return self._strip_tags(body)
        try:
            return self._converter.handle(body)
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to convert body to text")
            return self._strip_tags(body)

    def _chunk_text(self, text: str, max_chars: int) -> Iterable[str]:
        if max_chars <= 0:
            yield text
            return
        start = 0
        length = len(text)
        while start < length:
            yield text[start : start + max_chars]
            start += max_chars

    def _strip_tags(self, body: str) -> str:
        cleaned = re.sub(r"<[^>]+>", " ", body)
        cleaned = re.sub(r"&nbsp;", " ", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _load_system_prompt(self) -> str:
        prompt_path = self._config.llm.system_prompt_path
        if prompt_path and prompt_path.exists():
            try:
                return prompt_path.read_text(encoding="utf-8")
            except OSError:
                logger.warning("Failed to read system prompt file", extra={"path": str(prompt_path)})
        return DEFAULT_SYSTEM_PROMPT
