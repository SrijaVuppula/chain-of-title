"""
Remediation Agent -- for any tool that Verification did not clear, writes a
hold record to Firestore that blocks the shot from being "delivery ready".

Trigger set: flagged, needs_review, discontinued, unknown (all statuses
except cleared). See remediation_agent_design.md for the full design notes
and the Aug 9 decision to include "unknown" in the trigger set.

Built Day 16. Notification trigger (Day 17) and substitute-tool suggestion
(Day 18) are intentionally deferred -- suggested_substitute is written as
None for now.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Optional
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import requests
import config

HOLD_STATUSES = {"flagged", "needs_review", "discontinued", "unknown"}


def _get_db():
    return firestore.Client(project=config.GCP_PROJECT_ID, database=config.FIRESTORE_DATABASE)


def write_hold(manifest_id: str, shot_id: str, tool_name: str, verification_result: dict) -> Optional[dict]:
    """
    Given a manifest/shot and the dict returned by verification_agent.verify_tool(),
    writes a hold record if the status isn't 'cleared'. Returns the hold record
    (with its new doc id under 'hold_id') if one was written, or None if the tool
    was cleared and no hold was needed.
    """
    status = verification_result.get("status")
    if status not in HOLD_STATUSES:
        return None

    db = _get_db()
    hold_data = {
        "manifest_id": manifest_id,
        "shot_id": shot_id,
        "tool_name": verification_result.get("matched_name") or tool_name,
        "status": status,
        "evidence": verification_result.get("evidence"),
        "suggested_substitute": None,
        "created_at": firestore.SERVER_TIMESTAMP,
        "resolved": False,
        "resolved_at": None,
    }
    _, doc_ref = db.collection("holds").add(hold_data)
    hold_data["hold_id"] = doc_ref.id

    _notify(hold_data)

    return hold_data


def _notify(hold_data: dict) -> None:
    """
    Fires the notify-hold Cloud Function (logs the hold event). Best-effort:
    a notification failure must never block or fail the hold write itself,
    so any error here is caught and logged locally, not raised.
    """
    try:
        requests.post(
            config.NOTIFY_HOLD_URL,
            json={
                "manifest_id": hold_data["manifest_id"],
                "shot_id": hold_data["shot_id"],
                "tool_name": hold_data["tool_name"],
                "status": hold_data["status"],
                "hold_id": hold_data["hold_id"],
            },
            timeout=5,
        )
    except requests.RequestException as e:
        print(f"[remediation_agent] notify_hold call failed (non-fatal): {e}")


def is_delivery_ready(manifest_id: str) -> bool:
    """
    A manifest is delivery ready only if it has zero unresolved holds.
    Computed on read (not cached) to avoid stale-flag bugs.
    """
    db = _get_db()
    unresolved = (
        db.collection("holds")
        .where(filter=FieldFilter("manifest_id", "==", manifest_id))
        .where(filter=FieldFilter("resolved", "==", False))
        .limit(1)
        .stream()
    )
    return next(unresolved, None) is None


if __name__ == "__main__":
    # Quick manual test against a fake verification result -- no real
    # manifest needed, just confirms the write path works.
    fake_result = {
        "matched_name": "MidJourney (image/video)",
        "status": "flagged",
        "evidence": "Test evidence -- active litigation re: training data.",
        "vendor": None,
        "match_confidence": 0.9,
    }
    hold = write_hold("test-manifest-001", "shot-01", "MidJourney-based tool", fake_result)
    print("Hold written:", hold)
    print("Delivery ready?", is_delivery_ready("test-manifest-001"))
