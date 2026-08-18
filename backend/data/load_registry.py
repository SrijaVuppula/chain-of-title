"""
Loads backend/data/seed_registry.json into the Firestore `tool_registry` collection.

Usage:
    python load_registry.py

Requires GCP_PROJECT_ID set (see config.py) and Application Default Credentials
configured (`gcloud auth application-default login`).
"""
import json
import re
import sys
from pathlib import Path

# backend/data/ is one level below backend/, where config.py lives -- add it
# to the path explicitly so this works regardless of how the script is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
            "GCP_PROJECT_ID is not set. Finish GCP project setup and credentials first."
        )

    with open(REGISTRY_PATH) as f:
        data = json.load(f)

    db = firestore.Client(project=GCP_PROJECT_ID, database="chain-of-title-hackathon")
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

    # Sanity check: every entry must have a non-empty evidence field.
    missing_evidence = [t["name"] for t in data["tools"] if not t.get("evidence")]
    if missing_evidence:
        print(f"WARNING: these entries have no evidence field: {missing_evidence}")


if __name__ == "__main__":
    load_registry()
