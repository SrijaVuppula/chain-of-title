"""
Governance Agent -- consumes decision events from a local Kafka topic
(Redpanda, localhost:9092) published by Verification/Remediation and
persists an immutable entry to the `audit_log` Firestore collection.

Built using IBM Bob as part of the development process, per the IBM
track's mandatory requirement.

Event schema expected on the wire (all fields optional except `decision`):
    {
        "decision":   "cleared" | "flagged" | "needs_review"
                      | "discontinued" | "unknown",
        "tool":       "<tool name>",
        "manifest_id": "<manifest id>",
        "shot_id":    "<shot id>",
        "reasoning":  "<evidence / reasoning text>",
        "agent":      "verification" | "remediation",  # which agent produced the decision
        "confidence": <float 0-1>,  # match_confidence from verification; omit for remediation-driven holds
        "timestamp":  <unix float>   # optional; server timestamp used if absent
    }
"""

import sys
import json
import logging
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.cloud import firestore
from confluent_kafka import Consumer, KafkaException, KafkaError

import config

logging.basicConfig(
    level=logging.INFO,
    format="[governance_agent] %(levelname)s %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)

VALID_DECISIONS = {"cleared", "flagged", "needs_review", "discontinued", "unknown"}

# Consumer group id is stable so that restarts resume from the last committed
# offset rather than replaying the entire topic.
_CONSUMER_GROUP = "governance-agent"


def _get_db() -> firestore.Client:
    return firestore.Client(
        project=config.GCP_PROJECT_ID,
        database=config.FIRESTORE_DATABASE,
    )


def _parse_decision(raw: Optional[str]) -> str:
    """Normalise and validate the decision field; fall back to 'unknown'."""
    if raw and raw.strip().lower() in VALID_DECISIONS:
        return raw.strip().lower()
    return "unknown"


def log_decision(
    decision: str,
    tool_name: Optional[str],
    manifest_id: Optional[str],
    shot_id: Optional[str],
    reasoning: Optional[str],
    db: Optional[firestore.Client] = None,
    agent: Optional[str] = None,
    confidence: Optional[float] = None,
) -> str:
    """
    Write a single audit_log entry to Firestore and return its document id.

    All fields are stored even when None so that the schema is uniform across
    every entry and Firestore queries on any field will work correctly.

    Args:
        decision:    One of cleared/flagged/needs_review/discontinued/unknown.
        tool_name:   The AI tool name extracted from the manifest.
        manifest_id: The manifest that was being evaluated.
        shot_id:     The individual shot within the manifest.
        reasoning:   Evidence text from the verification/remediation result.
        db:          Optional Firestore client (injected for testing; a fresh
                     client is created when None).
        agent:       "verification" or "remediation" — which agent produced
                     the decision. None if not provided by the event.
        confidence:  match_confidence (0-1) from the verification result.
                     None for remediation-driven holds that have no confidence.

    Returns:
        The Firestore document id of the newly written entry.
    """
    if db is None:
        db = _get_db()

    entry = {
        "timestamp": firestore.SERVER_TIMESTAMP,
        "decision": _parse_decision(decision),
        "tool_name": tool_name,
        "manifest_id": manifest_id,
        "shot_id": shot_id,
        "reasoning": reasoning,
        "agent": agent,
        "confidence": confidence,
    }

    _, doc_ref = db.collection("audit_log").add(entry)
    logger.info(
        "audit_log/%s  decision=%s  manifest=%s  shot=%s",
        doc_ref.id,
        entry["decision"],
        manifest_id,
        shot_id,
    )
    return doc_ref.id


def _build_consumer() -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": _CONSUMER_GROUP,
            # Resume from the last committed offset so that a restart does not
            # replay already-logged decisions.
            "auto.offset.reset": "earliest",
            # Commit offsets only after a successful Firestore write so that a
            # crash before the write leaves the event available for retry.
            "enable.auto.commit": False,
        }
    )


def consume_and_log(max_messages: Optional[int] = None) -> None:
    """
    Blocking loop: consumes decision events from ``config.KAFKA_TOPIC`` and
    calls :func:`log_decision` for each one.

    Args:
        max_messages: Stop after this many messages (useful for smoke tests).
                      ``None`` means run forever.
    """
    db = _get_db()
    consumer = _build_consumer()
    consumer.subscribe([config.KAFKA_TOPIC])

    logger.info(
        "Subscribed to %s on %s (group=%s)",
        config.KAFKA_TOPIC,
        config.KAFKA_BOOTSTRAP_SERVERS,
        _CONSUMER_GROUP,
    )

    processed = 0
    try:
        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                # No message within the poll window — keep waiting.
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # Reached end of partition; not an error, just keep polling.
                    continue
                raise KafkaException(msg.error())

            try:
                payload = json.loads(msg.value())
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                logger.warning("Skipping undecodable message (offset %s): %s", msg.offset(), exc)
                consumer.commit(message=msg)
                continue

            log_decision(
                decision=payload.get("decision"),
                tool_name=payload.get("tool"),
                manifest_id=payload.get("manifest_id"),
                shot_id=payload.get("shot_id"),
                reasoning=payload.get("reasoning"),
                db=db,
                agent=payload.get("agent"),
                confidence=payload.get("confidence"),
            )
            consumer.commit(message=msg)
            processed += 1

            if max_messages is not None and processed >= max_messages:
                logger.info("Reached max_messages=%d — stopping.", max_messages)
                break

    finally:
        consumer.close()


if __name__ == "__main__":
    import time
    import uuid

    # ---------------------------------------------------------------------------
    # Standalone smoke test: produce one synthetic decision event, then consume
    # it and verify the audit_log entry was written to Firestore.
    # ---------------------------------------------------------------------------
    from confluent_kafka import Producer

    TEST_MANIFEST = f"test-manifest-{uuid.uuid4().hex[:8]}"
    TEST_SHOT = "shot-01"
    TEST_TOOL = "Adobe Firefly"
    TEST_DECISION = "cleared"
    TEST_REASONING = "Standalone governance_agent test — not a real manifest."
    TEST_AGENT = "verification"
    TEST_CONFIDENCE = 1.0

    # -- Produce a synthetic event -----------------------------------------------
    producer = Producer({"bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS})
    event = {
        "decision": TEST_DECISION,
        "tool": TEST_TOOL,
        "manifest_id": TEST_MANIFEST,
        "shot_id": TEST_SHOT,
        "reasoning": TEST_REASONING,
        "agent": TEST_AGENT,
        "confidence": TEST_CONFIDENCE,
        "timestamp": time.time(),
    }
    delivery: dict = {}

    def _on_delivery(err, msg):
        if err:
            delivery["error"] = err
        else:
            delivery["ok"] = (msg.partition(), msg.offset())

    producer.produce(
        config.KAFKA_TOPIC,
        key=TEST_MANIFEST,
        value=json.dumps(event),
        callback=_on_delivery,
    )
    producer.flush(timeout=10)

    if "error" in delivery:
        print(f"[ERROR] Produce failed: {delivery['error']}")
        sys.exit(1)

    p, o = delivery["ok"]
    print(f"Produced test event -> partition {p}, offset {o}")

    # -- Consume that one event and write to Firestore ---------------------------
    # Use a throwaway group id so auto.offset.reset="earliest" takes effect and
    # this run is guaranteed to see the message just produced above, regardless
    # of any prior committed offsets from the stable "governance-agent" group.
    print(f"Consuming from {config.KAFKA_TOPIC} (will stop after 1 message)…")
    _test_group = f"governance-agent-test-{uuid.uuid4().hex[:8]}"
    db = _get_db()
    consumer = Consumer(
        {
            "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": _test_group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([config.KAFKA_TOPIC])
    found_offset = delivery["ok"][1]  # partition offset of the event we produced
    processed = 0
    try:
        import time as _time
        deadline = _time.time() + 20
        while _time.time() < deadline and processed < 1:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                from confluent_kafka import KafkaError as _KE
                if msg.error().code() == _KE._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())
            # Skip any messages that came before the one we just produced.
            if msg.offset() < found_offset:
                consumer.commit(message=msg)
                continue
            try:
                payload = json.loads(msg.value())
            except (json.JSONDecodeError, UnicodeDecodeError):
                consumer.commit(message=msg)
                continue
            log_decision(
                decision=payload.get("decision"),
                tool_name=payload.get("tool"),
                manifest_id=payload.get("manifest_id"),
                shot_id=payload.get("shot_id"),
                reasoning=payload.get("reasoning"),
                db=db,
                agent=payload.get("agent"),
                confidence=payload.get("confidence"),
            )
            consumer.commit(message=msg)
            processed += 1
    finally:
        consumer.close()

    if processed == 0:
        print("[ERROR] Consumer timed out — no matching message received.")
        sys.exit(1)

    # -- Verify the entry landed in Firestore ------------------------------------
    from google.cloud.firestore_v1.base_query import FieldFilter
    results = list(
        db.collection("audit_log")
        .where(filter=FieldFilter("manifest_id", "==", TEST_MANIFEST))
        .limit(1)
        .stream()
    )

    if results:
        doc = results[0].to_dict()
        print("\naudit_log entry written successfully:")
        for k, v in doc.items():
            print(f"  {k}: {v}")
    else:
        print("[ERROR] No audit_log entry found — something went wrong.")
        sys.exit(1)
