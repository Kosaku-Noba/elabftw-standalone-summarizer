"""Mock summarizer backend for testing."""
import logging
from standalone_summarizer.config import LLMConfig
from standalone_summarizer.summarizer.base import SummarizeRequest, SummarizeResponse, SummarizerBackend

logger = logging.getLogger(__name__)

class MockBackend(SummarizerBackend):
    def __init__(self, config: LLMConfig) -> None:
        self._config = config
    
    @property
    def model_identifier(self) -> str:
        return "mock-model"
    
    def summarize(self, request: SummarizeRequest) -> SummarizeResponse:
        logger.info("Mock backend called")
        summary = f"【要約】\n目的: 実験の目的を記載\n方法: 実験手法の概要\n結果: 得られた結果\n\n(元テキスト: {len(request.prompt)}文字)"
        return SummarizeResponse(summary=summary, tokens_in=len(request.prompt)//4, tokens_out=len(summary)//4, model="mock")
