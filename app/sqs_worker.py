"""
SQS worker for AI task messages.

This worker polls AWS SQS and handles AI task events. It currently only logs
the identifiers needed for RECIPE_AI_REVIEW_REQUESTED messages.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError


MESSAGE_TYPE_RECIPE_AI_REVIEW_REQUESTED = "RECIPE_AI_REVIEW_REQUESTED"
POLL_WAIT_SECONDS = 20
MAX_MESSAGES = 10
IDLE_SLEEP_SECONDS = 1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value


def create_sqs_client(region: str):
    return boto3.client("sqs", region_name=region)


def parse_message_body(message: dict[str, Any]) -> dict[str, Any]:
    body = message.get("Body")
    if not isinstance(body, str):
        raise ValueError("SQS message Body must be a JSON string")

    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError("SQS message Body JSON must be an object")

    return parsed


def handle_message(message: dict[str, Any]) -> None:
    payload = parse_message_body(message)
    message_type = payload.get("type")

    if message_type == MESSAGE_TYPE_RECIPE_AI_REVIEW_REQUESTED:
        recipe_id = payload.get("recipeId")
        user_id = payload.get("userId")
        logger.info(
            "Received recipe AI review request: recipeId=%s userId=%s",
            recipe_id,
            user_id,
        )
        return

    logger.info("Ignored unsupported SQS message type: %s", message_type)


def delete_message(sqs_client, queue_url: str, message: dict[str, Any]) -> None:
    receipt_handle = message.get("ReceiptHandle")
    if not receipt_handle:
        raise ValueError("SQS message is missing ReceiptHandle")

    sqs_client.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle,
    )


def poll_messages(sqs_client, queue_url: str) -> list[dict[str, Any]]:
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=MAX_MESSAGES,
        WaitTimeSeconds=POLL_WAIT_SECONDS,
    )
    return response.get("Messages", [])


def run_worker() -> None:
    region = get_required_env("AWS_REGION")
    queue_url = get_required_env("AWS_SQS_AI_TASK_QUEUE_URL")
    sqs_client = create_sqs_client(region)

    logger.info("SQS worker started")

    while True:
        try:
            messages = poll_messages(sqs_client, queue_url)
        except (BotoCoreError, ClientError):
            logger.exception("Failed to receive SQS messages")
            time.sleep(IDLE_SLEEP_SECONDS)
            continue

        if not messages:
            continue

        for message in messages:
            message_id = message.get("MessageId")
            try:
                handle_message(message)
                delete_message(sqs_client, queue_url, message)
                logger.info("Deleted processed SQS message: messageId=%s", message_id)
            except json.JSONDecodeError:
                logger.exception(
                    "Failed to parse SQS message body: messageId=%s",
                    message_id,
                )
            except Exception:
                logger.exception(
                    "Failed to process SQS message: messageId=%s",
                    message_id,
                )


if __name__ == "__main__":
    try:
        run_worker()
    except KeyboardInterrupt:
        logger.info("SQS worker stopped")
