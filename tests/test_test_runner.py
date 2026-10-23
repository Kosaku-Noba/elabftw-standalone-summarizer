import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path

from standalone_summarizer.test_runner import run_tests


class TestRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_environ = os.environ.copy()
        self.addCleanup(logging.shutdown)
        return super().setUp()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._original_environ)
        super().tearDown()

    def test_run_tests_logs_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tests_dir = root / "temp_tests"
            tests_dir.mkdir(parents=True)

            # Ensure the temporary directory is importable by unittest discover.
            sys.path.insert(0, str(root))
            self.addCleanup(lambda: sys.path.remove(str(root)))

            (tests_dir / "__init__.py").write_text("", encoding="utf-8")
            (tests_dir / "test_dummy.py").write_text(
                "import unittest\n\n"
                "class DummyTest(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertEqual(1, 1)\n\n"
                "if __name__ == '__main__':\n"
                "    unittest.main()\n",
                encoding="utf-8",
            )

            log_dir = root / "logs"

            os.environ["ELAB_BASE_URL"] = "https://example/api/v2"
            os.environ["ELAB_API_KEY"] = "dummy"
            os.environ["ELAB_VERIFY_SSL"] = "false"
            os.environ["LLM_BACKEND"] = "ollama"
            os.environ["LLM_ENDPOINT_URL"] = "http://127.0.0.1:11434"
            os.environ["LLM_MODEL_ID"] = "dummy-model"
            os.environ["LOG_DIR"] = str(log_dir)
            os.environ["TARGET_TAGS"] = "summarize"

            result = run_tests(
                tests_path=tests_dir,
                top_level_dir=root,
                verbosity=1,
            )

            self.assertTrue(result.wasSuccessful())

            log_file = log_dir / "standalone-summarizer.log"
            self.assertTrue(log_file.exists(), "Log file was not created.")
            contents = log_file.read_text(encoding="utf-8")
            self.assertIn("Tests run: 1", contents)


if __name__ == "__main__":
    unittest.main()
