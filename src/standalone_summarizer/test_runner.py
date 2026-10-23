"""Utility CLI to execute the unit test suite and persist the results to logs."""

from __future__ import annotations

import argparse
import io
import logging
import sys
import unittest
from pathlib import Path

from standalone_summarizer.config import AppConfig
from standalone_summarizer.logging_utils import configure_logging

TEST_LOGGER_NAME = "standalone_summarizer.tests"


def run_tests(
    config: AppConfig | None = None,
    tests_path: str | Path = "tests",
    pattern: str = "test*.py",
    top_level_dir: str | Path | None = None,
    verbosity: int = 2,
) -> unittest.result.TestResult:
    """Discover and run tests, writing detailed output to the configured log file.

    Parameters
    ----------
    config:
        Optional prebuilt application config. When omitted, ``AppConfig.from_env`` is used.
    tests_path:
        Directory that contains the test modules to discover.
    pattern:
        Glob pattern used by ``unittest`` discovery. Defaults to ``test*.py``.
    top_level_dir:
        Optional top level directory for module imports. See :func:`unittest.loader.discover`.
    verbosity:
        Verbosity passed to :class:`unittest.TextTestRunner`.
    """

    if config is None:
        config = AppConfig.from_env()

    configure_logging(config)
    logger = logging.getLogger(TEST_LOGGER_NAME)

    tests_dir = Path(tests_path)
    if not tests_dir.exists():
        raise FileNotFoundError(f"Tests path not found: {tests_dir}")

    loader = unittest.defaultTestLoader
    suite = loader.discover(
        start_dir=str(tests_dir),
        pattern=pattern,
        top_level_dir=str(top_level_dir) if top_level_dir is not None else None,
    )

    buffer = io.StringIO()
    runner = unittest.TextTestRunner(stream=buffer, verbosity=verbosity)
    result = runner.run(suite)

    output = buffer.getvalue()
    if output:
        print(output.strip())
        logger.info("Test runner output:\n%s", output.strip())

    logger.info(
        "Tests run: %d | failures: %d | errors: %d | skipped: %d",
        result.testsRun,
        len(result.failures),
        len(result.errors),
        len(result.skipped),
    )

    # Log detailed failure and error information for easier debugging.
    for test, traceback in result.failures:
        logger.error("Failure in %s\n%s", test.id(), traceback)
    for test, traceback in result.errors:
        logger.error("Error in %s\n%s", test.id(), traceback)

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run unit tests and log the results.")
    parser.add_argument(
        "--tests-path",
        default="tests",
        help="Directory containing test modules (default: %(default)s)",
    )
    parser.add_argument(
        "--pattern",
        default="test*.py",
        help="Glob pattern for discovery (default: %(default)s)",
    )
    parser.add_argument(
        "--verbosity",
        type=int,
        default=2,
        help="Verbosity level for unittest runner (default: %(default)s)",
    )
    parser.add_argument(
        "--top-level-dir",
        default=None,
        help="Optional path to top level directory for imports.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    top_level_dir = args.top_level_dir if args.top_level_dir else None

    try:
        result = run_tests(
            tests_path=args.tests_path,
            pattern=args.pattern,
            top_level_dir=top_level_dir,
            verbosity=args.verbosity,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
