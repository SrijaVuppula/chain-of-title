"""
Director -- orchestrator for the Chain of Title pipeline.

Takes a manifest_id, fetches the manifest from Firestore, and for each shot:
  1. Verification Agent checks the tool against the registry.
  2. Remediation Agent writes a hold (+ notification + substitute suggestion)
     for anything not cleared.
  3. A decision event is published to Kafka for the Governance Agent to
     consume and log to audit_log (async -- see remediation_agent_design.md
     "Update -- Aug 10 (Day 20)" for why this is Director's job, not
     Verification's or Remediation's).

Aggregates a final verdict per manifest:
  - Greenlit:     every shot cleared.
  - Needs-Review: no hard holds, but at least one shot is needs_review.
  - Held:         at least one shot is flagged / discontinued / unknown.

Built on Google Agent Builder / Gemini. See CLAUDE.md for architecture.
Scaffolded Day 8, real orchestration logic built Day 22.
"""
import sys
import json
import logging
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.cloud import firestore
from confluent_kafka import Producer

import config
from agents.verification_agent import verify_tool
from agents.remediation_agent import write_hold

logging.basicConfig(
    level=logging.INFO,
    format="[director] %(levelname)s %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)

# Statuses that force a hard "Held" verdict for the whole manifest.
HARD_HOLD_STATUSES = {"flagged", "discontinued", "unknown"}
# Statuses that only soften the verdict to "Needs-Review" if nothing harder exists.
SOFT_HOLD_STATUSES = {"needs_review"}

_producer: Optional[Producer] = None


def _get_db() -> firestore.Client:
    return firestore.Client(
        project=config.GCP_PROJECT_ID,
        database=config.FIRESTORE_DATABASE,
    )


def _get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({"bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS})
    return _producer


def _publish_decision(event: dict) -> None:
    """
    Best-effort publish of a decision event to Kafka for the Governance Agent
    to pick up. A publish failure must never break the pipeline -- caught and
    logged, not raised. (Same non-fatal pattern as remediation_agent._notify.)
    """
    try:
        producer = _get_producer()
        producer.produce(
            config.KAFKA_TOPIC,
            key=event.get("manifest_id"),
            value=json.dumps(event),
        )
        producer.flush(timeout=5)
    except Exception as e:
        logger.warning("Kafka publish failed (non-fatal): %s", e)


def _aggregate_verdict(shot_statuses: list) -> str:
    if any(s in HARD_HOLD_STATUSES for s in shot_statuses):
        return "Held"
    if any(s in SOFT_HOLD_STATUSES for s in shot_statuses):
        return "Needs-Review"
    return "Greenlit"


def run_pipeline(manifest_id: str) -> dict:
    """
    Entry point: fetches the manifest by id, runs every shot through
    Verification -> Remediation (if needed) -> Kafka publish for Governance,
    and returns an aggregated verdict.

    Raises:
        ValueError: if no manifest with this id exists.
    """
    db = _get_db()
    manifest_doc = db.collection("manifests").document(manifest_id).get()
    if not manifest_doc.exists:
        raise ValueError(f"Manifest '{manifest_id}' not found.")

    manifest = manifest_doc.to_dict()
    shots = manifest.get("shots", [])

    shot_results = []
    statuses = []

    for shot in shots:
        shot_id = shot.get("shot_id")
        tool_name = shot.get("ai_tool")

        verification_result = verify_tool(tool_name)
        status = verification_result["status"]
        statuses.append(status)

        hold = None
        if status != "cleared":
            hold = write_hold(manifest_id, shot_id, tool_name, verification_result)

        _publish_decision({
            "decision": status,
            "tool": verification_result.get("matched_name") or tool_name,
            "manifest_id": manifest_id,
            "shot_id": shot_id,
            "reasoning": verification_result.get("evidence"),
            "agent": "verification",
            "confidence": verification_result.get("match_confidence"),
        })

        shot_results.append({
            "shot_id": shot_id,
            "tool_name": tool_name,
            "status": status,
            "evidence": verification_result.get("evidence"),
            "hold_id": hold["hold_id"] if hold else None,
            "suggested_substitute": hold["suggested_substitute"] if hold else None,
        })

        logger.info("shot=%s tool=%s status=%s", shot_id, tool_name, status)

    verdict = _aggregate_verdict(statuses)

    db.collection("manifests").document(manifest_id).update({"status": "processed"})

    result = {
        "manifest_id": manifest_id,
        "verdict": verdict,
        "shots": shot_results,
    }
    logger.info("Pipeline complete for manifest=%s verdict=%s", manifest_id, verdict)
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python director.py <manifest_id>")
        print("(Submit a manifest via POST /submit-manifest first to get an id.)")
        sys.exit(1)

    result = run_pipeline(sys.argv[1])
    print(json.dumps(result, indent=2))
