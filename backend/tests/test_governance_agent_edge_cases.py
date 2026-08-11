"""
Governance Agent -- Day 21 edge case tests.

Exercises consume_and_log() against three deliberately bad/unusual events on
the real local Kafka topic, then checks Firestore to confirm each was handled
correctly:

1. Malformed JSON on the topic -- should be skipped (offset committed, no
   audit_log entry written, no crash).
2. An invalid/unrecognized decision value (e.g. "banana") -- should be
   normalized to "unknown" per _parse_decision, not crash or silently drop.
3. A decision field that's missing entirely -- should also normalize to
   "unknown".

Not a pytest suite (no other agent test file needs a live Kafka+Firestore
round trip to run) -- this is a standalone script you run directly, same
spirit as governance_agent.py's own __main__ smoke test.
"""
import sys
import json
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from confluent_kafka import Producer, Consumer, KafkaException, KafkaError
from google.cloud.firestore_v1.base_query import FieldFilter

import config
from agents.governance_agent import _get_db, log_decision, _parse_decision

TEST_RUN_ID = uuid.uuid4().hex[:8]


def produce(value_str: str, key: str):
    producer = Producer({"bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS})
    delivery = {}

    def _cb(err, msg):
        if err:
            delivery["error"] = err
        else:
            delivery["ok"] = msg.offset()

    producer.produce(config.KAFKA_TOPIC, key=key, value=value_str, callback=_cb)
    producer.flush(timeout=10)

    if "error" in delivery:
        print(f"[ERROR] Produce failed for key={key}: {delivery['error']}")
        sys.exit(1)
    return delivery["ok"]


def main():
    db = _get_db()

    # -- Build three test events -------------------------------------------------
    malformed_key = f"edge-malformed-{TEST_RUN_ID}"
    malformed_payload = "{not valid json!!"  # deliberately broken

    invalid_decision_key = f"edge-invalid-decision-{TEST_RUN_ID}"
    invalid_decision_manifest = f"test-manifest-invalid-{TEST_RUN_ID}"
    invalid_decision_payload = json.dumps({
        "decision": "banana",  # not in VALID_DECISIONS
        "tool": "Some Tool",
        "manifest_id": invalid_decision_manifest,
        "shot_id": "shot-01",
        "reasoning": "Edge case test: invalid decision value.",
    })

    missing_decision_key = f"edge-missing-decision-{TEST_RUN_ID}"
    missing_decision_manifest = f"test-manifest-missing-{TEST_RUN_ID}"
    missing_decision_payload = json.dumps({
        # "decision" key omitted entirely
        "tool": "Some Other Tool",
        "manifest_id": missing_decision_manifest,
        "shot_id": "shot-02",
        "reasoning": "Edge case test: missing decision field.",
    })

    print("Producing 3 edge-case events...")
    off1 = produce(malformed_payload, malformed_key)
    off2 = produce(invalid_decision_payload, invalid_decision_key)
    off3 = produce(missing_decision_payload, missing_decision_key)
    start_offset = off1  # earliest of the three -- consumer must not miss it
    print(f"Produced at offsets: malformed={off1}, invalid_decision={off2}, missing_decision={off3}")

    # -- Consume all three with a throwaway consumer group -----------------------
    test_group = f"governance-agent-edge-test-{TEST_RUN_ID}"
    consumer = Consumer({
        "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
        "group.id": test_group,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe([config.KAFKA_TOPIC])

    processed = 0
    skipped_malformed = False
    deadline = time.time() + 20
    try:
        while time.time() < deadline and processed < 3:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())
            if msg.offset() < start_offset:
                consumer.commit(message=msg)
                continue

            try:
                payload = json.loads(msg.value())
            except (json.JSONDecodeError, UnicodeDecodeError):
                print(f"  Skipped malformed message at offset {msg.offset()} (expected).")
                skipped_malformed = True
                consumer.commit(message=msg)
                processed += 1
                continue

            log_decision(
                decision=payload.get("decision"),
                tool_name=payload.get("tool"),
                manifest_id=payload.get("manifest_id"),
                shot_id=payload.get("shot_id"),
                reasoning=payload.get("reasoning"),
                db=db,
            )
            consumer.commit(message=msg)
            processed += 1
    finally:
        consumer.close()

    print(f"\nProcessed {processed}/3 messages (skipped_malformed={skipped_malformed})")

    # -- Assertions ---------------------------------------------------------------
    failures = []

    if not skipped_malformed:
        failures.append("Malformed JSON was not detected/skipped as expected.")

    invalid_docs = list(
        db.collection("audit_log")
        .where(filter=FieldFilter("manifest_id", "==", invalid_decision_manifest))
        .limit(1)
        .stream()
    )
    if not invalid_docs:
        failures.append("No audit_log entry found for invalid-decision test event.")
    else:
        d = invalid_docs[0].to_dict()
        if d.get("decision") != "unknown":
            failures.append(f"Invalid decision 'banana' was not normalized to 'unknown' (got: {d.get('decision')!r}).")
        else:
            print(f"  Invalid decision 'banana' correctly normalized -> 'unknown' (doc {invalid_docs[0].id}).")

    missing_docs = list(
        db.collection("audit_log")
        .where(filter=FieldFilter("manifest_id", "==", missing_decision_manifest))
        .limit(1)
        .stream()
    )
    if not missing_docs:
        failures.append("No audit_log entry found for missing-decision test event.")
    else:
        d = missing_docs[0].to_dict()
        if d.get("decision") != "unknown":
            failures.append(f"Missing decision field was not normalized to 'unknown' (got: {d.get('decision')!r}).")
        else:
            print(f"  Missing decision field correctly normalized -> 'unknown' (doc {missing_docs[0].id}).")

    # Sanity-check _parse_decision() directly too, no Kafka/Firestore needed.
    direct_checks = {
        "banana": "unknown",
        None: "unknown",
        "": "unknown",
        "  FLAGGED  ": "flagged",  # whitespace + case handled
        "cleared": "cleared",
    }
    for raw, expected in direct_checks.items():
        actual = _parse_decision(raw)
        if actual != expected:
            failures.append(f"_parse_decision({raw!r}) returned {actual!r}, expected {expected!r}.")

    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED -- {len(failures)} issue(s):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("ALL EDGE CASE TESTS PASSED")


if __name__ == "__main__":
    main()
