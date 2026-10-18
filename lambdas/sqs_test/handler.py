import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Processes an SQS batch. Messages with {"fail": true} fail on
    purpose so the retry -> DLQ path can be tested."""
    failures = []

    for record in event["Records"]:
        message_id = record["messageId"]
        try:
            body = json.loads(record["body"])
            if body.get("fail"):
                raise ValueError("forced failure for DLQ test")
            logger.info(json.dumps({"event": "processed", "message_id": message_id, "body": body}))
        except Exception:
            logger.exception(json.dumps({"event": "failed", "message_id": message_id}))
            failures.append({"itemIdentifier": message_id})

    # Only failed messages return to the queue; the rest are deleted
    return {"batchItemFailures": failures}
