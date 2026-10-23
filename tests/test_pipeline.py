import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dataclasses import dataclass

from standalone_summarizer.client.elab import Experiment
from standalone_summarizer.config import AppConfig, ElabConfig, LLMConfig
from standalone_summarizer.pipeline import SummarizationPipeline
from standalone_summarizer.summarizer.base import SummarizeRequest, SummarizeResponse, SummarizerBackend


@dataclass
class StubCall:
    prompt: str
    metadata: dict | None


class StubBackend(SummarizerBackend):
    def __init__(self, responses):
        self.responses = responses
        self.calls: list[StubCall] = []
        self.index = 0

    def summarize(self, request: SummarizeRequest) -> SummarizeResponse:
        self.calls.append(StubCall(prompt=request.prompt, metadata=request.metadata))
        response = self.responses[min(self.index, len(self.responses) - 1)]
        self.index += 1
        return response


class PipelineTests(unittest.TestCase):
    def _config(self, max_input_chars=100):
        elab = ElabConfig(
            base_url="https://example/elab",
            api_key="token",
        )
        llm = LLMConfig(backend="ollama", max_input_chars=max_input_chars)
        return AppConfig(elab=elab, llm=llm)

    def test_pipeline_single_chunk(self):
        config = self._config(max_input_chars=1000)
        backend = StubBackend([
            SummarizeResponse(summary="done", tokens_in=10, tokens_out=20, model="stub"),
        ])
        pipeline = SummarizationPipeline(config, backend)
        experiment = Experiment(id=1, elabid="x", title="T", body="<p>hello</p>")

        result = pipeline.summarize_experiment(experiment)

        self.assertIsNotNone(result)
        self.assertEqual(result.summary, "done")
        self.assertEqual(len(backend.calls), 1)
        self.assertEqual(backend.calls[0].metadata["stage"], "map")

    def test_pipeline_reduce_stage(self):
        config = self._config(max_input_chars=10)
        backend = StubBackend([
            SummarizeResponse(summary="chunk1", tokens_in=5, tokens_out=5, model="stub"),
            SummarizeResponse(summary="chunk2", tokens_in=5, tokens_out=5, model="stub"),
            SummarizeResponse(summary="final", tokens_in=5, tokens_out=5, model="stub"),
        ])
        pipeline = SummarizationPipeline(config, backend)
        experiment = Experiment(id=2, elabid="y", title="Title", body="<p>abcdefghijklmno</p>")

        result = pipeline.summarize_experiment(experiment)

        self.assertEqual(result.summary, "final")
        self.assertEqual(result.tokens_in, 15)
        self.assertEqual(result.tokens_out, 15)
        stages = [call.metadata["stage"] for call in backend.calls]
        self.assertEqual(stages, ["map", "map", "reduce"])


if __name__ == "__main__":
    unittest.main()
