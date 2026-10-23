"""Entry point for the standalone summarizer worker."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Iterable, Sequence

from standalone_summarizer.client import ElabClient, Experiment
from standalone_summarizer.config import AppConfig
from standalone_summarizer.logging_utils import configure_logging
from standalone_summarizer.pipeline import SummarizationPipeline
from standalone_summarizer.state import ProcessedEntry, StateStore
from standalone_summarizer.summarizer import create_backend

logger = logging.getLogger(__name__)


def run_once(config: AppConfig, dry_run: bool = False, limit: int | None = None) -> None:
    configure_logging(config)
    client = ElabClient(config)
    backend = create_backend(config.llm)

    try:
        backend.load()
    except NotImplementedError:
        logger.error("Backend load not implemented", extra={"backend": config.llm.backend})
        return
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to load LLM backend")
        return

    state = StateStore()
    pipeline = SummarizationPipeline(config, backend)

    experiments = client.fetch_experiments(config.tags)
    logger.info("Fetched %d experiments", len(experiments))

    processed_count = 0

    for experiment in _limit(experiments, limit):
        entry = ProcessedEntry(
            experiment_id=experiment.id,
            elabid=experiment.elabid,
            body_hash=StateStore.compute_body_hash(experiment.body),
        )
        if not state.has_changed(entry):
            logger.debug("Skipping unchanged experiment", extra={"id": experiment.id})
            continue

        try:
            response = pipeline.summarize_experiment(experiment)
        except NotImplementedError:
            logger.error(
                "Summarizer backend not implemented yet",
                extra={"backend": config.llm.backend},
            )
            return
        except Exception:  # pragma: no cover - placeholder
            logger.exception("Summarization failed", extra={"experiment_id": experiment.id})
            continue

        if response is None:
            logger.info("No summary generated", extra={"experiment_id": experiment.id})
            continue

        logger.info(
            "Summary generated",
            extra={
                "experiment_id": experiment.id,
                "tokens_in": response.tokens_in,
                "tokens_out": response.tokens_out,
                "model": response.model,
            },
        )
        logger.info(
            "Summary preview for experiment %s:\n%s",
            experiment.id,
            response.summary.strip(),
        )

        if dry_run:
            logger.info("Dry-run: skipping comment post", extra={"experiment_id": experiment.id})
        else:
            try:
                client.post_comment(experiment.id, response.summary)
            except Exception:  # pragma: no cover - placeholder
                logger.exception("Failed to post comment", extra={"experiment_id": experiment.id})
                continue

            # Teams notification
            if config.teams_tag_map:
                from standalone_summarizer.notify import resolve_webhook_urls, send_teams_notification

                exp_tags = [t.strip() for t in config.tags]
                urls = resolve_webhook_urls(config.teams_tag_map, exp_tags)
                exp_url = config.elab.base_url.replace("/api/v2", "") + f"/experiments.php?mode=view&id={experiment.id}"
                for url in urls:
                    try:
                        send_teams_notification(
                            webhook_url=url,
                            title=experiment.title,
                            summary=response.summary,
                            experiment_url=exp_url,
                            tags=", ".join(exp_tags),
                        )
                    except Exception:
                        logger.exception("Teams notification failed", extra={"experiment_id": experiment.id})

        state.mark_processed(
            entry,
            metadata={
                "model": response.model,
                "tokens_in": str(response.tokens_in),
                "tokens_out": str(response.tokens_out),
            },
        )
        processed_count += 1

    logger.info("Completed run", extra={"processed": processed_count})


def _limit(items: Iterable[Experiment], limit: int | None) -> Iterable[Experiment]:
    if limit is None:
        yield from items
        return
    for idx, item in enumerate(items):
        if idx >= limit:
            break
        yield item


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone summarizer worker")
    parser.add_argument("--dry-run", action="store_true", help="Do not post comments")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most N experiments per run",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = AppConfig.from_env()
    if not config.elab.api_key:
        logger.error("ELAB_API_KEY is not set")
        return 1

    run_once(config=config, dry_run=args.dry_run, limit=args.limit)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
