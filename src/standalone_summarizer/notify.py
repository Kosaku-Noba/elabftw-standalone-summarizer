"""Teams notification via Incoming Webhook (Adaptive Card)."""

from __future__ import annotations

import json
import logging
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)


def send_teams_notification(
    webhook_url: str,
    title: str,
    summary: str,
    experiment_url: str,
    tags: str = "",
) -> None:
    """Post an Adaptive Card to a Teams Incoming Webhook."""
    card = {
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.5",
                    "msteams": {"width": "Full"},
                    "body": [
                        {
                            "type": "TextBlock",
                            "size": "Large",
                            "weight": "Bolder",
                            "text": title,
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": f"tag: {tags}",
                            "wrap": True,
                            "isSubtle": True,
                        },
                        {
                            "type": "TextBlock",
                            "size": "Medium",
                            "weight": "Bolder",
                            "text": "AI 要約",
                            "spacing": "Medium",
                        },
                        {
                            "type": "TextBlock",
                            "text": summary,
                            "wrap": True,
                            "spacing": "Small",
                        },
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "eLabFTW で開く",
                            "url": experiment_url,
                        }
                    ],
                },
            }
        ]
    }
    resp = requests.post(
        webhook_url,
        data=json.dumps(card),
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    if resp.status_code >= 400:
        logger.warning("Teams notification failed: HTTP %s", resp.status_code)
    else:
        logger.info("Teams notification sent")


def resolve_webhook_urls(
    tag_map: Dict[str, str], experiment_tags: List[str],
) -> List[str]:
    """Return webhook URLs whose key tag appears in *experiment_tags*."""
    tag_set = set(experiment_tags)
    return [url for tag, url in tag_map.items() if tag in tag_set]
