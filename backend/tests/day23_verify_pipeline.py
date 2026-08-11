"""
Day 23 -- full pipeline verification.

1. Drains the standing 'governance-agent' consumer group forward through any
   backlog until the topic goes idle (no new message for 5s), so today's real
   Director-published events (manifest DDLflmqtThR9b1HM9EPr) actually get
   consumed into audit_log, not left stuck behind old Day 20/21 test messages.
   (Doesn't use governance_agent.consume_and_log(max_messages=N) directly --
   that function blocks forever once N isn't reached and the topic runs dry,
   which would hang this script. Same consumer settings, just with an idle
   cutoff instead of a fixed message count.)
2. Confirms audit_log now has an entry for each of the 3 real shots.
3. Confirms the manifest's Firestore status flipped to "processed".
4. Confirms is_delivery_ready() correctly returns False (shots 34/51 are held).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from confluent_kafka import Consumer, KafkaException, KafkaError
from google.cloud.firestore_v1.base_query import FieldFilter

import config
from agents.governance_agent import log_decision, _get_db, _CONSUMER_GROUP
from agents.remediation_agent import is_delivery_ready
import json as _json

MANIFEST_ID = "DDLflmqtThR9b1HM9EPr"

print(f"Draining '{_CONSUMER_GROUP}' consumer group forward until idle...")
db = _get_db()
consumer = Consumer({
    "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
    "group.id": _CONSUMER_GROUP,  # the real, standing group -- not a throwaway
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
})
consumer.subscribe([config.KAFKA_TOPIC])

processed = 0
last_message_time = time.time()
IDLE_CUTOFF = 5.0

try:
    while time.time() - last_message_time < IDLE_CUTOFF:
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            raise KafkaException(msg.error())

        last_message_time = time.time()
        try:
            payload = _json.loads(msg.value())
        except (_json.JSONDecodeError, UnicodeDecodeError):
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

print(f"Drained {processed} message(s).\n")

# -- Confirm audit_log has entries for our 3 real shots ----------------------
print(f"Checking audit_log for manifest={MANIFEST_ID}...")
docs = list(
    db.collection("audit_log")
    .where(filter=FieldFilter("manifest_id", "==", MANIFEST_ID))
    .stream()
)
print(f"Found {len(docs)} audit_log entr{'y' if len(docs) == 1 else 'ies'}:")
for d in docs:
    entry = d.to_dict()
    print(f"  shot={entry.get('shot_id')} decision={entry.get('decision')} agent={entry.get('agent')}")

expected_shots = {"12", "34", "51"}
found_shots = {d.to_dict().get("shot_id") for d in docs}
if expected_shots.issubset(found_shots):
    print("  -> All 3 shots present in audit_log. PASS")
else:
    print(f"  -> MISSING shots: {expected_shots - found_shots}. FAIL")

# -- Confirm manifest status flipped to "processed" ---------------------------
manifest_doc = db.collection("manifests").document(MANIFEST_ID).get()
status = manifest_doc.to_dict().get("status") if manifest_doc.exists else None
print(f"\nManifest status: {status!r} -> {'PASS' if status == 'processed' else 'FAIL'}")

# -- Confirm delivery-ready gate is correctly False ---------------------------
ready = is_delivery_ready(MANIFEST_ID)
print(f"is_delivery_ready: {ready} -> {'PASS (correctly held)' if ready is False else 'FAIL'}")
