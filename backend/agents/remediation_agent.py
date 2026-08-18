"""
Remediation Agent -- for any tool that Verification did not clear, writes a
hold record to Firestore that blocks the shot from being "delivery ready".

Trigger set: flagged, needs_review, discontinued, unknown (all statuses
except cleared). "unknown" is included deliberately -- an untracked tool is
at least as risky as one that's explicitly flagged, so it gets the same
hold treatment rather than being silently waved through.

Also fires a best-effort notification via the notify-hold Cloud Function and
looks up a cleared substitute tool in the same category, if one exists.
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


def _find_substitute(matched_name: Optional[str]) -> Optional[str]:
    """
    Given the matched registry name of a non-cleared tool, looks up its
    category and returns the name of a cleared tool in the same category,
    or None if no substitute exists (or matched_name is None, e.g. for
    'unknown' tools that have no registry entry to look up a category from).
    """
    if not matched_name:
        return None

    db = _get_db()
    entry_docs = list(
        db.collection("tool_registry")
        .where(filter=FieldFilter("name", "==", matched_name))
        .limit(1)
        .stream()
    )
    if not entry_docs:
        return None

    category = entry_docs[0].to_dict().get("category")
    if not category:
        return None

    substitute_docs = list(
        db.collection("tool_registry")
        .where(filter=FieldFilter("category", "==", category))
        .where(filter=FieldFilter("status", "==", "cleared"))
        .limit(1)
        .stream()
    )
    if not substitute_docs:
        return None

    return substitute_docs[0].to_dict().get("name")


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
    substitute = _find_substitute(verification_result.get("matched_name"))

    hold_data = {
        "manifest_id": manifest_id,
        "shot_id": shot_id,
        "tool_name": verification_result.get("matched_name") or tool_name,
        "status": status,
        "evidence": verification_result.get("evidence"),
        "suggested_substitute": substitute,
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
