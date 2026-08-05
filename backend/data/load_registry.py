"""
Loads backend/data/seed_registry.json into the Firestore `tool_registry` collection.
Implemented: BUILD_PLAN.md Day 4 (Aug 5)

Usage:
    python load_registry.py

Requires GCP_PROJECT_ID set (see config.py) and Application Default Credentials
configured (`gcloud auth application-default login`) -- this is a Day 2 prerequisite,
do that first if you haven't.
"""
import json
import re
from pathlib import Path

from google.cloud import firestore

from config import GCP_PROJECT_ID

REGISTRY_PATH = Path(__file__).parent / "seed_registry.json"


def slugify(name: str) -> str:
    """Turns a tool name into a stable, readable Firestore document ID."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug


def load_registry() -> None:
    if not GCP_PROJECT_ID:
        raise RuntimeError(
            "GCP_PROJECT_ID is not set. Finish Day 2 (GCP project + credentials) first."
        )

    with open(REGISTRY_PATH) as f:
        data = json.load(f)

    db = firestore.Client(project=GCP_PROJECT_ID)
    batch = db.batch()
    collection = db.collection("tool_registry")

    count = 0
    for tool in data["tools"]:
        doc_id = slugify(tool["name"])
        doc_ref = collection.document(doc_id)
        batch.set(doc_ref, tool)
        count += 1

    batch.commit()
    print(f"Loaded {count} tools into tool_registry.")

    # Sanity check: every entry must have non-empty evidence (CLAUDE.md convention)
    missing_evidence = [t["name"] for t in data["tools"] if not t.get("evidence")]
    if missing_evidence:
        print(f"WARNING: these entries have no evidence field: {missing_evidence}")


if __name__ == "__main__":
    load_registry()
